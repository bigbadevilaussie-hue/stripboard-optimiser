# Stripboard Optimiser

**A stripboard (Veroboard) layout optimiser built on the Stripboard Editor project.**

Stripboard Optimiser is a development fork of [KarloFunke's Stripboard Editor](https://github.com/KarloFunke/stripboard-editor). The aim is to retain the editor's useful stripboard design workflow while adding a headless optimisation engine, independent layout validation, candidate comparison and a dedicated desktop interface.

This repository is under active development. The optimisation workflow and desktop application described below are the project direction; they should not be assumed to be implemented or production-ready yet.

## Project direction

The goal is to help turn an existing circuit layout into a more practical, compact and buildable stripboard design.

Planned capabilities include:

- **Optimise layouts:** run repeatable optimisation attempts with configurable effort, random seeds and worker count.
- **Respect design constraints:** preserve fixed components, excluded components, board dimensions and placement restrictions.
- **Handle real components:** import project JSON and custom part definitions, validate footprints and pin locations, and report missing definitions.
- **Validate candidates:** check component placement, overlaps, electrical connectivity and unintended shorts independently of the optimiser.
- **Compare results:** assess candidates using board area, wire count and length, cuts, track continuity and other layout measures—not just the solver's internal score.
- **Review and export:** inspect candidate layouts and export a selected, validated result without overwriting the original project.

The detailed requirements and staged development plan are maintained in [project.md](project.md).

## Starting point: Stripboard Editor

This fork inherits code and existing functionality from [Stripboard Editor](https://github.com/KarloFunke/stripboard-editor), an editor for drawing schematics, placing components on stripboard, adding cuts and link wires, checking layout conflicts, and producing printable build templates.

The inherited editor is the starting point—not a claim that the planned optimiser is already complete. Existing functionality and project structure may change as the optimiser is developed.

## Development status

The project specification is in place. Implementation is intended to proceed in stages:

1. Build and audit the headless optimisation pipeline.
2. Add independent electrical and physical validation and candidate ranking.
3. Build the desktop GUI around the headless engine.
4. Package distributable applications for macOS, Windows and Linux.

See [project.md](project.md) for scope, constraints and acceptance criteria.

## Technology

The repository currently contains the inherited Stripboard Editor codebase. Its existing stack includes:

- **Frontend:** Next.js
- **Backend:** Python, Django and SQLite

The planned optimiser will retain a separate headless solver interface so the optimisation engine can be tested and used independently of the GUI.

## Credits and licensing

This project is derived from [Stripboard Editor by KarloFunke](https://github.com/KarloFunke/stripboard-editor). The original project's authorship, copyright notices and licence terms remain applicable to inherited code. This fork is distributed under the repository's GPL-3.0 licence; see [LICENSE](LICENSE).

The built-in IC pinout data is derived from the [KiCad symbol library](https://gitlab.com/kicad/libraries/kicad-symbols) by the KiCad Library Team and is licensed under [CC-BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). The inherited import script is `src/frontend/scripts/importKicadIcs.js`, and the resulting data is in `src/frontend/data/icLibrary.ts`; the applicable attribution and share-alike terms continue to apply.

## Contributing and feedback

Bug reports, feature requests and development discussion can be raised through the [GitHub issues](https://github.com/bigbadevilaussie-hue/stripboard-optimiser/issues) for this fork.

When reporting an issue, include the project JSON or a minimal reproducible example where possible. Remove private or sensitive information before sharing project files.
