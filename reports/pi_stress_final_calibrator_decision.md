# pi_stress Final Calibrator Decision

## FINAL_CALIBRATOR_DECISION

Selected calibrator for the single evaluated policy: `platt`.

Platt is selected over isotonic for direct-governance evaluation because it preserves posterior improvement versus legacy while avoiding the 18-level isotonic plateau structure. Weighted Platt and balanced Platt are rejected because they inflate ordinary-correction and ghost-window trigger rates. This selection does not make the package deployable; policy robustness and downstream safety still fail.

| Calibrator | Brier | ECE | AUC | Mean Gap | Unique Levels | Largest Plateau | Flip @ 0.35 | Precision @ 0.35 | Recall @ 0.35 | FPR @ 0.35 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| isotonic | 0.0709 | 0.0253 | 0.9413 | 0.6111 | 18 | 0.1762 | 0.0343 | 0.6597 | 0.8629 | 0.1320 |
| platt | 0.0793 | 0.0758 | 0.9375 | 0.4611 | 2058 | 0.0010 | 0.0372 | 0.7244 | 0.7764 | 0.0876 |
| weighted_platt | 0.1237 | 0.2049 | 0.9375 | 0.4903 | 2064 | 0.0010 | 0.0729 | 0.4562 | 0.9346 | 0.3304 |
| platt_balanced | 0.1006 | 0.1583 | 0.9375 | 0.4741 | 2065 | 0.0010 | 0.0507 | 0.5404 | 0.9030 | 0.2278 |
