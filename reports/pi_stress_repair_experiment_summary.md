# pi_stress Repair Experiment Summary

| Candidate | OOS FP Avg | Crisis Recall | Brier | Failure Modes |
|---|---:|---:|---:|---|
| C1_logistic_identity_platt | 0.1605 | 0.4958 | 0.0905 | insufficient_false_positive_reduction,crisis_recall_loss |
| C2_hinge_price_isotonic | 0.0955 | 0.5781 | 0.0723 | none |
| C3_square_confirmed_platt | 0.2024 | 0.4536 | 0.1104 | insufficient_false_positive_reduction,crisis_recall_loss |
| C4_macro_support_platt | 0.1825 | 0.4810 | 0.1018 | insufficient_false_positive_reduction,crisis_recall_loss |
| C5_recall_balanced_platt | 0.2178 | 0.7553 | 0.0967 | insufficient_false_positive_reduction |
| C6_market_v2_weighted_platt | 0.2330 | 0.8987 | 0.1027 | insufficient_false_positive_reduction |
| C7_persist_v2_weighted_isotonic | 0.2062 | 0.9198 | 0.0968 | insufficient_false_positive_reduction |
| C8_market_persist_v2_weighted_platt | 0.2124 | 0.9008 | 0.0946 | insufficient_false_positive_reduction |
| C9_structural_confirmation_isotonic | 0.1263 | 0.5907 | 0.0709 | none |

Selected: `C9_structural_confirmation_isotonic`

## Window Buckets

```json
{
  "C1_logistic_identity_platt": {
    "false_positive_2023_jul_oct": {
      "average_pi_stress": 0.23714074166479315,
      "brier": 0.09866511193971743,
      "crisis_recall_at_0_50": 0.0,
      "ece": 0.18819687082293624,
      "false_positive_average": 0.24149725501501157,
      "fraction_above_0_50": 0.0,
      "jump_frequency_0_20": 0.0,
      "p95_pi_stress": 0.3199334323335757,
      "p99_pi_stress": 0.3743414380000187,
      "rows": 85.0,
      "worst_raw_beta_delta": -1.2918923580705037
    },
    "ordinary_correction_2018_q1": {
      "average_pi_stress": 0.16968000379499731,
      "brier": 0.17925255135185542,
      "crisis_recall_at_0_50": 0.0,
      "ece": 0.15323993110940384,
      "false_positive_average": 0.17975456080249225,
      "fraction_above_0_50": 0.0,
      "jump_frequency_0_20": 0.0,
      "p95_pi_stress": 0.25704777036388515,
      "p99_pi_stress": 0.26313103488430045,
      "rows": 65.0,
      "worst_raw_beta_delta": 0.013932635083740097
    },
    "prolonged_stress_2022_h1": {
      "average_pi_stress": 0.4031408410808025,
      "brier": 0.27439283662600594,
      "crisis_recall_at_0_50": 0.4065934065934066,
      "ece": 0.35266325246446967,
      "false_positive_average": 0.24042038914298017,
      "fraction_above_0_50": 0.29838709677419356,
      "jump_frequency_0_20": 0.0,
      "p95_pi_stress": 0.854064703050827,
      "p99_pi_stress": 0.8965085815592155,
      "rows": 124.0,
      "worst_raw_beta_delta": -0.28128460330262717
    },
    "recovery_2020_q2_q3": {
      "average_pi_stress": 0.3155664167925604,
      "brier": 0.11650802018328278,
      "crisis_recall_at_0_50": 0.42105263157894735,
      "ece": 0.22063772399996134,
      "false_positive_average": 0.2850009547606142,
      "fraction_above_0_50": 0.06299212598425197,
      "jump_frequency_0_20": 0.0,
      "p95_pi_stress": 0.5914426002731515,
      "p99_pi_stress": 0.691686123260542,
      "rows": 127.0,
      "worst_raw_beta_delta": -0.4867717810825032
    },
    "systemic_crisis_2020_covid": {
      "average_pi_stress": 0.43510311738058943,
      "brier": 0.25278747076787983,
      "crisis_recall_at_0_50": 0.4634146341463415,
      "ece": 0.353358421080949,
      "false_positive_average": 0.2263215064458067,
      "fraction_above_0_50": 0.36538461538461536,
      "jump_frequency_0_20": 0.0392156862745098,
      "p95_pi_stress": 0.774025060260985,
      "p99_pi_stress": 0.7818326699099114,
      "rows": 52.0,
      "worst_raw_beta_delta": -0.4867717810825032
    }
  },
  "C2_hinge_price_isotonic": {
    "false_positive_2023_jul_oct": {
      "average_pi_stress": 0.18442329602914104,
      "brier": 0.11170919704803242,
      "crisis_recall_at_0_50": 0.0,
      "ece": 0.18153583938762702,
      "false_positive_average": 0.19210998449256467,
      "fraction_above_0_50": 0.023529411764705882,
      "jump_frequency_0_20": 0.08333333333333333,
      "p95_pi_stress": 0.38235294117647056,
      "p99_pi_stress": 0.5576923076923077,
      "rows": 85.0,
      "worst_raw_beta_delta": -1.2918923580705037
    },
    "ordinary_correction_2018_q1": {
      "average_pi_stress": 0.16019185526150576,
      "brier": 0.2367475816698706,
      "crisis_recall_at_0_50": 0.0,
      "ece": 0.31852804772652304,
      "false_positive_average": 0.1894509986148436,
      "fraction_above_0_50": 0.0,
      "jump_frequency_0_20": 0.0625,
      "p95_pi_stress": 0.38235294117647056,
      "p99_pi_stress": 0.4883720930232558,
      "rows": 65.0,
      "worst_raw_beta_delta": 0.013932635083740097
    },
    "prolonged_stress_2022_h1": {
      "average_pi_stress": 0.5484240895880356,
      "brier": 0.19147776468058036,
      "crisis_recall_at_0_50": 0.42857142857142855,
      "ece": 0.21009765479575646,
      "false_positive_average": 0.2895757654287782,
      "fraction_above_0_50": 0.31451612903225806,
      "jump_frequency_0_20": 0.016260162601626018,
      "p95_pi_stress": 1.0,
      "p99_pi_stress": 1.0,
      "rows": 124.0,
      "worst_raw_beta_delta": -0.28128460330262717
    },
    "recovery_2020_q2_q3": {
      "average_pi_stress": 0.3468853879017986,
      "brier": 0.12216087662050258,
      "crisis_recall_at_0_50": 0.8947368421052632,
      "ece": 0.2188702606311908,
      "false_positive_average": 0.2823233745371168,
      "fraction_above_0_50": 0.28346456692913385,
      "jump_frequency_0_20": 0.15079365079365079,
      "p95_pi_stress": 1.0,
      "p99_pi_stress": 1.0,
      "rows": 127.0,
      "worst_raw_beta_delta": -0.4867717810825032
    },
    "systemic_crisis_2020_covid": {
      "average_pi_stress": 0.6001514177942483,
      "brier": 0.18056556135901355,
      "crisis_recall_at_0_50": 0.7560975609756098,
      "ece": 0.18831012066729003,
      "false_positive_average": 0.21838741486557559,
      "fraction_above_0_50": 0.6730769230769231,
      "jump_frequency_0_20": 0.11764705882352941,
      "p95_pi_stress": 1.0,
      "p99_pi_stress": 1.0,
      "rows": 52.0,
      "worst_raw_beta_delta": -0.4867717810825032
    }
  },
  "C3_square_confirmed_platt": {
    "false_positive_2023_jul_oct": {
      "average_pi_stress": 0.23705684932613758,
      "brier": 0.09169751277283726,
      "crisis_recall_at_0_50": 0.0,
      "ece": 0.17823331991437288,
      "false_positive_average": 0.23902951576661868,
      "fraction_above_0_50": 0.0,
      "jump_frequency_0_20": 0.0,
      "p95_pi_stress": 0.27841083900272157,
      "p99_pi_stress": 0.3097428168374648,
      "rows": 85.0,
      "worst_raw_beta_delta": -1.2918923580705037
    },
    "ordinary_correction_2018_q1": {
      "average_pi_stress": 0.21148223540439384,
      "brier": 0.17297619511973883,
      "crisis_recall_at_0_50": 0.0,
      "ece": 0.23311503375323567,
      "false_positive_average": 0.21878731286636688,
      "fraction_above_0_50": 0.0,
      "jump_frequency_0_20": 0.0,
      "p95_pi_stress": 0.2714771353713012,
      "p99_pi_stress": 0.2765909415303763,
      "rows": 65.0,
      "worst_raw_beta_delta": 0.013932635083740097
    },
    "prolonged_stress_2022_h1": {
      "average_pi_stress": 0.3656421241179456,
      "brier": 0.30190371423224976,
      "crisis_recall_at_0_50": 0.31868131868131866,
      "ece": 0.3744456075001643,
      "false_positive_average": 0.2534526306997806,
      "fraction_above_0_50": 0.23387096774193547,
      "jump_frequency_0_20": 0.0,
      "p95_pi_stress": 0.7234928683723209,
      "p99_pi_stress": 0.779529374290392,
      "rows": 124.0,
      "worst_raw_beta_delta": -0.28128460330262717
    },
    "recovery_2020_q2_q3": {
      "average_pi_stress": 0.27798334402868546,
      "brier": 0.11825581005660878,
      "crisis_recall_at_0_50": 0.15789473684210525,
      "ece": 0.2038363414870363,
      "false_positive_average": 0.26040811772850714,
      "fraction_above_0_50": 0.023622047244094488,
      "jump_frequency_0_20": 0.0,
      "p95_pi_stress": 0.4324043079443922,
      "p99_pi_stress": 0.509823216698339,
      "rows": 127.0,
      "worst_raw_beta_delta": -0.4867717810825032
    },
    "systemic_crisis_2020_covid": {
      "average_pi_stress": 0.35973244454921177,
      "brier": 0.31440809054423224,
      "crisis_recall_at_0_50": 0.2682926829268293,
      "ece": 0.4460738476738402,
      "false_positive_average": 0.2318043574959816,
      "fraction_above_0_50": 0.21153846153846154,
      "jump_frequency_0_20": 0.0196078431372549,
      "p95_pi_stress": 0.5912735860182246,
      "p99_pi_stress": 0.6058035524916258,
      "rows": 52.0,
      "worst_raw_beta_delta": -0.4867717810825032
    }
  },
  "C4_macro_support_platt": {
    "false_positive_2023_jul_oct": {
      "average_pi_stress": 0.2465664062449372,
      "brier": 0.09953617108538369,
      "crisis_recall_at_0_50": 0.0,
      "ece": 0.2165409176172401,
      "false_positive_average": 0.2502129647374057,
      "fraction_above_0_50": 0.0,
      "jump_frequency_0_20": 0.0,
      "p95_pi_stress": 0.31207249218661076,
      "p99_pi_stress": 0.35009186230122025,
      "rows": 85.0,
      "worst_raw_beta_delta": -1.2918923580705037
    },
    "ordinary_correction_2018_q1": {
      "average_pi_stress": 0.18773781489208563,
      "brier": 0.17227815042618863,
      "crisis_recall_at_0_50": 0.0,
      "ece": 0.17648580370368946,
      "false_positive_average": 0.19471179289446022,
      "fraction_above_0_50": 0.0,
      "jump_frequency_0_20": 0.0,
      "p95_pi_stress": 0.24521545849506318,
      "p99_pi_stress": 0.2492380604638585,
      "rows": 65.0,
      "worst_raw_beta_delta": 0.013932635083740097
    },
    "prolonged_stress_2022_h1": {
      "average_pi_stress": 0.3714929688415186,
      "brier": 0.29496799248190936,
      "crisis_recall_at_0_50": 0.38461538461538464,
      "ece": 0.4009779718019033,
      "false_positive_average": 0.2356290122945064,
      "fraction_above_0_50": 0.28225806451612906,
      "jump_frequency_0_20": 0.0,
      "p95_pi_stress": 0.7687139355139357,
      "p99_pi_stress": 0.8254157540340623,
      "rows": 124.0,
      "worst_raw_beta_delta": -0.28128460330262717
    },
    "recovery_2020_q2_q3": {
      "average_pi_stress": 0.3059076200085717,
      "brier": 0.12165379535808797,
      "crisis_recall_at_0_50": 0.3684210526315789,
      "ece": 0.22024054536915408,
      "false_positive_average": 0.2840602660306589,
      "fraction_above_0_50": 0.05511811023622047,
      "jump_frequency_0_20": 0.0,
      "p95_pi_stress": 0.5001756097230858,
      "p99_pi_stress": 0.5828402546374406,
      "rows": 127.0,
      "worst_raw_beta_delta": -0.4867717810825032
    },
    "systemic_crisis_2020_covid": {
      "average_pi_stress": 0.38928133589289654,
      "brier": 0.28946644978993097,
      "crisis_recall_at_0_50": 0.3902439024390244,
      "ece": 0.39918020256864184,
      "false_positive_average": 0.23362442591149127,
      "fraction_above_0_50": 0.3076923076923077,
      "jump_frequency_0_20": 0.0196078431372549,
      "p95_pi_stress": 0.6604178194053033,
      "p99_pi_stress": 0.6662302004830621,
      "rows": 52.0,
      "worst_raw_beta_delta": -0.4867717810825032
    }
  },
  "C5_recall_balanced_platt": {
    "false_positive_2023_jul_oct": {
      "average_pi_stress": 0.42246817846917556,
      "brier": 0.23151259075463992,
      "crisis_recall_at_0_50": 0.0,
      "ece": 0.364920414545215,
      "false_positive_average": 0.4343981060561261,
      "fraction_above_0_50": 0.3058823529411765,
      "jump_frequency_0_20": 0.011904761904761904,
      "p95_pi_stress": 0.6276170016829207,
      "p99_pi_stress": 0.7131662649837034,
      "rows": 85.0,
      "worst_raw_beta_delta": -1.2918923580705037
    },
    "ordinary_correction_2018_q1": {
      "average_pi_stress": 0.23841059707625212,
      "brier": 0.21268441143078268,
      "crisis_recall_at_0_50": 0.0,
      "ece": 0.29859386024555146,
      "false_positive_average": 0.26277634035704633,
      "fraction_above_0_50": 0.0,
      "jump_frequency_0_20": 0.0,
      "p95_pi_stress": 0.44690813456376716,
      "p99_pi_stress": 0.4607300776502645,
      "rows": 65.0,
      "worst_raw_beta_delta": 0.013932635083740097
    },
    "prolonged_stress_2022_h1": {
      "average_pi_stress": 0.5870488858745541,
      "brier": 0.1794105123667898,
      "crisis_recall_at_0_50": 0.5494505494505495,
      "ece": 0.20774642369550653,
      "false_positive_average": 0.4002938128592747,
      "fraction_above_0_50": 0.4838709677419355,
      "jump_frequency_0_20": 0.0,
      "p95_pi_stress": 0.9751654543459418,
      "p99_pi_stress": 0.9828659327200142,
      "rows": 124.0,
      "worst_raw_beta_delta": -0.28128460330262717
    },
    "recovery_2020_q2_q3": {
      "average_pi_stress": 0.5681863336114471,
      "brier": 0.2714557009527456,
      "crisis_recall_at_0_50": 0.8947368421052632,
      "ece": 0.43196128074609125,
      "false_positive_average": 0.5329184722266137,
      "fraction_above_0_50": 0.5669291338582677,
      "jump_frequency_0_20": 0.007936507936507936,
      "p95_pi_stress": 0.8906402686820425,
      "p99_pi_stress": 0.9305963704470942,
      "rows": 127.0,
      "worst_raw_beta_delta": -0.4867717810825032
    },
    "systemic_crisis_2020_covid": {
      "average_pi_stress": 0.6472631174337639,
      "brier": 0.15778637413979582,
      "crisis_recall_at_0_50": 0.7560975609756098,
      "ece": 0.16349134247089764,
      "false_positive_average": 0.3566969971679906,
      "fraction_above_0_50": 0.6730769230769231,
      "jump_frequency_0_20": 0.0196078431372549,
      "p95_pi_stress": 0.9536114418838655,
      "p99_pi_stress": 0.9552007182144252,
      "rows": 52.0,
      "worst_raw_beta_delta": -0.4867717810825032
    }
  },
  "C6_market_v2_weighted_platt": {
    "false_positive_2023_jul_oct": {
      "average_pi_stress": 0.48018768977418863,
      "brier": 0.29058224081116274,
      "crisis_recall_at_0_50": 0.0,
      "ece": 0.4363197685054011,
      "false_positive_average": 0.494665282062971,
      "fraction_above_0_50": 0.5176470588235295,
      "jump_frequency_0_20": 0.023809523809523808,
      "p95_pi_stress": 0.7181044584766454,
      "p99_pi_stress": 0.8015887717327729,
      "rows": 85.0,
      "worst_raw_beta_delta": -1.2918923580705037
    },
    "ordinary_correction_2018_q1": {
      "average_pi_stress": 0.2764094350127288,
      "brier": 0.21283834170858584,
      "crisis_recall_at_0_50": 0.0,
      "ece": 0.24621884057855842,
      "false_positive_average": 0.29629222732771787,
      "fraction_above_0_50": 0.09230769230769231,
      "jump_frequency_0_20": 0.0,
      "p95_pi_stress": 0.5157565026324025,
      "p99_pi_stress": 0.5322535167011928,
      "rows": 65.0,
      "worst_raw_beta_delta": 0.013932635083740097
    },
    "prolonged_stress_2022_h1": {
      "average_pi_stress": 0.6976312127118557,
      "brier": 0.14322730174941004,
      "crisis_recall_at_0_50": 0.9560439560439561,
      "ece": 0.17768514230173124,
      "false_positive_average": 0.4876748250436917,
      "fraction_above_0_50": 0.8629032258064516,
      "jump_frequency_0_20": 0.0,
      "p95_pi_stress": 0.9979871658461709,
      "p99_pi_stress": 0.9981633354503066,
      "rows": 124.0,
      "worst_raw_beta_delta": -0.28128460330262717
    },
    "recovery_2020_q2_q3": {
      "average_pi_stress": 0.6443642958297834,
      "brier": 0.34335333776770705,
      "crisis_recall_at_0_50": 0.8947368421052632,
      "ece": 0.5012879608985729,
      "false_positive_average": 0.6102090758045379,
      "fraction_above_0_50": 0.8503937007874016,
      "jump_frequency_0_20": 0.007936507936507936,
      "p95_pi_stress": 0.9428628673394177,
      "p99_pi_stress": 0.9851786916510852,
      "rows": 127.0,
      "worst_raw_beta_delta": -0.4867717810825032
    },
    "systemic_crisis_2020_covid": {
      "average_pi_stress": 0.7254444085694488,
      "brier": 0.12369083990487634,
      "crisis_recall_at_0_50": 0.8536585365853658,
      "ece": 0.17525501450638703,
      "false_positive_average": 0.39613007390545435,
      "fraction_above_0_50": 0.75,
      "jump_frequency_0_20": 0.0196078431372549,
      "p95_pi_stress": 0.9891788369610317,
      "p99_pi_stress": 0.9904717391738911,
      "rows": 52.0,
      "worst_raw_beta_delta": -0.4867717810825032
    }
  },
  "C7_persist_v2_weighted_isotonic": {
    "false_positive_2023_jul_oct": {
      "average_pi_stress": 0.460268448898278,
      "brier": 0.28446349061839915,
      "crisis_recall_at_0_50": 0.0,
      "ece": 0.40144491948651345,
      "false_positive_average": 0.4733587372219395,
      "fraction_above_0_50": 0.47058823529411764,
      "jump_frequency_0_20": 0.11904761904761904,
      "p95_pi_stress": 0.668468158255073,
      "p99_pi_stress": 0.8934762948721228,
      "rows": 85.0,
      "worst_raw_beta_delta": -1.2918923580705037
    },
    "ordinary_correction_2018_q1": {
      "average_pi_stress": 0.2796346222662296,
      "brier": 0.27850092191071557,
      "crisis_recall_at_0_50": 0.0,
      "ece": 0.33954678224624757,
      "false_positive_average": 0.31623213395159744,
      "fraction_above_0_50": 0.2153846153846154,
      "jump_frequency_0_20": 0.046875,
      "p95_pi_stress": 0.668468158255073,
      "p99_pi_stress": 0.668468158255073,
      "rows": 65.0,
      "worst_raw_beta_delta": 0.013932635083740097
    },
    "prolonged_stress_2022_h1": {
      "average_pi_stress": 0.737155707488588,
      "brier": 0.13300475691041083,
      "crisis_recall_at_0_50": 0.967032967032967,
      "ece": 0.11135389094887717,
      "false_positive_average": 0.5098900344323924,
      "fraction_above_0_50": 0.8629032258064516,
      "jump_frequency_0_20": 0.024390243902439025,
      "p95_pi_stress": 1.0,
      "p99_pi_stress": 1.0,
      "rows": 124.0,
      "worst_raw_beta_delta": -0.28128460330262717
    },
    "recovery_2020_q2_q3": {
      "average_pi_stress": 0.5223000291172035,
      "brier": 0.2440801640572091,
      "crisis_recall_at_0_50": 0.8947368421052632,
      "ece": 0.374675394421275,
      "false_positive_average": 0.4600723340660648,
      "fraction_above_0_50": 0.4330708661417323,
      "jump_frequency_0_20": 0.031746031746031744,
      "p95_pi_stress": 1.0,
      "p99_pi_stress": 1.0,
      "rows": 127.0,
      "worst_raw_beta_delta": -0.4867717810825032
    },
    "systemic_crisis_2020_covid": {
      "average_pi_stress": 0.745868327465621,
      "brier": 0.1366112372074611,
      "crisis_recall_at_0_50": 0.8536585365853658,
      "ece": 0.16711492176172218,
      "false_positive_average": 0.37179582917581266,
      "fraction_above_0_50": 0.75,
      "jump_frequency_0_20": 0.0784313725490196,
      "p95_pi_stress": 1.0,
      "p99_pi_stress": 1.0,
      "rows": 52.0,
      "worst_raw_beta_delta": -0.4867717810825032
    }
  },
  "C8_market_persist_v2_weighted_platt": {
    "false_positive_2023_jul_oct": {
      "average_pi_stress": 0.520873735531969,
      "brier": 0.3151965934261619,
      "crisis_recall_at_0_50": 0.0,
      "ece": 0.4620502061202043,
      "false_positive_average": 0.533969461467983,
      "fraction_above_0_50": 0.6352941176470588,
      "jump_frequency_0_20": 0.023809523809523808,
      "p95_pi_stress": 0.718723992340675,
      "p99_pi_stress": 0.7718543958078582,
      "rows": 85.0,
      "worst_raw_beta_delta": -1.2918923580705037
    },
    "ordinary_correction_2018_q1": {
      "average_pi_stress": 0.2488140717868552,
      "brier": 0.20161419804346184,
      "crisis_recall_at_0_50": 0.0,
      "ece": 0.1988077442890931,
      "false_positive_average": 0.26569326791743036,
      "fraction_above_0_50": 0.0,
      "jump_frequency_0_20": 0.0,
      "p95_pi_stress": 0.4573374681824242,
      "p99_pi_stress": 0.4734467318904782,
      "rows": 65.0,
      "worst_raw_beta_delta": 0.013932635083740097
    },
    "prolonged_stress_2022_h1": {
      "average_pi_stress": 0.6991019061713221,
      "brier": 0.12874059662114065,
      "crisis_recall_at_0_50": 0.945054945054945,
      "ece": 0.12673689206203792,
      "false_positive_average": 0.45616036623333656,
      "fraction_above_0_50": 0.8467741935483871,
      "jump_frequency_0_20": 0.0,
      "p95_pi_stress": 0.9987999341134074,
      "p99_pi_stress": 0.9988910157429947,
      "rows": 124.0,
      "worst_raw_beta_delta": -0.28128460330262717
    },
    "recovery_2020_q2_q3": {
      "average_pi_stress": 0.6165209596382529,
      "brier": 0.31067646446983016,
      "crisis_recall_at_0_50": 0.8947368421052632,
      "ece": 0.4734176801791245,
      "false_positive_average": 0.5785196842052962,
      "fraction_above_0_50": 0.8031496062992126,
      "jump_frequency_0_20": 0.007936507936507936,
      "p95_pi_stress": 0.9499761190889466,
      "p99_pi_stress": 0.9871744777978327,
      "rows": 127.0,
      "worst_raw_beta_delta": -0.4867717810825032
    },
    "systemic_crisis_2020_covid": {
      "average_pi_stress": 0.7232471530733805,
      "brier": 0.11690843918869595,
      "crisis_recall_at_0_50": 0.8536585365853658,
      "ece": 0.1491125172809727,
      "false_positive_average": 0.3701087877579327,
      "fraction_above_0_50": 0.75,
      "jump_frequency_0_20": 0.0196078431372549,
      "p95_pi_stress": 0.9916411797593757,
      "p99_pi_stress": 0.9935668790654391,
      "rows": 52.0,
      "worst_raw_beta_delta": -0.4867717810825032
    }
  },
  "C9_structural_confirmation_isotonic": {
    "false_positive_2023_jul_oct": {
      "average_pi_stress": 0.1368992006779616,
      "brier": 0.0672281344646772,
      "crisis_recall_at_0_50": 0.0,
      "ece": 0.07807567126619691,
      "false_positive_average": 0.13657922346846268,
      "fraction_above_0_50": 0.0,
      "jump_frequency_0_20": 0.03571428571428571,
      "p95_pi_stress": 0.3339486491021978,
      "p99_pi_stress": 0.4454130434782607,
      "rows": 85.0,
      "worst_raw_beta_delta": -1.2918923580705037
    },
    "ordinary_correction_2018_q1": {
      "average_pi_stress": 0.19219940002771455,
      "brier": 0.22710250169327661,
      "crisis_recall_at_0_50": 0.0,
      "ece": 0.3045980320420302,
      "false_positive_average": 0.21640974350359388,
      "fraction_above_0_50": 0.0,
      "jump_frequency_0_20": 0.03125,
      "p95_pi_stress": 0.4869565217391304,
      "p99_pi_stress": 0.4869565217391304,
      "rows": 65.0,
      "worst_raw_beta_delta": 0.013932635083740097
    },
    "prolonged_stress_2022_h1": {
      "average_pi_stress": 0.6070589506816059,
      "brier": 0.16118407611261035,
      "crisis_recall_at_0_50": 0.43956043956043955,
      "ece": 0.1806338823310423,
      "false_positive_average": 0.3567668837703515,
      "fraction_above_0_50": 0.3467741935483871,
      "jump_frequency_0_20": 0.024390243902439025,
      "p95_pi_stress": 1.0,
      "p99_pi_stress": 1.0,
      "rows": 124.0,
      "worst_raw_beta_delta": -0.28128460330262717
    },
    "recovery_2020_q2_q3": {
      "average_pi_stress": 0.24457887391786473,
      "brier": 0.07592535970157578,
      "crisis_recall_at_0_50": 0.42105263157894735,
      "ece": 0.11208622186121664,
      "false_positive_average": 0.1760987088983369,
      "fraction_above_0_50": 0.06299212598425197,
      "jump_frequency_0_20": 0.007936507936507936,
      "p95_pi_stress": 0.9767441860465116,
      "p99_pi_stress": 1.0,
      "rows": 127.0,
      "worst_raw_beta_delta": -0.4867717810825032
    },
    "systemic_crisis_2020_covid": {
      "average_pi_stress": 0.6041943618201633,
      "brier": 0.1473233054269794,
      "crisis_recall_at_0_50": 0.5365853658536586,
      "ece": 0.1877957581516082,
      "false_positive_average": 0.17549018272656822,
      "fraction_above_0_50": 0.4230769230769231,
      "jump_frequency_0_20": 0.13725490196078433,
      "p95_pi_stress": 1.0,
      "p99_pi_stress": 1.0,
      "rows": 52.0,
      "worst_raw_beta_delta": -0.4867717810825032
    }
  }
}
```
