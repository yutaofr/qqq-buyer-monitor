# Stabilizer Release Forensics

- failure rows: `17`
- raw recovery share: `41.18%`
- mean barrier gap: `0.3401`

## Root Causes

- `posterior_trapped_in_bust`: `8`
- `recovery_acceleration_fade`: `4`
- `stabilizer_barrier_hold`: `3`
- `topology_not_confirmed`: `2`

## Representative Dates

- `2023-02-03` posterior_trapped_in_bust | raw=BUST stable=BUST | bust=0.559 recovery=0.282 | conf=0.110 | bear=0.000 | accel=-0.0938 | gap=0.9219
- `2023-02-08` posterior_trapped_in_bust | raw=BUST stable=BUST | bust=0.568 recovery=0.274 | conf=0.108 | bear=0.000 | accel=-0.0642 | gap=0.8727
- `2023-02-06` posterior_trapped_in_bust | raw=BUST stable=BUST | bust=0.570 recovery=0.275 | conf=0.109 | bear=0.000 | accel=0.0037 | gap=0.8609
- `2023-02-09` posterior_trapped_in_bust | raw=BUST stable=BUST | bust=0.557 recovery=0.293 | conf=0.110 | bear=0.000 | accel=0.0128 | gap=0.8489
- `2023-02-10` topology_not_confirmed | raw=BUST stable=BUST | bust=0.678 recovery=0.126 | conf=0.105 | bear=0.000 | accel=-0.0023 | gap=0.6280
- `2023-04-12` recovery_acceleration_fade | raw=RECOVERY stable=BUST | bust=0.179 recovery=0.373 | conf=0.211 | bear=0.000 | accel=-0.0150 | gap=0.3144
- `2023-03-15` recovery_acceleration_fade | raw=RECOVERY stable=BUST | bust=0.366 recovery=0.385 | conf=0.272 | bear=0.000 | accel=-0.0271 | gap=0.2310
- `2023-04-14` topology_not_confirmed | raw=MID_CYCLE stable=MID_CYCLE | bust=0.005 recovery=0.177 | conf=0.293 | bear=0.000 | accel=-0.0284 | gap=0.2034
- `2023-03-06` posterior_trapped_in_bust | raw=BUST stable=BUST | bust=0.429 recovery=0.286 | conf=0.220 | bear=0.000 | accel=-0.0093 | gap=0.1937
- `2023-03-08` stabilizer_barrier_hold | raw=RECOVERY stable=BUST | bust=0.333 recovery=0.408 | conf=0.174 | bear=0.000 | accel=0.0364 | gap=0.1845
