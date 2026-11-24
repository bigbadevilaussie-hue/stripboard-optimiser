# Route-O-Matic: one Work directory per source JSON

Each loaded source JSON gets an isolated workspace under the existing repo
`Work/` directory. Source JSON files are not moved or rewritten.

## Naming rule

```
Work/
  audio--<12 hexadecimal characters>/
    project.json.info
    pass 1/results.csv
    pass 1/activity.log
    pass 2/candidates.csv
    pass 2/activity.log
    jsons/
    logs/
  moto--<12 hexadecimal characters>/
    ...
```

The folder name is the lowercased, filename-safe JSON stem (max 48 characters)
followed by `--` and the first 12 characters of SHA-256 of its **resolved
absolute source path**. Examples: `audio--...`, `moto--...`,
`motomix--...`. Two `audio.json` files in different directories are
always separated. Edits to the same file do **not** change the workspace.
Moving/renaming the source JSON intentionally gives it a new identity; the
previous workspace is preserved.

`project.json.info` records the source path and source filename and prevents
accidentally binding a folder to a different file.

## Project selection

- **Load JSON:** after successful import, GUI binds that source to its named
  workspace. All Pass One output goes to its own `pass 1/`.
- **Pass One GO:** clears only that JSON's `pass 1/` immediately before running;
  preserves other JSONs, pass 2, jsons and logs.
- **Pass Two GO:** imports results from the selected JSON's `pass 1/`; clears
  only that same JSON's `pass 2/`. The Pass Two optimiser itself remains
  unimplemented.
- **Cold-start Pass Two:** when no JSON is loaded, choose an existing named
  workspace; if only one exists it is automatically selected. No full JSON
  import or new Pass One sweep is required.

## Protecting existing results from the old layout

Previous `Work/pass 1/` and `Work/pass 2/` are **never automatically cleared,
moved, or overwritten** by the new GUI.

After loading a source JSON and completing its lock review, the GUI can
**copy** legacy `Work/pass 1/results.csv` and `activity.log` to that source's
new workspace, but **only** if the original Pass One `input_sha256` in its
activity log exactly matches the current native-solver input prepared from the
reviewed JSON. The destination must have an empty Pass One folder. Nonmatching
or already-present data is left alone. The originals remain untouched.

No JSON layout is reconstructed from a CSV; only the native solver replay can
recreate a saved candidate.

## Operational safety

- Project folders are created lazily when a JSON is successfully loaded.
- Starting the app alone never clears or associates legacy results.
- Source and workspace directories cannot be symlinks.
- This workspace change does not modify native solver flags, quality formula,
  seed numbers, routing policies, verifier or board renderer.
- This directory is gitignored by `/Work/`, as before.
