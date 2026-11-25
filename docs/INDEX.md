# Documentation index — Version 2.00 / StripSolve GUI 2.23

## Start here (current authority)

- [Q2 construction-quality research and current contract](QUALITY_Q2_2026-11-25.md)

**New chat / current live work:** [ACTIVE HANDOFF — Audio + Moto WR sweep, multipass and GUI status (24 Nov 2026)](ACTIVE_HANDOFF_2026-11-24.md). This is the most current conversation handoff; older research notes below are dated historical evidence.

1. [README](../README.md) — install, current architecture and commands
2. [Project contract](../project.md) — accepted native pipeline and rules
3. [Full repository audit, 24 Nov 2026](REPOSITORY_AUDIT_2026-11-24.md) — verified static findings, known gaps, target-Mac test matrix
4. [Route-Mate GUI integration](../gui/README.md) — current native Pass One, Q2 dashboard and import-only Pass Two
5. [Standalone renderers](../src/frontend/standalone-renderer/README.md) — Node SVG CLI usage
6. [Headless solver](../src/frontend/README.md) — builds and strict CLI verification

## Static 100-check Audio/Moto input audit (24 Nov 2026)

- [Results, detailed coverage and search-outcome prediction](AUDIO_MOTO_100_CHECK_PREFLIGHT_2026-11-24.md) — 100 checks per circuit using `scripts/audit_100_audio_moto.js`; Audio 99 PASS / 1 planning WARN, Moto 91 PASS / 9 planning WARN, **zero input-contract FAILs**. Pre-solve only; not strict saved-board certification.

## Nick's Fantastic Ideas Basket

- [🧺 Seed 69 GUI calibration + optometrist board comparisons](NICKS_FANTASTIC_IDEAS_BASKET.md) — ideas only, **not implemented**.

## Active WR experiment — Audio and Moto

- [WR 12k discovery + native call chain + last reported results + safe-use warning](ACTIVE_HANDOFF_2026-11-24.md). This **passes-only runner wipes output directories on rerun**, has no resume, and is separate from AUDIOEX's resumable forensic ladder.

## Active AUDIOEX experiment

- [Fixed BMS overhang native 270-trial ladder](audioex-fixed-bms-native-ladder-2026-11-24.md):
  24×56, BMS row −2/col 24 locked, Edge ON/Slide OFF, knives/stacking
  permitted; full strict archive, top five and resumable Mac invocation

## Source / architecture references

- [Route-Mate code reuse & GUI handover](Route-Mate_GUI_Code_Handover.md):
  **donor historical reference**, not approval to run a Python solver
- [Native solver / Route-Mate roadmap](route-mate-native-solver-integration-roadmap.md):
  original architecture decision; the GUI import-only transplant has since occurred
- [Native solver handoff](START_HERE_NATIVE_SOLVER_HANDOFF_2026-11-24.md):
  historical solver research checkpoint, not an always-current release status

## Immutable research notes (historical as dated)

- [Native CLI audit (23 Nov)](cli-audit-2026-11-23.md)
- [Native benchmark](native-solver-benchmark-2026-11-23.md)
- [Native budget sweep](native-cli-budget-sweep-v161.md)
- [MOTO C1 correction](moto-c1-correction-v162.md)
- [Native AUDIO ladder](native-audio-ladder-v163.md)
- [Native speed lab v1.64](native-speed-lab-v164.md)
- [Native speed lab v1.65](native-speed-lab-v165-results-and-followup.md)
- [MOTOEX locked USB regression](motoex-locked-usb-24x56-regression.md)
- [Native Edge + Slide](native-edge-slide-motoex.md)
- [Native fixed USB sweep](native-fixed-usb-200x25k-sweep.md)
- [Native full-slide sweep](native-full-slide-200x25k-sweep.md)
- [MOTOEX seed-37 winner ladder](motoex-seed37-winner-ladder-2026-11-24.md)
- [Conflict-directed slide and routing research](research-conflict-directed-slide-and-routing-2026-11-24.md)

Research notes record results, hypotheses and status **at the time written**.
Do not use a historical “next step” or version number as the current GUI
integration status. Current authority is this index, the latest audit,
`gui/VERSION` and the checked-in source. GUI features that have not been
wired to the native CLI remain disabled.
