# 27 November 2026 — Dave's fixed USB Edge budget ladder and Q86.80 verification

## Current outcome and evidence levels

MOTOEX: **8/100 STRICT PASS at 100k, eight distinct signatures; Q81.92 (seed 97)**. This supersedes the partial 7/90 terminal snapshot. MOTO (different fixture): **Q86.80, seed 1216 at 460k + deterministic stack polish**, independently reproduced arithmetically by Claude from the owner-supplied winner.zip. No claim of a world record across other solvers or a Q86 result at 2k. No production solver or GUI change.

Evidence: owner terminal logs for the completed lower-budget runs; owner-provided winner2.zip directly inspected for 100k; archived Mortal Kombat results and intermediate witnesses in this repository; owner's pasted Claude review of winner.zip. The final polished MOTO output and raw MOTOEX ZIP have not been added to Git by this documentation commit. Do not confuse report verification with a new full electrical/geometry replay.

## Fixture and controlled campaign

Canonical source: test-fixtures/masters/moto/motoex.json, SHA256 e078b01bd5e563f0b9cd37289143e7fa7000a36a8b8a90d9474ce70b6f6d4bae. 45 components, 123 net assignments, 10 off-board. Original canvas 99×500. Prepared by existing prepare_trial: 24 rows × 56 cols, both locked, all other placements/locks cleared (including TVS); USB ID 8cee7751-5442-4b06-aaff-7af39f032ec3 remains at zero-based row13 col47 rotation0, locked=true, edge=true, slide=false. Its 6×13 body reaches row25; two overhanging body rows are intentional. Pins IN+ and GND at (13,47) and (13,52) remain on board. No master edit, no board expansion permitted.

Existing native Edge experiment, not Arm C. Native build macro V5_EXPERIMENT_EDGE_MOUNT=1 (plus fast-grid-clear and identical-genome shortcuts); strict=1, drilled=0, nostack=0, drill-domain=0, wire-polish=0, routing-preference=wires. Knives and stacking allowed; no nonvertical wires, crossing, electrical or dimension failures accepted. Bum Mode remains unimplemented/off. Runner's historical top-five order is W, C, wire length, price, not Q3.

Same sequential seed IDs 1–100, specified before execution, fresh anneal for each budget. Three workers, 10-seed batch barrier, 30-second idle cooldown after each of the first nine batches; 270 seconds intentional idle per full run. No final cooldown. Eight scheduler/fixture unit tests passed on Mac in 0.056s. Commit 7f5b662143ef1357b4f9edd15d6841d129e6c436 introduced optional cooldown only. No source rebuild or change requested between subsequent budget rungs. Binary identity across lower rungs is owner workflow evidence, not independently checked manifests.

| Moves | Strict | No feasible placement | Layouts produced | Wall seconds including smoko | Local campaign folder |
| ---: | ---: | ---: | ---: | ---: | --- |
| 2,000 | 0/100 | 19 | 81 | 293.74 | ~/DAVE_EDGE_2K_20261127_122016 |
| 10,000 | 0/100 | 4 | 96 | 343.16 | ~/DAVE_EDGE_10K_20261127_122607 |
| 50,000 | 0/100 | 0 | 100 | 453.16 | ~/DAVE_EDGE_50K_20261127_124108 |
| 100,000 | 8/100 | 0 | 100 | 565.42 | ~/DAVE_EDGE_100K_20261127_130647 |

Lower rungs are terminal-log observations, not raw JSON re-audits. At 100k manifest + all 100 timing/row/col records agree with 100,000 moves, 24×56. 60 reported electrically complete (8 strict, 52 failed); 40 incomplete; 100 geometry=0; 84 nonvertical>0, 80 crossings>0, 20 zero crossing. Mean per-seed elapsed 7.694s, median 7.002s; actual solver mean 7.231s, median 6.578s, p95 12.354s; total wall 565.42s, 295.42s excluding scheduled 270s pauses (not pure CPU time). Wilson 95% interval for 8/100 approximately 4.1–15.0%; this is the observed sequential-seed sample, not a general success guarantee.

Claude initially used pooled 0/300 and Fisher's independent-sample test. Because seed IDs recur across budgets, do not treat the 300 as independent; for 50k vs 100k the observed paired discordances are eight gains, zero losses, exact one-sided sign/McNemar p=0.00390625 (two-sided 0.0078125) under the symmetric-discordance null. Budget improves this fixture's observed hit rate; does not establish 100k as universally optimal, nor justify the blanket claim that zero survivors always requires deeper search.

## 100k evidence provenance

Owner upload winner2.zip SHA256 401fd5214e8414dd24beb7225ddafad0bee6ee67adbf8abe70bd73fe706aa97b. Contains manifest.json, results.csv, results.json, prepared_input.json and exactly eight solved JSONs. Manifest gitCommit 7f5b662143ef1357b4f9edd15d6841d129e6c436, createdUTC 2026-11-27T03:06:48.685170+00:00.

- Prepared input raw SHA256 0554804ce7ef1fb2c527d6adbbe7996085d00fd598b9781a842dae76c9176dce; Python canonical sorted-key JSON SHA256 0e5673f34990969ff9824913a86d9e1b6ed7dd6c6e9bf5c67b69eea8f45df844.
- Manifest Edge decoder SHA256 3a3a651fe7b8fa12a1a936d7cf26ed94973b06603d3d3d6c53339fcda995d520.
- Native route SHA256 5758e84282da0145c480fd2b900222cd4926bd7b6299eb57b326d225e3bcf0b4.
- Native addon SHA256 5b308c4e2376bad5ba9ae3fc20154cb51605fea4a7180c6f6322646fd3350bc7.

Recorded binary fingerprints, not binaries independently rehashed in this session.

## Independent saved-JSON construction metrics

Recomputed from all eight ZIP JSONs, not CLI stacked-wire count. Q3 per gui/quality.py contract: W, C, L in mm at 2.54 mm pitch, D, U and maximum positive-length vertical edge coverage S. Touching endpoints alone do not stack. S1 ceiling is theoretical assuming all stacks can be removed without other changes, not a demonstrated polish.

| Seed | W | C | Drilled | Knife | S | L mm | Q3 | S1 ceiling |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 97 | 29 | 45 | 39 | 6 | 2 | 439.42 | **81.92** | 82.32 |
| 71 | 33 | 49 | 44 | 5 | 2 | 424.18 | 80.45 | 80.85 |
| 79 | 35 | 51 | 43 | 8 | 2 | 535.94 | 78.75 | 79.15 |
| 60 | 34 | 50 | 43 | 7 | 2 | 645.16 | 78.28 | 78.68 |
| 10 | 36 | 52 | 44 | 8 | 3 | 650.24 | 76.24 | 77.84 |
| 66 | 37 | 53 | 47 | 6 | 3 | 619.76 | 76.08 | 77.68 |
| 16 | 34 | 50 | 49 | 1 | 4 | 675.64 | 74.83 | 78.43 |
| 51 | 44 | 60 | 45 | 15 | 3 | 795.02 | 71.88 | 73.48 |

Seed97 outranks every other winner even against its S1 ceiling. Seed16 has only one knife, but S4. All eight have C−W=16. Q3 is not an electrical score, and does not separately penalize knife count. No new MOTOEX polish executed.

All eight exact raw file SHA256 values match results.json savedSha256:

| File (under solved/) | SHA256 |
| --- | --- |
| seed_0010_col_47.json | 84325eb714f53a073ff3a62b4bcaad11a1ec08d74282672fd83167d30fc4e4c9 |
| seed_0016_col_47.json | 8d21e9df66b66ddf964485584f20fa0c1d56d5a95ac8ca63baf43cce03afff20 |
| seed_0051_col_47.json | 5091eddbbfa0d523e9cd76394685e20de30555ca650add5dee28679319d09848 |
| seed_0060_col_47.json | aa238583df331b5c5106a894780042cb31eebf9744773ebfc3a0d64328f0e374 |
| seed_0066_col_47.json | 222e35443b98663d80f1b11967d8fc4992f58239958ecd94c69620825f680507 |
| seed_0071_col_47.json | 58ee579c48cb0e2576d9cb3bdc4c2cbb12669138c1ec5311964e84e68563041d |
| seed_0079_col_47.json | fb36561feb1e4e7256edc8c43c57d58ee5b17d9b88fb3c19b9089b3bfe91d0e7 |
| seed_0097_col_47.json | 848994b9663a5a6f001f23930d91a402151128710fb7bf360a5a64c61e29c7c0 |

Direct ZIP checks all eight: exact 24×56 with both locks, full USB object equal to prepared input, only USB locked, component ID set unchanged, nets/assignments/componentDefs unchanged, all on-board components placed, cuts and wire endpoints within frame (between cut not in last column), every jumper vertical with positive length. Recorded strict pass, zero conflicts/incomplete/geometry/nonvertical/crossings. **Seed60 has a recorded C1 (1000uF) body-overhang warning at row1 col48**, unlike the other seven; strict status permits this warning, but physical fit needs inspection. Do not call these eight independent complete body/pin/copper-graph audits: library definitions and repo transforms are required, and full replays are outstanding. The ZIP contains only the solved boards, not 92 rejected board JSONs.

## Failure diagnostics: GPS and MPU

From all 100 results.json incompleteNets records:

| Incomplete net names | Boards |
| --- | ---: |
| None | 60 |
| GND, net25, net29 | 32 |
| GND, net10, net11 | 5 |
| GND, net10, net11, net25, net29 | 1 |
| GND, net25, net29, net8 | 1 |
| 12v Switched | 1 |

37/40 incomplete boards have exactly three incomplete nets. 32/37 are the GPS triple; five MPU triple. GPS exact triple seeds 6,7,8,12,14,24,28,30,33,35,38,40,41,43,44,47,50,52,61,64,72,74,75,77,82,84,85,90,94,95,98,99. Seeds 6,33,74 explicitly show isolated GPS.GND, GPS.TXD (net25 to ESP32.RX), GPS.RXD (net29 to R12.1). MPU triple seeds 49,65,70,87,92; net10 SDA to ESP32.GPIO6/U2 SDA, net11 SCL to ESP32.GPIO7/U2 SCL; GND also disconnected. These are diagnostic patterns, not proof of the causal rotation or that the prior Arm C mask can be copied unchanged.

Seven incomplete boards have no nonvertical or crossing records: 6,7,33,74,82,85,94. Four electrically complete non-strict boards have one nonvertical and at most two crossing records: 18 (1 crossing), 21 (0), 26 (2), 62 (1). Need actual rejected JSONs to determine distinct offenders and repairability; crossings count records, not distinct jumpers. No speculative Bum Mode acceptance.

Next proposed research, not launched: inspect actual GPS/MPU rotations and access corridors in rejected boards; build a separate Edge + validated orientation-domain experimental decoder, paired 100 seeds at 100k with identical rules/anchor/worker/cooldown. Baseline 8/100 and Q81.92. Re-audit eight winners against prepared input with repo strict audit and independent graph using correct edge semantics; inspect C1 warning; deterministic stack polish only on proven strict incumbents and record any Q gain. Do not modify canonical master, production binary, strict gate or GUI. Preserve all experiment archives. No owner approval to start another campaign implied by documentation.

## Claude review: MOTO Q86.80 (separate from MOTOEX)

Original archive: research/mortal-kombat/0460k/Dave/candidates/seed_1216.json.gz and result.json. Intermediate: research/karl-autopsy/20261127/460000_1216_direct_endpoint.json, full SHA256 e544f6c89470b60f3e21e42b4361606347a5f3440827c3bd8746c1c3653e0e9c; already independently rechecked and committed. Local final report ~/KARL_STACK_POLISH_20261127_105635/report.json, output original_1216_460000.json (the filename denotes the input cohort, not the pre-polish state). Claude noted provenance ambiguity and requested rename on archival.

| State | W | C | L mm | S | Q3 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Original 1216 / 460k | 21 | 37 | 279.40 | 3 | 85.20 |
| First endpoint witness | 21 | 37 | 279.40 | 2 | 86.40 |
| Iterative stack polish | 21 | 37 | 279.40 | 1 | **86.80** |

Q3 unrounded final 86.8048, original 85.2048, intermediate 86.4048. Four relocations from original (227 checks), three from intermediate (168 checks). No extra annealing. Claude independently reconstructed earlier states by reversing steps, reproduced final metrics from saved board, and recomputed 64 before/after states in 32 report entries with zero mismatches; 11 improvements (9/25 original strict plus 2/7 overlapping witnesses); W/C/L invariant. Steve 1859/500k 85.66→86.06 as independently predicted. Claude reported 36 drilled/1 knife on final 1216, no intervening cut on affected endpoint rows, no new drilled endpoint or shared wire endpoint in eight recorded moves inspected. He could not independently check library component lead occupancy or body crossing from JSON alone. Original research harness checked strict audit and separate graph before/after, sharing repository pin transforms. Distinguish that from Claude's independent arithmetic and limited hole-level checks. No claim of a fully independent manufacturing audit.

Claude-reported hash prefixes: compressed original f8c94976…, polished final 7a2f96ae…; intermediate full hash above. Do not expand prefixes into guessed full hashes. Archive final output under an unambiguous name such as 460000_1216_stack_polished.json, with exact raw final SHA256, original compressed and decompressed hashes labeled by representation, intermediate hash, report and exact input provenance. Original and final must never overwrite one another. Raw final artifact not provided to this documentation session; outstanding exact archive and repo-based independent replay. The initial 284-layout analysis omitted this 1216/460k board, explaining the apparent ceiling discrepancy. No need to change Q3.

## Reproduction (Mac)

Use existing compiled Edge binary, not the separate Arm C binary, and a fresh output folder. Check manifest hashes if comparing across builds.

```bash
cd ~/Documents/stripboard-optimiser && \
/opt/local/bin/python3.13 scripts/run_motoex_native_sweep.py \
--seeds 100 --moves 100000 --workers 3 \
--cooldown-every 10 --cooldown-seconds 30 \
--column 47 --slide no \
--out "$HOME/DAVE_EDGE_100K_$(date +%Y%m%d_%H%M%S)"
```

This is the already completed baseline command, not a request to rerun it. Raw winner2.zip and final MOTO polish report/artifacts remain to be archived; exact source files must be preserved rather than reconstructed from narrative. GUI 2.39 and root version 2.00 unchanged. Main only.

## 27 November — systematic high-ID seed sampling (requested, not yet run)

Owner requests 100 evenly spaced IDs over conservative exact JavaScript seed-initialisation range, 10k moves per seed, 15s smoko. Keep three workers; use batches of ten (assumed cadence from earlier 100-seed tests), nine pauses. autoLayout5.ts multiplies (seed+1) by 0x9e3779b9 and 0x85ebca6b before >>>0; floor((2^53−1)/0x9e3779b9)−1 = 3,393,262 guarantees exact integer products, not a proof of a hard solver limit or unique layouts. Step=floor(3393262/100)=33932; seeds i*33932 for i=1..100, last3393200. Systematic ID sampling is not random or uniformly covering RNG states; even stride shares low bits. Optional --seed-stride default1, manifest and summary preserve stride, resume validates it (legacy default1) and rejects off-schedule checkpoint records. Runner now refuses IDs beyond conservative bound; native solver unchanged. Same 24×56 USB Edge fixed col47, strict knives/stacks allowed, drill-domain off. Added schedule/bound test; Mac execution pending. No GUI version bump.

