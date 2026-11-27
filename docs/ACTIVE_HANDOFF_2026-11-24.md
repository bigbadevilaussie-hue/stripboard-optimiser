# ACTIVE HANDOFF — StripSolve (updated 27 Nov 2026)

**Current AI entry point:** [../aihandover.md](../aihandover.md). This dated file retains historical evidence; follow the root handover for current status and next actions.

## 27 November — latest verified repository and research status

Read [Karl forensic checkpoint](KARL_FORENSICS_2026-11-27.md) first. Main-only rule enforced; all four former branches merged and deleted. 100 Mortal Kombat saved boards and both forensic scripts are in main. Championship finished 234–216 (1216 wins), 25 strict passes, best strict Q3 85.66 (1859 at 500k). No Q86 result. No production solver or GUI change; GUI 2.39 / Q3 remains current.

Current research: fixed-placement wire surgery and independent copper-graph replay, one worker, no extra annealing or board growth. Script syntax checked, runtime replay not yet verified. Five source findings are documented with limits; do not claim fixes or measured gains. Earlier campaign snapshots below are historical, not instructions to resume old runs. No new branches, PRs or upstream reports. Local uncommitted files are preserved. No new test result after consolidation.

## Current release: StripSolve GUI 2.39 / Q3 (25 November 2026)


## 26 November 2026 — HISTORICAL V1.40 LADDER AND SAVE-GAME RESEARCH

Read [V1.40 ladder forensics and MAME-style warm-start design](MOTO_V1_40_LADDER_AND_WARM_START_2026-11-26.md) before continuing this work.

- Owner's local standalone V1.40 ladder: 500 seeds per rung, 2k–30k in 2k steps, three workers, 7,500 planned trials. Last reported 2,318 completed, all FAIL, zero strict/diag passes and zero ERROR rows. 476 electrically complete, 334 otherwise valid routing-only near-misses. Latest report is partial 10k, not the final campaign. Do not interrupt or rebuild the active run.
- Frozen [three-way wager](MOTO_V1_40_WR_WAGER_2026-11-26.md) is a separate 2,000 × 20k strict-only batch; Claude 78.56, GPT Sister 79.76, ChatGPT 80.72. No wager changes.
- Confirmed standard non-Edge board-lock enforcement weakness; routing faults dominate the partial data. Replay matched seeds and old input controls before attributing a regression. No solver fix implemented.
- Owner's new Pass Two concept: each strict survivor has a MAME-style `.sav` (winning genome plus verified board); LOAD → controlled reheat → audit → retain the better result. Warm-start research first, exact checkpoint later. Experimental hook, format, round-trip and regression gates documented in the new note. **Not implemented. GUI Pass Two remains import-only; no production solver/GUI changes.**

## 26 November 2026 — LAST REPORTED MAC REGRESSION STATUS

- The owner reports the Mac Python GUI regression suite now passes after the fixes to the **Slide/EXPERIMENTAL** label and dashboard return-to-board fallback; the immediately preceding run had 2 failures among 129 Python tests.
- The owner also reported **"All 7 suites passed"** from `src/frontend` after running `npm run test:headless`. This is owner-provided target-Mac evidence, not an assertion that a separate packaged app, full 5k-seed campaign, or new world record has passed.
- Native candidate policies and the research runner were merged into **`main`** at `7d24708`. GUI regression fixes were committed to **`main`** at `e51b657`. [Policy details and commands](CANDIDATE_POLICIES.md), [changelog](../CHANGELOG.md).
- The opt-in CLI accepts `--candidate-policy strict|diagonal|crossings|archive` **only with** `--strict 1`. The native result's candidate prequalification is diagnostic; the saved-board audit determines research acceptance. Default strict behaviour and final build-ready verification remain strict. The existing GUI Pass One is unchanged, and GUI Pass Two **still does not perform an optimisation search**.
- The **previous Moto 5,000-seed diagonal hunt was stopped manually**, not completed. Last observed evidence: **369 recorded trials**, **3 strict passes**, **349 archived candidates with diagonal-related flags**, with many also failing other electrical/physical rules. Do not infer those candidates are electrically complete; do not claim the new policy has recovered a historical WR.
- New isolated controller: `scripts/run_candidate_hunt.py` (default 5,000 seeds / 10k moves / 2 workers; resumable; class-specific champions and audit records). Prefer a fresh **10-seed smoke campaign** before 5,000 trials. **Do not rerun the old destructive WR Audio/Moto script** or overwrite the stopped Moto results.
- Repository collaboration rule from owner: **make future approved changes directly on `main`; do not create feature branches or new pull requests**.

**Current release:** GUI **2.39 / Q3**; this research-policy addition is not a GUI feature-version bump. The earlier dated notes below remain useful historical evidence but may describe superseded GUI budget or Pass Two plans.


Budget recommendation: [100-point JSON complexity sniff](JSON_SNIFF.md). CPU allocation is separate; no native decodes or qualification trials run before GO.

**Historical GUI 2.26 budget policy (superseded by GUI 2.39):** The prior speed probe and actual-JSON qualification budget probe are documented in [budget probe](BUDGET_PROBE.md), but **current GUI 2.39 uses the static 100-point JSON complexity sniff before GO**. Locked Edge decoder selection remains separate. No Slide search or change to strict GUI qualification.

macOS standalone build: [build_mac_app.sh](../build_mac_app.sh) adapts the Mac-tested Route-Mate packaging workflow to StripSolve, including the native V5 CLI, Node, SVG renderers, librsvg converter and approved artwork. See [STANDALONE_MACOS.md](STANDALONE_MACOS.md). Packaged Work lives in `~/Library/Application Support/StripSolve/Work/`; source checkout Work is unchanged. The new StripSolve bundle is not yet Mac-verified.

GUI 2.26 gives Open/Save file-dialog navigation buttons a 22 px icon and dedicated compact padding, preserving the Arctic Ice theme. Pass One completion updates the status bar before the winner-consent popup; viewing a winner may then show its own status.

GUI 2.26: the run-outcomes ring shows campaign completion (definitive PASS + FAIL divided by scheduled seeds). Qualification rate is displayed separately, to one decimal. Errors remain retryable, not completed seeds.

GUI 2.26 uses plain-English quality and construction labels, displays the live audited pass rate to one decimal place (excluding errors and pending seeds), and separates elapsed time from estimated remaining time. The winner dialog displays actual verified metrics and freezes the campaign timer before the user decides whether to view the saved board. Q3 is the current scoring version; the CSV structure is unchanged.

GUI 2.26: renderer-version popup windows removed entirely; revision stamps remain in Activity and CLI stderr. Seed count appears only above the progress bar, not inside the ETA text.

The live construction score is Q3, with W = jumper count, C = cut count,
L = total jumper span in mm (2.54 mm pitch), D = nonvertical jumper count,
U = unplaced on-board component count, S = maximum simultaneous vertical
hole-to-hole overlap. S = 0 for no jumpers and 1 for unstacked jumpers.
Touching endpoints do not stack.

`Q3 = round(max(0, 100 - 0.4*(0.6*W + 0.4*C + 0.02*L + 10*D + 15*U + max(0,S-1)**2)), 2)`

Strict audit qualification and the native engine are unchanged. The GUI ranks
only audited passes. Q3 uses the existing campaign paths, with schema 2,
quality_version=Q3, and S and wire_length_mm in the CSV. Q1/Q2 campaigns cannot
resume or feed Pass Two; explicitly overwrite the selected old campaign to
start fresh. Do not relabel old scores. Historical WR research JSONs and
reports remain historical evidence. No score is a percent of theoretical
optimum.

The dashboard displays W/C/S/Q3, champion wire length in mm/inches, audited
outcomes, runtime and one progress/ETA control. No duplicated sidebar progress,
project/workspace box, worker count or noisy quality/complexity chart. CPU
allocation is max(1, available logical CPUs - 1); the 100-point JSON sniff
assesses board complexity and recommends 10k/20k, without solver calls. CPU allocation is recorded in disk logs. On completion,
save winner JSON and both SVGs before the themed trophy consent dialog.
Pass Two is still an import-only stage.

See [Q3 calibration and archive comparison](QUALITY_Q3_2026-11-25.md) for the formula, research evidence and reproducible rescoring command. Target range 85–95 (default 90) is reserved for a future independently verified stopping policy in Pass Two/Grand Final; Pass One runs all selected seeds.

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


## Board display diagnostic (2.26)

GUI 2.26 diagnostic: component and mirrored copper previews now use the same 2400 px librsvg → PNG display path as schematic, with a bounded cache. Original SVG bytes go directly to librsvg; the Qt-only text CSS overrides are removed. QtSvg fallback is logged in Activity. Standalone SVG generation, Python overlays, exports and solver remain unchanged. This isolates display-backend effects from Karl's print-vs-interactive renderer differences; visual parity is not yet established. See [details](BOARD_PREVIEW_BACKEND.md).


GUI 2.27 restores Open Solved as an idle-only, read-only JSON preview. It opens both sides in a separate BoardView with the same librsvg pipeline, Fit and zoom controls; it does not enter project preparation, change the active campaign or certify the imported board.
