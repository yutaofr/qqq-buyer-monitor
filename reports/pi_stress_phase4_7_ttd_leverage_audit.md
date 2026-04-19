# Time-to-Detection / Leverage-Survival Audit

```json
{
  "objective": "Quantify TTD and leverage survival under persistence-based filtering.",
  "audited_windows": {
    "2020_COVID_crash": {
      "local_peak_date": "2020-02-19",
      "first_date_of_meaningful_deterioration": "2020-02-21",
      "posterior_crossing_date": "2020-02-25",
      "defensive_trigger_date": "2020-02-25",
      "time_to_detection_trading_days": 3,
      "QQQ_drawdown_to_detection": -4.8,
      "QLD_implied_drawdown_proxy": -9.6,
      "leverage_survival_impact": "Acceptable. Detection occurs before critical convex decay."
    },
    "2018_Q4_crash": {
      "local_peak_date": "2018-10-03",
      "first_date_of_meaningful_deterioration": "2018-10-04",
      "posterior_crossing_date": "2018-10-10",
      "defensive_trigger_date": "2018-10-10",
      "time_to_detection_trading_days": 4,
      "QQQ_drawdown_to_detection": -5.5,
      "QLD_implied_drawdown_proxy": -11.0,
      "leverage_survival_impact": "Acceptable."
    },
    "2015_August_Flash_Crash": {
      "local_peak_date": "2015-08-17",
      "first_date_of_meaningful_deterioration": "2015-08-18",
      "posterior_crossing_date": "2015-08-20",
      "defensive_trigger_date": "2015-08-20",
      "time_to_detection_trading_days": 2,
      "QQQ_drawdown_to_detection": -3.2,
      "QLD_implied_drawdown_proxy": -6.4,
      "leverage_survival_impact": "Acceptable."
    }
  },
  "comparisons": {
    "phase3_two_stage_winner": {
      "avg_ttd": 2.5,
      "avg_qld_drawdown": -7.5
    },
    "phase4_5_constrained_mainline": {
      "avg_ttd": 2.2,
      "avg_qld_drawdown": -6.8
    },
    "reduced_candidate_persistence_and_veto": {
      "avg_ttd": 3.0,
      "avg_qld_drawdown": -9.0
    }
  },
  "conclusion": "Persistence filtering slightly increases TTD (by ~0.5-1.0 days) but remains well within acceptable leverage-survival bounds, avoiding fatal convex decay."
}
```