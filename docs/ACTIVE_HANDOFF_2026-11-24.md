# ACTIVE HANDOFF — StripSolve (updated 25 Nov 2026)

## Current release: StripSolve GUI 2.20 / Q2 (25 November 2026)

GUI 2.20: renderer-version popup windows removed entirely; revision stamps remain in Activity and CLI stderr. Seed count appears only above the progress bar, not inside the ETA text.

The live construction score is Q2, with W = jumper count, C = cut count,
L = total jumper span in mm (2.54 mm pitch), D = nonvertical jumper count,
U = unplaced on-board component count, S = maximum simultaneous vertical
hole-to-hole overlap. S = 0 for no jumpers and 1 for unstacked jumpers.
Touching endpoints do not stack.

`Q2 = round(max(0, 100 - 0.6*W - 0.4*C - 0.02*L - 10*D - 15*U - max(0,S-1)**2), 2)`

Strict audit qualification and the native engine are unchanged. The GUI ranks
only audited passes. Q2 uses the existing campaign paths, with schema 2,
quality_version=Q2, and S and wire_length_mm in the CSV. Q1 campaigns cannot
resume or feed Pass Two; explicitly overwrite the selected old campaign to
start fresh. Do not relabel old scores. Historical WR research JSONs and
reports remain historical evidence. No score is a percent of theoretical
optimum.

The dashboard displays W/C/S/Q2, champion wire length in mm/inches, audited
outcomes, runtime and one progress/ETA control. No duplicated sidebar progress,
project/workspace box, worker count or noisy quality/complexity chart. CPU
allocation is max(1, available logical CPUs - 1); the 100-decode calibration
only estimates speed. CPU allocation is recorded in disk logs. On completion,
save winner JSON and both SVGs before the themed trophy consent dialog.
Pass Two is still an import-only stage.

See [Q2 research](QUALITY_Q2_2026-11-25.md) for the 1,053-board comparison.

**Historical 24 November snapshot follows; any older GUI status or Q formula below is superseded.**

> **START HERE IN A NEW CHAT.** This is a working-state handoff, not a proposal to rewrite the solver. Then read [README](../README.md), [documentation index](INDEX.md), and the checked-in source. The log figures below are **user-provided Mac observations**, not GitHub-hosted result files. Do not assume a running Mac job has completed since the last message.

## Current mission: Audio + Moto WR discovery, then a practical multipass GUI

- **One authorised optimiser:** existing native C/TypeScript V5 solver via `src/frontend/tests/solver/v5Solve.js` (`--native 1 --strict 1`). There is **no Route-Mate Python Quick Solve in this pipeline**. Python is a controller, not an alternative optimiser.
- **Qualification:** a candidate is a strict pass only after CLI strict success **and** `src/frontend/tests/solver/auditSavedStrict.js` checks its saved JSON against its prepared input. The saved auditor is a separate execution but reuses some project electrical/geometry helpers; don't call it a fully disjoint independent electrical oracle.
- **Current WR runner:** `scripts/run_wr_audio_moto.py` imports `scripts/run_audioex_native_ladder.py` as `core`, calls `core.run_one()` (which launches the native CLI and saved-layout auditor), then applies `score_quality()` from `scripts/run_audioex_10k_2000_quality.py` **only after** a strict pass.
- **Circuit sources:** `test-fixtures/masters/audio/{audio.json,audio.net}` and `test-fixtures/masters/moto/{moto.json,moto.net}`. Both require **locked 24×56** input boards; Audio has 85 assigned pins and Moto 123, with source/netlist counts checked before running.
- **Current WR experiment config:** `--drilled 0` (knife cuts permitted), `--drill-domain 0`, `--nostack 0` (stacked vertical jumpers permitted), `--wire-polish 0`, `--routing-preference wires`; `--strict 1 --native 1`. These are **this experiment's settings**, not universal physical rules. Don't silently change them.
- **Work:** 2,000 seeds (1–2000) × {5k, 10k, 20k} moves × {Audio, Moto} = **12,000 trials**, six groups. This is independent-seed discovery; **same seed at a higher move budget is not a saved-board warm start**.

### Mac command (from the user's local checkout)

```sh
cd ~/Documents/stripboard-optimiser
git pull --ff-only
python3 scripts/run_wr_audio_moto.py --jobs 3
```

**CRITICAL: do not casually rerun this command.** The runner **deletes and recreates the output folder at the start of each circuit/budget group**. It will wipe earlier passing JSONs in that folder, including completed Audio 5k/10k results, if run again from the beginning. There is **no `--resume`**. A new chat should first find out what is already complete before suggesting any command.

Output folders: `~/Desktop/WR_Audio/{5k,10k,20k}/` and `~/Desktop/WR_Moto/{5k,10k,20k}/`.

The user specifically wants **only passing lines** printed, every passing JSON saved, no failed-seed messages, no failed-result database, no top-10/top-20 pruning, and no resume/checkpoint subsystem. Temporary per-trial logs/rejected JSONs are discarded. A worker exception is currently treated as a silent non-pass by the controller; absent output alone isn't proof of a specific failure cause. The desktop output folders are **not checked into Git**. Do not claim to have accessed the user's Mac files.

### Latest observed WR run results (not assumed final)

| Circuit | Budget | State as last reported | Strict passes | Best reported score | Best seed | Wires / cuts |
|---|---|---|---:|---:|---:|---|
| Audio | 5k | **Completed** | **113 / 2000** (5.65%) | **70.16** | 1312 | **13W / 41C** |
| Audio | 10k | **Completed** | **170 / 2000** (8.50%) | **74.14** | 1171 | **11W / 39C** |
| Audio | 20k | **Completed per subsequently shared external review** | **215 / 2000** (10.75%) | **74.65** (score leader) | 0813 | **11W / 39C** |
| Moto | 5k | **In progress when last reported** | unknown total | **30.54** so far | 0198 | **50W / 66C** |\n| Moto | 10k, 20k | **Not yet reported** | unknown | unknown | — | — |

The **later user-supplied external review** of Audio 20k reports **215 strict passes** and **20k seed 0813 Q74.65 (11W/39C)**, with **seed 1125 Q74.18 (10W/39C)** as the **fewest-wire** candidate. Those figures are reported from the external review, **not independently checked against all 2,000 saved JSONs in this chat**. Existing Audio reference remains **10W/38C**; neither 20k candidate matches 38 cuts. The new 100-check audit targets unsolved inputs only.

**Historical reference board filenames on the user's Mac**: `~/Desktop/koala/audio10wires38cuts.json` (Audio reference **10W/38C**) and `~/Desktop/koala/moto14wires30cuts.json` (Moto reference **14W/30C**). These are **reference baselines**, not independently reaudited against the current build during this chat. Do not confuse them with the **separate MOTOEX** 27W/43C saved candidate in [the MOTOEX ladder notes](motoex-seed37-winner-ladder-2026-11-24.md).

The diagnostic quality formula is:

```text
Q = round(max(0, 100 - 0.6*wires - 0.4*cuts
                 - 0.02*wireLengthMm - 10*nonvertical - 15*unplaced), 2)
```

Length is derived from jumper endpoints using **2.54 mm per grid step**. Qualified boards must already be strict-valid. This **is a construction-cost heuristic, not a school grade or the official WR acceptance rule**. A score of 74/100 can be excellent for a circuit. Keep wires, cuts, length, and strict validity visible separately. Do not arbitrarily promise 80+ or equate Q with percent of physical optimum.

## NEW: 100-check JSON+KiCad pre-solve audit (24 Nov 2026)

- **Implemented:** `scripts/audit_100_audio_moto.js` — 100 nonmutating checks on each current Audio and Moto master JSON **and** paired `.net`; checks schema, locks, component IDs, custom footprint pins/body cells, net assignments, exact KiCad tuple parity and ten transparent complexity planning flags. Executed against the GitHub source bytes, **not** on the owner's iMac. Node standard library; run `node scripts/audit_100_audio_moto.js` after pulling.
- **Result:** Audio **99 PASS, 1 complexity WARN, 0 FAIL**; Moto **91 PASS, 9 complexity WARN, 0 FAIL**. All **90 structural/netlist checks** passed on both. J10 flags the 22-column custom TFT on both. Moto's additional flags reflect complexity, not invalid electrical input.
- **Meaningful differences:** 14 vs 33 on-board parts, 85 vs 123 pin assignments, 29 vs 35 nets, GND 16 vs 27 pins, net-edge proxy 56 vs 88. Static script does not fully resolve built-in footprint geometry (10 Audio / 28 Moto on-board parts use built-ins), run the native optimiser, or certify solved-board routing.
- **Prediction:** Moto likely has a lower strict-pass rate and worse initial W/C at comparable 5k/10k/20k budgets. A deliberately **illustrative 1% Moto 5k baseline** with Audio's measured budget multipliers gives ~**20/30/38** passes out of 2,000 at 5k/10k/20k; **not a statistical forecast**. Moto 5k first *reported* success was seed 0198, **50W/66C, Q30.54**, without an established full pass rate. Details and caveats in [100-check report](AUDIO_MOTO_100_CHECK_PREFLIGHT_2026-11-24.md).
- **Do not touch the running WR sweep** to run the static audit. It reads fixtures only. Avoid a rerun of WR controller because that deletes prior passing outputs.

## Nick's Fantastic Ideas Basket (not implemented)

The future GUI calibration idea and optometrist comparison are recorded in [the ideas basket](NICKS_FANTASTIC_IDEAS_BASKET.md). On JSON load, five separate native timing probes at **5k/10k/15k/20k/25k moves**, **seed 69**; estimate per-project time/move and recommend budgets before starting multipass. This is a *speed probe* only; no claim of optimal quality from one seed. Do not run it via the destructive WR sweep controller.

## Multipass plan — a practical thought experiment, NOT built yet

Goal: use the six WR datasets to choose smarter search effort and ultimately drive the native engine from the GUI; **quality/strict legality matters more than raw speed**, with a simple human-readable UI. The project owner explicitly rejected an excessively academic/committee-style process. Grok's peer reviews are **ideas for consideration, not approved specifications**.

1. **Pass 1 — Discovery:** many independent native seeds at evidence-informed budgets; retain **all** strict-passing layouts and their full JSONs. Current 12k corpus is this experiment.
2. **Pass 2 — Additional search:** use observations on budget success, late bloomers, quality and layout diversity to allocate higher-budget attempts. There are competing proposed policies: **universal participation** versus **priority-weighted CPU with fresh-seed exploration**. **No final allocation rule or budgets have been chosen.** Same-seed reruns at higher budgets are new searches, **not** board refinement until warm-start exists.
3. **Grand Final — 1v1 Mortal Komabat:** a strictly qualified challenger goes against the reigning best board; keep the winning champion and every valid loser JSON, independently recheck any proposed new WR, and apply an agreed **official record-comparison rule** (not Q alone). The record metric/tie-break order still needs explicit agreement.
4. **GUI:** existing Route-Mate PySide6 import/preview/spacing/individual Fixed-Movable-Edge-Slide review is present; **native CLI solve adapter / Pass 1 / Pass 2 are NOT connected**, GUI stops before Pass 1. Do **not** add donor Quick Solve, Hell Mode or another Python placement/router.

Desired optional GUI **commentary/theme** for the 1v1 final (not implemented):
- 🦂 “GET OVER HERE!!!” when the challenger attacks/takes the lead.
- 🩸 “FIRST BLOOD!” for a clear metric win; 🩸🩸 “DOUBLE DAMAGE!”; 🩸🩸🩸 “TRIPLE DAMAGE!”.
- 💀 “FINISH HIM!!!”; 🏆 “FLAWLESS VICTORY!!!” if a strictly valid challenger wins on **all** agreed comparison dimensions; 👑 “NEW WORLD RECORD — FATALITY!!!” **only if** a frozen record is actually beaten and verified.
- The user likes clean, entertaining **emoji progress logs without failures**; this theatre must not replace correct technical metrics or falsely announce records.

## Corrections already settled — do not revive these mistakes

- A prior external reviewer (**DeepSeek**, jokingly “Deep Creep”) misread the repo and claimed the WR Python script used Route-Mate `quick_fit`. **False.** It invokes native V5 through `core.run_one()`; the reviewer retracted the claim after checking the exact call chain.
- A separate **drill-ON forensic** Audio study reported **3/50** audited strict passes at 20k with drill-domain / bypass flags. This is **not the same configuration** as the drill-OFF 12k WR study; do not merge pass rates, call them different solvers, or infer a causal performance ratio from a tiny non-equivalent sample.
- Saved-board audit is **already in** the WR runner. Don't propose a redundant “first ever audit of seed 1171” as though its strict qualification was never performed.
- The historic project audit `docs/REPOSITORY_AUDIT_2026-11-24.md` describes a static Git snapshot and may use an earlier GUI number. Current GUI version lives in `gui/VERSION` (**2.04** at writing); repo release remains **2.00**.
- The forensic drill-ON analysis also raised `lockedBoardKept: false` for some rejected candidates. If investigated, inspect original saved forensic records, not guesses. This isn't evidence that an invalid board passed the WR gate.

## Next steps when the owner asks

1. **Do not interrupt or restart the Mac sweep.** Ask for/follow the user's new results if needed; remember a rerun destroys already saved per-group passes.
2. Once complete, analyse the six pass-only directories (get the JSONs or logs from the user). If only pass-only outputs exist, calculate pass rates from completed 2,000-seed groups; don't assume an interrupted group completed.
3. Agree a **simple** Pass 2 selection/allocation strategy and official WR ranking for the GUI, without changing the frozen native solver by accident.
4. When explicitly asked to code, implement and test a thin **GUI → existing native CLI → strict saved-board audit** adapter and then the 1v1 Grand Final UI.

## Collaboration style / boundaries

- The owner likes concise, direct answers, visible verified GitHub commits when code/docs are changed, and *minimal commentary*. Swearing, pirate jokes and Mortal Kombat-style commentary are welcome in this project.
- **Do not** silently assume Drill ON/OFF, stacking, ranking rules, directory retention or extra functionality; user objected to unrequested resume, failure logs and protective folder checks.
- No speculative “I'll do it later”: carry out requested GitHub edits now if authorised. Target Mac filesystem is **not remotely accessible** from this chat. Be precise about what was code-inspected versus user-reported.
- **Steal with pride 🏴‍☠️, but read the fucking call chain.**
