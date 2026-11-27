# 27 November 2026 — main-only consolidation and Karl forensic research

## Revision and scope

- Repository milestone: 2.00 (root VERSION); headless package: 2.0.0; StripSolve GUI: 2.39; construction score: Q3.
- Baseline after consolidation: `84cdc2315a2afe72b71c27fca5bd4852c0cb455d`. GitHub verification after cleanup returned only main. The four former branch tips are ancestors of main.
- Research scripts and archives were added; active solver, GUI and renderer implementations were not modified by consolidation. GUI version policy does not require a bump for research/documentation-only changes. No new release tag.
- Owner's standing rule: work directly on main, never create branches or pull requests, and never submit reports, fixes, comments or contributions to Karl's upstream repository. Research lives in directories within main. Changes must carry their revision and documentation updates together. Do not change unrelated user files.
- Owner's Mac cleanup output showed main and origin/main only, with pre-existing tracked renderer modification and untracked local research files preserved. Do not reset, clean, stash or commit those indiscriminately.

## Completed Mortal Kombat — archived evidence

Source: [manifest](../research/mortal-kombat/manifest.json), [scorecard](../research/mortal-kombat/scorecard.csv), [championship](../research/mortal-kombat/championship.json), and 100 compressed saved candidates with individual result JSONs. All 50 rounds completed. Each budget is a fresh anneal, not a warm start; 10k–500k in 10k steps; one worker per fighter, 30-second interval between rounds. Fixed 24×56, knives and stacking allowed. Experimental orientation decoder used; do not assume it is the production binary.

Manifest input SHA-256: `0eee8b94847ebf622c4b2b0d580644f8456bb079a159617c0c72b65f76d09313`.
Manifest decoder SHA-256: `265ce63fb3828d467d4aff4307a658cbcbb3e550cee384e2ffeeb53504948064`. These are recorded fingerprints, not a fresh binary verification.

| Metric | Dave / Sub-Zero 1216 | Steve / Scorpion 1859 |
|---|---:|---:|
| Championship points | 234 | 216 |
| Round wins | 26 | 16 |
| Strict passes | 14/50 | 11/50 |
| Best strict Q3 | 85.58 at 450k | 85.66 at 500k |
| W/C/S at best | 23/39/1 | 22/38/2 |
| Cumulative solve seconds | 733.699 | 740.129 |

Eight drawn rounds; 25 strict passes, 75 failures. Championship scoring is distinct from strict qualification and best Q3. Neither reaches Q86. These two selected seeds are not an unbiased sample of solver performance. No additional competition run authorized.

## Forensic source findings (not runtime regression results)

Source reviewed against the repository code preceding consolidation:

1. `layout2/finish.ts:573–576,594–596`: endpoint repick and channel repair reject nonvertical wires at entry. Other repair paths exist; a reproducible saved-board rescue would establish impact.
2. `layout2/slantRepairPass.ts:59` and `layout2/finish.ts:182`: tap selection checks lockedIds, not c.locked; caller passes an empty set. A locked one-hole tap can enter the candidate set. No illegal adoption demonstrated; Moto fixture has no locked components.
3. `layout2/finish.ts:372`: final crossing score uses original padded comps rather than chosen updated placements. Possible stale-geometry scoring after movement; runtime reproduction pending.
4. `v5wasm/route.c:125,683–741,946–967`: relay budget prioritises wider donated tails, retaining free groups even beyond nominal cap; one intermediate relay per connection attempt. Search limitations, not yet established causes of Moto failure.
5. `layout2/finish.ts:535–536,826`: final repair eligibility tests no new geometry violations relative to the starting layout, not zero violations. Saved strict audit remains mandatory.

Source locations are under src/frontend/components/stripboard/. Do not describe these as fixed or claim a measured speedup.

Priority archive cases: seed 1216 at 280k (Q73.82, NONVERTICAL_1), 350k (Q81.97, BODY_CROSSINGS_1), 360k (Q80.04, BODY_CROSSINGS_1), 490k (Q79.76, BODY_CROSSINGS_2). Archived audit records report zero conflicts, incomplete nets, geometry violations and unplaced components for these cases.

## Research scripts and next gate

Owner Mac net-wide smoke (report KARL_AUTOPSY_SMOKE_20261127_103201): 6/6 replay, two strict, zero graph disagreements, zero rescues or improvements. Seed1216 280k source/target free holes 52/68, zero eligible cross-group column pairs; 350k 27/19, all 9 pairs blocked by bodies; 360k 9/14, 1/1 blocked; 490k 1/33, 1/1 blocked. All had zero clean edges and no search truncation. This disproves only the tested endpoint/relay search under existing cuts, occupied-hole restrictions and no shared solder holes, not arbitrary fixed-placement routability. Next gate: single existing cut slide, preserving kind/count, all component pin and existing wire-anchor copper partitions, original locks/netlist, remaining wires and 24×56 dimensions. Enumerate every candidate single-cut column, prioritize shortest displacement; require independent graph before rerouting and both audits after rerouting. Four-hop bounded search (5,000 queued states and eight paths per cut), 256 candidate audits per board, explicit truncation/cap reporting. JS syntax and extracted graph/path/cut-partition tests passed; owner runtime pending. No production or GUI change.

Owner Mac six-board smoke (27 Nov, report KARL_AUTOPSY_SMOKE_20261127_102846): exact input fingerprint matched, graph self-test passed, 6/6 boards replayed, 2 strict reproduced, zero electrical graph disagreements, four single offending wires (490k crosses two bodies), zero rescues/improvements. Each rejected board reached only one audit trial (redundant offending-wire removal). Direct and one-empty-strip relay searches produced no audit candidates. This is a negative result for the restricted search, not proof of placement infeasibility. Follow-up net-wide search removes the same offending wire and considers all copper strips joined to either side, plus pinless transit groups, with unique new endpoint holes, no cuts/placement changes and at most four hops. Bounded at 20,000 queued states and 64 paths per board, reports truncation and blocked edges; not exhaustive. JS syntax and extracted graph/path self-tests pass; net-wide Mac replay completed as recorded above. No production change.

**Smoke gate update:** run `scripts/run_karl_autopsy.py` with MacPorts Python from the checkout after pulling main. It locates the original prepared input by the manifest fingerprint and defaults to the four near-misses and two champions; `--all` requires separate explicit invocation after smoke review. The JS harness independently rechecks the fingerprint, skips electrical graph disagreements and attempts removing a redundant offending wire. JavaScript syntax and extracted graph self-test passed in AI tooling. Initial six-board Mac smoke completed as recorded above; full 100-board replay and new net-wide rescue remain unverified.

- [scripts/karl_autopsy.js](../scripts/karl_autopsy.js), original commit 8e42c3f: fixed-placement/cut wire surgery, existing isolated relay strips, redundant jumper removal, stack reduction and a horizontal copper-graph replay. JavaScript syntax checked before commit only. Embedded synthetic graph self-test and full archive replay have **not been executed** on the Mac. The graph reuses repository pin transforms; not a fully independent physical verifier. Verify prepared-input provenance against manifest using the canonical Python fingerprint and confirm compiled helper compatibility before running. Preserve original archives; report results separately; one worker; no annealing or board growth.
- [scripts/sister_forensics.js](../scripts/sister_forensics.js), original commit 628a3d1: independent graph/topology research, runtime validation pending.
- [Historical legal-topology patch](../research/legacy-topology/README.md): archived obsolete desktop worker, not active GUI implementation.
- Candidate policy source already matched main byte-for-byte at merge; newer main documentation retained.

The immediate objective is a reproducible strict rescue from a failed placement with no additional annealing, no part/cut changes and no larger board. Only a verified rescue is evidence of a missed router opportunity. The eventual 2k strict Q86 goal remains a research target, not a result. GUI Pass Two is still import-only. Production tests were last owner-reported passing on 26 November; no post-consolidation rebuild or regression run reported.
