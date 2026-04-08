# Stabilizer Release Forensics

- failure rows: `24`
- raw recovery share: `45.83%`
- mean barrier gap: `0.3657`

## Root Causes

- `posterior_trapped_in_bust`: `7`
- `recovery_acceleration_fade`: `7`
- `stabilizer_barrier_hold`: `5`
- `topology_not_confirmed`: `5`

## Representative Dates

- `2023-04-13` topology_not_confirmed | raw=LATE_CYCLE stable=BUST | bust=0.167 recovery=0.346 | conf=0.020 | bear=0.000 | accel=0.0222 | gap=1.9736
- `2023-02-08` posterior_trapped_in_bust | raw=BUST stable=BUST | bust=0.568 recovery=0.265 | conf=0.025 | bear=0.000 | accel=-0.0642 | gap=0.9117
- `2023-02-03` posterior_trapped_in_bust | raw=BUST stable=BUST | bust=0.560 recovery=0.283 | conf=0.058 | bear=0.000 | accel=-0.0938 | gap=0.8922
- `2023-02-09` topology_not_confirmed | raw=BUST stable=BUST | bust=0.642 recovery=0.153 | conf=0.026 | bear=0.000 | accel=0.0128 | gap=0.7687
- `2023-02-06` topology_not_confirmed | raw=BUST stable=BUST | bust=0.652 recovery=0.143 | conf=0.021 | bear=0.000 | accel=0.0037 | gap=0.7375
- `2023-02-10` topology_not_confirmed | raw=BUST stable=BUST | bust=0.680 recovery=0.119 | conf=0.105 | bear=0.000 | accel=-0.0023 | gap=0.6241
- `2023-04-05` stabilizer_barrier_hold | raw=RECOVERY stable=BUST | bust=0.209 recovery=0.383 | conf=0.284 | bear=0.000 | accel=0.0135 | gap=0.3252
- `2023-04-12` recovery_acceleration_fade | raw=LATE_CYCLE stable=BUST | bust=0.194 recovery=0.345 | conf=0.211 | bear=0.000 | accel=-0.0150 | gap=0.3251
- `2023-04-06` stabilizer_barrier_hold | raw=RECOVERY stable=BUST | bust=0.197 recovery=0.379 | conf=0.311 | bear=0.000 | accel=0.0083 | gap=0.2566
- `2023-03-15` posterior_trapped_in_bust | raw=BUST stable=BUST | bust=0.379 recovery=0.378 | conf=0.272 | bear=0.000 | accel=-0.0271 | gap=0.2485
