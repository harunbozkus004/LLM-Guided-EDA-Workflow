# Per-task profile

- Per-configuration cells: success rate % over runs. Profile: never solved (no successful episode), always solved (every episode succeeded) or configuration-dependent; run-dependent = outcome varied between runs of at least one configuration.
- Counts: never solved 13, always solved 1, configuration dependent 36; run-dependent 34.

| Task | Category | Difficulty | A_baseline | B_rag | C_feedback | D_full | E_vector_only | F_single_repair | G_targeted_repair | Profile | Run-dependent |
|---|---|---|---|---|---|---|---|---|---|---|---|
| FP-01 | floorplanning | medium | 0 | 0 | 0 | 0 | 0 | 0 | 0 | never solved | no |
| FP-02 | floorplanning | easy | 0 | 100 | 0 | 100 | 100 | 100 | 100 | configuration dependent | no |
| FP-03 | floorplanning | easy | 0 | 0 | 0 | 67 | 100 | 100 | 100 | configuration dependent | yes |
| FP-04 | floorplanning | easy | 0 | 33 | 67 | 100 | 67 | 67 | 100 | configuration dependent | yes |
| FP-05 | floorplanning | hard | 0 | 33 | 0 | 100 | 67 | 67 | 100 | configuration dependent | yes |
| FP-06 | floorplanning | medium | 0 | 100 | 0 | 100 | 67 | 100 | 100 | configuration dependent | yes |
| FP-07 | floorplanning | medium | 33 | 33 | 100 | 67 | 67 | 0 | 67 | configuration dependent | yes |
| FP-08 | floorplanning | hard | 0 | 0 | 0 | 33 | 0 | 0 | 33 | configuration dependent | yes |
| PL-01 | placement | easy | 0 | 67 | 67 | 100 | 100 | 100 | 100 | configuration dependent | yes |
| PL-02 | placement | easy | 0 | 67 | 67 | 100 | 100 | 100 | 100 | configuration dependent | yes |
| PL-03 | placement | medium | 0 | 100 | 0 | 33 | 33 | 33 | 67 | configuration dependent | yes |
| PL-04 | placement | easy | 0 | 100 | 67 | 100 | 100 | 100 | 100 | configuration dependent | yes |
| PL-05 | placement | medium | 0 | 33 | 0 | 67 | 100 | 100 | 67 | configuration dependent | yes |
| PL-06 | placement | easy | 0 | 100 | 33 | 100 | 100 | 100 | 100 | configuration dependent | yes |
| PL-07 | placement | medium | 0 | 0 | 0 | 67 | 100 | 67 | 100 | configuration dependent | yes |
| PL-08 | placement | hard | 0 | 0 | 0 | 0 | 0 | 0 | 0 | never solved | no |
| PL-09 | placement | hard | 0 | 0 | 0 | 0 | 0 | 0 | 0 | never solved | no |
| PL-10 | placement | hard | 0 | 0 | 0 | 0 | 0 | 0 | 0 | never solved | no |
| TA-01 | timing | easy | 0 | 0 | 0 | 33 | 0 | 67 | 33 | configuration dependent | yes |
| TA-02 | timing | easy | 0 | 33 | 0 | 100 | 33 | 33 | 100 | configuration dependent | yes |
| TA-03 | timing | easy | 0 | 33 | 0 | 67 | 67 | 67 | 100 | configuration dependent | yes |
| TA-04 | timing | medium | 0 | 33 | 0 | 67 | 0 | 100 | 67 | configuration dependent | yes |
| TA-05 | timing | medium | 0 | 67 | 0 | 67 | 33 | 0 | 33 | configuration dependent | yes |
| TA-06 | timing | medium | 0 | 0 | 0 | 100 | 67 | 33 | 100 | configuration dependent | yes |
| TA-07 | timing | hard | 0 | 0 | 0 | 0 | 33 | 0 | 0 | configuration dependent | yes |
| TA-08 | timing | hard | 0 | 0 | 0 | 0 | 0 | 0 | 33 | configuration dependent | yes |
| CT-01 | cts | easy | 0 | 67 | 0 | 100 | 100 | 100 | 100 | configuration dependent | yes |
| CT-02 | cts | easy | 0 | 67 | 0 | 67 | 100 | 100 | 67 | configuration dependent | yes |
| CT-03 | cts | medium | 0 | 67 | 0 | 33 | 33 | 67 | 67 | configuration dependent | yes |
| CT-04 | cts | hard | 0 | 0 | 0 | 0 | 0 | 33 | 0 | configuration dependent | yes |
| CT-05 | cts | hard | 0 | 0 | 0 | 0 | 0 | 0 | 0 | never solved | no |
| CT-06 | cts | hard | 0 | 0 | 0 | 0 | 0 | 0 | 0 | never solved | no |
| RT-01 | routing | easy | 0 | 67 | 67 | 100 | 100 | 100 | 100 | configuration dependent | yes |
| RT-02 | routing | hard | 0 | 0 | 0 | 0 | 0 | 0 | 0 | never solved | no |
| RT-03 | routing | medium | 0 | 100 | 0 | 100 | 100 | 100 | 100 | configuration dependent | no |
| RT-04 | routing | medium | 0 | 0 | 0 | 0 | 33 | 0 | 0 | configuration dependent | yes |
| RT-05 | routing | easy | 33 | 67 | 0 | 67 | 0 | 0 | 67 | configuration dependent | yes |
| RT-06 | routing | medium | 0 | 0 | 0 | 0 | 0 | 0 | 0 | never solved | no |
| RT-07 | routing | hard | 0 | 0 | 0 | 33 | 33 | 0 | 33 | configuration dependent | yes |
| RT-08 | routing | easy | 100 | 100 | 100 | 100 | 100 | 100 | 100 | always solved | no |
| IN-01 | inspection | easy | 0 | 0 | 0 | 0 | 0 | 0 | 0 | never solved | no |
| IN-02 | inspection | easy | 33 | 67 | 100 | 100 | 100 | 100 | 100 | configuration dependent | yes |
| IN-03 | inspection | medium | 0 | 0 | 0 | 33 | 33 | 0 | 33 | configuration dependent | yes |
| IN-04 | inspection | medium | 0 | 0 | 0 | 0 | 0 | 0 | 0 | never solved | no |
| IN-05 | inspection | hard | 0 | 0 | 0 | 0 | 0 | 0 | 0 | never solved | no |
| IN-06 | inspection | hard | 0 | 0 | 0 | 0 | 0 | 0 | 0 | never solved | no |
| OP-01 | optimization | easy | 0 | 33 | 0 | 0 | 67 | 33 | 100 | configuration dependent | yes |
| OP-02 | optimization | medium | 0 | 0 | 0 | 0 | 0 | 0 | 0 | never solved | no |
| OP-03 | optimization | medium | 0 | 0 | 0 | 0 | 67 | 0 | 0 | configuration dependent | yes |
| OP-04 | optimization | hard | 0 | 67 | 0 | 100 | 100 | 100 | 100 | configuration dependent | yes |
