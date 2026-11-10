# Stripboard Optimiser — Project Specification

## 1. Project objective

Develop a distributable desktop application around the headless stripboard
optimisation engine.

The application is designed for practical Veroboard/stripboard electronics.
It optimises component placement, copper track cuts and jumper wiring.

This is NOT a PCB design or PCB fabrication application.

Target distributions:
- macOS: DMG installer
- Windows: EXE installer
- Linux: AppImage

Ordinary users must not need Python, a compiler, a terminal or manual
dependency installation.

## 2. Architecture

Keep the optimisation engine separate from the user interface.

The application consists of:

1. Desktop user interface.
2. JSON input and validation.
3. Pre-processing engine.
4. Headless C/WASM solver.
5. Candidate collection and storage.
6. Independent post-processing and validation.
7. Candidate ranking and export.

The existing headless fork remains the optimisation engine.
Do not replace its solver with a separate GUI implementation.

The GUI must call the same underlying solver and preserve reproducibility.

## 3. Input and pre-processing

Accept the existing project JSON format.

Before solving:

- Validate JSON structure.
- Validate components, pins and connections.
- Validate board dimensions.
- Check component positions and rotations.
- Check fixed and excluded placements.
- Identify invalid placements, overlaps and out-of-bounds components.
- Preserve electrical connections and component identities.
- Preserve the original input JSON unchanged.

Generate normalised solver inputs and, where permitted, alternative
starting placement configurations.

Pre-processing must not change the electrical design.

Every generated input must be traceable to the original project.

## 4. Optimisation settings

### 4.1 Basic settings

Expose these options in the main application interface:

- Allow diagonal wires.
- Allow track cuts.
- Allow drilled cuts.
- No stacked wires.
- Allow standing parts.
- Extra room between parts.
- Board dimensions.
- Solver effort / move budget.
- Processor threads.

Important distinctions:

`--drilled 0|1` controls drilled cuts. It does not necessarily disable
all track cuts.

The general Allow cuts control must only be enabled once its behaviour
is implemented and verified in the solver.

Diagonal routing must likewise be verified as a solver capability before
the checkbox is enabled.

Do not display non-functional controls as though they work.

### 4.2 Board constraint mode

Provide two distinct modes.

SOFT LOCK:
- Use W_LOCKOVER as a solver penalty.
- Permit exploration beyond the locked dimensions during optimisation.
- Penalise candidates that exceed the permitted board size.
- Never export an over-size candidate as a valid final layout.

HARD CLAMP:
- Enforce lockedRows and lockedCols.
- Do not accept component placements outside the board.
- Reject invalid candidates before final selection.

Do not confuse the W_LOCKOVER penalty with hard board constraints.

### 4.3 Electrical validation

Provide an Electrical check option.

This is an independent validation stage, not an assumed existing
solver setting.

When enabled:
- Check all required electrical connections.
- Detect disconnected nets.
- Detect unintended shorts.
- Reject electrically invalid candidates.
- Report validation failures.

A candidate must not become champion merely because its annealing
score is good.

## 5. Advanced solver weights

Expose these in an Advanced settings panel.

| Parameter | Default | Purpose |
|---|---:|---|
| W_AREA | 0.35 | Price per board cell |
| W_WIRE | 25.0 | Price per jumper wire |
| W_WLEN | 0.4 | Price per hole of wire length |
| W_CUT | 0.05 | Price per track cut |
| W_BCUT | 2.0 | Price per knife cut when drilled cuts are off |
| W_BCUT_DRILL | 24.0 | Price for a cut that could have been drilled |
| W_TALL | 2.0 | Aspect ratio penalty |
| W_LOCKOVER | 5000.0 | Penalty per row over locked size |
| CONN_FULL | 30.0 | Connector price when far from an edge |
| W_SIBLING | 0.5 | Price for separation of pads of one off-board part |

Requirements:

- Preserve the listed defaults.
- Allow users to restore defaults.
- Validate numerical input.
- Save settings with each optimisation run.
- Keep W_* values synchronised between decode.c and boardPrice.ts.
- Add a consistency check to detect mismatched values.
- Do not silently change weights between application versions.

## 6. Existing headless harness controls

Preserve these controls:

- --drilled 0|1
- --moves N
- --seed N
- noWireStacking
- allowStandingParts
- extraRoom

The GUI must translate its settings into the corresponding harness
arguments and JSON properties.

Record the exact arguments and settings used for every run.

## 7. Structural constraints

Preserve existing project properties:

- lockedRows
- lockedCols
- locked: true
- boardExcluded: true

Their meanings must remain unchanged.

A locked component cannot be moved by the optimiser.
An excluded component is not placed on the board.
Locked board dimensions are hard limits in clamp mode.

## 8. Candidate generation

Support multiple seeds and configurable move budgets.

The user must be able to configure:

- Number of seeds.
- Starting seed.
- Move budgets.
- Number of processor threads.
- Maximum candidate count.

Each solver run must produce a separate candidate record.

Do not retain only the current best result.

Store all valid candidates so post-processing can compare them.

Record:
- Candidate identifier.
- Original project identifier.
- Seed.
- Move budget.
- Solver settings.
- Solver score.
- Wire count.
- Cut count.
- Wire length.
- Board dimensions.
- Component placements.
- Candidate JSON path.
- Solver completion status.

Failed and invalid runs must be recorded separately.

## 9. Post-processing

Post-processing must independently inspect every candidate.

Required operations:

1. Parse candidate JSON.
2. Validate board dimensions.
3. Validate component positions.
4. Validate component overlaps.
5. Verify electrical connectivity when enabled.
6. Detect unintended shorts when supported by the electrical model.
7. Recalculate actual jumper wire count.
8. Recalculate actual wire length.
9. Recalculate actual track cut count.
10. Analyse copper-track fragmentation.
11. Detect redundant or unnecessary wiring.
12. Detect duplicate or equivalent layouts.
13. Reject invalid candidates.
14. Rank the remaining candidates.

Do not rely solely on the annealer's reported score.

The post-processor must not silently modify electrical connections.

Any layout modification must be followed by another complete validation.

## 10. Candidate ranking

Do not rank candidates solely by the annealer's weighted score.

Retain a Pareto shortlist covering:

- Lowest jumper wire count.
- Lowest cut count.
- Shortest total wire length.
- Best track continuity.
- Best overall physical layout.

A candidate with fewer wires is not automatically better if it requires
substantially more cuts or damages copper-track continuity.

Provide a configurable final ranking policy.

Keep individual metrics visible so users can make an informed choice.

## 11. Champion selection

A champion must:

- Pass structural validation.
- Pass electrical validation when enabled.
- Respect the selected board constraint mode.
- Have independently verified wire and cut counts.
- Have its original candidate JSON preserved.

Save the winning candidate separately.

Never overwrite the original project JSON.

Retain alternative candidates, including Pareto-optimal results.

The selected champion must be exportable as the existing project JSON
format so it can be opened in the original editor.

Export must preserve component identities, pin assignments, connections,
board properties and layout information.

## 12. User interface

The main workflow should be:

1. Open project JSON.
2. Review board and component information.
3. Configure optimisation settings.
4. Start optimisation.
5. Monitor progress.
6. Review generated candidates.
7. Inspect validation results.
8. Compare candidate layouts.
9. Select champion.
10. Export final JSON and reports.

Provide an Advanced section for solver weights.

Provide clear progress reporting:
- Seeds completed.
- Seeds remaining.
- Current move budget.
- Valid candidate count.
- Invalid candidate count.
- Current best candidate.

The user must be able to cancel an optimisation run safely.

## 13. Reproducibility and reporting

Save a run manifest containing:

- Input project hash.
- Application version.
- Solver version.
- All solver weights.
- All GUI settings.
- Seed list.
- Move budgets.
- Processor thread count.
- Candidate results.
- Validation results.
- Final ranking.

A run must be reproducible from its manifest and original input.

Generate a summary report showing the champion and alternative candidates.

## 14. Performance and reliability

- Support parallel seed execution.
- Avoid corrupting candidate files during concurrent writes.
- Handle solver crashes and timeouts.
- Preserve completed candidates if a run is interrupted.
- Never treat a failed run as a valid candidate.
- Keep the original project safe throughout optimisation.

## 15. Implementation stages

### Stage 1 — Headless pipeline
- Audit current JSON input/output.
- Implement pre-processing.
- Implement candidate manifest.
- Preserve all solver candidates.
- Implement independent post-processing.

### Stage 2 — Validation and ranking
- Electrical connectivity checks.
- Structural checks.
- Independent metric calculation.
- Track fragmentation analysis.
- Pareto ranking.

### Stage 3 — Desktop application
- Basic settings.
- Advanced settings.
- Progress display.
- Candidate comparison.
- Layout inspection.
- Export.

### Stage 4 — Packaging
- macOS DMG.
- Windows EXE installer.
- Linux AppImage.
- Test on clean installations without development dependencies.

## 16. Acceptance criteria

The project is ready for release when:

- Users can open an existing project JSON.
- Users can configure all implemented optimisation settings.
- Users can run multi-seed optimisation without a terminal.
- Every candidate is preserved and traceable.
- Invalid candidates cannot become champions.
- Electrical validation works when enabled.
- Candidate metrics are independently recalculated.
- Alternative candidates can be compared.
- The selected champion can be exported in the original project format.
- The application installs and runs on supported operating systems
  without requiring users to install development tools.
