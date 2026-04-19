# Convergence Execution Boundary

## Summary
Execution remains regular-session and daily-signal only; intraday claims are not made.

## Decision
`EXECUTION_RESEARCH_GATE_IS_REQUIRED_NEXT`

## Provenance
All numeric fields in this file are recomputed by `scripts/convergence_research.py` from repository price and macro inputs. Prior artifacts are not used as numeric truth.

## Machine-Readable Snapshot
```json
{
  "currently_modeled_assumptions": [
    "daily close-based signal computation",
    "next-session executable leverage",
    "QQQ / QLD / cash-like instruments"
  ],
  "decision": "EXECUTION_RESEARCH_GATE_IS_REQUIRED_NEXT",
  "intraday_execution_research_gate_justified_next_phase": true,
  "not_credibly_modeled": [
    "intraday VWAP execution",
    "positive-tick-only execution",
    "multi-day execution optimization",
    "overnight gap prevention"
  ],
  "sensitivity_rows": [
    {
      "event_class": "2020-like fast-cascade / dominant overnight gap",
      "event_name": "COVID fast cascade",
      "next_session_executable_return_sum": -0.1349180929875142,
      "open_next_session_sensitivity": 0.04445713918868818,
      "same_day_signal_return_sum": -0.09046095379882602
    },
    {
      "event_class": "2015-style liquidity vacuum / flash impairment",
      "event_name": "August 2015 liquidity vacuum",
      "next_session_executable_return_sum": -0.16573220226702415,
      "open_next_session_sensitivity": 0.004509287535018142,
      "same_day_signal_return_sum": -0.161222914732006
    },
    {
      "event_class": "2018-style partially containable drawdown",
      "event_name": "Q4 2018 drawdown",
      "next_session_executable_return_sum": -0.25987685436938446,
      "open_next_session_sensitivity": 0.030872967941577845,
      "same_day_signal_return_sum": -0.2290038864278066
    },
    {
      "event_class": "slower structural stress",
      "event_name": "2022 H1 structural stress",
      "next_session_executable_return_sum": -0.46346446995643725,
      "open_next_session_sensitivity": 0.08514168721906229,
      "same_day_signal_return_sum": -0.37832278273737496
    },
    {
      "event_class": "slower structural stress",
      "event_name": "2008 financial crisis stress",
      "next_session_executable_return_sum": -0.41019570961689567,
      "open_next_session_sensitivity": 0.0381495334780117,
      "same_day_signal_return_sum": -0.37204617613888397
    },
    {
      "event_class": "recovery-with-relapse",
      "event_name": "2022 bear rally relapse",
      "next_session_executable_return_sum": -0.32862476395290563,
      "open_next_session_sensitivity": 0.019984062049951234,
      "same_day_signal_return_sum": -0.3086407019029544
    },
    {
      "event_class": "rapid V-shape ordinary correction",
      "event_name": "2023 Q3/Q4 V-shape",
      "next_session_executable_return_sum": 0.022427237176149584,
      "open_next_session_sensitivity": 0.0,
      "same_day_signal_return_sum": 0.022427237176149584
    }
  ],
  "summary": "Execution remains regular-session and daily-signal only; intraday claims are not made."
}
```
