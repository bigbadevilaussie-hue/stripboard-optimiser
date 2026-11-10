# Stripboard Optimiser

**A stripboard (Veroboard) layout optimiser built on the Stripboard Editor project.**

Stripboard Optimiser is a development fork of [KarloFunke's Stripboard Editor](https://github.com/KarloFunke/stripboard-editor). The aim is to retain the editor's useful stripboard design workflow while adding a headless optimisation engine, independent layout validation, candidate comparison and a dedicated desktop interface.

This repository is under active development. The existing web editor is the starting application. The optimisation workflow and desktop application described below are the project direction; they should not be assumed to be implemented or production-ready yet.

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

## Existing application

The repository currently contains the inherited Stripboard Editor web application. It provides the existing schematic and stripboard design workflow, including component placement, copper-strip net colouring, cuts, link wires, layout conflict feedback and printable build templates.

The current application is a web application built with Next.js and Django. The planned desktop optimiser is a separate development goal; this README does not imply that a desktop build or the complete optimisation pipeline is already available.

## Running the existing web editor locally

These instructions are for running the inherited web application, not for running a completed desktop optimiser.

### Requirements

- Node.js and npm
- Python 3
- The Python dependencies listed in `src/backend/requirements.txt`

The frontend also provides optional build scripts for WebAssembly and native solver components. Those scripts require a compatible Clang toolchain and, for the native Node addon, the relevant Node development headers.

### Backend

From the repository root:

```bash
cd src/backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

The Django API is served at `http://localhost:8000/api/`.

### Frontend

In a second terminal, from the repository root:

```bash
cd src/frontend
npm install
cp .env.local.example .env.local
npm run dev
```

The Next.js frontend is served at `http://localhost:3000`.

The example environment files are templates. Review and configure their values for your local setup before running the application. Do not commit real credentials, secrets or local environment files.

### Available frontend scripts

Run these from `src/frontend`:

| Command | Purpose |
|---|---|
| `npm run dev` | Start the Next.js development server |
| `npm run build` | Build the frontend |
| `npm run start` | Start the built frontend |
| `npm run lint` | Run ESLint |
| `npm run test:solver` | Run the solver test suite |
| `npm run test:schematic` | Run schematic tests |
| `npm run test:board` | Run board tests |
| `npm run test:branches` | Run branch tests |
| `npm run build:wasm` | Compile the existing C solver sources to WebAssembly |
| `npm run build:native` | Build the existing native solver libraries and Node addon |

The solver build scripts compile existing code; they do not by themselves provide the new optimiser pipeline described in [project.md](project.md).

## Deployment

The repository retains the inherited Docker deployment configuration:

- `docker-compose.yml` defines the Django, Next.js and Nginx services.
- `deploy.sh` pulls the current Git branch, rebuilds the Docker services and updates the running deployment.

These files belong to the existing web application deployment. They are not the packaging or release process for the planned macOS, Windows and Linux desktop applications.

## Development roadmap

The optimiser work is intended to proceed in stages:

1. **Headless pipeline:** input normalisation, solver execution, candidate preservation and run manifests.
2. **Validation and ranking:** independent electrical and physical checks, metrics and Pareto-based candidate comparison.
3. **Desktop GUI:** configure runs, monitor progress, inspect and compare candidates, and export a validated result.
4. **Distribution:** package standalone applications for macOS, Windows and Linux.

See [project.md](project.md) for the complete scope, constraints and acceptance criteria.

## Credits and licensing

This project is derived from [Stripboard Editor by KarloFunke](https://github.com/KarloFunke/stripboard-editor). The original project's authorship, copyright notices and licence terms remain applicable to inherited code. This fork is distributed under the repository's GPL-3.0 licence; see [LICENSE](LICENSE).

The built-in IC pinout data is derived from the [KiCad symbol library](https://gitlab.com/kicad/libraries/kicad-symbols) by the KiCad Library Team and is licensed under [CC-BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). The inherited import script is `src/frontend/scripts/importKicadIcs.js`, and the resulting data is in `src/frontend/data/icLibrary.ts`; the applicable attribution and share-alike terms continue to apply.

## Contributing and feedback

Bug reports, feature requests and development discussion can be raised through the [GitHub issues](https://github.com/bigbadevilaussie-hue/stripboard-optimiser/issues) for this fork.

When reporting an issue, include the project JSON or a minimal reproducible example where possible. Remove private or sensitive information before sharing project files.
