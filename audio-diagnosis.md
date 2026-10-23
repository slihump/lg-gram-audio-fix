# LG gram 16Z90TP — 우분투 내장 스피커 무음 문제 진단 기록

작성: 2026-09-07 / Ubuntu 24.04.4, 커널 7.0.0-31-generic

## 증상
내장 스피커에서 소리가 안 남. 며칠 단위로 됐다 안 됐다 반복.
USB-C 이어폰은 정상(별도 USB 사운드카드라 내장 코덱을 우회함).

## 결론
**직전에 Windows가 돌았던 세션에서만 무음.**

| 직전 OS | 전환 방식 | 결과 |
|---|---|---|
| 리눅스 | 다시 시작 (웜) | 소리 남 |
| Windows | 다시 시작 (웜) | 무음 |
| Windows | 다시 시작 (웜, powercfg /h off 적용 후) | 무음 |

**메커니즘:** "다시 시작"(웜 리부팅)은 오디오 앰프의 전원을 끊지 않음.
마지막으로 돌았던 OS가 앰프에 남긴 상태가 그대로 이어지고, 리눅스는 이를 리셋하지 못함.
Windows가 남긴 상태 = 무음 / 리눅스가 남긴 상태 = 정상.
**전원을 실제로 끊는 완전 종료(콜드 부팅)만이 이 상태를 지움.**

주의: Windows 빠른 시작은 "시스템 종료"에만 적용되고 "다시 시작"은 항상 완전 재시작이라
빠른 시작과는 무관한 경로임. (초기 진단에서 이 둘을 혼동해 잘못 안내한 적 있음)

### 빠른 판별법
**`sudo python3 ~/audio-debug/check-audio-state.py`** — COEF 0x28/0x5b를 읽어
정상/고장을 즉시 판정. 종료 코드 0=정상, 1=고장.

(구 지표: `who -b`와 uptime 역산 부팅 시각의 9시간 차이 = 직전 Windows 부팅.
**2026-09-08에 Windows에 RealTimeIsUniversal을 적용하면서 이 지표는 무효가 됨** —
Windows가 RTC에 UTC를 쓰게 되어 스큐가 안 생김. 증상 자체는 그대로 발생함.)

## 배제된 원인 (모두 실측으로 확인)
- **하드웨어 고장** — Windows에서 스피커 정상 동작
- **음소거/볼륨** — Master 127 on, Speaker on, 라우트 [Out] Speaker mute=False
- **PipeWire/WirePlumber** — 스택 재시작 무효, ALSA 직결(plughw/hw/device31)로도 무음
- **UCM 설정** — plughw/hw 직결은 UCM을 안 거치는데도 무음
- **커널 회귀(7.0.0-30 → -31)** — 두 부팅의 오디오 드라이버 로그가 완전히 동일
- **SOF 펌웨어/토폴로지 손상** — dpkg -V 무결성 정상, 펌웨어 2.14.1.1 정상 부팅
- **잘못된 코덱 핀** — BIOS가 0x17을 [Fixed] Speaker at Int로 선언, 드라이버가 정확히 구동 중
- **snd_hda_intel.power_save=1** — 0으로 꺼도 무음. 재부팅 후 1로 원복됐는데 소리는 정상
- **절전 복귀** — 절전 36초 테스트 후 정상 재생 확인 (긴 절전은 미검증)
- **PCI 콜드 재초기화** — DSP/코덱을 unbind/bind 해도 무음 (전원이 안 끊기므로)

## 핵심 관찰
소리가 날 때와 안 날 때의 **소프트웨어 상태가 완전히 동일함**.

    핀 0x17 Amp-Out [0x00 0x00] 언뮤트 / Pin-ctls 0x40 OUT / EAPD 0x2 / D0 / 연결 0x0d*
    DAC 0x03 stream=1, D0 / Master 127 on / Speaker on / 라우트 Speaker mute=False

고장은 리눅스가 읽을 수 있는 어떤 레지스터에도 기록되지 않음.
→ 소프트웨어로는 탐지·복구 불가.

## 대처
- **복구**: 완전 종료 후 전원 켜기(콜드 부팅). "다시 시작"으로는 안 됨.
  리눅스→리눅스는 다시 시작으로도 되지만, Windows→우분투는 반드시 콜드 부팅.
- **예방**: Windows에서 관리자 권한으로
  - `powercfg /h off` — 빠른 시작 끄기. 이게 있어야 "시스템 종료"가 진짜 전원 차단이 됨
  - `reg add "HKLM\SYSTEM\CurrentControlSet\Control\TimeZoneInformation" /v RealTimeIsUniversal /t REG_DWORD /d 1 /f`
    — RTC를 UTC로. 시계 9시간 틀어짐도 함께 해결
  - **운영 규칙: Windows → 우분투 전환 시 "다시 시작" 금지, "시스템 종료" 후 전원 버튼으로 켜기**

## 검증 결과 (2026-09-08 확정)
- **콜드 부팅으로 복구됨을 실측 확인.** Windows→다시 시작→우분투(무음) 상태에서
  `shutdown -h now` 후 전원 재투입 → 소리 정상 복귀.
- RTC 스큐 지표도 검증됨:
  | 부팅 | utmp 기록 | uptime 역산 | 스큐 | 직전 OS | 소리 |
  |---|---|---|---|---|---|
  | 이전 | 09-08 08:54 | 09-07 23:54 | 9시간 | Windows | 무음 |
  | 이후 | 09-07 23:59 | 09-07 23:59 | 없음 | 리눅스 콜드부팅 | 정상 |

## 남은 불확실성
- `Windows → 시스템 종료(powercfg /h off 적용) → 전원 켜기 → 우분투` 경로는 아직 직접
  검증 안 됨. 같은 원리(진짜 전원 차단)이므로 정상 동작할 것으로 예상되나, 평소 사용 중
  확인 필요. 만약 이 경로에서도 무음이면 `powercfg /h off`가 적용 안 됐을 가능성부터 확인
  (Windows 파티션에 hiberfil.sys가 남아있는지 확인).
- 긴 절전(1시간 이상) 후 안전한지 미검증. 36초 절전만 테스트함.


---

# 심층 분석: 근본 원인 위치 특정 (2026-09-08)

"근본적으로 고칠 수 있는가"를 확인하기 위해 벤더 레지스터까지 파고든 기록.

## 결정적 발견
정상 상태와 고장 상태의 코덱 전체를 덤프해 비교한 결과,
**차이가 ALC298 벤더 COEF 레지스터 6개뿐이었음.** 그 외 전부 동일:
표준 핀 설정, EAPD, 앰프 게인/뮤트, 전원 상태, 연결 선택, GPIO, /proc 코덱 덤프, amixer.

| COEF | GOOD (소리 남) | BAD (무음) | 쓰기 가능 |
|---|---|---|---|
| 0x22 | 0x0039 | 0x0000 | 가능 |
| 0x23 | 0x23ff | 0x0000 | 가능 |
| 0x25 | 0x0001 | 0x0000 | 가능 |
| 0x26 | 0xb001 | 0x3000 | 가능 |
| **0x28** | **0x0000** | **0x003f** | **불가 — 래치됨** |
| **0x5b** | **0x0000** | **0x4342** | **불가 — 래치됨** |

## 시도한 것과 결과
- **COEF 4개를 GOOD 값으로 복원** → 기록은 성공, 소리는 여전히 무음
- **0x28 / 0x5b 쓰기** → verb는 수락되나 값이 안 바뀜 (읽기전용 또는 하드웨어 래치)
- **코덱 reconfig** (`/sys/class/sound/hwC0D0/reconfig`) → `Device or resource busy`.
  이 코덱은 SOF/ASoC 카드에 묶여 있어 레거시 HDA용 reconfig 사용 불가
- **HDA 함수 그룹 리셋** (NID 0x01, verb 0x7ff) → verb는 오류 없이 수락되나 **실제로는
  아무것도 리셋되지 않음**(직전에 써넣은 0x22/0x23 값이 그대로 남아 있는 것으로 확인).
  이후 재생 경로를 수동 복원해도 무음

## 결론
고장의 위치는 **정확히 특정됨**: ALC298 벤더 COEF 레지스터, 그 중에서도 소프트웨어로
접근 불가능한 0x28 / 0x5b에 래치된 상태. Windows 드라이버가 설정하고,
**전원이 실제로 끊기기 전까지 어떤 리눅스 측 수단으로도 해제되지 않음.**

→ **리눅스 단독으로는 근본 수정 불가.** 콜드 부팅 규칙이 유일한 실용적 해법.

## 남은 유일한 근본 해결 경로
상류 커널(ALSA) 제보. Realtek COEF 레지스터 의미는 비공개이므로 실험으로 알아낼 수 없지만,
ALSA 메인테이너(Takashi Iwai)는 정확히 이런 제보를 받아 ALC quirk를 추가해 왔음.
제보에 필요한 데이터는 이미 전부 확보됨:
- 기기: LG gram 16Z90TP, 코덱 ALC298, SSID **1854:0548**, BIOS A1ZJ3340 (2025-07-15)
- 커널 7.0.0-31-generic (Ubuntu 24.04), SOF 펌웨어 2.14.1.1, 이 기종 전용 quirk 없음(modelname 비어있음)
- 재현: Windows 부팅 → "다시 시작" → 우분투 = 내장 스피커 무음 (콜드 부팅하면 정상)
- 위 COEF 차이표, `~/audio-debug/state-GOOD.txt`, `state-BAD.txt`


---

# 상류 제보 기록

- **발송**: 2026-09-07 15:57 UTC (KST 2026-09-08 00:57)
- **수신처**: alsa-devel@alsa-project.org
- **제목**: [BUG] ALC298 (SSID 1854:0548): internal speakers silent after warm reboot from Windows
- **첨부**: lg-gram-alc298-dumps.tar.gz (state-GOOD/BAD.txt, alsa-info-GOOD/BAD.txt)
- **Message-ID**: CACC0HWCjUNOK=PU8ARxDD5UOptEBm5KJhc5yzweLyb2004UY4w@mail.gmail.com
- **permalink (정식 인용 주소)**:
  https://lore.kernel.org/alsa-devel/CACC0HWCjUNOK=PU8ARxDD5UOptEBm5KJhc5yzweLyb2004UY4w@mail.gmail.com/
- **검색**: https://lore.kernel.org/alsa-devel/?q=16Z90TP
- **상태**: 독립 스레드로 정상 등재 확인. 답장 대기 중.

## 답장이 오면
하루 안에 회신할 것. 재현은 Windows 부팅 → 다시 시작 → 우분투 (2분).

    sudo python3 ~/audio-debug/check-audio-state.py              # 상태 판정
    sudo python3 ~/audio-debug/dump-codec.py ~/audio-debug/state-BAD2.txt

## 기대 결과
quirk가 머지되면 커널 커밋에 Reported-by: 태그로 이름이 남음.
머지되지 않아도 위 아카이브 링크는 영구 보존됨.
