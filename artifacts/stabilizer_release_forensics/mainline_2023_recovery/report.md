# Stabilizer Release Forensics

- failure rows: `18`
- raw recovery share: `38.89%`
- mean barrier gap: `0.4417`

## Root Causes

- `posterior_trapped_in_bust`: `6`
- `recovery_acceleration_fade`: `4`
- `stabilizer_barrier_hold`: `3`
- `topology_not_confirmed`: `5`

## Representative Dates

- `2023-04-13` topology_not_confirmed | raw=LATE_CYCLE stable=BUST | bust=0.162 recovery=0.346 | conf=0.020 | bear=0.000 | accel=0.0222 | gap=2.2204
- `2023-02-03` posterior_trapped_in_bust | raw=BUST stable=BUST | bust=0.559 recovery=0.276 | conf=0.058 | bear=0.000 | accel=-0.0938 | gap=0.9514
- `2023-02-08` posterior_trapped_in_bust | raw=BUST stable=BUST | bust=0.568 recovery=0.265 | conf=0.025 | bear=0.000 | accel=-0.0642 | gap=0.9120
- `2023-02-09` topology_not_confirmed | raw=BUST stable=BUST | bust=0.642 recovery=0.153 | conf=0.026 | bear=0.000 | accel=0.0128 | gap=0.7688
- `2023-02-06` topology_not_confirmed | raw=BUST stable=BUST | bust=0.649 recovery=0.140 | conf=0.021 | bear=0.000 | accel=0.0037 | gap=0.7568
- `2023-02-10` topology_not_confirmed | raw=BUST stable=BUST | bust=0.680 recovery=0.119 | conf=0.105 | bear=0.000 | accel=-0.0023 | gap=0.6242
- `2023-04-12` recovery_acceleration_fade | raw=RECOVERY stable=BUST | bust=0.179 recovery=0.373 | conf=0.211 | bear=0.000 | accel=-0.0150 | gap=0.3146
- `2023-03-15` recovery_acceleration_fade | raw=RECOVERY stable=BUST | bust=0.366 recovery=0.385 | conf=0.272 | bear=0.000 | accel=-0.0271 | gap=0.2298
- `2023-04-14` topology_not_confirmed | raw=MID_CYCLE stable=MID_CYCLE | bust=0.005 recovery=0.177 | conf=0.293 | bear=0.000 | accel=-0.0284 | gap=0.2034
- `2023-03-06` posterior_trapped_in_bust | raw=BUST stable=BUST | bust=0.429 recovery=0.285 | conf=0.220 | bear=0.000 | accel=-0.0093 | gap=0.1952
