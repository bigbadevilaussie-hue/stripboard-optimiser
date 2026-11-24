# 🧺 Nick's Fantastic Ideas Basket

Ideas for the Stripboard Optimiser to revisit when the current native solver and GUI integration are ready. **Ideas only — not implemented or approved engineering specifications.** Keep this separate from the live WR sweep, which must not be interrupted.

## 🦂 Idea 001 — Seed 69 auto-calibration when a JSON is loaded

**Added:** 24 November 2026  
**Implementation status:** Standalone **native CLI seed-69 probe implemented** as `scripts/probe_seed69.py`. **GUI auto-run/pop-up/caching/recommendation not implemented.**  
**Nick's concept:** “When we load the JSON, pop up ‘Calibrating the optimizer please hold’. Then we do 5k, 10k, 15k, 20k and 25k on 1 seed only. Pick 69 cos it's funny. Then make some slash thingo. Then get going.”

### Experience

1. The human loads a project JSON in the GUI and completes any necessary preparation/lock review.
2. GUI displays **“⚡ CALIBRATING OPTIMISER — PLEASE HOLD 🦂”** and a simple five-step progress display.
3. Run **five separate native V5 solver probes**, on **the same prepared input and policy**, with **seed 69**:
   - **5,000 moves**
   - **10,000 moves**
   - **15,000 moves**
   - **20,000 moves**
   - **25,000 moves**
4. Record actual wall/solve times, and optionally whether each probe achieved an **independently audited strict pass** and its W/C/length; the primary goal is **speed calibration**, not to crown the single seed's result. Do not declare these probes a statistically sufficient quality study.
5. The **“slash thingo”**: estimate `seconds ≈ startup/finish overhead + moves × time_per_move`. Use a simple measured slope/robust fit, acknowledge outlier routing-repair time, and compute indicative moves per second and projected time per trial.
6. Use the measured timing plus selected worker count and empirical Audio/Moto WR experience to propose **Pass 1 / Pass 2 budgets and expected runtime** for the current machine and circuit. Let the human override. Then start the **existing native CLI + saved-board strict auditor** from the GUI.
7. Optionally cache the calibration under a fingerprint of the **prepared JSON + locks/settings + native binary/version + machine environment**, so a repeat open can reuse genuinely compatible measurements. Offer recalibration rather than pretending an old estimate is current.

### Rules / cautions

- **Only one solver:** Python/GUI may orchestrate, but no alternative Python Route-Mate Quick Solve/Hell Mode. Native CLI `v5Solve.js --native 1 --strict 1`, and `auditSavedStrict.js` for any saved-board strict claims.
- The **seed is deliberately 69** (because Nick said so 😂); same-seed runs at different move budgets are **independent solves, not warm starts or guaranteed progressive improvements**.
- This is a **runtime probe**. One seed cannot establish strict-pass probability, a best move budget, or a guaranteed world record. Source complexity from [100-check JSON audit](AUDIO_MOTO_100_CHECK_PREFLIGHT_2026-11-24.md) can inform recommendations but does not substitute for measured speed.
- Preserve the user's circuit JSON, current WR saved layouts and running sweep. Never launch or restart `scripts/run_wr_audio_moto.py` for calibration: its output directories **are wiped per budget rung**. Probes need isolated scratch folders.
- The existing **PySide6 GUI 2.04 currently stops before Pass 1**. Pop-up, five probes, estimation, cache and automatic launch are **future GUI work**, not live features.
- If the user explicitly changes drilling/stacking/board locks, reuse only calibration matching those settings.
- Keep dialogue concise, logs entertaining and metrics real. Sample celebration: “🦂 SEED 69 — GET OVER HERE!!! 🩸 CALIBRATION COMPLETE!”

### Why this idea is useful

JSON topology alone cannot predict how quickly the actual native solver can run on the user's CPU. Five short probes provide machine-and-project-specific timing evidence before committing to large multipass sweeps. Pair the timing with observed success rates to make a recommendation, not a blind universal move count.

### Run the standalone probe safely

```sh
cd ~/Documents/stripboard-optimiser
git pull --ff-only
python3 scripts/probe_seed69.py                  # Moto by default
# python3 scripts/probe_seed69.py --circuit both # Audio + Moto, five runs each
```

**Protection:** creates a fresh `~/Desktop/Seed69Calibrations/` subdirectory with logs, candidate layouts, audit results, CSV, per-circuit summaries, SHA256 manifest; **never deletes or writes to** `~/Desktop/WR_Audio` or `~/Desktop/WR_Moto`. Refuses by default while `run_wr_audio_moto.py` is running, to avoid distorted timings or CPU contention; `--allow-concurrent` is available for an intentionally under-load experiment. It does **not** run automatically on JSON load yet. Runs must be performed on the owner's Mac to get genuine performance.

## Other candidate ideas noted (not yet designed)

- **👓 Optometrist Grand Final:** switch between two **strictly qualified** board previews, copper/component side, and let the human pick which one is easier to build (“Number one… or number two?”). Keep both saved JSONs and separate the human preference from numeric Q and official WR claims.
- **🩸 Mortal Komabat 1v1 commentary:** GET OVER HERE / FIRST BLOOD / FINISH HIM / FLAWLESS VICTORY only when actual verified metric changes justify it. Pure UI theatre; never changes strict qualification.
