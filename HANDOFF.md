# HANDOFF — LG gram 내장 스피커 무음 문제

> 다른 에이전트/세션이 이 문서만 읽고 이어서 작업할 수 있도록 정리한 인수인계 문서.
> 최종 업데이트: 2026-09-10 (원본 작업 세션 2026-09-07~08에서 복구·정리)

---

## 0. 30초 요약

- **기기:** LG gram 16Z90TP-GA5BK / Ubuntu 24.04.4 + Windows 듀얼부팅 / 커널 7.0.0-31-generic
- **증상:** 내장 스피커 무음. USB-C 이어폰은 정상(내장 코덱 우회).
- **근본 원인:** **직전에 Windows가 돌았고 "다시 시작"(웜 리부팅)으로 우분투에 진입한 세션에서만** 발생.
  Windows 드라이버가 ALC298 벤더 COEF 레지스터 `0x28`/`0x5b`에 남긴 상태가 하드웨어에 래치되어,
  전원이 실제로 끊기기 전까지 리눅스 측 어떤 수단으로도 해제되지 않음.
- **해법:** 복구는 **완전 종료(콜드 부팅)** 뿐. 예방은 Windows에서 `powercfg /h off` + 운영 규칙("다시 시작" 금지).
- **리눅스 단독 근본 수정: 불가능** (심층 조사로 확정). 유일한 근본 경로는 ALSA 상류 quirk 제보 → **이미 제보 완료, 답장 대기 중.**
- **지금 열려 있는 유일한 작업:** alsa-devel 메일 답장이 오면 하루 안에 회신하는 것.

---

## 1. 현재 상태 (2026-09-10 기준)

| 항목 | 상태 |
|---|---|
| 근본 원인 규명 | ✅ 완료 — ALC298 COEF 0x28/0x5b 하드웨어 래치 |
| 리눅스 측 우회/복구법 | ✅ 확정 — 콜드 부팅. 실측 검증됨(2026-09-08) |
| 예방책 | ✅ Windows에 `powercfg /h off` + `RealTimeIsUniversal=1` 적용 완료. 운영 규칙 수립 |
| 상류(ALSA) 제보 | ✅ 발송·아카이브 등재 확인 (2026-09-07 15:57 UTC) |
| 상류 답장 | ⏳ **대기 중** — 이것이 유일하게 남은 액티브 태스크 |
| 미검증 항목 | ⚠️ "Windows→시스템 종료(빠른시작 off)→전원 켜기→우분투" 경로 / 1시간+ 긴 절전 복귀 |

---

## 2. 근본 원인 (상세)

정상 부팅(콜드)과 고장 부팅(Windows→웜 리부팅) 상태에서 ALC298 코덱 전체를 덤프해 diff한 결과,
**차이가 벤더 COEF 레지스터 6개뿐이었음.** 표준 핀 설정, EAPD, 앰프 게인/뮤트, 전원 상태(D0),
연결 선택, GPIO, `/proc/asound/.../codec#0` 전체, amixer 출력 — **전부 바이트 단위로 동일.**

| COEF | GOOD (소리 남) | BAD (무음) | 쓰기 |
|---|---|---|---|
| 0x22 | 0x0039 | 0x0000 | 가능 |
| 0x23 | 0x23ff | 0x0000 | 가능 |
| 0x25 | 0x0001 | 0x0000 | 가능 |
| 0x26 | 0xb001 | 0x3000 | 가능 |
| **0x28** | **0x0000** | **0x003f** | **불가 (하드웨어 래치)** |
| **0x5b** | **0x0000** | **0x4342** | **불가 (하드웨어 래치)** |

- COEF 0x00–0x7f 전부 스캔했고 그 외 인덱스는 모두 일치.
- 고장은 리눅스가 읽을 수 있는 어떤 표준 레지스터에도 기록되지 않음 → **소프트웨어 탐지·복구 불가**.
  (유일한 판별 수단이 COEF 0x28/0x5b 직접 읽기 = `check-audio-state.py`)

### 메커니즘
"다시 시작"(웜 리부팅)은 오디오 앰프/코덱의 전원을 끊지 않음. 마지막으로 돌았던 OS가 남긴
COEF 상태가 그대로 이어짐. Windows가 남긴 상태 = 무음, 리눅스가 남긴 상태 = 정상.
**전원을 실제로 차단하는 완전 종료(콜드 부팅)만이 래치를 지움.**

주의: Windows "빠른 시작(Fast Startup)"은 **"시스템 종료"에만** 적용되고 **"다시 시작"은 항상 완전 재시작**.
따라서 이 문제는 빠른 시작과 무관한 별개 경로. (초기 진단에서 이 둘을 혼동해 잘못 안내한 이력 있음 — 반복 금지.)

---

## 3. 이미 배제한 원인 — **다시 시도하지 말 것**

모두 2026-09-07~08에 실측으로 확인:

- 하드웨어 고장 (Windows에서는 스피커 정상)
- 음소거/볼륨 (Master 127 on, Speaker on, PipeWire 라우트 [Out] Speaker mute=False)
- PipeWire/WirePlumber (스택 재시작 무효, ALSA 직결 `plughw:0,0`/`hw:0,0`/deep-buffer `plughw:0,31`으로도 무음)
- UCM 설정 (hw 직결은 UCM 우회하는데도 무음)
- 커널 회귀 7.0.0-30 ↔ -31 (두 부팅의 오디오 드라이버 로그 완전 동일)
- SOF 펌웨어/토폴로지 손상 (`dpkg -V` 무결성 정상, 펌웨어 2.14.1.1 정상 부팅)
- 코덱 핀 오인식 (BIOS가 0x17을 [Fixed] Speaker at Int로 선언, 드라이버가 정확히 구동)
- `snd_hda_intel.power_save` (0으로 꺼도 무음)
- 절전 복귀 (36초 절전 후 정상 재생 확인 — 단, 긴 절전은 미검증)
- **COEF 0x22/0x23/0x25/0x26을 GOOD 값으로 복원** → 쓰기는 성공, 소리는 여전히 무음
- **COEF 0x28/0x5b 쓰기** → verb는 수락되나 값이 안 바뀜 (읽기전용/래치)
- **코덱 reconfig** (`/sys/class/sound/hwC0D0/reconfig`) → `Device or resource busy` (SOF/ASoC 바인딩)
- **HDA 함수 그룹 리셋** (NID 0x01, verb 0x7ff) → 수락되나 실제로 아무것도 리셋 안 됨
- **PCI 콜드 재초기화** (`0000:00:1f.3` unbind/bind) → 펌웨어·토폴로지 재로드되나 무음 (전원 안 끊김)

→ **리눅스 단독 근본 수정은 불가능하다는 것이 결론.** 위 경로 재탐색은 시간 낭비.

---

## 4. 사용자 대처법 (확정)

### 복구
**완전 종료 후 전원 켜기 (콜드 부팅).** "다시 시작"으로는 안 됨.
리눅스→리눅스 재부팅은 "다시 시작"으로도 되지만, **Windows→우분투는 반드시 콜드 부팅.**

### 예방 (Windows 관리자 권한, 이미 적용됨)
- `powercfg /h off` — 빠른 시작 끄기. 이게 있어야 "시스템 종료"가 진짜 전원 차단이 됨
- `reg add "HKLM\SYSTEM\CurrentControlSet\Control\TimeZoneInformation" /v RealTimeIsUniversal /t REG_DWORD /d 1 /f` — RTC를 UTC로 (시계 9시간 스큐도 해결)
- **운영 규칙: Windows → 우분투 전환 시 "다시 시작" 금지. "시스템 종료" 후 전원 버튼으로 켜기.**

### 상태 판별
```bash
sudo python3 ~/audio-debug/check-audio-state.py
```
COEF 0x28/0x5b를 읽어 즉시 판정. 종료 코드 `0`=정상, `1`=고장.

> ⚠️ 구 지표였던 "utmp 부팅시각 vs uptime 역산의 9시간 스큐"는 2026-09-08 `RealTimeIsUniversal`
> 적용 이후 **무효**(스큐가 더 이상 안 생김). 스큐 없다고 정상이라 판단하지 말 것 — 증상은 그대로 발생함.

---

## 5. 상류 제보 (ALSA) — 진행 중인 유일한 태스크

- **발송:** 2026-09-07 15:57 UTC (KST 09-08 00:57)
- **수신처:** alsa-devel@alsa-project.org
- **제목:** `[BUG] ALC298 (SSID 1854:0548): internal speakers silent after warm reboot from Windows`
- **첨부:** `lg-gram-alc298-dumps.tar.gz` (state-GOOD/BAD.txt, alsa-info-GOOD/BAD.txt)
- **Message-ID:** `CACC0HWCjUNOK=PU8ARxDD5UOptEBm5KJhc5yzweLyb2004UY4w@mail.gmail.com`
- **permalink:** https://lore.kernel.org/alsa-devel/CACC0HWCjUNOK=PU8ARxDD5UOptEBm5KJhc5yzweLyb2004UY4w@mail.gmail.com/
- **검색:** https://lore.kernel.org/alsa-devel/?q=16Z90TP
- **상태:** 독립 스레드로 정상 등재 확인. 리스트 배포 완료(아카이브에 있다는 것이 배포 완료의 증거). 답장 대기 중.
- 사용자가 Gmail에 필터 생성 완료 (발신자/제목 기준). 필터 생성 이전 도착 메일엔 미적용 → 포럼 탭·스팸함도 확인 권고.

### 답장이 오면 (다른 에이전트가 할 일)
1. **하루 안에 회신** (머지 확률을 가장 크게 좌우).
2. 회신은 **전체답장 · 일반텍스트 · 인용 아래 작성(bottom-post)**.
3. 재현·덤프 요청이면:
   ```bash
   # Windows 부팅 → "다시 시작" → 우분투 (약 2분)
   sudo python3 ~/audio-debug/check-audio-state.py
   sudo python3 ~/audio-debug/dump-codec.py ~/audio-debug/state-BAD2.txt
   ```
4. 패치 테스트 요청이면 커널 빌드부터. 이 기종 전용 quirk 없음(`modelname` 비어 있음, 제네릭 ALC269 패밀리 경로).
5. 기대 결과: quirk 머지 시 커널 커밋에 `Reported-by:` 태그. 머지 안 돼도 아카이브 링크는 영구 보존.
6. 2주 무응답이면 **같은 스레드에 전체답장으로 한 줄 ping** (새 메일 아님 — 스레드 유지가 핵심).

---

## 6. 이 폴더의 파일 목록

| 파일 | 내용 |
|---|---|
| `HANDOFF.md` | 이 문서 |
| `session-transcript-2026-09-07.md` | 원본 CLI 작업 세션 전체 대화 복구본 (세션 ID `c8964b94-49e1-4ec0-8239-a7c812ebbd09`) |
| `~/audio-diagnosis.md` | 진단 기록 원본 (증상·결론·배제 원인·심층 분석·상류 제보 3개 섹션) |
| `upstream-report.md` | alsa-devel에 보낸 버그 리포트 전문 (구조화 버전) |
| `email-body.txt` | 실제 발송한 메일 본문 (플레인 텍스트, 줄바꿈 정리본) |
| `state-GOOD.txt` / `state-BAD.txt` | 정상/고장 코덱 전체 덤프 (root 소유, diff 원본) |
| `alsa-info-GOOD.txt` / `alsa-info-BAD.txt` | 정상/고장 `alsa-info.sh` 출력 |
| `lg-gram-alc298-dumps.tar.gz` | 위 4개 덤프 묶음 (메일 첨부한 것과 동일) |
| `check-audio-state.py` | **상태 판정** — COEF 0x28/0x5b 읽어 정상/고장 즉시 판정. 종료코드 0/1. `sudo` 필요 |
| `dump-codec.py` | 코덱 전체 상태 덤프 (표준 레지스터 + 벤더 COEF). `sudo python3 dump-codec.py <출력파일>` |
| `apply-coef.py` | COEF를 GOOD 값으로 복원 시도 (결과: 무음 그대로 — 참고용, 해결책 아님) |
| `func-reset.py` | HDA 함수 그룹 리셋 + 재생 경로 수동 복원 시도 (결과: 리셋 무효 — 참고용) |
| `try-reconfig.sh` | 코덱 reconfig 시도 (결과: `Device or resource busy` — 참고용) |

> `apply-coef.py`, `func-reset.py`, `try-reconfig.sh`는 **실패로 끝난 실험**. 근본 원인 조사 이력으로 남겨둔 것이며 해결책이 아님. 재실행 불필요.

---

## 7. 기기 식별 정보 (상류 회신 시 필요)

```
Machine        : LG Electronics 16Z90TP-GA5BK (board 16Z90TP)
BIOS           : Phoenix A1ZJ3340 X64, 07/15/2025
CPU            : Intel Core Ultra 5 225H (Arrow Lake-H)
Distro/Kernel  : Ubuntu 24.04.4 LTS / 7.0.0-31-generic
Codec          : Realtek ALC298  (Vendor 0x10ec0298, Subsystem 0x18540548, Rev 0x100103)
Card           : sof-hda-dsp / skl_hda_dsp_generic
SOF firmware   : intel/sof-ipc4/arl/sof-arl.ri  (booted 2.14.1.1)
SOF topology   : sof-hda-generic-2ch.tplg (ABI 3:29:1)
firmware-sof-signed : 2023.12.1-1ubuntu1.11
alsa-ucm-conf       : 1.2.10-1ubuntu5.14
Userspace      : PipeWire 1.0.5 / WirePlumber 1.0.5
SSID 1854:0548 에 매칭되는 machine-specific quirk 없음. modelname 비어 있음.
핀: NID 0x17 = 0x90170110 [Fixed] Speaker at Int / NID 0x21 = 0x03211020 [Jack] HP Out
```

---

## 8. 남은 불확실성 (평소 사용 중 확인 필요)

1. `Windows → 시스템 종료(powercfg /h off 적용) → 전원 켜기 → 우분투` 경로는 아직 직접 검증 안 됨.
   같은 원리(진짜 전원 차단)이므로 정상일 것으로 예상. 만약 이 경로에서도 무음이면
   `powercfg /h off` 미적용 가능성부터 확인 (Windows 파티션에 `hiberfil.sys` 잔존 여부).
2. 긴 절전(1시간+) 후 안전한지 미검증 (36초 절전만 테스트).

---

## 9. 관련 메모리 파일

`~/.claude/projects/-home-slihump/memory/gram-audio-fast-startup.md` — 이 문제의 요약 메모리.
이 HANDOFF와 내용 일치. 새 사실이 생기면 양쪽 다 갱신.
