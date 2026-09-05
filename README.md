# 월패드 RS485 연동 (EW11)

삼성(지그방) 스마트월패드 SHP-W810BM 아파트에서 EW11(RS485-WiFi)로 Home Assistant 연동을 시도한 저장소.

* **작업 기록 및 패킷 분석 결과: [EW11_INTEGRATION.md](EW11_INTEGRATION.md)** — 먼저 읽어보세요
* 결론 요약: 이 단지의 월패드는 신형(무선 제어)이라 RS485 로컬 제어는 불가. 라인은 관리망/검침용

## 구성

| 경로 | 내용 |
|---|---|
| `sds_wallpad/` | 삼성SDS 월패드 애드온 본체 (n-andflash/ha_addons 포크). `options_standalone.json`에 EW11(192.168.0.93:8899) 설정 완료 |
| `tools/` | EW11 캡처/설정 도구 (녹화, 프로브, UART 설정 헬퍼) |
| `share/` | docker-compose 마운트용 |

## 실행 (docker)

```bash
docker compose up -d samsung-wallpad   # 현재는 프로토콜 불일치로 stop 상태 유지 권장
```

## 참고

* 원본 애드온: https://github.com/n-andflash/ha_addons
* EW11 설정 API 사용법은 EW11_INTEGRATION.md 2장 참조
