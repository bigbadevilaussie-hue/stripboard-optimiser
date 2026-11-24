# Repository integrity and integration audit — 24 November 2026

**Scope:** entire Git-tracked `main` tree at baseline commit
`133636a628cb7a31eac09e1bacdc23b149c93c3e`, after Version 2.00
two-repository consolidation and Route-Mate GUI 2.01.

**Method:** GitHub tree/contents inspection, source import resolution, CLI/test
entrypoint review, fixture ID/net cross-checks, independently recalculated
SHA-256 for the 11 previously listed fixture files, and historical source
comparison against the removed Tk application's compiled schematic renderer.

**Verification boundary:** this was a **source/static audit**, not a clean
dependency install, C compilation, PySide6 test, fresh benchmark or full
saved-board electrical certification. Those need to run on the target Mac.
Never treat a source review, JSON sanity PASS, or solver Q0 as a final circuit
certification.

## Executive assessment

- **Main architecture preserved:** one native C/TypeScript optimiser,
  `src/frontend/tests/solver/v5Solve.js`, standalone board/schematic Node SVG
  CLIs, a donor PySide6 GUI for import and lock review, test fixtures and
  research scripts. The GUI cannot start Pass 1.
- **No obsolete GUI/backend tracked:** no legacy `desktop/` Tk app, Next.js
  editor, Django backend, Nginx deployment, Route-Mate Quick Solve/parallel
  router or Hell Mode engine remains in the current source tree. The
  repository **remains a fork** of KarloFunke/stripboard-editor.
- **Static dependency scan:** 76 TypeScript source files had no unresolved
  local-relative or `@/` imports. 65 Python files were reviewed for imports;
  the sole missing internal module found was the *optional* `solve.slide_fit`
  used only for Edge+Slide position counting, inside an ImportError handler.
  No native C code was modified by this audit.
- **Fixtures:** AUDIO 19 components / 29 nets / 85 assignments; MOTO 44 /
  35 / 123; MOTOEX 45 / 35 / 123. All three contain unique component IDs and
  reference existing component/net IDs in their pin assignments. This does
  not prove every pin name/physical footprint is valid.
- **Fixture SHA-256:** two **stale** entries (`moto.json` and `moto.net`)
  and one **omitted** entry (`motoex.json`). This audit corrects the manifest
  against the *existing* Git file bytes; no fixture JSON/netlist is edited.
- **GUI schematic:** the standalone schematic source and its compiled
  symbol, definition and rendering modules were compared with the original
  Tk-bundled compiled copy and matched. Old Tk displayed a 2400px PNG
  generated via librsvg; Route-Mate 2.01 uses that same method and caches the
  PNG. User-confirmed visual output is evidence of GUI display, not electrical
  correctness.

## Tracked inventory at baseline

| Area | Files / state | Responsibility |
|---|---:|---|
| Whole repo | **280 tracked files**, ~3.27 MB | Unified fork |
| Python (`.py`) | **65** | GUI shell, importer, sidecar, geometry validators, audit scripts/tests |
| TypeScript (`.ts`) | **76** | Native solver orchestration, geometry, SVG renderer sources |
| Native C | `decode.c`, `route.c`, `addon.c` | Search/routing and Node adapter |
| Standalone renderer compiled `dist/` | **31 files** | Existing board and schematic Node CLIs |
| Root Python tests | **6** test files | GUI preflight, import/locks, version, SVG bridge/raster behaviour |
| Python research tests | **13** test files | Sweep/requalification/controller logic |
| Default Node solver test globs | **6** `*.test.js` files | `tests/solver/run.js` |
| Default Node board test globs | **7** `*.test.js` files | `tests/board/run.js` |
| Fixture payloads | **12** | 7 KiCad footprints, 3 JSON projects, 2 KiCad netlists |

The additional standalone Node scripts named `test*.js` are **not** all
included by the default `*.test.js` runners. They need explicit invocation.

## Findings and actions

| ID | Severity | Verified finding | Action/status |
|---|---|---|---|
| A01 | **High — fixed in audit** | `SHA256SUMS` did not match current `moto.json` and `moto.net`, and lacked `motoex.json` | Recalculate and restore 12/12 manifest coverage, preserve old digests below |
| A02 | **High — open** | No tracked `src/frontend/package-lock.json`; `npm install` may resolve different dependency patch versions | Generate and commit lockfile only after target-Mac install/build verification; do not invent one |
| A03 | **High — integration gate** | GUI has no native CLI adapter / Pass 1 or Pass 2; `solve_board()` intentionally returns | Keep disabled until a tested adapter maps source/locks/options and qualifies saved JSON |
| A04 | **Medium — open** | Existing GUI spacing dialog has 0/1/2 choices. This is stored in donor stage options but **not passed to the existing native CLI** | Later map to Karl's native `partSpacing` behaviour, or disable unsupported choices; do not claim solver enforcement |
| A05 | **Medium — open** | MOTOEX raw master is **99×500**, `board.lockedRows=true`, `board.lockedCols=false`; GUI's physical dialog produces a prepared 24×56 in-memory project | Adapter must explicitly create a **24×56, both-locks-true** prepared CLI input; never infer it from screenshot alone |
| A06 | **Medium — open** | Optional `solve.slide_fit` is not retained. Edge+Slide position-count warning is caught; no position count available | Use only native edge/slide semantics in future adapter; never restore donor solver |
| A07 | **Medium — open** | Saved-board `auditSavedStrict.js` demands both board dimensions locked and reuses some electrical/geometry helpers from CLI; useful second execution over saved JSON, but not a fully disjoint external electrical oracle | Preserve its exact contract and add independent cross-checks before claiming comprehensive certification |
| A08 | **Medium — open** | Full native/Qt test suite, fresh compiled binary and end-to-end CLI run were not executed in this repository-only session | Run the Mac verification matrix below; retain logs and hashes |
| A09 | **Low — fixed in audit** | GUI docs prescribed Homebrew although deployment machine uses MacPorts | Document `sudo port install librsvg` and `/opt/local/bin/rsvg-convert` |
| A10 | **Low — fixed in audit** | Automatic `*.routemate-state.json` and `*.routemate-geometry.json` files could appear as untracked Git files when fixtures are opened | Ignore only generated sidecar names in `.gitignore`; files remain on disk |
| A11 | **Low — current decision** | No `v2.00` annotated/lightweight Git tag or GitHub release found | `VERSION=2.00` is the consolidated project designation, **not** proof of a tag |
| A12 | **Low — open** | Repository licence contains GPL-3.0; copied donor files require source-by-source attribution/licence review before redistributable GUI packaging | Record donor commit and retain licence; review notices before packaging |

### Prior vs current fixture digests

The 9 other entries in `test-fixtures/SHA256SUMS` matched their actual files.

| File | Old manifest SHA-256 | Current tracked bytes SHA-256 |
|---|---|---|
| `masters/moto/moto.json` | `938f014c2b8d6d3bedc2bc575e49dba196f1a8ab64be10c1f8d57c69479320df` | `b0bfd4ef8b107a254fb0464e6c630e83fa35b17279e30d53e7d55ac5e9d5445b` |
| `masters/moto/moto.net` | `f6bc0efe7c1075edfe191f6e9f81ba454fc14ddf3108147d56e63db9ffdd3dcb` | `6450b9fa919b59524651cc8ac2bb417bab0d1fdfefe43a1cdafd9aa74922d43b` |
| `masters/moto/motoex.json` | *omitted* | `e078b01bd5e563f0b9cd37289143e7fa7000a36a8b8a90d9474ce70b6f6d4bae` |

These hashes identify the **current** committed inputs, not the old
experimental snapshots. Do not silently rewrite or re-qualify historic
benchmark results against these files.

## Current execution boundaries

### Route-Mate GUI 2.01

1. Load original JSON; donor collector validates input.
2. Ask for actual/desired dimensions and current 0/1/2 nominal body spacing.
3. Persist sidecars next to the selected project:
   `<stem>.routemate-state.json` and `<stem>.routemate-geometry.json`.
4. Record electrical **input** sanity and advisory presolve/geometry.
5. Render board component/copper views using local standalone Node renderer.
6. Render schematic via local standalone Node SVG CLI, then convert to
   2400px PNG with `rsvg-convert -w 2400 -b white` for the Qt display.
7. Review each already-positioned part via highlighted Fixed / Movable /
   Edge / Slide lock dialogs.
8. Call the intentional **disabled** `solve_board()` guard; stop before Pass 1.

This is the GUI flow proven from the user-supplied MOTOEX screenshots/logs.
Neither this nor the sidecar is a qualified solver result.

### Native solver and qualification

- `v5Solve.js` is the **only** approved optimiser. Compile solver TS and
  native C bridge separately. Native mode is explicitly `--native 1`.
- The CLI's strict gate is **opt-in**: `--strict 1`, with exit `2` for a
  nonqualifying candidate. Exit 0 with `--strict 0` cannot be interpreted as
  a strict pass.
- `--drilled 0` allows knife cuts; `--nostack 0` allows insulated stacking.
  `--routing-preference wires` targets fewer wires first. The optional
  `--wire-polish 1` is **not** the default.
- The saved-board auditor must run on `candidate.json` **and its prepared
  input project JSON**, not on the unprepared 99×500 MOTOEX master.
  It requires both board locks and vertical jumpers, and treats body-only
  overhang as a warning rather than an electrical failure.
- Prior 27-wire/43-cut MOTOEX champion is an archived, user-reported,
  independently audited result; its JSON is on the user's Mac rather
  than tracked in this repo, so this audit did **not** revalidate its bytes.
- No new Python optimisation/search/routing engine is permitted in the GUI.

## Target-Mac verification matrix (NOT run in this GitHub-only audit)

From repository root:

```sh
git pull --ff-only
git status --short
python3 scripts/audit_repo_integrity.py

cd test-fixtures
shasum -a 256 -c SHA256SUMS
cd ..

python3 -m unittest discover -s tests -p 'test_*.py' -v
PYTHONPATH=scripts python3 -m unittest discover -s scripts/tests -p 'test_*.py' -v

cd src/frontend
npm install
npm run build:solver
npm run build:renderers
npm run build:native
npm run build:native:edge
npm run test:headless
node tests/solver/testAuditSavedStrict.js
node tests/solver/testNativeBodyBoardBounds.js
node tests/solver/testPackageBodyBoardBounds.js
node tests/solver/testWireColumnPolish.js
cd ../..

/opt/local/bin/rsvg-convert --version
PATH="/opt/local/bin:$PATH" python3 run_gui.py
```

**Notes:** `npm install` will create a local `package-lock.json` that is
currently not tracked; do not commit until reviewed. The audit script is
read-only, prints JSON and exits nonzero for static errors. GUI smoke tests
are offscreen where supported; actual interactive dialogs, SVG/PNG fidelity,
and Mac-native performance must still be observed on the Mac.

A final GUI→native test must check: import/source unchanged, exact prepared
24×56 both-locked board, preserved component/edge/slide constraints, correct
default drill/stack policy, speed probe accounting, Pass 1/Pass 2 qualification
and strict saved JSON re-audit. **That milestone is not yet complete.**

## Change-control rules after this audit

- GUI import/renderer/behaviour changes require **`gui/VERSION` increment**
  and a changelog entry in the same commit. **No GUI implementation changed
  in this audit, so GUI stays at 2.01.**
- Root `VERSION` stays `2.00` (consolidation milestone); native CLI retains
  its internal diagnostic build identifier independently.
- No fixture byte changes without new hashes, provenance and test updates.
- No claim of strict compliance from preflight alone; compare actual saved
  board and prepared input with the independent audit.
- Prefer fewer **wires** then fewer **cuts** among qualified candidates.
- Edge Lock and Slide are optional specialist controls, not compulsory
  solver assumptions.

### Audit evidence files

- [GUI contract](../gui/README.md)
- [Project architecture](../project.md)
- [Existing native CLI audit](cli-audit-2026-11-23.md)
- [Original Route-Mate donor handover](Route-Mate_GUI_Code_Handover.md)
- [Native CLI integration roadmap](route-mate-native-solver-integration-roadmap.md)
- [MOTOEX winner ladder](motoex-seed37-winner-ladder-2026-11-24.md)
- [Research archive index](INDEX.md)
