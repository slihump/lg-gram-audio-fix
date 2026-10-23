Subject: [BUG] LG gram 16Z90TP (ALC298, SSID 1854:0548): internal speakers
         silent after warm reboot from Windows; vendor COEF regs 0x28/0x5b latched

Hi,

I am reporting a reproducible internal-speaker failure on an LG gram laptop with
a Realtek ALC298 behind Intel SOF (skl_hda_dsp_generic). I have narrowed the
difference between the working and failing states down to six vendor COEF
registers and would appreciate guidance, as two of them appear to be latched in
hardware and I cannot find any way to clear them from the driver side.

================================================================================
1. SUMMARY
================================================================================

After booting Windows and then performing a *warm* reboot ("Restart") into
Linux, the internal speakers are completely silent. Everything the driver
exposes reads as correctly configured: the speaker pin is unmuted, its pin
control is set to OUT, EAPD is enabled, the DAC has the stream assigned, all
mixer controls are on, and the PCM reaches RUNNING with hw_ptr advancing
normally. There is simply no audible output.

A *cold* boot (full power off, then power on) always restores sound. A warm
reboot from Linux to Linux also works, because Linux leaves the codec in a good
state. Only the "last OS that ran was Windows" case fails, and only because a
warm reboot never removes power from the codec.

Headphone output could not be tested (no 3.5 mm device available). USB-C
headphones work, but they bypass the codec entirely.

================================================================================
2. SYSTEM
================================================================================

Machine        : LG Electronics 16Z90TP-GA5BK (LG gram 16, board 16Z90TP)
BIOS           : Phoenix A1ZJ3340 X64, 07/15/2025
CPU            : Intel(R) Core(TM) Ultra 5 225H (Arrow Lake-H)
Distro         : Ubuntu 24.04.4 LTS
Kernel         : 7.0.0-31-generic (#31~24.04.1-Ubuntu SMP PREEMPT_DYNAMIC)
Codec          : Realtek ALC298
  Vendor Id    : 0x10ec0298
  Subsystem Id : 0x18540548      <-- no machine-specific quirk matches this
  Revision Id  : 0x100103
Card           : sof-hda-dsp / LGElectronics-16Z90TP_GA5BK-0.1-16Z90TP
Machine driver : skl_hda_dsp_generic
SOF firmware   : intel/sof-ipc4/arl/sof-arl.ri, booted version 2.14.1.1
SOF topology   : intel/sof-ipc4-tplg/sof-hda-generic-2ch.tplg (ABI 3:29:1)
firmware-sof-signed : 2023.12.1-1ubuntu1.11
alsa-ucm-conf       : 1.2.10-1ubuntu5.14
Userspace      : PipeWire 1.0.5 / WirePlumber 1.0.5

/sys/class/sound/hwC0D0/modelname is empty and no fixup/quirk messages appear in
dmesg, so this machine runs through the generic ALC269-family path.

Pin configuration as parsed by the driver (identical in both states):

  snd_hda_codec_alc269 ehdaudio0D0: autoconfig for ALC298:
      line_outs=1 (0x17/0x0/0x0/0x0/0x0) type:speaker
      speaker_outs=0 (0x0/0x0/0x0/0x0/0x0)
      hp_outs=1 (0x21/0x0/0x0/0x0/0x0)
      mono: mono_out=0x0
      inputs: Mic=0x18

  NID 0x17 = 0x90170110 [Fixed] Speaker at Int  (internal speaker)
  NID 0x21 = 0x03211020 [Jack]  HP Out at Ext Left
  NID 0x14, 0x1a, 0x1e = 0x411111f0 (not connected)

================================================================================
3. REPRODUCTION
================================================================================

  1. Boot Windows (dual boot on the same machine). Sound works there.
  2. From Windows, choose "Restart" (a warm reboot; note that Windows Fast
     Startup is NOT involved, since Fast Startup only applies to Shutdown).
  3. Boot into Linux.
  => Internal speakers are silent for the entire session.

  4. Full power off, wait ~15 s, power on, boot Linux.
  => Internal speakers work again.

100% reproducible in both directions, verified over several cycles.

A convenient side indicator that Windows ran last: the boot timestamp recorded
in utmp differs from the uptime-derived boot time by exactly the local UTC
offset (+9 h here), because Windows writes localtime to the RTC. Every session
showing this skew was silent; sessions without it were fine. (This indicator
disappears once RealTimeIsUniversal is set on the Windows side, which does not
affect the audio symptom itself -- a session with the registry value set and no
clock skew still reproduced the silence.)

================================================================================
4. KEY FINDING: ONLY VENDOR COEF REGISTERS DIFFER
================================================================================

I dumped the full codec state in a known-good session (cold boot) and in a
failing session (warm reboot from Windows), using HDA verbs issued through
/dev/snd/hwC0D0 (SET_COEF_INDEX 0x5 then GET_PROC_COEF 0xc on NID 0x20 for the
coefficients).

The two dumps are byte-identical except for six COEF registers. Pin controls,
EAPD state, amplifier gain/mute values, power states, connection selects, GPIO
mask/dir/data, the complete /proc/asound/card0/codec#0 dump and full amixer
output are all identical.

  COEF index | good (cold boot) | bad (warm reboot from Windows) | writable
  -----------+------------------+--------------------------------+----------
    0x22     |      0x0039      |             0x0000             |   yes
    0x23     |      0x23ff      |             0x0000             |   yes
    0x25     |      0x0001      |             0x0000             |   yes
    0x26     |      0xb001      |             0x3000             |   yes
    0x28     |      0x0000      |             0x003f             |   NO
    0x5b     |      0x0000      |             0x4342             |   NO

COEF indices 0x00-0x7f were scanned; all other indices matched.

================================================================================
5. WHAT I TRIED (all failed)
================================================================================

a) Restored 0x22, 0x23, 0x25, 0x26 to their known-good values.
   The writes verified correctly on read-back, but the speakers stayed silent.

b) Tried to write 0x28 and 0x5b.
   The verbs are accepted without error, but the registers do not change. They
   read back the failing values. They appear to be read-only status registers or
   hardware-latched state.

c) Codec reconfiguration via /sys/class/sound/hwC0D0/reconfig:
     write error: Device or resource busy
   The codec is bound as a component of the SOF/ASoC card, so the legacy HDA
   reconfig path is unavailable.

d) HDA function group reset (AC_VERB_SET_CODEC_RESET, verb 0x7ff on NID 0x01):
   The verb is accepted without error, but nothing is actually reset -- values I
   had written to 0x22/0x23 immediately beforehand survived the reset unchanged.
   Manually restoring the whole playback path (power states, pin controls,
   amplifier mute/gain, EAPD, connection select, COEFs) afterwards still gave no
   sound.

e) PCI-level cold re-initialisation of the audio controller
   (unbind/bind 0000:00:1f.3 on sof-audio-pci-intel-mtl): firmware and topology
   reload cleanly, the ALC298 autoconfig output is identical to a fresh boot,
   but the speakers remain silent. This does not remove power from the codec.

Also ruled out by measurement, in case it helps: hardware failure (speakers work
under Windows), mute/volume state, PipeWire/WirePlumber (restarting the stack,
and playing via ALSA directly with plughw:0,0, hw:0,0 and the deep-buffer PCM
plughw:0,31 with all mixers at 100%), UCM (bypassed by the direct hw access),
a kernel regression (audio init logs for 7.0.0-30 and 7.0.0-31 are identical),
SOF firmware/topology integrity (dpkg -V clean), and
snd_hda_intel.power_save (setting it to 0 changed nothing; after the cold boot
that restored sound it was back at the default 1).

================================================================================
6. QUESTIONS
================================================================================

  1. Are COEF 0x28 and 0x5b on ALC298 known to be writable at all, and is there
     a documented unlock sequence or a different coefficient page/NID
     (e.g. a coefex NID) that should be used to reach them?

  2. Is there any supported way to force a genuine codec re-initialisation when
     the codec is bound to an ASoC card, given that reconfig returns -EBUSY and
     verb 0x7ff appears to be a no-op here?

  3. If the values above look like a plausible speaker-path configuration, would
     a machine quirk for SSID 1854:0548 that programs the known-good COEF values
     during codec init be the right fix? I am happy to test patches -- the
     failure is trivially reproducible on demand.

alsa-info output is available from both a working session and a failing session,
along with the two full codec/COEF register dumps referenced above. The failure
has been reproduced on demand several times in both directions.

Thanks for your time.
