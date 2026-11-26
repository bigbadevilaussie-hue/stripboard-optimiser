# Moto-Mate V1.40 — current hardware test input

Imported unchanged from [Moto-Mate commit 152f18c](https://github.com/bigbadevilaussie-hue/Moto-Mate/commit/152f18cb28b2ece0ffe1ddaaa54d8ee0a5680b44), directory hardware/V1.40. All three destination Git blob IDs were checked against the source. SHA-256 hashes are in test-fixtures/SHA256SUMS.

Location: test-fixtures/masters/moto/V1.40/

This is the new Moto hardware input, **not** a continuation of the old WR Moto sweep. The V1.00 master, MotoEX, Audio fixtures and analysis/WR_Moto remain untouched as historical research. Existing benchmark scripts retain their historical input paths; use this new directory explicitly for V1.40 testing. Do not compare qualification rates as if the circuit were unchanged.

| Feature | V1.00 | V1.40 |
|---|---:|---:|
| Board holes | 24 × 56 | 24 × 56 |
| Components | 44 | 44 |
| On-board (shared mounting policy) | 32 | 35 |
| Off-board (shared mounting policy) | 12 | 9 |
| Nets | 35 | 34 |
| Net assignments | 123 | 125 |
| Saved jumpers / cuts | 0 / 0 | 0 / 0 |

Only Q1 and Q2 have board positions; neither has a lock flag set. Zero-based board coordinates: Q1 row 9 col 11, rotation 180; Q2 row 14 col 11, rotation 0. Both have explicit E/B/C physical footprint overrides (logical IDs 3/1/2). Their generic NPN model is not a manufacturer pinout certification. Preserve their positions for import and lock-review testing, allow the user to choose locks, and leave source files immutable.

Files:
- Moto-Mate_V_1_40.json — 139564 bytes, Git blob `cd54ad2fe22b9ece9cc3888c5f19c08cb5e8aace`
- Moto-Mate_V_1_40.net — 30080 bytes, Git blob `656a8c4a64b8357f0558868735563b231acd2844`
- StripboardEditor.pretty.zip — 32971 bytes, Git blob `ba0ed891e0b80591696c0af48a1b17fd8fc49fa8`

No solver campaign or native electrical audit has been run for V1.40 during import. No GUI or solver revision change.
