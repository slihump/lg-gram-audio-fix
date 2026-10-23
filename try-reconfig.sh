#!/bin/bash
# 코덱만 완전 재초기화 (PCI rebind와 다름: 코덱 init 시퀀스를 처음부터 다시 실행)
set -u
DUMP=/home/slihump/audio-debug/dump-codec.py

echo "=== reconfig 전 COEF ==="
python3 - <<'PY'
import fcntl,struct
fd=open("/dev/snd/hwC0D0","rb")
def verb(nid,v,p):
    val=(nid<<24)|(v<<16)|(p&0xffff) if v<=0xf else (nid<<24)|(v<<8)|(p&0xff)
    return struct.unpack("II",fcntl.ioctl(fd,0xc0084811,struct.pack("II",val,0)))[1]
for i in (0x22,0x23,0x25,0x26,0x28,0x5b):
    verb(0x20,0x5,i); print(f"  COEF[0x{i:02x}] = 0x{verb(0x20,0xc,0):04x}")
PY

echo
echo "=== reconfig 실행 ==="
if echo 1 > /sys/class/sound/hwC0D0/reconfig 2>/tmp/reconfig.err; then
  echo "reconfig 쓰기 성공"
else
  echo "reconfig 쓰기 실패: $(cat /tmp/reconfig.err)"
fi
sleep 4

echo
echo "=== 카드 상태 ==="
cat /proc/asound/cards

echo
echo "=== 코덱 init 실행 횟수 (2 이상이면 reconfig가 동작한 것) ==="
echo "autoconfig 횟수: $(dmesg | grep -c 'autoconfig for ALC298')"
dmesg | grep -E "autoconfig for ALC298" | tail -2

echo
echo "=== reconfig 후 COEF ==="
python3 - <<'PY'
import fcntl,struct
try:
    fd=open("/dev/snd/hwC0D0","rb")
except Exception as e:
    print("  hwdep 열기 실패:",e); raise SystemExit
def verb(nid,v,p):
    val=(nid<<24)|(v<<16)|(p&0xffff) if v<=0xf else (nid<<24)|(v<<8)|(p&0xff)
    return struct.unpack("II",fcntl.ioctl(fd,0xc0084811,struct.pack("II",val,0)))[1]
GOOD={0x22:0x0039,0x23:0x23ff,0x25:0x0001,0x26:0xb001,0x28:0x0000,0x5b:0x0000}
for i in (0x22,0x23,0x25,0x26,0x28,0x5b):
    verb(0x20,0x5,i); v=verb(0x20,0xc,0)
    print(f"  COEF[0x{i:02x}] = 0x{v:04x}   (GOOD 0x{GOOD[i]:04x}) {'일치' if v==GOOD[i] else '다름'}")
PY

echo
echo "=== 믹서 복구 ==="
amixer -c 0 -q set Master 100% on 2>/dev/null
amixer -c 0 -q set Speaker 100% on 2>/dev/null
amixer -c 0 get Speaker 2>/dev/null | grep "Front Left"
