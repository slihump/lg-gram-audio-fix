#!/usr/bin/env python3
"""ALC298 벤더 COEF를 정상(GOOD) 값으로 복원.
Windows가 남긴 값을 리눅스 정상 부팅 때의 값으로 되돌린다."""
import fcntl, struct, sys

DEV = "/dev/snd/hwC0D0"
IOCTL_VERB_WRITE = 0xc0084811

# state-GOOD.txt vs state-BAD.txt diff 로 확인된 차이 (2026-09-08)
GOOD = {0x22: 0x0039, 0x23: 0x23ff, 0x25: 0x0001,
        0x26: 0xb001, 0x28: 0x0000, 0x5b: 0x0000}

def verb(fd, nid, v, param):
    val = (nid << 24) | (v << 16) | (param & 0xffff) if v <= 0xf \
          else (nid << 24) | (v << 8) | (param & 0xff)
    out = fcntl.ioctl(fd, IOCTL_VERB_WRITE, struct.pack("II", val, 0))
    return struct.unpack("II", out)[1]

def read_coef(fd, idx):
    verb(fd, 0x20, 0x5, idx)          # SET_COEF_INDEX
    return verb(fd, 0x20, 0xc, 0)     # GET_PROC_COEF

def write_coef(fd, idx, val):
    verb(fd, 0x20, 0x5, idx)          # SET_COEF_INDEX
    verb(fd, 0x20, 0x4, val)          # SET_PROC_COEF

fd = open(DEV, "rb")
print("=== 적용 전 ===")
before = {i: read_coef(fd, i) for i in sorted(GOOD)}
for i in sorted(GOOD):
    print(f"COEF[0x{i:02x}] = 0x{before[i]:04x}   (목표 0x{GOOD[i]:04x})")

print("\n=== 쓰기 ===")
for i in sorted(GOOD):
    write_coef(fd, i, GOOD[i])
    print(f"COEF[0x{i:02x}] <- 0x{GOOD[i]:04x}")

print("\n=== 적용 후 검증 ===")
ok = True
for i in sorted(GOOD):
    now = read_coef(fd, i)
    mark = "OK" if now == GOOD[i] else "!! 불일치"
    if now != GOOD[i]:
        ok = False
    print(f"COEF[0x{i:02x}] = 0x{now:04x}  {mark}")
fd.close()
print("\n결과: " + ("전부 목표값으로 기록됨" if ok else "일부 기록 실패"))
