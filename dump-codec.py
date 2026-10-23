#!/usr/bin/env python3
"""ALC298 전체 상태 덤프 - 표준 레지스터 + 벤더 COEF 레지스터.
사용법: sudo python3 dump-codec.py <출력파일>
정상 상태와 고장 상태에서 각각 떠서 diff 하는 용도."""
import fcntl, struct, sys, subprocess

DEV = "/dev/snd/hwC0D0"
# HDA_IOCTL_VERB_WRITE = _IOWR('H', 0x11, struct hda_verb_ioctl{u32 verb; u32 res;})
IOCTL_VERB_WRITE = 0xc0084811

def verb(fd, nid, v, param):
    # verb 형식: nid<<24 | verb<<8 | param  (8bit verb) 또는 nid<<24|verb<<16|param (4bit verb)
    if v <= 0xf:
        val = (nid << 24) | (v << 16) | (param & 0xffff)
    else:
        val = (nid << 24) | (v << 8) | (param & 0xff)
    buf = struct.pack("II", val, 0)
    try:
        out = fcntl.ioctl(fd, IOCTL_VERB_WRITE, buf)
        return struct.unpack("II", out)[1]
    except OSError as e:
        return None

def main():
    out = open(sys.argv[1], "w") if len(sys.argv) > 1 else sys.stdout
    fd = open(DEV, "rb")

    print("########## 벤더 COEF 레지스터 (ALC298, NID 0x20) ##########", file=out)
    for idx in range(0x80):
        # Set Coef Index (0x5), then Get Processing Coefficient (0xc)
        verb(fd, 0x20, 0x5, idx)
        val = verb(fd, 0x20, 0xc, 0)
        print(f"COEF[0x{idx:02x}] = 0x{val:04x}" if val is not None else f"COEF[0x{idx:02x}] = ERR", file=out)

    print("\n########## EAPD / 핀 상태 (주요 노드) ##########", file=out)
    for nid in (0x14, 0x17, 0x21, 0x0c, 0x0d, 0x02, 0x03):
        pinctl = verb(fd, nid, 0xf07, 0)        # Get Pin Widget Control
        eapd   = verb(fd, nid, 0xf0c, 0)        # Get EAPD/BTL Enable
        ampL   = verb(fd, nid, 0xb, 0x8000)     # Get Amp Gain/Mute, output left
        ampR   = verb(fd, nid, 0xb, 0xa000)     # output right
        power  = verb(fd, nid, 0xf05, 0)        # Get Power State
        conn   = verb(fd, nid, 0xf01, 0)        # Get Connection Select
        def h(x): return "----" if x is None else f"0x{x:04x}"
        print(f"NID 0x{nid:02x}: pinctl={h(pinctl)} eapd={h(eapd)} ampL={h(ampL)} ampR={h(ampR)} power={h(power)} conn={h(conn)}", file=out)

    print("\n########## GPIO ##########", file=out)
    for nid in (0x01,):
        for name, v in (("gpio_mask",0xf16),("gpio_dir",0xf17),("gpio_data",0xf15)):
            val = verb(fd, nid, v, 0)
            print(f"NID 0x{nid:02x} {name} = " + ("----" if val is None else f"0x{val:04x}"), file=out)

    fd.close()
    print("\n########## /proc codec 덤프 ##########", file=out)
    out.flush()
    subprocess.run(["cat", "/proc/asound/card0/codec#0"], stdout=out)
    print("\n########## amixer ##########", file=out)
    out.flush()
    subprocess.run(["amixer", "-c", "0"], stdout=out)
    if out is not sys.stdout:
        out.close()
        print(f"저장 완료: {sys.argv[1]}")

main()
