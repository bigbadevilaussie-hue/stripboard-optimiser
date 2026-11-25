# StripSolve: one Work directory per source JSON

GUI 2.19 uses Q2 in the same paths shown below. Old Q1 campaigns must be replaced through explicit overwrite; they cannot resume or feed Pass Two. CPU allocation is recorded in `logs/cpu.log` and campaign activity.log.

Each loaded source JSON gets an isolated workspace under the existing repo
`Work/` directory. Source JSON files are not moved or rewritten.

## Naming rule

```
Work/
  audio--<12 hexadecimal characters>/
    project.json.info
    pass 1/10k/results.csv
    pass 1/10k/activity.log
    pass 1/10k/campaign.json
    pass 1/10k/debug/results.csv   # 200 seeds only
    pass 1/10k/debug/activity.log
    pass 1/10k/debug/campaign.json
    pass 1/20k/results.csv
    pass 1/20k/activity.log
    pass 1/20k/campaign.json
    jsons/10k/winner_seed_XXXX.json
    jsons/10k/winner_seed_XXXX-components.svg
    jsons/10k/winner_seed_XXXX-copper.svg
    jsons/10k/debug/            # Debug winner JSON/SVG, if a seed qualifies
    jsons/20k/
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
- **Debug ON/OFF:** an unchecked Debug box runs all 2,000 seeds; checked
  Debug runs exactly 200 seeds. Debug results and winner outputs live inside
  `pass 1/<budget>/debug/` and `jsons/<budget>/debug/` and never clear the
  corresponding full-run folders. The independent strict-audit requirements
  are unchanged.
- **Pass One GO:** keeps 10k and 20k campaigns separate. A fresh campaign
  starts in its own budget folder. If that budget already has files, the GUI
  explicitly offers Resume (for a compatible unfinished run), Overwrite & Start
  (requires a separate checkbox), or Cancel. Only the selected budget's
  `pass 1/<budget>/` and `jsons/<budget>/` folders can be cleared.
- **Pass One CSV:** one row **per seed**, `seed,cut,w,q,time_taken,s,wire_length_mm,quality_version,status,reason`,
  with `PASS`, `FAIL` and `ERROR`. A separate `campaign.json` is
  `INCOMPLETE`, `STOPPED`, or `COMPLETED`. Resume keeps all completed PASS
  and FAIL seeds; only missing and ERROR seeds run again. Source fingerprint,
  solver rules, Q2 schema/version, move budget and seed count must all match. Worker allocation may change on resume.
- **Pass One winner:** after every seed has a definitive PASS/FAIL status,
  replay the highest-Q PASS at its original move budget, independently audit it,
  and save winner JSON plus component/copper SVGs under `jsons/<budget>/`.
  Replay/render failure is reported; an unverified winner is never published.
- **Pass Two GO:** selects exactly one completed Q2 budget CSV, imports only independently verified PASS seeds, and clears
  only that same JSON's `pass 2/`. New-format campaigns must be marked
  COMPLETED. Pass Two native optimisation is still unimplemented.
- **Cold-start Pass Two:** when no JSON is loaded, choose an existing named
  workspace; if only one exists it is automatically selected. No full JSON
  import or new Pass One sweep is required.

## Protecting existing results from the old layout

Previous `Work/pass 1/` and `Work/pass 2/` are **never automatically cleared,
moved, or overwritten** by the new GUI.

After loading a source JSON and completing its lock review, the GUI can
**copy** legacy `Work/pass 1/results.csv` and `activity.log` to that source's
new workspace's **legacy `pass 1/` root**, but **only** if the original Pass
One `input_sha256` in its activity log exactly matches the current native-solver
input prepared from the reviewed JSON. The destination must have an empty
Pass One folder. Nonmatching or already-present data is left alone.
The originals remain untouched.

Any previous `Work/<project>/pass 1/results.csv` remains readable for historical inspection, but cannot enter Pass Two. It is not silently migrated into 10k or 20k,
and it does not contain the failed-seed records required for safe resume.

No JSON layout is reconstructed from a CSV; only the native solver replay can
recreate a saved candidate.

## Operational safety

- Project folders are created lazily when a JSON is successfully loaded.
- Starting the app alone never clears or associates legacy results.
- Source and workspace directories cannot be symlinks.
- This workspace change does not modify native solver flags, quality formula,
  seed numbers, routing policies, verifier or board renderer.
- This directory is gitignored by `/Work/`, as before.
