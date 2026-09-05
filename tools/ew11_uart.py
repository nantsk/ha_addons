#!/usr/bin/env python3
"""EW11 UART 설정 조회/변경/재시작 헬퍼

사용:
  python3 ew11_uart.py get                 # 현재 UART 설정 + 카운터 조회
  python3 ew11_uart.py set 9600 8 EVEN 1   # 보레이트/데이터비트/패리티/스톱비트 변경 + 재시작
  python3 ew11_uart.py restart             # 장치 재시작
"""
import json
import subprocess
import sys
import time

EW11 = "192.168.0.93"
ADMIN = "admin:admin"


def api(pl, cid):
    body = json.dumps({"CID": cid, "PL": pl}) if pl is not None else json.dumps({"CID": cid})
    out = subprocess.run(
        ["curl", "-m", "5", "-s", "-u", ADMIN, "-X", "POST",
         "-H", "Content-Type: application/json; charset=utf-8",
         "-d", f"msg={body}", f"http://{EW11}/cmd"],
        capture_output=True, text=True).stdout.strip()
    return out


def get():
    cfg = json.loads(api(["UART"], 10003))["PL"]["UART"]
    cnt = json.loads(api(["UART"], 10001))["PL"]["UART"]
    print("config   :", {k: cfg[k] for k in ("Baudrate", "Databits", "Parity", "Stopbits")})
    print("counters :", {k: cnt[k] for k in ("RecvBytes", "RecvFrames", "FailedBytes", "FailedFrames")})


def set_uart(baud, dbits, parity, stop):
    cfg = {"Baudrate": int(baud), "Databits": int(dbits), "Stopbits": int(stop), "Parity": parity.upper(),
           "BufSize": 512, "GapTime": 50, "FlowCtrl": 2, "SoftwareFlowCtrl": 0,
           "Xon": "11", "Xoff": "13", "CliGetIn": "Serial-String", "SerailString": "+++",
           "CliWaitTime": 300, "UartProto": "NONE", "FrameLen": 16, "FrameTime": 100,
           "TagEnable": 0, "TagHead": "00", "TagTail": "00"}
    print("set  :", api({"UART": cfg}, 10005))
    restart()
    get()


def restart():
    print("restart:", api(None, 20003))
    for _ in range(24):
        r = subprocess.run(["bash", "-c",
                            f"timeout 2 bash -c 'echo > /dev/tcp/{EW11}/8899' 2>/dev/null && echo ok"],
                           capture_output=True, text=True)
        if "ok" in r.stdout:
            print("device back online")
            time.sleep(2)
            return
        time.sleep(5)
    print("device did not come back (check power/wifi)")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "get"
    if cmd == "get":
        get()
    elif cmd == "set":
        set_uart(*sys.argv[2:6])
    elif cmd == "restart":
        restart()
    else:
        print(__doc__)
