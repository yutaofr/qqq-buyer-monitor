# Stabilizer Release Forensics

- failure rows: `46`
- raw recovery share: `39.13%`
- mean barrier gap: `0.5410`

## Root Causes

- `posterior_trapped_in_bust`: `14`
- `recovery_acceleration_fade`: `14`
- `stabilizer_barrier_hold`: `10`
- `topology_not_confirmed`: `5`
- `unclassified_release_failure`: `3`

## Representative Dates

- `2023-04-13` topology_not_confirmed | raw=LATE_CYCLE stable=BUST | bust=0.183 recovery=0.318 | conf=0.020 | bear=0.000 | accel=0.0222 | gap=1.9183
- `2023-03-06` posterior_trapped_in_bust | raw=BUST stable=BUST | bust=0.472 recovery=0.231 | conf=0.220 | bear=0.000 | accel=-0.0093 | gap=1.6672
- `2023-03-03` posterior_trapped_in_bust | raw=BUST stable=BUST | bust=0.484 recovery=0.250 | conf=0.092 | bear=0.000 | accel=0.0439 | gap=1.4762
- `2023-04-10` stabilizer_barrier_hold | raw=RECOVERY stable=BUST | bust=0.190 recovery=0.352 | conf=0.374 | bear=0.000 | accel=0.0010 | gap=0.9791
- `2023-02-17` posterior_trapped_in_bust | raw=BUST stable=BUST | bust=0.550 recovery=0.277 | conf=0.163 | bear=0.000 | accel=0.0222 | gap=0.9428
- `2023-04-05` stabilizer_barrier_hold | raw=RECOVERY stable=BUST | bust=0.198 recovery=0.383 | conf=0.284 | bear=0.000 | accel=0.0135 | gap=0.9406
- `2023-04-06` stabilizer_barrier_hold | raw=RECOVERY stable=BUST | bust=0.193 recovery=0.379 | conf=0.311 | bear=0.000 | accel=0.0083 | gap=0.9358
- `2023-04-11` recovery_acceleration_fade | raw=LATE_CYCLE stable=BUST | bust=0.194 recovery=0.337 | conf=0.363 | bear=0.000 | accel=-0.0043 | gap=0.9153
- `2023-02-16` posterior_trapped_in_bust | raw=BUST stable=BUST | bust=0.553 recovery=0.281 | conf=0.289 | bear=0.000 | accel=-0.0633 | gap=0.9126
- `2023-03-20` recovery_acceleration_fade | raw=RECOVERY stable=BUST | bust=0.292 recovery=0.404 | conf=0.400 | bear=0.000 | accel=-0.0004 | gap=0.8537
