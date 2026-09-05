"""Record EW11 traffic with timestamps to JSONL for protocol analysis."""
import socket, time, json, sys, signal

DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 300
OUT = sys.argv[2] if len(sys.argv) > 2 else "/tmp/wallpad_capture.jsonl"

soc = socket.create_connection(("192.168.0.93", 8899), timeout=10)
soc.settimeout(0.5)

f = open(OUT, "w")
t0 = time.time()
total = 0
packets = 0

def flush(sig=None, frame=None):
    f.close()
    soc.close()
    print(f"\nstopped: {total} bytes, {packets} records -> {OUT}", flush=True)
    sys.exit(0)

signal.signal(signal.SIGTERM, flush)
signal.signal(signal.SIGINT, flush)

print(f"recording {DURATION}s to {OUT} ...", flush=True)
while time.time() - t0 < DURATION:
    try:
        d = soc.recv(4096)
        if d:
            ts = round((time.time() - t0) * 1000)
            f.write(json.dumps({"t": ts, "hex": d.hex()}) + "\n")
            f.flush()
            total += len(d)
            packets += 1
            el = int(time.time() - t0)
            if packets % 20 == 0:
                print(f"  [{el:3d}s] {packets} recs, {total} bytes", flush=True)
    except socket.timeout:
        pass
flush()
