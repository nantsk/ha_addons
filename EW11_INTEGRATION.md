# EW11 - 삼성 스마트월패드 연동 작업 기록

* 작업일: 2026-09-05
* 대상: 부평브라운스톤 아파트 / 월패드 **SHP-W810BM** (지그방(직방, 구 삼성SDS) **스마트 월패드** - 신형 무선 IoT 월패드)
* 결론: **RS485 로컬 제어는 불가능** (관리망/검침선 확인). 상태는 HA 대시보드 등 향후 참조용

## 1. 시스템 구성

```
[월패드 SHP-W810BM] --RS485--> [EW11 (192.168.0.93:8899)] --WiFi/TCP--> [docker samsung-wallpad] --MQTT--> [mosquitto] <-- [Home Assistant]
```

* docker-compose (~/smarthome/docker-compose.yml) 3개 서비스
  * homeassistant: host network, ./config 마운트
  * mosquitto: host network, 1883, allow_anonymous
  * samsung-wallpad: python:3.11-slim, `sds_wallpad/` 마운트 후 `run_standalone.sh` 실행
* HA MQTT 통합: 127.0.0.1:1883 등록 완료

## 2. EW11 설정 (완료)

* 웹 UI: `http://192.168.0.93` (admin/admin)
* SOCKET: TCP-SERVER, LocalPort 8899, 라우팅 uart (기본값 유지)
* UART: **9600 / 8 / EVEN / 1** 로 수정 (출고값 Parity=NONE → 삼성 SDS 표준인 EVEN으로 변경)
  * 설정 직후에는 라인에 적용되지 않으므로 **재시작(CID 20003) 필요**

### EW11 설정 API (curl 예시)

설정 조회/변경은 POST `/cmd` 로 수행한다.

```bash
# UART 설정 조회 (소문자 xxx 아님! 대문자 "UART"/"SOCK" 사용)
curl -u admin:admin -X POST -H "Content-Type: application/json; charset=utf-8" \
  -d 'msg={"CID":10003,"PL":["UART"]}' http://192.168.0.93/cmd

# UART 설정 변경 (전체 필드 전송 필요)
curl -u admin:admin -X POST -H "Content-Type: application/json; charset=utf-8" \
  -d 'msg={"CID":10005,"PL":{"UART":{"Baudrate":9600,"Databits":8,"Stopbits":1,"Parity":"EVEN","BufSize":512,"GapTime":50,"FlowCtrl":2,"SoftwareFlowCtrl":0,"Xon":"11","Xoff":"13","CliGetIn":"Serial-String","SerailString":"+++","CliWaitTime":300,"UartProto":"NONE","FrameLen":16,"FrameTime":100,"TagEnable":0,"TagHead":"00","TagTail":"00"}}}' \
  http://192.168.0.93/cmd

# 재시작
curl -u admin:admin -X POST -d 'msg={"CID":20003}' http://192.168.0.93/cmd

# UART 수신/에러 카운터 조회 (신호 품질 판정에 유용)
curl -u admin:admin -X POST -d 'msg={"CID":10001,"PL":["UART"]}' http://192.168.0.93/cmd
# => {"UART":{"Config":"9600,8,1,EVEN","RecvBytes":..,"RecvFrames":..,"FailedBytes":0,"FailedFrames":0}}
```

CID 코드: 10001=상태조회, 10003=설정조회, 10005=설정저장, 20003=재시작

## 3. 패킷 분석 경위 및 결과 (중요)

### 3.1 초기 증상

* sds_wallpad 애드온이 프로토콜 자동감지에 실패 (`check loop count fail: A1→AB→A5→AC...` 반복)
* EW11 TCP 연결, MQTT 연결은 정상

### 3.2 배제한 원인 (모두 테스트 완료)

| 가설 | 검증 방법 | 결과 |
|---|---|---|
| 패리티 불일치 | EW11 NONE→EVEN 변경+재시작 | 데이터 패턴 변화 없음 |
| 보레이트 불일치 | 1200/2400/4800/9600/19200/38400 전수 테스트 | 38400에서 4배 오버샘플 패턴 확인 → 전송기는 9600 |
| 프레이밍 불일치 | 9600에서 7/8비트 × N/E/O × 1/2스톱 12조합 | 모두 SDS 체크섬 부적중 (랜덤 수준) |
| A/B 라인 반전 | 비트 단위 극성/페이즈 분석 | 반전 흔적 없음 |
| 신호 불량 | EW11 FailedFrames 카운터 | **0** — 신호는 완벽히 클린 |

### 3.3 관측된 버스 트래픽 구조

* **485ms 주기 상태 방송** (~65B): 헤드 `2f 69 24 ad df dc 42 f3 ...` + 5-phase 롤링 카운터 + 가변 영역 + 테일 `...3e 4d 69 7f 74`
* **주기 폴링 2종**: ~50초 / ~60초 간격 (검침/미터 폴링으로 추정)
* **상태 플래그**: 방송 내 `ac 82` 다음 2바이트가 `e374`(off) ↔ `a3f8`(on)으로 전환
  * 실험에서 레인지(후드) ON 58초 동안 정확히 `a3f8` 유지 확인
* **이벤트 패턴 3종** (방송 사이 삽입, +4~22B)

### 3.4 최종 판정: RS485 로컬 제어 불가

* 물리 스위치 / 월패드 화면으로 조명·난방·환기·콘센트를 조작해도 **명령 프레임이 버스에 흐르지 않음**
* 관측된 이벤트 패턴 A(`fe3df773 fe3ff7f4 f4544c5c 78d86308 fc040404 046442fafc3`)는 5회 모두 바이트 단위 동일 = 기기 무관 "조작 발생" 알림
* 결론: 이 라인은 **관리망/검침선**이며, SHP-W810BM은 기기를 **자체 무선망(지그방 IoT)**으로 제어한다
* 구형 이지온(SHT-xxxx)용 본 애드온의 프로토콜(A1/AC/AE 헤더, 4-10B 패킷, XOR 체크섬)과는 호환되지 않음

## 4. 향후 경로

1. **지그방 스마트홈 앱 / SmartThings 연동** (권장): 월패드 메뉴 또는 관리실에 스마트싱스 연동 단지 여부 확인. HA는 SmartThings 공식 통합 존재
2. **월패드 LAN 연결 확인**: 공유기 기기목록에서 월패드가 보이면 로컬 API 가능성 탐색
3. **읽기 전용 센서화 (선택)**: EW11이 그대로면 레인지 상태 플래그, 검침 폴링 값을 모니터링 센서로 만들 수 있음

## 5. 도구 (tools/)

| 파일 | 용도 |
|---|---|
| `tools/ew11_record.py` | 버스 트래픽 타임스탬프 녹화: `python3 ew11_record.py <초> <출력.jsonl>` |
| `tools/ew11_probe.py` | TCP 접속해 수동 쿼리 전송/수신 테스트 |
| `tools/ew11_uart.py` | EW11 UART 설정 조회/변경/재시작 헬퍼 |

분석 노트: 캡처 데이터는 head(`2f6924ad...`) 기준으로 프레임 재조립 → 가변 영역(`fbfffd26`~`4d697f74`) 카탈로그 방식이 유용했다.

## 6. 2026-09-05 파일 정리 내역

* 삭제: `sds_wallpad_test/` (테스트 복제본), `wallpad_dump/` (미사용 덤프 애드온), `repository.json` (HA 애드온 스토어 등록용, docker 사용 불필요), `sds_wallpad/log/` (디버그 로그), `sds_wallpad/package-lock.json` (불필요 파일)
* 유지: `sds_wallpad/` (애드온 본체 + 옵션), `share/` (compose 마운트), 본 문서
