> Historical workflow; superseded in GUI 2.39 by [JSON complexity sniff](JSON_SNIFF.md). The GUI no longer invokes either native decoding or qualification sampling during preparation.

# JSON search-budget probe — GUI 2.25

## Evidence and decision rule

The prior 30-second decoder-only gate recommended 20k almost universally.
It could not predict qualification or account for routing and finishing.

Historical 2,000-seed WR campaigns: Audio 10k 170 survivors vs 20k 215;
Moto 10k 15 vs 20k 37. User-reported MOTOMIX 10k FULL produced 252 survivors
in 14m36s. These justify a working target of 100 survivors per 2,000 seeds,
not an optimal threshold or a guarantee. Q1 versus Q2 changes ranking, not
strict qualification. Historical circuit names are never hardcoded as classifiers.

## Actual prepared JSON

After board dimensions, placement locks and routing rules are confirmed,
the existing 100-decode speed calibration is followed by a distinct budget
probe using the current JSON, identical native CLI flags, exact board locks
and independent saved-board auditor as Pass One. Both knives/drills and
stacking choices are respected. No candidate or source JSON is modified.

1. Reuse completed, error-free, matching 2,000-seed Q2 FULL campaigns where
   available. Input fingerprint, rules, seed count and move budget must match.
   DEBUG and incomplete runs are not used as authoritative FULL history.
2. Without a matching 10k FULL campaign, test 100 actual 10k seeds, evenly
   distributed across seed IDs 1–2000 (10, 30, ... 1990).
3. At 5% or more verified survival, select 10k; no extra 20k sample is needed.
4. Below 5%, use matching FULL 20k history or test the same 100 seeds at 20k.
   Select 20k if its observed survival is at least as good, otherwise 10k.
   If both produce no passes, explicitly mark the choice inconclusive and
   preselect 20k only as a deeper trial. If both are below target, warn.
5. Report observed count/rate, projected 2,000-seed survivors, approximate
   sampling range (Wilson 95% approximation, not a validated prediction),
   and projected runtime from real per-seed wall times divided by workers.
   Runtime includes routing and finishing but excludes winner replay,
   startup and parallel scheduling overhead.

Sampling is a screening tool, not a powered comparison of close rates.
FULL results are exact observed counts, not future probabilities. A 100-seed
sample with 5 passes does not establish that 100 will qualify in a full run.
The user can override either budget and must explicitly confirm GO. No
automatic 200/2,000-seed campaign starts. Pilot seeds are not inserted into
campaign CSVs and will be solved again in a selected campaign.

## Files and cancellation

The separate report `Work/<project>/logs/budget_probe.json` contains input
fingerprint, routing rules, decoder, per-budget summaries and actual sampled
seed rows. It does not clear or modify any Pass One/Two output, winner or
original JSON. Existing full history may avoid new sampling altogether.
Probe progress appears in the status bar and preview header. Stop cancels
native subprocesses; a native execution error aborts the probe rather than
counting as a failed layout. A successful report replaces the prior probe
report only.

## Edge decoder selection

Any on-board locked component with explicit edge=true selects
`native/build/edge/libv5decode.so` for speed calibration, probe, campaign and
winner replay. Missing Edge library is a clear prerequisite error. Existing
standard campaigns keep their historical identity; new Edge campaigns include
decoder name and SHA256 in their manifest, invalidating earlier mismatched
standard-decoder Edge campaigns. The build includes both decoders already.
This does not implement Slide search, change native algorithm/pricing or
guarantee a strict MOTOEX pass. Standard campaign history predates binary
fingerprinting and is accepted on matching existing input/rule identity.

## Verification

Unit tests cover threshold decisions, actual sampled IDs, exact JSON/rules,
history reuse, output isolation, native error handling and Edge selection.
Target Mac execution and new standalone bundle rebuild are outstanding.
