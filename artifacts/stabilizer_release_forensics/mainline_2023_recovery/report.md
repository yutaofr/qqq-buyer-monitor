# Stabilizer Release Forensics

- failure rows: `34`
- raw recovery share: `58.82%`
- mean barrier gap: `0.5275`

## Root Causes

- `posterior_trapped_in_bust`: `7`
- `recovery_acceleration_fade`: `10`
- `stabilizer_barrier_hold`: `11`
- `topology_not_confirmed`: `5`
- `unclassified_release_failure`: `1`

## Representative Dates

- `2023-04-13` topology_not_confirmed | raw=LATE_CYCLE stable=BUST | bust=0.167 recovery=0.346 | conf=0.020 | bear=0.000 | accel=0.0222 | gap=1.9736
- `2023-04-05` stabilizer_barrier_hold | raw=RECOVERY stable=BUST | bust=0.209 recovery=0.383 | conf=0.284 | bear=0.000 | accel=0.0135 | gap=0.9972
- `2023-04-06` stabilizer_barrier_hold | raw=RECOVERY stable=BUST | bust=0.197 recovery=0.379 | conf=0.311 | bear=0.000 | accel=0.0083 | gap=0.9345
- `2023-02-08` posterior_trapped_in_bust | raw=BUST stable=BUST | bust=0.568 recovery=0.265 | conf=0.025 | bear=0.000 | accel=-0.0642 | gap=0.9117
- `2023-04-04` recovery_acceleration_fade | raw=RECOVERY stable=BUST | bust=0.217 recovery=0.395 | conf=0.381 | bear=0.000 | accel=-0.0100 | gap=0.8998
- `2023-02-03` posterior_trapped_in_bust | raw=BUST stable=BUST | bust=0.560 recovery=0.283 | conf=0.058 | bear=0.000 | accel=-0.0938 | gap=0.8922
- `2023-04-10` stabilizer_barrier_hold | raw=RECOVERY stable=BUST | bust=0.183 recovery=0.373 | conf=0.374 | bear=0.000 | accel=0.0010 | gap=0.8089
- `2023-03-20` recovery_acceleration_fade | raw=RECOVERY stable=BUST | bust=0.291 recovery=0.404 | conf=0.400 | bear=0.000 | accel=-0.0004 | gap=0.7936
- `2023-02-09` topology_not_confirmed | raw=BUST stable=BUST | bust=0.642 recovery=0.153 | conf=0.026 | bear=0.000 | accel=0.0128 | gap=0.7687
- `2023-04-11` recovery_acceleration_fade | raw=RECOVERY stable=BUST | bust=0.182 recovery=0.367 | conf=0.363 | bear=0.000 | accel=-0.0043 | gap=0.7643
