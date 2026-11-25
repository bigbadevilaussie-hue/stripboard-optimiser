# JSON sniff — StripSolve 2.39 / SNIFF1

A fast deterministic read-only assessment of the prepared JSON after dimensions,
locks, cuts and stacking have been confirmed. It recommends 10k or 20k before
Pass One GO. The 100-point rubric is complexity, not construction quality Q3,
100 validation tests, or measured probability of finding a valid board.

## Weighted rubric

Each factor is capped at its maximum. Let H be available holes, calculated
from min(physical, preferred) for each dimension. P is on-board part count,
A is on-board pin assignments, N is sum over nets of max(0, assigned endpoints
minus 1), F is summed nominal footprint rectangle area, M is maximum assigned
net fanout. Off-board assignments contribute to N and M, since they require
connections. The shared mounting policy and footprint override resolver are
used. Nominal rectangle area is not measured physical clearance.

| Factor | Points | Formula |
|---|---:|---|
| Placement workload | 25 | 25 × min(1,P/32) |
| Pin density | 25 | 25 × min(1,A × max(0.5,1344/H)/100) |
| Connection workload | 20 | 20 × min(1,N/100) |
| Footprint pressure | 15 | 15 × min(1,F/(0.4H)) |
| Net fanout | 5 | 5 × min(1,M/25) |
| Constraints | 10 | min(10,2/fixed + 4/edge + 6/slide + 2/drilled-only + 2/no stacking), where / means per constraint |
| Total | 100 | Sum |

Raw score below 60 recommends 10k; 60 or more recommends 20k. Unknown footprints
also select 20k conservatively, with the uncertainty explicitly logged.
The threshold and weights are engineering choices calibrated on two known
circuit families, not a fitted or independently validated prediction model.

## Calibration evidence

Source fixtures at commit 56fc268507e826bc7ae04cd19e18af830db5824b:
test-fixtures/masters/audio/audio.json and test-fixtures/masters/moto/moto.json.
Both physical boards 24×56, no component locks. Compare using knife allowed,
stacking allowed. Features independently extracted from the repository JSONs
and the existing shared footprint registry:

| Feature | Audio | Moto |
|---|---:|---:|
| On-board components | 14 | 32 |
| Off-board components | 5 | 12 |
| Board pin assignments | 59 | 89 |
| Total assignments | 85 | 123 |
| Assigned nets | 29 | 35 |
| Connection demand | 56 | 88 |
| Max fanout | 16 | 27 |
| Nominal footprint cells | 412 | 293 |
| Complexity | 51.58 | 78.03 |
| Recommended moves | 10k | 20k |
| Historical 10k strict survivors / 2000 | 170 | 15 |
| Historical 20k strict survivors / 2000 | 215 | 37 |

Audio already exceeds the historical 100-survivor target at 10k. Moto
benefited from 20k, although neither budget reached 100 survivors. These
counts come from the historical archive inventory, not new solver runs.
The same-board examples motivated the score threshold between 51.58 and 78.03.
No claim of general accuracy or a guaranteed survivor count. Board constraints
or altered footprints may change the recommendation.

## GUI behaviour

CPU allocation retains the existing available-logical-CPUs-minus-one policy.
The separate 100-point checklist tick now refers to this static assessment,
not native speed measurements. No native decodes, seed trials, subprocess
solver invocations, or campaign-directory cleanup happen in the sniff.
Prepared source JSON and old campaigns are not modified. Only the independent
audit report is written: Work/<project>/logs/json_sniff.json. Activity logs
record individual factors, features and selected budget. Both radio options
remain selectable; confirmation and GO are still required.

Old native_calibration and budget_probe functions remain for historical
research and existing CLI/testing contracts; they are no longer called
by the GUI preparation worker. Strict solver qualification and Q3 unchanged.

Run regression tests with:
```bash
PATH="/opt/local/bin:$PATH" python3 -B -m unittest discover -s tests -v
```

Actual target Mac execution remains outstanding at release.
