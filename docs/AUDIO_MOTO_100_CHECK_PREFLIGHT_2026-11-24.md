# Audio + Moto — 100-check fixture preflight and preliminary search forecast

**Date:** 24 November 2026  
**Source:** `main` branch `test-fixtures/masters/audio/{audio.json,audio.net}` and `test-fixtures/masters/moto/{moto.json,moto.net}`, fetched through the GitHub connector and audited in the same JS implementation committed to `scripts/audit_100_audio_moto.js`.  
**Scope:** **100 checks per circuit**, comprising 90 JSON / board / component / definition / footprint / net / assignment / netlist checks and 10 explicit **search pressure** heuristics. Static analysis only. No solver was executed in the audit environment and the result does **not** certify that any particular saved board is electrically or physically build-ready.

## Run and reproduce on the Mac

```sh
cd ~/Documents/stripboard-optimiser
git pull --ff-only
node scripts/audit_100_audio_moto.js
node scripts/audit_100_audio_moto.js --json --out ~/Desktop/audio_moto_100check.json > /dev/null
```

The report writes a new output file only when `--out` is supplied. It never changes the fixture JSONs, native binaries, running WR sweep or WR result directories. Node standard library only.

### Direct audit results

| Group | IDs | Audio | Moto | What was tested |
|---|---|---:|---:|---|
| Project schema | A01–A10 | 10 pass | 10 pass | Root metadata, JSON structure and required collections |
| Board geometry/locks | B01–B10 | 10 pass | 10 pass | 24×56, both locks, no pre-saved wires/cuts |
| Component identities | C01–C10 | 10 pass | 10 pass | Component IDs, labels, rotations, off-board designation |
| Placement flags | D01–D10 | 10 pass | 10 pass | Position format, lock/edge/slide flags, pre-positioned known parts |
| Embedded component definitions | E01–E10 | 10 pass | 10 pass | Custom ID resolution, dimensions, pins and unique IDs |
| Embedded footprint details | F01–F10 | 10 pass | 10 pass | Pin offsets, body-cell coordinates, gross area feasibility |
| Net identity | G01–G10 | 10 pass | 10 pass | Net names/IDs, existence, endpoint counts |
| Assignment sanity | H01–H10 | 10 pass | 10 pass | Pin references, assignment uniqueness, component/net foreign keys |
| KiCad netlist parity | I01–I10 | 10 pass | 10 pass | Parse KiCad `.net`, compare exact `(net name, component label, pin ID)` tuples |
| Search-pressure checks | J01–J10 | **9 pass / 1 warn** | **1 pass / 9 warn** | Planning thresholds for footprint width, component count, net fanout etc. |
| **TOTAL** | **100 each** | **99 PASS / 1 WARN / 0 FAIL** | **91 PASS / 9 WARN / 0 FAIL** | **No detected input-contract failure** |

**Interpret the scores correctly:** 99/100 and 91/100 here measure how many static audit checks returned PASS, **not** whether one circuit is 99% or 91% quality. A warning is **not** a failed strict validation. The J-series thresholds are preliminary design probes, not measured feasibility cutoffs.

### Measured comparison (source-grounded)

| Indicator | Audio | Moto | Moto / Audio |
|---|---:|---:|---:|
| On-board parts | 14 | 33 | 2.36× |
| Total parts | 19 | 44 | 2.32× |
| Off-board parts | 5 | 11 | 2.20× |
| Assigned pins | 85 | 123 | 1.45× |
| Distinct nets | 29 | 35 | 1.21× |
| Largest net GND — pin endpoints | 16 | 27 | 1.69× |
| Largest net GND — components | 14 | 25 | 1.79× |
| Net connection-edge proxy, sum over nets of max(pins−1,0) | 56 | 88 | 1.57× |
| On-board parts needing built-in library definitions (not embedded in JSON) | 10 | 28 | 2.80× |
| On-board custom gross footprint rectangles, *partial only* | 380 hole-equivalents | 299 hole-equivalents | **DO NOT compare total occupancy** |

Both have a wide **22-column TFT custom footprint** that triggers J10; Moto additionally triggers J01–J08 from additional components, net fanout and connections.

**Crucial scope limitation:** many generic/built-in footprint definitions are **not embedded** in either JSON; the native engine resolves them from its library. The static script verifies every embedded custom definition and the exact JSON↔netlist assignments, but it does **not** reproduce the solver's complete built-in footprint resolver, global packing feasibility, routing repair, electrical path tracing or saved-board auditor. The known footprint area fractions exclude those built-in parts and cannot determine congestion or prove fit.

### Prediction (explicit assumptions; not measured results)

We have **measured Audio pass rates** from the completed WR sweep and only **one Moto 5k passing row reported so far**. These are not equivalent sample sizes. The figures below are a **rough scenario forecast**, not a trained predictor and not certified probabilities.

- Actual Audio strict pass rates: **113/2000 = 5.65% at 5k**, **170/2000 = 8.50% at 10k**, **215/2000 = 10.75% at 20k**.
- First reported Moto 5k strict result: **seed 0198, 50 wires / 66 cuts, score 30.54**. Completion order is asynchronous; seed number 198 does **not** mean exactly 198 attempts had completed, nor does one result establish a true pass rate.
- Moto's higher component and connectivity pressure predicts **lower strict-pass probability at the same move count**, generally more router work and worse early wire/cut counts than Audio. It does **not** prove infeasibility, the exact required moves or a physical optimum.
- If Moto 5k happens to have a ~1% true pass rate (an **illustrative assumption only**), carrying over Audio's observed *relative* 10k/5k and 20k/5k success multipliers gives Moto **about 20, 30, 38 strict passes** out of 2,000 at 5k, 10k, 20k. In a wide uncertainty scenario, e.g. assuming Moto 5k pass rate 0.5–3%, the extrapolated counts are roughly **10–60, 15–90, 19–114**. These are mathematical scenarios rather than evidence-based confidence bounds.
- **Qualitative prediction:** expect the Moto 5k 50W/66C survivor to be superseded during additional seeds / move rungs, but **do not claim a numeric eventual best board** from static input features alone. Historical `moto14wires30cuts.json` is a reference baseline, not a prediction of what these exact current sweeps will attain.
- Runtime seconds per 5k/10k/20k solve and a circuit's ideal move budget **cannot** be read from JSON alone. The future GUI should use a real native timing + feasibility probe on the target Mac, followed by empirical calibration against this corpus.

### Audit versus strict certification

`scripts/audit_100_audio_moto.js` tests **unsolved inputs** before the search. The live WR controller `scripts/run_wr_audio_moto.py` already uses `core.run_one()`, which invokes **the native V5 CLI, followed by the strict saved JSON auditor**, and retains only passes. **Do not substitute 100/100 static checks for strict saved-board validation**. No Quick Solve/Hell Mode donor engine is involved.

### Practical next step

Let the 12,000-trial sweep finish **without restarting it**. After Moto results are reported, compare measured strict-pass counts with the illustrative prediction and recalibrate a simple, honest JSON→budget recommendation for the GUI. Existing WR runner **wipes each rung's output directory** when rerun; this audit does **not**.
