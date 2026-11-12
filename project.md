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
the checkbox is enabled. The current route output includes point-to-point
straight-line wires; a route whose endpoints differ in both row and column
is diagonal. Do not convert such routes to L-shapes after solving: an
orthogonal replacement can cross uncut copper strips and create shorts.
Orthogonal-only routing, if required, must be implemented and validated
within solver routing/search logic.

Do not display non-functional controls as though they work.

### 4.2 Board constraint mode

Provide two distinct modes.

SOFT LOCK:
- Use W_LOCKOVER as a solver penalty.
- Permit exploration beyond the locked dimensions during optimisation.
- Penalise candidates that exceed the permitted board size.
- Never export an over-size candidate as a valid final layout.

HARD CLAMP:
- Treat lockedRows and lockedCols as hard final board-size limits.
- The current finish-stage check in layout2/finish.ts tests the maximum
  required row/column after annealing and throws if the locked cap is exceeded.
  This is a finalisation check, not evidence that the annealer is constrained
  to remain within the locked dimensions throughout its search.
- Reject an over-size result; do not silently resize the board or export it
  as valid.
- Any earlier in-search hard constraint is a separate capability and must
  be verified in the solver source before being claimed.

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

- Preserve the listed defaults, but verify them against the exact solver
  revision being packaged.
- Treat weights as search/objective preferences, not direct proof of
  physical superiority or universal user preference.
- Allow users to adjust supported weights, including the jumper-wire versus
  track-cut trade-off.
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
An excluded component is not physically placed as a full component on the
board, but it must remain represented electrically through the off-board
expansion process (see Section 20).
Locked board dimensions are hard limits at finalisation in clamp mode;
do not assume this is an in-search annealer constraint.

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

The current price expression combines area/aspect, jumper wire count,
wire length, track cuts, drilled/knife-cut pricing, lock overrun, connector
edge cost, shaft-in cost and sibling-pad separation. Its weighted score
(eBase/score as exposed by the relevant pipeline) is a search objective,
not a complete user preference model. Weight magnitudes alone do not prove
that a particular wire/cut combination is universally superior.

Independently calculate and retain at least these Pareto dimensions:

- Jumper wire count.
- Track cut count.
- Board area.
- Total wire length.
- Track continuity.
- Other validated physical-layout measures.

Retain a Pareto shortlist covering:

- Lowest jumper wire count.
- Lowest cut count.
- Smallest board area.
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

## 17. Input files and import contract

The import workflow must handle the actual files exported by Stripboard Editor. It must not assume that one JSON file always contains every item needed to solve a project.

### 17.1 Supported input set

| Input | Requirement | Purpose |
|---|---|---|
| Project JSON | Required | Complete project state: components, nets, pin assignments, board layout, cuts, wires and settings |
| Parts Library JSON | Optional | User's exported My Parts library; supplies custom component definitions missing from the project |
| `.net` export | Optional, subject to format audit | Additional netlist/electrical reference for cross-checking the project |
| Original project assets | Optional | Any referenced assets required to display or inspect the project; must not be required by the headless solver unless its format demonstrably depends on them |

The application must identify files by content and validated format, not solely by filename or extension. It must tell the user which files were loaded, which were optional, and which checks could not be performed because an optional file was absent.

The precise `.net` syntax and semantics must be established from real exports and the upstream implementation before a parser or validation rule is finalised. Do not invent a format or silently reinterpret it. The project JSON remains the primary source of project state unless an audited format definition establishes otherwise.

### 17.2 Project JSON fields to preserve and validate

The importer must understand and preserve, at minimum, the following project structures where present:

- Project metadata: version, name, description and notes.
- `componentDefs`: built-in and embedded custom component definitions.
- `components`: component instances, UUID `id`, `componentDefId`, `boardPos`, rotation, `locked`, `boardExcluded` and label.
- `nets`: net IDs, names and colours.
- `netAssignments`: component ID, pin ID and net ID assignments.
- `board`: rows, columns, cuts and jumper wires.
- Root and board-level solver settings, including `lockedRows`, `lockedCols`, `v5Effort`, `v5RandomSeeds`, `noWireStacking`, and other recognised settings.
- Schematic-only information, such as `schematicWires` and `netLabels`, which must be preserved even if the solver does not consume it.

Unknown fields must be retained through import/export wherever possible. Do not discard data simply because the optimiser does not use it.

### 17.3 Parts Library JSON

Support the Stripboard Editor My Parts export format, including:

- `format: "stripboard-editor-parts"`
- `version`
- `parts` array
- Definition ID, name and category
- Width and height
- Pin definitions and exact `offsetRow` / `offsetCol` coordinates
- `bodyCells` and symbol data where supplied

The parts library is optional when the project JSON already contains all definitions needed by its component instances.

### 17.4 Merge and normalisation rules

Before solving:

1. Load the original project JSON without modifying it.
2. Load the optional Parts Library JSON when supplied.
3. Match every component instance's `componentDefId` against project `componentDefs`.
4. For definitions absent from the project, find a matching definition in the imported parts library and append it to the normalised `componentDefs`.
5. Do not duplicate definitions already present.
6. If the same definition ID exists with conflicting content, report a definition conflict and stop; do not silently choose one or overwrite either source.
7. Verify that every component instance resolves to exactly one valid definition.
8. Normalise `board.lockedRows` and `board.lockedCols` to the root-level fields expected by the headless harness, while retaining the original board-level values.
9. Produce a separate normalised solver input and record its relationship to the original files.

Never change component IDs, pin IDs, net IDs, pin assignments or electrical topology during merge/normalisation. Never overwrite the user's original project or Parts Library files.

### 17.5 Optional netlist cross-check

When a `.net` export is supplied and its format has been verified:

- Parse it independently of the project JSON.
- Compare its component/pin/net relationships with the JSON `netAssignments`.
- Report missing, additional, duplicate or conflicting connections.
- Distinguish a genuine design mismatch from unsupported or unparseable netlist syntax.
- Do not silently merge conflicting electrical data or use the `.net` file to rewrite the project.

If the `.net` file is absent, report that this cross-check was not performed; do not imply that the electrical design has been independently cross-checked against it.

## 18. Import validation and preflight checks

Import validation is a distinct stage and must finish before any solver process starts. Produce a readable report with severity, file, object ID, field/path and explanation for each finding.

### 18.1 File and schema checks

- File exists, is readable and is not empty.
- JSON parses successfully and has the expected root type.
- Recognised format/version is supported.
- Required fields have the correct types and valid ranges.
- IDs are present, correctly typed and unique within their required scope.
- References between objects resolve.
- Unsupported versions or malformed structures stop the run with a useful error; do not guess defaults for required electrical or geometric data.

### 18.2 Component and footprint checks

- Every component instance references an existing component definition.
- Every assigned pin exists in that definition.
- Pin offsets are valid and lie within the definition's declared footprint unless the format explicitly supports otherwise.
- Width and height are positive, finite and meaningful.
- Body-cell coordinates are valid and do not create impossible geometry.
- Rotations are one of the supported values and are applied consistently to both body geometry and pin coordinates.
- Component IDs and definition IDs are not accidentally conflated.
- Duplicate or conflicting definitions are reported.
- Missing definitions must never be treated as zero-sized footprints.

### 18.3 Electrical checks

- Every `netAssignment` references an existing component, pin and net.
- Detect duplicate assignments and conflicting assignments of one pin.
- Detect references to missing or deleted nets.
- Preserve intentional unconnected pins.
- Distinguish an intentionally unconnected pin from a required connection that is missing; requiredness must come from the project model or an explicit rule, not a guess.
- Compare JSON electrical assignments with the optional `.net` file when supplied and supported.
- Do not change the electrical design during validation or preprocessing.

### 18.4 Board and geometry checks

- Board row and column dimensions are valid positive integers.
- Cuts and wires reference valid board coordinates and valid strip/hole locations.
- Component placements and rotations are valid.
- Check footprint bounds, pin locations, body-cell locations and component-to-component overlap.
- Check whether placements violate locked rows/columns or other hard constraints.
- Check whether a component is both excluded and placed in a contradictory state.
- Preserve off-board components and their electrical assignments.
- Report pre-existing invalid placements separately from errors introduced by a solver candidate.

### 18.5 Preflight result

Preflight must classify findings as:
- **Error:** unsafe or ambiguous input; solving is blocked.
- **Warning:** input is usable but a check is incomplete or a condition needs user attention.
- **Information:** optional file absent, recognised setting, or non-blocking observation.

The user must be able to inspect the report before starting a run. Do not silently repair errors. Any explicitly supported repair/normalisation must be logged and applied only to the separate working copy.

## 19. Locked test fixtures and regression data

Real projects are required as regression fixtures before substantial optimiser implementation. Fixture files must be committed to the repository, versioned and traceable; do not recreate simplified examples and call them equivalent to the real designs.

Initial fixture set:

- **Bike-Mate Ver 1:** baseline/regression project.
- **Bike-Mate Ver 2:** more demanding project and primary import/optimisation test.
- **Audio-Mate:** additional mixed-signal project fixture when its export set is available and approved for repository use.

For each fixture, retain the actual exported files that are relevant and available, for example:

```
tests/
  fixtures/
    bike-mate-v1/
      project.json
      project.net
      my-parts.parts.json
    bike-mate-v2/
      project.json
      project.net
      my-parts.parts.json
    audio-mate/
      project.json
      project.net
      my-parts.parts.json
```

This is a suggested organisation, not a requirement to create empty placeholder files. Include only files that actually exist for that fixture. Record the source application/export version and a short fixture README describing which files are present and any known limitations.

Fixture rules:

- Preserve original exported files byte-for-byte as baseline inputs.
- Do not reset component positions, unlock components, remove off-board parts or change excluded flags to make a test pass.
- Keep the original electrical design and component identities intact.
- Do not commit personal credentials, tokens or unrelated private information.
- If a fixture is updated, retain a clear history/reason for the new baseline.
- Store generated normalised inputs, solver outputs and reports separately from immutable fixture inputs.
- Add regression tests for import, definition merging, locks, exclusions, pin mapping, board geometry, electrical checks and export round-trip.

Bike-Mate Ver 2 is specifically important because it exercises custom parts, existing placements, off-board components and the distinction between electrically present components and components physically placed on the board. Bike-Mate Ver 1 provides a simpler regression baseline. The known-good Moto-Mate and Audio-Mate reference JSONs provide 14-wire and 10-wire baseline layouts respectively; preserve those files and their measured metrics for regression testing.

## 20. Off-board components and mechanical placement constraints

Electrical participation and physical board placement are separate properties.

- A component with `boardExcluded: true` remains part of the electrical design but is not placed on the stripboard as a full component. The current pipeline calls `expandOffBoard` before solver execution and transforms off-board components into one-hole rigid pad representations. Those pads must remain in the solver model to preserve net connections; solver results are subsequently mapped back to the original off-board component. Do not remove these pad representations from the solver pool.
- A component with `boardExcluded: false` is eligible for board placement subject to its other constraints.
- A `boardPos: null` value means no current board placement; it does not mean the component is electrically absent.
- A component with `locked: true` must retain its existing placement and must not be moved.
- Never delete an off-board component or its net assignments as a shortcut to obtaining a solution.

The optimiser must support general mechanical placement constraints rather than special-case workarounds for individual USB or GPS modules.

The GUI must display the original off-board component appropriately and must
not render its internal one-hole solver pads as full physical components or
duplicate user-visible components.

Required constraint model:

- Required board edge: top, bottom, left or right.
- Permitted orientation(s).
- Whether the body must remain wholly on the board or may overhang.
- Permitted overhang/protrusion distance and direction.
- Optional position/offset along the selected edge.
- Optional clearance from adjacent components or board features.
- Optional fixed placement or allowed placement region.

This is needed for connectors, USB sockets, GPS modules, BMS terminals, switches, displays and other parts that must be accessible from outside an enclosure. A connector may need its electrical pins and mounting footprint on the board while its socket/body protrudes beyond the board edge. Model body geometry, board mounting footprint and electrical pin coordinates separately where the component definition requires it.

Do not assume all components of a category have the same mechanical requirements. Constraints must be configurable per component instance or through a reusable component-definition constraint.

A candidate violating a required mechanical constraint is invalid even if it is electrically connected and has a good solver score. The GUI must expose and display these constraints so the user can see why a placement is accepted or rejected.

## 21. Circuit-aware physical design checks

Generic electrical connectivity validation is necessary but does not guarantee a physically robust stripboard layout. Add a configurable rule-checking layer for measurable circuit-specific layout constraints.

Potential rule families include:

- **Decoupling:** maximum permitted distance between a device supply pin and its decoupling capacitor. Identify both exact component-pin endpoints and measure Manhattan distance between their actual board-hole coordinates; component-centre distance is insufficient.

  Provisional schema concept (field names are not yet a committed format):

  ```json
  {
    "component": "C2",
    "pin": "VCC",
    "near": "ESP32",
    "targetPin": "3V3",
    "maxPinDistance": 3
  }
  ```
- **Switching power:** compactness/maximum span of buck-converter switching loops and associated high-current connections.
- **Analog/digital separation:** proximity restrictions between sensitive analogue inputs and noisy digital switching or clock signals.
- **High-current paths:** limits on path length, shared track sections or other measurable stripboard routing properties.
- **Ground/return paths:** explicit constraints where the circuit definition provides enough information to evaluate them.

Rules must be explicit, configurable and tied to identifiable components, pins, nets or groups. Each finding must state the rule, affected objects, measured value and configured limit.

Do not claim to calculate actual EMI, acoustic noise, amplifier stability, thermal behaviour or analogue performance from board geometry alone. The tool can enforce measurable layout rules that reduce known risks; it cannot replace circuit analysis or physical testing.

Rule checks must distinguish hard failures from advisory warnings. A rule must not be enabled by default unless its assumptions and thresholds are documented and verified for the applicable circuit.

## 22. Parallel execution and candidate isolation

Thread count is a user-configurable run setting, with an automatic mode based on available logical CPU cores and a manual range bounded by the machine's available resources.

Parallelism is useful for independent solver runs/seeds; it must not be presented as a guarantee that one solver run becomes faster with more threads.

Every worker must have an isolated working directory and unique input, output, log and temporary-file paths. Workers must never write to a shared candidate filename or mutable project file. The desktop implementation should create each worker directory using a thread-safe temporary-directory facility (for example, Python's `tempfile.mkdtemp()`) and retain unique candidate filenames. This specifically prevents races such as multiple workers writing to the same `projects/0.json`.

Requirements:

- Assign each run a unique run ID and each candidate a unique candidate ID.
- Give each worker its own working copy and output directory.
- Use atomic file writes or equivalent safe publication of completed results.
- Coordinate cancellation and worker shutdown.
- Preserve completed candidates if another worker crashes or the user cancels.
- Record worker ID, seed, start/end time, exit status and error output.
- Test concurrent runs against deterministic fixtures and verify no output is overwritten or cross-contaminated.

## 23. Import/export round-trip and data integrity

The import/export pipeline must prove that it does not damage a project.

- Keep immutable copies or hashes of all original inputs.
- Record hashes for original project JSON, optional Parts Library JSON and optional `.net` file.
- Record the normalised solver input hash and exactly which transformations were applied.
- Export into a new file; never overwrite the original.
- Preserve project metadata, component and definition IDs, pin assignments, nets, schematic data, board settings, cuts, wires, lock flags and excluded flags.
- Normalise `lockedRows` and `lockedCols` to the root-level fields required by the editor/import contract, while retaining their board-level values where present. If root and board-level values conflict, report the conflict rather than silently selecting one representation.
- Preserve unknown fields where possible.
- Do not export internal optimiser-only metadata into the editor project format unless the format explicitly supports it; store run metadata in a separate manifest/report.
- Re-import the exported champion and run the full preflight checks again.
- Compare the exported project's electrical topology and protected properties with the original.
- Any intended layout changes must be limited to the properties the optimiser is authorised to change.
- A failed round-trip or changed electrical topology blocks champion export.

Provide a machine-readable validation report and a human-readable summary for each run.

## 24. Additional acceptance criteria

In addition to Section 16, release acceptance requires:

- The importer accepts a valid Project JSON with no Parts Library when all referenced definitions are embedded.
- The importer merges missing custom definitions from a valid My Parts export without duplicating definitions.
- Conflicting or missing definitions are reported and block solving.
- Optional `.net` input is parsed only after its actual format is verified; supported netlist data is cross-checked against JSON without rewriting it.
- Preflight reports malformed references, invalid pin mappings, bad dimensions, invalid placements and contradictory flags before solving.
- Real Bike-Mate Ver 1 and Ver 2 fixtures pass the applicable import and regression tests.
- Off-board components remain electrically present and are not silently removed.
- Edge-mounted and protruding components can be represented and validated using general mechanical constraints.
- Each parallel worker has isolated files and concurrent execution cannot overwrite another worker's inputs or candidates.
- Candidate export preserves electrical topology and protected project data, and passes a fresh import/validation round-trip.
- Circuit-aware physical rules report measurable findings without claiming to simulate physical EMI or analogue behaviour.


## 25. Solver capability audit — Stage 0

Do not redesign or implement solver features until the existing solver,
routing code, TypeScript integration and Python harnesses have been mapped.
This stage separates verified existing behaviour from partial support,
unsupported requirements and unresolved questions.

### 25.1 Code facts supplied for audit

The following details are documented from the supplied source snippets.
They must be checked against the exact source revision packaged for each
release, with source paths, line references and tests recorded in the audit
report.

**Cost function — `components/stripboard/v5wasm/decode.c`**

The supplied snippet defines:

- `W_AREA = 0.35`
- `W_WIRE = 25.0`
- `W_WLEN = 0.4`
- `W_CUT = 0.05`
- `W_BCUT = 2.0`
- `W_BCUT_DRILL = 24.0`
- `W_TALL = 2.0`
- `W_LOCKOVER = 5000.0`
- `W_SIBLING = 0.5`
- `CONN_FULL = 30.0`

The supplied pricing expression includes area/aspect, wire count, wire
length, cuts, selected drilled/knife-cut pricing, lock overrun, connector
edge cost, shaft-in cost and sibling-pad separation. A positive lock overrun
receives a fixed very large penalty (`999999999.0`) in that expression.
The TypeScript mirror is `components/stripboard/layout2/boardPrice.ts`.
The two implementations must remain consistent and have an automated
consistency check.

Do not assume every defined weight is directly user-adjustable until the
source and UI integration are checked. Preserve the defaults only as
version-specific documented values. A lower weighted score does not alone
prove a better physical board.

**Board-size validation — `components/stripboard/layout2/finish.ts`**

The supplied lines 287–294 check the required maximum row and column against
`lockedRowsCap` and `lockedColsCap` during finalisation, throwing an error
when the finished layout exceeds either cap. This establishes a finalisation
guard; it does not establish that the annealer itself is prevented from
exploring over-size layouts. Keep soft penalty and final hard rejection
semantically distinct.

**Multi-seed portfolio — `components/stripboard/autoLayout5.ts`**

The supplied lines 175–200 show a default of six independent seeds
(`options.seeds ?? 6`), a configurable move budget and optional seed index
or base. Seed results are sorted by annealer energy `E`; only the top four
are passed to finalisation, and the best finalised result is selected by
final score. Preserve this distinction in performance reporting and audit
whether seed-level pruning can discard a candidate that would perform better
after finalisation. The desktop app must not describe this as exhaustive
finalisation of every seed unless that behaviour is changed and tested.

**Routing — `components/stripboard/v5wasm/route.c`**

The supplied evidence indicates point-to-point straight-line wire routing.
A wire is diagonal when both its row and column coordinates differ between
endpoints. Diagonal-to-L-shape post-processing is prohibited because the
replacement can cross uncut copper strips and create shorts. Orthogonal-only
routing, if required, must be implemented in solver routing/search logic and
validated against real stripboard connectivity.

**Headless harness — `tests/solver/v5Solve.js`**

The supplied harness patch preserves a component's `boardPos` and
`locked` state when `locked` is true and a board position exists. Other
unlocked components are reset to `boardPos: null`, have
`flexibleEndPos` cleared and rotation reset to zero, and have the lock field
removed before solving. Treat this as harness input preparation, not as a
general import/export rule. Audit that the desktop workflow applies the
intended lock semantics without unintentionally discarding placements or
flags.

**Off-board expansion — `components/stripboard/layout2/finish.ts` and
`autoLayout5.ts`**

The supplied findings state that `expandOffBoard` runs before solver
execution, replacing off-board components with one-hole rigid pad
representations and mapping results back afterwards. Retain those pads in
the solver model to preserve electrical net connections. The GUI must not
present internal pads as full component bodies or duplicate user-visible
parts.

### 25.2 Existing behaviour versus extensions

**Sibling pads and proximity**

`W_SIBLING` is a penalty for separation of pads belonging to the same
off-board component. It is not automatically a general pin-to-pin proximity
constraint between arbitrary component instances. Audit its exact inputs,
distance calculation and scope before reusing it. Decoupling constraints
must identify both exact component-pin endpoints and measure Manhattan
distance between their board-hole coordinates.

**Rigid component groups**

Support groups of original component instances as rigid placement units
without merging or mutating their `componentDefs`, IDs, pins or nets. A
provisional concept is:

```json
{
  "group": ["MP1584EN", "L1", "C3"],
  "relative": "rigid"
}
```

Before implementation, define how relative positions and orientations are
established, whether the group can rotate or reflect as a unit, how member
locks/exclusions behave, and how board bounds, overlaps and electrical
validation apply. Audit `leadSiblings` first; do not assume it supports
arbitrary component groups.

### 25.3 Required audit deliverables

Produce a capability matrix covering:

- Off-board expansion and reverse mapping.
- Sibling-pad grouping and exact `W_SIBLING` scope.
- Weight definitions, defaults, objective use and TypeScript parity.
- Annealer score versus finalised candidate score and seed pruning.
- Hard and soft board constraints and when each is enforced.
- Wire/cut generation and diagonal route behaviour.
- Existing lock/exclusion handling and harness normalisation.
- Pin-coordinate transforms under component rotation.
- Existing group/sibling mechanisms.
- Candidate output format and score fields.
- Python harness arguments, worker isolation and output naming.
- Root-level and board-level lock-field import/export behaviour.

Classify every item as **verified existing**, **partially supported**,
**not supported** or **not yet verified**. Cite source locations and record
a reproducible test or fixture where possible. Do not add GUI controls for
unverified or non-functional solver behaviour.

### 25.4 Regression gates

Before accepting any solver, preprocessing, routing or export change:

- Run the real Moto-Mate (14-wire) and Audio-Mate (10-wire) reference JSONs.
- Compare independently calculated wire count, cut count, board area, wire
  length and validation results with recorded baselines.
- Confirm off-board pad expansion and reverse mapping preserve electrical
  connections and original component identities.
- Confirm no diagonal-to-L-shape post-processing is used.
- Confirm worker outputs remain isolated and no candidate is overwritten.
- Confirm required root-level `lockedRows` and `lockedCols` are present in
  normalised/exported JSON, while retaining corresponding board-level values.
- Re-import exported candidates and compare electrical topology and
  protected project properties with the original fixtures.

A lower weighted solver score alone is not a passing regression result.


## 26. Implementation snapshot — 2026-11-13

This section records a source-tree inspection of the repository at commit
`affa0f5`. It is an implementation snapshot, not a replacement for the
requirements and acceptance criteria above. A feature described in earlier
sections remains a requirement until its implementation and verification
are recorded explicitly.

### 26.1 Web application

The inherited Next.js frontend, Django backend and Nginx/Docker deployment
remain in the repository. Their existing run and deployment instructions
are in the root README.

### 26.2 Standalone rendering

The frontend renderer now has two separate TypeScript CLI entry points:

- `src/frontend/standalone-renderer/cli.ts` renders the component-side and
  copper-side board SVGs.
- `src/frontend/standalone-renderer/schematic/cli.ts` renders a schematic
  SVG from schematic data in a project JSON file.

The production TypeScript configuration includes the schematic source.
Compiled JavaScript is under `src/frontend/standalone-renderer/dist/`.
The desktop UI has a bundled runtime copy under
`desktop/src/stripboard_optimizer/resources/standalone-renderer/`.
Keep the source, compiled output and desktop runtime copy synchronised when
renderer code changes. The desktop UI's `Render JSON...` action invokes the
board and schematic CLIs separately, converts available SVG files to PNG
with `rsvg-convert`, and provides Front (Top), Back (Copper) and Schematic
views.

The standalone renderer's parity test sources and their recorded historical
results are documented in
`src/frontend/standalone-renderer/README.md`. Those historical results
must not be described as a fresh test run unless the tests are rerun.

### 26.3 Desktop application status

The tracked desktop prototype is under `desktop/src/stripboard_optimizer/`.
The current UI includes project JSON loading, optional netlist and KiCad ZIP
loading, a preflight panel, mode-selection controls, solver-worker queue
handling, renderer invocation and a three-view image viewer.

**Known launch blocker at this snapshot:**
`desktop/src/stripboard_optimizer/ui/main_window.py` imports
`stripboard_optimizer.solver.worker.SolveWorker`, but the tracked
`desktop/src/stripboard_optimizer/solver/` directory contains only
`__init__.py`. The imported worker module is absent. The desktop entry point
therefore must not be described as launch-ready until that module is
implemented and the application is run successfully.

The current desktop tree also has no `pyproject.toml`, desktop requirements
file, installer or packaging configuration. The current render path calls
Node.js and `rsvg-convert`; the image viewer uses Pillow. Cross-platform
path handling, dependency management and packaging remain to be completed.

The desktop README documents the actual tracked file structure and current
limitations. Do not infer that the broader desktop architecture specified
in Sections 2–24 exists merely because its target modules are listed there.

### 26.4 Documentation maintenance rule

Keep these documents aligned by responsibility:

- Root `README.md`: repository overview, web setup, renderer entry points,
  desktop status and links to detailed documentation.
- `desktop/README.md`: actual desktop file tree, current UI behaviour,
  runtime dependencies and known launch blockers.
- `src/frontend/README.md`: frontend setup and npm scripts.
- `src/frontend/standalone-renderer/README.md`: renderer source, build,
  CLI inputs/outputs, desktop runtime copy and parity tests.
- `project.md`: canonical target requirements, acceptance criteria and
  dated implementation snapshots.

When implementation changes, update the document responsible for that
area. Do not describe planned or unverified behaviour as implemented.
