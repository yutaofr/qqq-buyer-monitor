# pi_stress Repair Baseline Report

## Architecture Map
- Legacy stress was a topology-only covariance blend input.
- New audit frame evaluates component scores independently before combination.

## Baseline Metrics
```json
{
  "all": {
    "average_pi_stress": 0.23631070944391913,
    "brier": 0.09708822907642568,
    "crisis_recall_at_0_50": 0.5337552742616034,
    "ece": 0.08701066851232168,
    "false_positive_average": 0.15763369124682605,
    "fraction_above_0_50": 0.13513513513513514,
    "jump_frequency_0_20": 0.0,
    "p95_pi_stress": 0.672113331808021,
    "p99_pi_stress": 0.8526516436951076,
    "rows": 2072.0,
    "worst_raw_beta_delta": -1.4583578443507152
  },
  "oos": {
    "average_pi_stress": 0.1763110735258203,
    "brier": 0.048980215072007116,
    "crisis_recall_at_0_50": 0.5428571428571428,
    "ece": 0.13829487261149825,
    "false_positive_average": 0.15358011380775763,
    "fraction_above_0_50": 0.03667953667953668,
    "jump_frequency_0_20": 0.0,
    "p95_pi_stress": 0.42978174575419364,
    "p99_pi_stress": 0.6576040900290464,
    "rows": 518.0,
    "worst_raw_beta_delta": -1.4583578443507152
  },
  "separation": {
    "mean_gap": 0.34392148038898096,
    "negative_mean": 0.15763369124682605,
    "negative_p75": 0.20580338874455428,
    "positive_mean": 0.501555171635807,
    "positive_p25": 0.36120568992718605,
    "rank_auc": 0.9180040451408142
  },
  "train": {
    "average_pi_stress": 0.21232102381829127,
    "brier": 0.08092642501608109,
    "crisis_recall_at_0_50": 0.4523809523809524,
    "ece": 0.08222596400201174,
    "false_positive_average": 0.14517293465708198,
    "fraction_above_0_50": 0.0913081650570676,
    "jump_frequency_0_20": 0.0,
    "p95_pi_stress": 0.6643338556376954,
    "p99_pi_stress": 0.884674999790191,
    "rows": 1139.0,
    "worst_raw_beta_delta": -1.0732101539498262
  },
  "validation": {
    "average_pi_stress": 0.3770433921744381,
    "brier": 0.20149364131503125,
    "crisis_recall_at_0_50": 0.6069868995633187,
    "ece": 0.19463094584619411,
    "false_positive_average": 0.2303967061658704,
    "fraction_above_0_50": 0.3783132530120482,
    "jump_frequency_0_20": 0.0,
    "p95_pi_stress": 0.7578293974890689,
    "p99_pi_stress": 0.8465267155913141,
    "rows": 415.0,
    "worst_raw_beta_delta": -1.4098672080384476
  },
  "windows": {
    "false_positive_2023_jul_oct": {
      "average_pi_stress": 0.3205246018380117,
      "brier": 0.15750804928382833,
      "crisis_recall_at_0_50": 0.0,
      "ece": 0.261701072426247,
      "false_positive_average": 0.3275929943826063,
      "fraction_above_0_50": 0.15294117647058825,
      "jump_frequency_0_20": 0.0,
      "p95_pi_stress": 0.5424591780999638,
      "p99_pi_stress": 0.6021688433057452,
      "rows": 85.0,
      "worst_raw_beta_delta": -1.2918923580705037
    },
    "ordinary_correction_2018_q1": {
      "average_pi_stress": 0.1473444298012959,
      "brier": 0.1769674559018652,
      "crisis_recall_at_0_50": 0.0,
      "ece": 0.15721032855720574,
      "false_positive_average": 0.15388765102272556,
      "fraction_above_0_50": 0.0,
      "jump_frequency_0_20": 0.0,
      "p95_pi_stress": 0.2673892617195026,
      "p99_pi_stress": 0.27641814485861393,
      "rows": 65.0,
      "worst_raw_beta_delta": 0.013932635083740097
    },
    "prolonged_stress_2022_h1": {
      "average_pi_stress": 0.5463649276364116,
      "brier": 0.1586928739511506,
      "crisis_recall_at_0_50": 0.6813186813186813,
      "ece": 0.21545251998253537,
      "false_positive_average": 0.3131184371019945,
      "fraction_above_0_50": 0.5241935483870968,
      "jump_frequency_0_20": 0.0,
      "p95_pi_stress": 0.8874429206912524,
      "p99_pi_stress": 0.8928675494944723,
      "rows": 124.0,
      "worst_raw_beta_delta": -0.28128460330262717
    },
    "recovery_2020_q2_q3": {
      "average_pi_stress": 0.2535791297587928,
      "brier": 0.1405291633356186,
      "crisis_recall_at_0_50": 0.0,
      "ece": 0.12310949651891052,
      "false_positive_average": 0.23888185618355812,
      "fraction_above_0_50": 0.031496062992125984,
      "jump_frequency_0_20": 0.0,
      "p95_pi_stress": 0.49453347487611216,
      "p99_pi_stress": 0.514024977366382,
      "rows": 127.0,
      "worst_raw_beta_delta": -0.4867717810825032
    },
    "systemic_crisis_2020_covid": {
      "average_pi_stress": 0.29222788681357553,
      "brier": 0.3464059166724346,
      "crisis_recall_at_0_50": 0.0,
      "ece": 0.5298399938738073,
      "false_positive_average": 0.07943317253381423,
      "fraction_above_0_50": 0.0,
      "jump_frequency_0_20": 0.0,
      "p95_pi_stress": 0.4959023631331947,
      "p99_pi_stress": 0.4984873413089785,
      "rows": 52.0,
      "worst_raw_beta_delta": -0.4867717810825032
    }
  }
}
```
