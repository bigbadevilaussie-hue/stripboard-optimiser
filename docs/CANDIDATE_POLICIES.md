# Native V5 candidate qualification policies

This is an **opt-in discovery interface** around the existing V5 C/TypeScript solver and saved-board auditor. It does not replace the annealer or relax the strict validator. It fixes the assumption that every native exit-2 result must be discarded before Pass Two.

**26 November 2026 validation:** the owner reported that the Mac Python GUI test suite passed after the two GUI fixes, and that **all 7 headless Node solver suites passed**. This validates the checked-in regression paths, **not** a completed 5,000-seed Moto campaign, a proven optimum, or a production-ready diagonal PCB.

## Policies

| Policy | What qualifies from the saved audit | Build-ready |
| --- | --- | --- |
| strict | Strict-valid boards only | Yes |
| diagonal | Strict, or otherwise fully valid with nonvertical (including horizontal) jumpers | Strict only |
| crossings | Strict, diagonal, or additionally wire-to-component-body crossings | Strict only |
| archive | Same qualification as crossings, while retaining remaining rejected candidates for research | Strict only |

Results retain the existing strict **valid** and **failures** fields. The optional **candidate** object records **status**, **qualified**, **strictValid**, **buildReady**, **electricalComplete**, **diagonals**, **bodyCrossings**, **hardFailures**, and **archiveOnly**.

A saved board may be STRICT_PASS, DIAG_PASS, ROUTE_CANDIDATE, REJECTED or AUDIT_ERROR. Only STRICT_PASS is build-ready. ROUTE_CANDIDATE has physical crossing problems; these must be repaired before building.

The auditor never exempts short circuits, incomplete nets (including GPS), unplaced components, illegal cuts, off-board copper, locked board/component movement, geometry conflicts, netlist/definition edits or unknown violations. Native SOLVER_ISSUES is **not** an exemption: the saved audit checks real copper connectivity and the physical board independently from the native result.

## Interfaces

**Native V5 CLI:** add the optional flags --strict 1 --candidate-policy diagonal. Valid policies: strict, diagonal, crossings, archive. The native output gets **candidate.prequalified** for triage, but its exit code stays exactly as before: exit 2 for any strict failure. A raw native prequalification is never a final acceptance.

**Saved-board auditor:** call node tests/solver/auditSavedStrict.js SAVED.json PREPARED_INPUT.json --candidate-policy diagonal. Exit 0 now means qualified for the explicitly requested policy, even if the original strict **valid:false** remains. Without the option, strict audit JSON and exit code remain unchanged.

## 5,000 seeds at 10k moves

New controller: **scripts/run_candidate_hunt.py**. It uses native V5 and the saved auditor, not a second optimizer. It archives every produced candidate JSON in gzip form, writes each trial to CSV, resumes using a matching manifest, shows qualified candidates only in terminal output with actual diagonal and body-crossing counts, and tracks strict/diagonal/routing champions separately. Only the strict champion is build-ready.

From the repository root, after pulling the updated `main` branch (use the existing Moto prepared input path):

    python3 -m py_compile scripts/run_candidate_hunt.py
    caffeinate -i python3 -u scripts/run_candidate_hunt.py --input "Work/moto--588c4c42a903/logs/moto_pass1_verified_input.json" --policy diagonal --seeds 5000 --moves 10000 --workers 2

For a small live smoke test first, change `--seeds 5000` to `--seeds 10` and explicitly choose a fresh `--out Work/candidate_hunt_smoke_10x10000` so the full campaign remains untouched.

The default full-run output folder is Work/candidate_hunt_diagonal_5000x10000. It never overwrites the earlier stopped ladder or earlier diagonal experiment. Run the same command again to resume completed seeds. ERROR seeds are retried; saved rejected candidates remain archived. If the script is interrupted, check results.csv for exactly what has completed.

Champion JSON files are WR_strict.json, WR_diagonal_candidate.json and (in crossings policy) WR_routing_candidate.json. A higher Q3 never overrides build readiness. The native solver's generation and energy function are unchanged.

## Tests

From the root:

    cd src/frontend
    npm run test:headless
    node tests/solver/testAuditSavedStrict.js
    cd ../..
    python3 -m py_compile scripts/run_candidate_hunt.py
    QT_QPA_PLATFORM=offscreen PATH="/opt/local/bin:$PATH" python3 -B -m unittest discover -s tests -v

New candidatePolicy.test.js and candidateAuditCli.test.js run automatically under npm run test:solver.

## Limits

This changes **qualification**, not the C decoder/router's move distribution. Higher move budgets with the same seed are still independent restarts, not warm-start board repairs. It does not prove any historical WR candidate has been recovered. The owner-reported Mac tests passed; a fresh live Moto candidate-campaign smoke run and its full candidate classifications have **not** yet been reported.

The saved-board auditor is a separate invocation and re-evaluates the saved layout, but it **shares electrical and geometry helpers** with the solver CLI; it is not a completely independent second electrical implementation. Research candidates are never a manufacturing sign-off.
