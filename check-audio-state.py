#!/usr/bin/env python3
"""내장 스피커가 정상 상태인지 즉시 판정. (sudo 필요)
RTC 스큐 지표는 RealTimeIsUniversal 적용 후 무효가 되어, 코덱 레지스터를 직접 본다."""
import fcntl, struct, sys
fd = open("/dev/snd/hwC0D0", "rb")
def verb(nid, v, p):
    val = (nid<<24)|(v<<16)|(p&0xffff) if v <= 0xf else (nid<<24)|(v<<8)|(p&0xff)
    return struct.unpack("II", fcntl.ioctl(fd, 0xc0084811, struct.pack("II", val, 0)))[1]
def coef(i):
    verb(0x20, 0x5, i); return verb(0x20, 0xc, 0)

c28, c5b = coef(0x28), coef(0x5b)
c22, c26 = coef(0x22), coef(0x26)
print(f"COEF[0x28] = 0x{c28:04x}   (정상 0x0000 / 고장 0x003f)")
print(f"COEF[0x5b] = 0x{c5b:04x}   (정상 0x0000 / 고장 0x4342)")
print(f"COEF[0x22] = 0x{c22:04x}   (정상 0x0039 / 고장 0x0000)")
print(f"COEF[0x26] = 0x{c26:04x}   (정상 0xb001 / 고장 0x3000)")
good = (c28 == 0 and c5b == 0)
print()
if good:
    print(">>> 정상 상태 — 스피커에서 소리가 나야 합니다")
else:
    print(">>> 고장 상태 — 내장 스피커 무음")
    print(">>> 조치: 완전 종료 후 전원 켜기 (다시 시작은 효과 없음)")
sys.exit(0 if good else 1)
