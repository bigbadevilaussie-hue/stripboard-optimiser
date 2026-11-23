# MOTO / MOTOMIX C1 capacitor input correction — v1.62

**Scope:** native CLI test inputs, MOTO schematic JSON and netlists, local stored project copies. **The Tkinter GUI and native annealing algorithms are unchanged.**

## Correct value and observed effect

The user identified a schematic value error: the **C1 polarized capacitor** immediately after the fuse was labelled `1000mf` instead of the intended **1000 µF**. C4 is a different capacitor and remains **15 pF**. The mistake was visible in the schematic screenshot and was confirmed in the tracked MOTO files.

`parseCapacitance("1000mf")` returns **1 F**; `parseCapacitance("1000µF")` returns **0.001 F**. For the editor's radial electrolytic body model, `canDiameter` maps the old value to **16 mm** and the corrected value to **10 mm** (a model estimate, not a measurement of the real capacitor). This changes the packing/obstacle geometry and may change solver outcomes even though the electrical nets are unchanged.

The tracked source corrections committed to GitHub are:

- `test-fixtures/masters/moto/moto.json` — component `C1`, UUID `867a45fb-f2cc-4ea6-b8fc-71ccd51ee464`: value `1000mf` → `1000µF`.
- `test-fixtures/masters/moto/moto.net` — only the `(comp (ref "C1") (value ...))` entry changes to `1000µF`.

**C4 stays `15pf`.** The footprint in the KiCad netlist remains `CP_Radial_D5.0mm_P2.50mm`. This physical footprint label may not correspond to the actual purchased 1000 µF part; its dimensions **must be verified separately** rather than changed without a part datasheet.

The repository's `motomix.json` is **not Git-tracked** on `main`; it was an untracked Mac-local benchmark input. Other user copies may live in `~/Documents`, `~/Downloads`, or `~/Desktop`. The code changes here do not remotely edit those Mac files; run the local migration below.

## Safe local update for every active MOTO/MOTOMIX copy

```bash
cd ~/Documents/stripboard-optimiser && \
git pull --ff-only origin main && \
python3 -m py_compile scripts/fix_moto_c1.py scripts/benchmark_drill_stack.py scripts/tests/test_moto_c1.py && \
PYTHONPATH=scripts python3 -m unittest discover -s scripts/tests -p 'test_moto_c1.py' -v && \
python3 scripts/fix_moto_c1.py --apply
```

`scripts/fix_moto_c1.py` searches recursively across the repository and the user's `~/Documents`, `~/Downloads`, `~/Desktop` by default. It considers `moto*.json` and `moto*.net`, plus JSON/netlist files inside `moto` and `motomix` directories; it **only changes C1 when the previous value is exactly `1000mf` (case-insensitive)** and an unambiguous component/reference match is present. It leaves C4, all other components, wire/cut arrangements, net assignments and board dimensions unchanged. Files already corrected are identified and skipped.

Before changing any local file, the updater copies its original bytes into `~/Desktop/stripboard_c1_originals/` (preserving the original path under that directory), validates the backup, and atomically writes the corrected source. It generates `c1_migration_manifest.json` containing original and corrected SHA256 hashes and paths. An ambiguous C1 value, unexpected duplicate, or malformed JSON is reported rather than guessed at. For additional folders, run `python3 scripts/fix_moto_c1.py --apply --root /path/to/other/folder` (repeat `--root` if needed). Without `--apply`, the command is a read-only dry run.

### World-record (WR) solve provenance — explicitly flagged

**The user's earlier WR MOTO solve was obtained using the erroneous `C1 = 1000mf` source value and the editor's oversized **16 mm** capacitor body model (versus **10 mm** for the corrected `1000µF` input).** Treat it as a **historical WR under the old, incorrectly specified fixture**, not as a corrected-input reference result. Do not silently reclassify the old solve as a new corrected-input record, mix its scores with fresh v1.62 runs, or delete its original file.

Since the wrong capacitor body was **larger**, the historical result may still be buildable with a smaller actual component; its electrical correctness and actual purchased capacitor footprint need separate checking. This provenance warning alone does **not** establish that its wiring is invalid. The next WR should be measured on the corrected fixture and explicitly labelled with the new input revision and source hash.

**Mac-local correction confirmed from user log:** 5/5 migration tests passed, **33 files updated**, archived 80-run/36-run outputs were skipped, and a subsequent dry-run reported **0 remaining matches requiring correction** among scanned candidates. Files in `Desktop/Route-Mate/benchmarks/moto/` reported `Other C1 value` were **left untouched deliberately**; that message does not establish their C1 equals `1000µF`. Preserve existing named quality baselines/WR files rather than rewriting their provenance.

### Historical benchmark provenance

The original **80-run/36-run** benchmarks were computed using the old C1 value in their source snapshots. Their saved layouts and `sig` fingerprints are **historical evidence for that old input**, not valid goldens for the corrected input. The local updater deliberately skips `stripboard_drill_stack_80*`, `stripboard_baseline_80*`, `cli_profile_v160*` and `cli_budget_sweep_v161*` archive directories. This is not a partial source correction: it is necessary to avoid silently contaminating immutable measurements.

The native `scripts/benchmark_drill_stack.py` now requires **C1 = `1000µF` in both MOTO and MOTOMIX** before running. It defaults to a fresh output `/tmp/stripboard_drill_stack_80_c1_v162`, refuses to overwrite an existing `comparison.csv` or the original baseline directory, and saves both input SHA256 hashes and `input_revision = "v1.62-C1-1000uF"` in the new benchmark configuration.

To create a clean **new** 80-run baseline after correcting the Mac-local `motomix.json` and compiling native frontend TypeScript:

```bash
cd ~/Documents/stripboard-optimiser && \
(cd src/frontend && npx tsc -p tests/solver/tsconfig.json) && \
python3 scripts/benchmark_drill_stack.py --jobs 4
```

Because the solver source is unchanged, this is an **input/fixture revision**, not an annealing speed improvement or a new solver algorithm version. The existing native CLI executable remains `v1.60-cli-audit`; the source/migration and new comparison data are identified as **v1.62-C1-1000uF**.

## Verification status

Tracked MOTO JSON and netlist corrections were checked against actual component/reference labels prior to commit. Python script syntax, local Mac search results, local MOTOMIX source contents and a corrected 80-run baseline need execution on the Mac. Do not claim all stored files were corrected remotely until the local updater manifest is produced.
