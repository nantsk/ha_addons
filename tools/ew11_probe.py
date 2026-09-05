import socket, time

HOST, PORT = "192.168.0.93", 8899

def chk(packet):
    c = 0
    for b in packet[:-1]:
        c ^= b
    if c >= 0x80:
        c -= 0x80
    return c

def mk(header, length, id_pos=None, idn=None):
    p = bytearray(length)
    p[0] = header >> 8
    p[1] = header & 0xFF
    if id_pos is not None:
        p[id_pos] = idn
    p[-1] = chk(p)
    return bytes(p)

soc = socket.create_connection((HOST, PORT), timeout=10)
print("connected", flush=True)
soc.settimeout(0.5)

def drain(seconds, tag):
    buf = b""
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            d = soc.recv(4096)
            if d:
                buf += d
        except socket.timeout:
            pass
        except Exception as e:
            print(f"  [err] {e}", flush=True)
            break
    print(f"  [{tag}] RX {len(buf)} bytes: {buf.hex()[:400] if buf else '(none)'}", flush=True)
    return buf

print("== passive listen 5s ==", flush=True)
drain(5, "passive")

for name, pkt in [
    ("light id2",  mk(0xAC79, 5, 2, 2)),
    ("light id1",  mk(0xAC79, 5, 2, 1)),
    ("energy id2", mk(0xAA6F, 4, 2, 2)),
    ("gas",        mk(0xAB41, 4)),
]:
    print(f"== TX {name}: {pkt.hex()} ==", flush=True)
    try:
        soc.sendall(pkt)
    except Exception as e:
        print(f"  [send err] {e}", flush=True)
        break
    drain(3, name)

soc.close()
