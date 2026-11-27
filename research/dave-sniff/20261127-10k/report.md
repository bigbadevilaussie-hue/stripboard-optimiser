# Dave — local campaign sniff

Read-only Python inspection. Electrical/geometry/crossing status is recorded CLI evidence, not an independent copper graph/body audit. Q3 on rejected boards is descriptive only. Near misses are research candidates, not strict passes.

## Comparison

| Metric | DAVE_EDGE_10K_1000_20261127_144302 | DAVE_EDGE_SAFARI_300_20261127_145216 |
|---|---:|---:|
| Attempts | 1000 | 300 |
| Strict | 0 | 0 |
| Unsolved | 40 | 13 |
| Saved hashes verified | 960 | 287 |
| Missing saved | 0 | 0 |
| Reported electrically complete | 262 | 86 |
| Reported incomplete | 698 | 201 |
| Reported conflicts | 1 | 0 |
| Zero crossings | 29 | 10 |
| Zero nonvertical | 19 | 13 |
| Wire diagnostic mismatches | 0 | 0 |
| Net diagnostic mismatches | 0 | 0 |
| Invariant failures | 0 | 0 |
| Read/schema errors | 0 | 0 |
| distinct_placements | 960 | 287 |
| distinct_layouts | 960 | 287 |
| candidate_count | 34 | 13 |
| reported_duration_s | 510.64 | 207.84 |

## Provenance

Matching manifest fields: {"binarySha256":true,"board":true,"drillDomain":true,"drilled":true,"moves":true,"nostack":true,"rank":true,"sourceSha256":true,"usb":true,"wirePolish":true}

Cross-campaign overlaps: {"layouts":1,"placements":1,"seed_ids":1}

## DAVE_EDGE_10K_1000_20261127_144302

### Incomplete-net combinations

| Net combination | Boards |
|---|---:|
| GND;net25;net29 | 435 |
| (none) | 262 |
| GND;net10;net11;net25;net29 | 44 |
| 12v Switched;GND;net25;net29 | 34 |
| GND;net10;net11 | 27 |
| 12v Switched | 19 |
| GND;net25;net29;net8 | 18 |
| GND;net2;net25;net29 | 10 |
| net5 | 9 |
| GND;net25;net29;net5 | 9 |
| 3V3;GND;net10;net14;net15;net17;net18;net19;net20;net22;net25;net29;net3;net6;net9 | 6 |
| 3V3;GND;net10;net14;net15;net17;net18;net19;net20;net22;net25;net3;net6;net9 | 5 |
| 12v Switched;GND;net10;net11 | 4 |
| net8 | 4 |
| net2 | 4 |
| GND;net25;net27;net29 | 4 |
| net3 | 3 |
| 12v Switched;GND;net25;net29;net5 | 3 |
| GND;net25;net29;net9 | 3 |
| GND;net10;net11;net25;net29;net8 | 3 |
| net4 | 3 |
| net24 | 3 |
| net6 | 3 |
| net27 | 2 |
| GND;net25;net29;net3 | 2 |
| GND;net25;net29;net4 | 2 |
| GND;net25;net29;net6 | 2 |
| 12v Switched;net8 | 2 |
| 12v Switched;GND;net2;net25;net29 | 2 |
| net28 | 2 |
| GND;net25;net26;net29;net8 | 1 |
| GND;net10;net11;net8 | 1 |
| GND;net24;net25;net29 | 1 |
| GND;net10;net11;net25;net29;net5 | 1 |
| 12v Switched;GND;net25;net29;net8 | 1 |
| 12v Switched;GND;net10;net11;net25;net29 | 1 |
| net22 | 1 |
| GND;net10;net11;net22 | 1 |
| net29 | 1 |
| GND;net25;net26;net29 | 1 |
| 12v Switched;net2 | 1 |
| 3V3;GND;net10;net11;net25;net29 | 1 |
| net26 | 1 |
| 12v Switched;5vSwitched;GND;net22;net25;net29;net5 | 1 |
| GND;net10;net11;net25;net27;net29 | 1 |
| 12v Switched;net4 | 1 |
| 12v Switched;3V3;GND;net10;net14;net15;net17;net18;net19;net20;net22;net25;net3;net6;net9 | 1 |
| 12v Switched;GND;net10;net11;net25;net29;net8 | 1 |
| GND;net10;net11;net2;net22;net25;net29 | 1 |
| 3V3;GND;net10;net11;net14;net15;net17;net18;net19;net20;net22;net25;net3;net6;net9 | 1 |
| 5V;GND;net10;net11;net2;net25;net29 | 1 |
| 5vSwitched;GND;net10;net11 | 1 |
| 12v Switched;5vSwitched | 1 |
| net1 | 1 |
| GND;net22;net25;net29;net5 | 1 |
| GND;net22;net25;net29 | 1 |
| GND;net13;net25;net29 | 1 |
| 12v Switched;net3 | 1 |
| net29;net5 | 1 |
| 12v Switched;GND;net22;net25;net29 | 1 |
| 12v Switched;5V;GND;net25;net29 | 1 |

### Most crossed components (wire/body records)

- ESP32: 1228
- GPS: 982
- MPU: 735
- M1: 629
- Switched Buck: 554
- 12v Mosfet: 281
- F1: 263
- R12: 259
- R7: 252
- C6: 242
- C1: 228
- R3: 213
- R6: 211
- L1: 203
- R11: 202

### GPS / MPU rotation versus net combination

- GPS 0 | 12v Switched;5V;GND;net25;net29: 1
- GPS 0 | 12v Switched;GND;net10;net11;net25;net29: 1
- GPS 0 | 12v Switched;GND;net10;net11;net25;net29;net8: 1
- GPS 0 | 12v Switched;GND;net22;net25;net29: 1
- GPS 0 | 12v Switched;GND;net25;net29: 31
- GPS 0 | 12v Switched;GND;net25;net29;net5: 3
- GPS 0 | 12v Switched;GND;net25;net29;net8: 1
- GPS 0 | 12v Switched;GND;net2;net25;net29: 1
- GPS 0 | 3V3;GND;net10;net11;net25;net29: 1
- GPS 0 | 3V3;GND;net10;net14;net15;net17;net18;net19;net20;net22;net25;net29;net3;net6;net9: 5
- GPS 0 | 5V;GND;net10;net11;net2;net25;net29: 1
- GPS 0 | GND;net10;net11;net25;net27;net29: 1
- GPS 0 | GND;net10;net11;net25;net29: 41
- GPS 0 | GND;net10;net11;net25;net29;net5: 1
- GPS 0 | GND;net10;net11;net25;net29;net8: 3
- GPS 0 | GND;net10;net11;net2;net22;net25;net29: 1
- GPS 0 | GND;net13;net25;net29: 1
- GPS 0 | GND;net22;net25;net29: 1
- GPS 0 | GND;net22;net25;net29;net5: 1
- GPS 0 | GND;net24;net25;net29: 1
- GPS 0 | GND;net25;net26;net29: 1
- GPS 0 | GND;net25;net26;net29;net8: 1
- GPS 0 | GND;net25;net27;net29: 4
- GPS 0 | GND;net25;net29: 394
- GPS 0 | GND;net25;net29;net3: 2
- GPS 0 | GND;net25;net29;net4: 2
- GPS 0 | GND;net25;net29;net5: 8
- GPS 0 | GND;net25;net29;net6: 2
- GPS 0 | GND;net25;net29;net8: 18
- GPS 0 | GND;net25;net29;net9: 2
- GPS 0 | GND;net2;net25;net29: 8
- GPS 180 | 12v Switched;5vSwitched;GND;net22;net25;net29;net5: 1
- GPS 180 | 12v Switched;GND;net25;net29: 3
- GPS 180 | 12v Switched;GND;net2;net25;net29: 1
- GPS 180 | 3V3;GND;net10;net14;net15;net17;net18;net19;net20;net22;net25;net29;net3;net6;net9: 1
- GPS 180 | GND;net10;net11;net25;net29: 3
- GPS 180 | GND;net25;net29: 41
- GPS 180 | GND;net25;net29;net5: 1
- GPS 180 | GND;net25;net29;net9: 1
- GPS 180 | GND;net2;net25;net29: 2
- GPS 270 | : 99
- GPS 270 | 12v Switched: 5
- GPS 270 | 12v Switched;3V3;GND;net10;net14;net15;net17;net18;net19;net20;net22;net25;net3;net6;net9: 1
- GPS 270 | 12v Switched;GND;net10;net11: 3
- GPS 270 | 12v Switched;net3: 1
- GPS 270 | 12v Switched;net4: 1
- GPS 270 | 3V3;GND;net10;net11;net14;net15;net17;net18;net19;net20;net22;net25;net3;net6;net9: 1
- GPS 270 | 3V3;GND;net10;net14;net15;net17;net18;net19;net20;net22;net25;net3;net6;net9: 2
- GPS 270 | GND;net10;net11: 10
- GPS 270 | net2: 1
- GPS 270 | net24: 2
- GPS 270 | net26: 1
- GPS 270 | net28: 1
- GPS 270 | net29: 1
- GPS 270 | net3: 1
- GPS 270 | net4: 1
- GPS 270 | net5: 2
- GPS 270 | net6: 1
- GPS 270 | net8: 1
- GPS 90 | : 163
- GPS 90 | 12v Switched: 14
- GPS 90 | 12v Switched;5vSwitched: 1
- GPS 90 | 12v Switched;GND;net10;net11: 1
- GPS 90 | 12v Switched;net2: 1
- GPS 90 | 12v Switched;net8: 2
- GPS 90 | 3V3;GND;net10;net14;net15;net17;net18;net19;net20;net22;net25;net3;net6;net9: 3
- GPS 90 | 5vSwitched;GND;net10;net11: 1
- GPS 90 | GND;net10;net11: 17
- GPS 90 | GND;net10;net11;net22: 1
- GPS 90 | GND;net10;net11;net8: 1
- GPS 90 | net1: 1
- GPS 90 | net2: 3
- GPS 90 | net22: 1
- GPS 90 | net24: 1
- GPS 90 | net27: 2
- GPS 90 | net28: 1
- GPS 90 | net29;net5: 1
- GPS 90 | net3: 2
- GPS 90 | net4: 2
- GPS 90 | net5: 7
- GPS 90 | net6: 2
- GPS 90 | net8: 3
- MPU 0 | : 211
- MPU 0 | 12v Switched: 17
- MPU 0 | 12v Switched;3V3;GND;net10;net14;net15;net17;net18;net19;net20;net22;net25;net3;net6;net9: 1
- MPU 0 | 12v Switched;5V;GND;net25;net29: 1
- MPU 0 | 12v Switched;5vSwitched: 1
- MPU 0 | 12v Switched;5vSwitched;GND;net22;net25;net29;net5: 1
- MPU 0 | 12v Switched;GND;net22;net25;net29: 1
- MPU 0 | 12v Switched;GND;net25;net29: 31
- MPU 0 | 12v Switched;GND;net25;net29;net5: 3
- MPU 0 | 12v Switched;GND;net25;net29;net8: 1
- MPU 0 | 12v Switched;GND;net2;net25;net29: 1
- MPU 0 | 12v Switched;net2: 1
- MPU 0 | 12v Switched;net3: 1
- MPU 0 | 12v Switched;net4: 1
- MPU 0 | 12v Switched;net8: 2
- MPU 0 | 3V3;GND;net10;net14;net15;net17;net18;net19;net20;net22;net25;net29;net3;net6;net9: 5
- MPU 0 | 3V3;GND;net10;net14;net15;net17;net18;net19;net20;net22;net25;net3;net6;net9: 5
- MPU 0 | GND;net22;net25;net29: 1
- MPU 0 | GND;net24;net25;net29: 1
- MPU 0 | GND;net25;net26;net29: 1
- MPU 0 | GND;net25;net27;net29: 4
- MPU 0 | GND;net25;net29: 336
- MPU 0 | GND;net25;net29;net3: 1
- MPU 0 | GND;net25;net29;net4: 1
- MPU 0 | GND;net25;net29;net5: 7
- MPU 0 | GND;net25;net29;net6: 2
- MPU 0 | GND;net25;net29;net8: 14
- MPU 0 | GND;net25;net29;net9: 3
- MPU 0 | GND;net2;net25;net29: 8
- MPU 0 | net1: 1
- MPU 0 | net2: 4
- MPU 0 | net22: 1
- MPU 0 | net24: 3
- MPU 0 | net26: 1
- MPU 0 | net27: 1
- MPU 0 | net28: 2
- MPU 0 | net29: 1
- MPU 0 | net29;net5: 1
- MPU 0 | net3: 3
- MPU 0 | net4: 3
- MPU 0 | net5: 8
- MPU 0 | net6: 3
- MPU 0 | net8: 4
- MPU 180 | : 51
- MPU 180 | 12v Switched: 2
- MPU 180 | 12v Switched;GND;net25;net29: 3
- MPU 180 | 12v Switched;GND;net2;net25;net29: 1
- MPU 180 | 3V3;GND;net10;net11;net14;net15;net17;net18;net19;net20;net22;net25;net3;net6;net9: 1
- MPU 180 | 3V3;GND;net10;net14;net15;net17;net18;net19;net20;net22;net25;net29;net3;net6;net9: 1
- MPU 180 | GND;net13;net25;net29: 1
- MPU 180 | GND;net22;net25;net29;net5: 1
- MPU 180 | GND;net25;net26;net29;net8: 1
- MPU 180 | GND;net25;net29: 99
- MPU 180 | GND;net25;net29;net3: 1
- MPU 180 | GND;net25;net29;net4: 1
- MPU 180 | GND;net25;net29;net5: 2
- MPU 180 | GND;net25;net29;net8: 4
- MPU 180 | GND;net2;net25;net29: 2
- MPU 180 | net27: 1
- MPU 180 | net5: 1
- MPU 270 | 12v Switched;GND;net10;net11: 4
- MPU 270 | 12v Switched;GND;net10;net11;net25;net29: 1
- MPU 270 | 12v Switched;GND;net10;net11;net25;net29;net8: 1
- MPU 270 | 3V3;GND;net10;net11;net25;net29: 1
- MPU 270 | 5V;GND;net10;net11;net2;net25;net29: 1
- MPU 270 | GND;net10;net11: 15
- MPU 270 | GND;net10;net11;net22: 1
- MPU 270 | GND;net10;net11;net25;net27;net29: 1
- MPU 270 | GND;net10;net11;net25;net29: 28
- MPU 270 | GND;net10;net11;net25;net29;net5: 1
- MPU 270 | GND;net10;net11;net25;net29;net8: 2
- MPU 90 | 5vSwitched;GND;net10;net11: 1
- MPU 90 | GND;net10;net11: 12
- MPU 90 | GND;net10;net11;net25;net29: 16
- MPU 90 | GND;net10;net11;net25;net29;net8: 1
- MPU 90 | GND;net10;net11;net2;net22;net25;net29: 1
- MPU 90 | GND;net10;net11;net8: 1

### Routing-only candidates (up to three distinct offending wires)

| Seed | Offenders | Nonvertical | Crossing wires | W/C | Raw Q3 |
|---:|---:|---:|---:|---:|---:|
| 514 | 1 | 1 | 1 | 46/62 | 68.02 |
| 902 | 1 | 1 | 1 | 48/64 | 67.5 |
| 542 | 1 | 1 | 0 | 53/69 | 64.46 |
| 949 | 1 | 1 | 1 | 56/72 | 62.44 |
| 399 | 1 | 1 | 1 | 58/74 | 60.09 |
| 522 | 2 | 1 | 2 | 46/62 | 66.8 |
| 768 | 2 | 2 | 2 | 42/58 | 65.6 |
| 617 | 2 | 2 | 2 | 43/59 | 64.67 |
| 983 | 2 | 2 | 2 | 46/62 | 64.28 |
| 911 | 2 | 2 | 2 | 45/61 | 63.91 |
| 737 | 2 | 1 | 2 | 52/69 | 63.32 |
| 858 | 2 | 2 | 2 | 46/62 | 62.96 |
| 689 | 2 | 2 | 2 | 50/66 | 61.78 |
| 517 | 2 | 2 | 2 | 51/67 | 61.18 |
| 639 | 2 | 2 | 2 | 52/68 | 60.76 |
| 718 | 2 | 2 | 2 | 56/72 | 57.56 |
| 597 | 3 | 2 | 2 | 38/54 | 68.78 |
| 764 | 3 | 1 | 3 | 49/65 | 67.65 |
| 281 | 3 | 3 | 2 | 32/48 | 67.12 |
| 436 | 3 | 3 | 3 | 38/54 | 63.53 |

Integrity warnings/errors: 0. Full details in summary.json and seeds.csv.

## DAVE_EDGE_SAFARI_300_20261127_145216

### Incomplete-net combinations

| Net combination | Boards |
|---|---:|
| GND;net25;net29 | 126 |
| (none) | 86 |
| 12v Switched;GND;net25;net29 | 9 |
| GND;net10;net11;net25;net29 | 8 |
| 3V3;GND;net10;net14;net15;net17;net18;net19;net20;net22;net25;net29;net3;net6;net9 | 7 |
| GND;net10;net11 | 6 |
| 12v Switched | 6 |
| GND;net2;net25;net29 | 5 |
| net8 | 4 |
| 3V3;GND;net10;net14;net15;net17;net18;net19;net20;net22;net25;net3;net6;net9 | 3 |
| GND;net10;net11;net25;net27;net29 | 2 |
| GND;net25;net26;net29 | 2 |
| GND;net25;net29;net6 | 2 |
| GND;net25;net27;net29 | 2 |
| 12v Switched;GND;net10;net11 | 2 |
| net3 | 1 |
| net2 | 1 |
| 12v Switched;GND;net10;net11;net25;net29 | 1 |
| net26;net28 | 1 |
| 3V3;GND;net10;net14;net15;net17;net18;net19;net20;net22;net25;net28;net3;net6;net9 | 1 |
| net26 | 1 |
| GND;net10;net11;net28 | 1 |
| net22 | 1 |
| net28 | 1 |
| net27;net5 | 1 |
| 3V3;GND;net10;net11;net14;net15;net17;net18;net19;net20;net22;net25;net3;net6;net9 | 1 |
| 12v Switched;GND;net10;net11;net4 | 1 |
| net6 | 1 |
| GND;net22;net25;net29 | 1 |
| 12v Switched;5vSwitched;net27 | 1 |
| GND;net25;net29;net4 | 1 |
| GND;net2;net25;net29;net8 | 1 |

### Most crossed components (wire/body records)

- ESP32: 328
- GPS: 315
- MPU: 235
- M1: 173
- Switched Buck: 165
- C6: 89
- C1: 84
- F1: 83
- 12v Mosfet: 82
- R9: 75
- R7: 72
- R12: 67
- L1: 65
- R11: 63
- TVS: 60

### GPS / MPU rotation versus net combination

- GPS 0 | 12v Switched;GND;net10;net11;net25;net29: 1
- GPS 0 | 12v Switched;GND;net25;net29: 8
- GPS 0 | 3V3;GND;net10;net14;net15;net17;net18;net19;net20;net22;net25;net29;net3;net6;net9: 5
- GPS 0 | GND;net10;net11;net25;net27;net29: 2
- GPS 0 | GND;net10;net11;net25;net29: 7
- GPS 0 | GND;net25;net26;net29: 2
- GPS 0 | GND;net25;net27;net29: 1
- GPS 0 | GND;net25;net29: 115
- GPS 0 | GND;net25;net29;net4: 1
- GPS 0 | GND;net25;net29;net6: 2
- GPS 0 | GND;net2;net25;net29: 5
- GPS 0 | GND;net2;net25;net29;net8: 1
- GPS 180 | 12v Switched;GND;net25;net29: 1
- GPS 180 | 3V3;GND;net10;net14;net15;net17;net18;net19;net20;net22;net25;net29;net3;net6;net9: 2
- GPS 180 | GND;net10;net11;net25;net29: 1
- GPS 180 | GND;net22;net25;net29: 1
- GPS 180 | GND;net25;net27;net29: 1
- GPS 180 | GND;net25;net29: 11
- GPS 270 | : 38
- GPS 270 | 12v Switched: 3
- GPS 270 | 12v Switched;5vSwitched;net27: 1
- GPS 270 | 12v Switched;GND;net10;net11: 1
- GPS 270 | 3V3;GND;net10;net14;net15;net17;net18;net19;net20;net22;net25;net3;net6;net9: 3
- GPS 270 | GND;net10;net11: 3
- GPS 270 | net26: 1
- GPS 270 | net3: 1
- GPS 90 | : 48
- GPS 90 | 12v Switched: 3
- GPS 90 | 12v Switched;GND;net10;net11: 1
- GPS 90 | 12v Switched;GND;net10;net11;net4: 1
- GPS 90 | 3V3;GND;net10;net11;net14;net15;net17;net18;net19;net20;net22;net25;net3;net6;net9: 1
- GPS 90 | 3V3;GND;net10;net14;net15;net17;net18;net19;net20;net22;net25;net28;net3;net6;net9: 1
- GPS 90 | GND;net10;net11: 3
- GPS 90 | GND;net10;net11;net28: 1
- GPS 90 | net2: 1
- GPS 90 | net22: 1
- GPS 90 | net26;net28: 1
- GPS 90 | net27;net5: 1
- GPS 90 | net28: 1
- GPS 90 | net6: 1
- GPS 90 | net8: 4
- MPU 0 | : 62
- MPU 0 | 12v Switched: 5
- MPU 0 | 12v Switched;5vSwitched;net27: 1
- MPU 0 | 12v Switched;GND;net25;net29: 8
- MPU 0 | 3V3;GND;net10;net14;net15;net17;net18;net19;net20;net22;net25;net28;net3;net6;net9: 1
- MPU 0 | 3V3;GND;net10;net14;net15;net17;net18;net19;net20;net22;net25;net29;net3;net6;net9: 7
- MPU 0 | 3V3;GND;net10;net14;net15;net17;net18;net19;net20;net22;net25;net3;net6;net9: 2
- MPU 0 | GND;net22;net25;net29: 1
- MPU 0 | GND;net25;net26;net29: 1
- MPU 0 | GND;net25;net27;net29: 2
- MPU 0 | GND;net25;net29: 104
- MPU 0 | GND;net25;net29;net4: 1
- MPU 0 | GND;net25;net29;net6: 2
- MPU 0 | GND;net2;net25;net29: 5
- MPU 0 | net22: 1
- MPU 0 | net26: 1
- MPU 0 | net26;net28: 1
- MPU 0 | net27;net5: 1
- MPU 0 | net6: 1
- MPU 0 | net8: 3
- MPU 180 | : 24
- MPU 180 | 12v Switched: 1
- MPU 180 | 12v Switched;GND;net25;net29: 1
- MPU 180 | 3V3;GND;net10;net14;net15;net17;net18;net19;net20;net22;net25;net3;net6;net9: 1
- MPU 180 | GND;net25;net26;net29: 1
- MPU 180 | GND;net25;net29: 22
- MPU 180 | GND;net2;net25;net29;net8: 1
- MPU 180 | net2: 1
- MPU 180 | net28: 1
- MPU 180 | net3: 1
- MPU 180 | net8: 1
- MPU 270 | 12v Switched;GND;net10;net11: 2
- MPU 270 | 12v Switched;GND;net10;net11;net25;net29: 1
- MPU 270 | 12v Switched;GND;net10;net11;net4: 1
- MPU 270 | 3V3;GND;net10;net11;net14;net15;net17;net18;net19;net20;net22;net25;net3;net6;net9: 1
- MPU 270 | GND;net10;net11: 6
- MPU 270 | GND;net10;net11;net25;net27;net29: 2
- MPU 270 | GND;net10;net11;net25;net29: 4
- MPU 270 | GND;net10;net11;net28: 1
- MPU 90 | GND;net10;net11;net25;net29: 4

### Routing-only candidates (up to three distinct offending wires)

| Seed | Offenders | Nonvertical | Crossing wires | W/C | Raw Q3 |
|---:|---:|---:|---:|---:|---:|
| 327991 | 1 | 1 | 1 | 44/60 | 68.33 |
| 2951911 | 2 | 1 | 2 | 44/60 | 68.48 |
| 237511 | 2 | 1 | 2 | 50/66 | 65.8 |
| 2386411 | 2 | 2 | 2 | 45/61 | 64.72 |
| 1232791 | 2 | 2 | 2 | 50/66 | 60.63 |
| 1289341 | 2 | 2 | 2 | 50/66 | 60.08 |
| 689911 | 3 | 2 | 3 | 44/60 | 65.38 |
| 1357201 | 3 | 2 | 2 | 49/65 | 62.61 |
| 2284621 | 3 | 3 | 3 | 40/56 | 61.92 |
| 158341 | 3 | 3 | 2 | 48/64 | 60.69 |
| 3234661 | 3 | 3 | 3 | 42/58 | 60.23 |
| 1164931 | 3 | 3 | 3 | 48/64 | 59.06 |
| 3212041 | 3 | 3 | 3 | 51/67 | 55.52 |

Integrity warnings/errors: 0. Full details in summary.json and seeds.csv.

