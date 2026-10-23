#!/usr/bin/env python3
"""ALC298 함수 그룹 리셋 후 재생 경로 수동 복원.
0x28/0x5b 래치가 리셋으로 풀리는지 확인하는 것이 핵심."""
import fcntl, struct, time, subprocess

DEV = "/dev/snd/hwC0D0"
IOCTL = 0xc0084811
fd = open(DEV, "rb")

def verb(nid, v, p):
    val = (nid<<24)|(v<<16)|(p&0xffff) if v <= 0xf else (nid<<24)|(v<<8)|(p&0xff)
    return struct.unpack("II", fcntl.ioctl(fd, IOCTL, struct.pack("II", val, 0)))[1]

def rcoef(i):
    verb(0x20, 0x5, i); return verb(0x20, 0xc, 0)
def wcoef(i, v):
    verb(0x20, 0x5, i); verb(0x20, 0x4, v)

WATCH = (0x22, 0x23, 0x25, 0x26, 0x28, 0x5b)
GOOD  = {0x22:0x0039, 0x23:0x23ff, 0x25:0x0001, 0x26:0xb001, 0x28:0x0000, 0x5b:0x0000}

print("=== 1. 리셋 전 ===")
for i in WATCH: print(f"  COEF[0x{i:02x}] = 0x{rcoef(i):04x}")

print("\n=== 2. 함수 그룹 리셋 (NID 0x01, verb 0x7ff) ===")
try:
    verb(0x01, 0x7ff, 0x00)
    print("  리셋 verb 전송됨")
except OSError as e:
    print("  실패:", e)
time.sleep(1)

print("\n=== 3. 리셋 직후 (핵심: 0x28/0x5b가 0으로 풀렸는가) ===")
after = {}
for i in WATCH:
    after[i] = rcoef(i)
    tag = "→ 풀림!" if i in (0x28,0x5b) and after[i] == 0 else ""
    print(f"  COEF[0x{i:02x}] = 0x{after[i]:04x} {tag}")

latch_cleared = after[0x28] == 0 and after[0x5b] == 0
print(f"\n  래치 해제 여부: {'YES — 리셋이 통했음' if latch_cleared else 'NO — 리셋으로도 안 풀림'}")

print("\n=== 4. 재생 경로 수동 복원 ===")
# 전원 D0
for nid in (0x01, 0x02, 0x03, 0x0c, 0x0d, 0x17, 0x21):
    verb(nid, 0x705, 0x00)
# COEF 복원
for i in WATCH:
    wcoef(i, GOOD[i])
# 스피커 경로: DAC 0x03 -> mixer 0x0d -> pin 0x17
verb(0x03, 0x3, 0xb000 | 0x7a)   # DAC 출력 게인 0x7a, 언뮤트
verb(0x17, 0x701, 0x01)          # 연결 선택 = 0x0d
verb(0x17, 0x3, 0xb000)          # 핀 앰프 언뮤트
verb(0x17, 0x707, 0x40)          # pinctl = OUT
verb(0x17, 0x70c, 0x02)          # EAPD 활성
# 헤드폰은 뮤트 유지
verb(0x02, 0x3, 0xb000 | 0x4c)
verb(0x21, 0x707, 0xc0)
verb(0x21, 0x3, 0xb080)
print("  복원 verb 전송 완료")

print("\n=== 5. 복원 후 상태 ===")
for i in WATCH:
    v = rcoef(i)
    print(f"  COEF[0x{i:02x}] = 0x{v:04x}  (GOOD 0x{GOOD[i]:04x}) {'일치' if v==GOOD[i] else '다름'}")
for nid in (0x17, 0x03):
    print(f"  NID 0x{nid:02x}: pinctl=0x{verb(nid,0xf07,0):04x} eapd=0x{verb(nid,0xf0c,0):04x} "
          f"ampL=0x{verb(nid,0xb,0x8000):04x} power=0x{verb(nid,0xf05,0):04x} conn=0x{verb(nid,0xf01,0):04x}")
fd.close()

print("\n=== 6. 믹서 재동기화 ===")
for args in (["Master","100%","on"], ["Speaker","100%","on"]):
    subprocess.run(["amixer","-c","0","-q","set"]+args)
subprocess.run(["amixer","-c","0","get","Speaker"])
