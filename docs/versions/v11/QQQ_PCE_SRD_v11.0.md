# Archived Research Note

> 归档状态: Historical research only
> 现行规范: `conductor/tracks/v11/spec.md`
> 说明: 本文档保留为 v11 概念探索记录，不再作为实现或验收依据。

# SRD: QQQ Probabilistic Cycle Engine (v11.0)

> 版本: v11.0
> 状态: Draft — For Architect Review
> 日期: March 2026
> 适用范围: QQQ Monitor v11.0 架构规范
> 替换文档: QQQ Buyer Monitor v10.0 (deterministic HSM)

## 1. Purpose and Scope

This document specifies the architecture requirements for a replacement
of the QQQ Buyer Monitor v10.0 system. The predecessor system employed a
deterministic Hierarchical State Machine (HSM) with hard-coded absolute
thresholds to classify market regimes and produce discrete asset
allocation instructions.

This SRD defines requirements for a probabilistic, continuous-output
successor that preserves the predecessor's sound conceptual framework —
multi-cycle awareness, credit-spread primacy, leverage asymmetry — while
eliminating its structural defects: threshold brittleness, state-machine
boundary effects, in-sample parameter overfitting, and path-dependency
blindness.

### 1.1 What This Document Is Not

A trading strategy specification or financial advice document

A validation study of predecessor system claims

A specification for execution infrastructure (broker APIs, order
management)

### 1.2 Predecessor System — Critical Defects Motivating This Rewrite

DEFECT-01 Absolute threshold brittleness. ERP \< 2.5% as a LATE_CYCLE
trigger ignores structural shifts in the risk-free rate regime. A
threshold calibrated in the 2000–2023 period may produce systematic
false negatives or false positives under a persistently higher or lower
rate structure.

DEFECT-02 State boundary discontinuity. ERP 2.49% and ERP 2.51% produce
materially different allocation instructions despite negligible
real-world risk difference. Discrete state machines are inappropriate
for continuous-valued market signals.

DEFECT-03 In-sample overfitting. Parameters derived from ≤ 5 historical
crises (1987, 2000, 2008, 2020, 2022) have insufficient degrees of
freedom. Walk-forward out-of-sample validation is absent from the
predecessor specification.

DEFECT-04 Path dependency blindness. Allocation caps expressed as
percentage of current net asset value produce compounding leverage
errors after drawdown. A 25% QLD cap post-40% account decline represents
a materially different absolute risk exposure than the same cap at
inception.

DEFECT-05 Regime uncertainty suppressed. The system assumes regime
identification is deterministic. In reality, identification error is
highest precisely at regime transition points — the moments of maximum
decision consequence.

## 2. Architecture Principles

These principles are not guidelines. They are binding constraints on any
compliant implementation. A design that satisfies functional
requirements but violates a principle is non-compliant.

PRINCIPLE-01: Probability Over State

The system SHALL NOT output a discrete regime label as its primary
decision variable. All downstream components SHALL consume a probability
distribution over regime states P(regime_i) where ΣP = 1. Hard regime
labels MAY be derived for logging and human-readable reporting only,
never for allocation computation.

Output: { BUST: 0.12, CAPITULATION: 0.05, RECOVERY: 0.31, MID_CYCLE:
0.44, LATE_CYCLE: 0.08 }

Rationale: forces the position-sizing layer to explicitly incorporate
regime uncertainty into allocation decisions, rather than masking it
inside a classification step.

PRINCIPLE-02: Percentile-Relative Thresholds

All threshold comparisons SHALL use rolling historical percentile rank
of each signal, not absolute values. Rolling window SHALL be
configurable (default: 20 years). This makes the system self-calibrating
as the macro rate regime shifts.

erp_trigger = erp_rolling_percentile(window=20yr) ≤ 0.15 \# bottom 15th,
not "\< 2.5%"

Rationale: eliminates DEFECT-01. A 2.5% ERP in a 5% rate environment and
in a 0.5% rate environment represent fundamentally different equity risk
compensation. Only relative rank captures this.

PRINCIPLE-03: Signal Smoothing Before Threshold Application

Raw signals SHALL be smoothed via exponential moving average (span
configurable, default: 10 trading days) before any threshold comparison.
Confirmation windows SHALL require 80% of observations within a rolling
N-day window to exceed threshold before a gate fires.

confirmed = (signal.ewm(span=10).mean() \> threshold).rolling(5).mean()
\> 0.80

Rationale: prevents single-day data artifacts, illiquid-hour prints, or
news-driven spikes from triggering regime changes. Eliminates whipsawing
at threshold boundaries.

PRINCIPLE-04: Dollar-Anchored Position Sizing

All position limits SHALL be computed as absolute dollar amounts
relative to reference_capital, not as percentage of current net asset
value. reference_capital SHALL be defined as inception capital or
rolling peak equity, whichever is higher.

max_qqq_dollars = reference_capital × regime_qqq_cap

current_qqq_dollars = shares × price

room_to_add = max(0, max_qqq_dollars - current_qqq_dollars)

Rationale: eliminates DEFECT-04. Without dollar anchoring, a leveraged
position post-drawdown implies a larger percentage of remaining equity,
compounding risk when the account is most vulnerable.

PRINCIPLE-05: Explicit Uncertainty Propagation

The Kelly-derived position size SHALL include regime_uncertainty² in the
denominator's variance term. Regime uncertainty is measured as the
entropy of P(regime) distribution. Maximum entropy (uniform
distribution) produces minimum position size.

position = (edge / (variance + regime_uncertainty²)) × 0.5 \# half-Kelly
cap

Rationale: eliminates DEFECT-05. When the classifier is uncertain —
precisely at cycle turning points — positions automatically shrink. The
system becomes most conservative when identification confidence is
lowest.

PRINCIPLE-06: Immutable Override Audit

Every manual override of system output SHALL be logged immutably with:
timestamp, system recommendation, override decision, and structured
rationale. Aggregate override accuracy SHALL be computed and reviewed on
a fixed schedule. This is an architectural requirement, not an
operational preference.

Rationale: without empirical tracking of override outcomes, the system's
greatest vulnerability — operator discretion — cannot be measured,
managed, or improved.

## 3. Component Architecture

The system is decomposed into six functional modules arranged in a
strict unidirectional data pipeline. No downstream module MAY feed data
back to an upstream module during a decision cycle. Feedback loops, if
required for model calibration, SHALL operate on a separate asynchronous
schedule.

### 3.1 Module Interface Specification

| **Module** | **Inputs** | **Outputs** | **SLA / Constraint** |
|:---|:---|:---|:---|
| DataIngestion | Raw feeds (FRED, CBOE, price) | Normalized time series | Validate schema; reject stale data \> T+2 |
| SignalEngine | Normalized time series | Percentile-ranked signals + momentum vectors | All outputs in \[0,1\] or labeled momentum direction |
| RegimeClassifier | Signal vector + uncertainty estimate | P(regime) distribution over 5 states | No hard state output; always probabilistic |
| PositionSizer | P(regime), reference_capital, current_positions | Target \$ allocation per asset | Smooth transitions; max 10%pt shift per day |
| RiskController | Target allocation, live positions, VaR | Approved allocation or blocked + reason | Veto gates enforced here, not in classifier |
| OverrideLogger | Manual override event + rationale | Audit trail + running override accuracy stat | Immutable log; reviewed monthly |
| BacktestEngine | Historical signals, parameters | Walk-forward metrics, sensitivity report | Cannot access future data in any calibration step |

### 3.2 Data Flow

DataIngestion

→ \[validated, normalized time series\]

SignalEngine

→ \[percentile-ranked signal vector + momentum vectors\]

RegimeClassifier

→ \[P(regime) distribution, entropy/uncertainty score\]

PositionSizer

→ \[target allocations in \$ per asset, smooth delta from prior\]

RiskController

→ \[approved allocation OR blocked event with reason code\]

OverrideLogger (parallel tap)

→ \[immutable audit trail\]

### 3.3 Module: DataIngestion

Required Data Feeds

FRED BAMLH0A0HYM2 — ICE BofA US High Yield OAS (daily)

FRED BAMLH0A0HYM2EY — HY effective yield (for spread decomposition)

Damodaran Implied ERP — monthly; interpolate to daily

CBOE VIX, VIX3M — daily close

QQQ and SPY adjusted close prices — daily

S&P 500 constituent prices — for breadth calculation (% above 200d MA)

Federal Reserve H.4.1 balance sheet — weekly; interpolate to daily

Data Quality Requirements

Reject any feed with \> 2 consecutive missing trading days without
explicit backfill policy

Flag and quarantine data points \> 5 standard deviations from 252-day
rolling mean

All timestamps normalized to US/Eastern market close (16:00 ET)

Schema versioning: breaking feed format changes SHALL trigger system
halt, not silent adaptation

### 3.4 Module: SignalEngine

The SignalEngine transforms raw time series into decision-ready signal
vectors. All outputs are dimensionless and in \[0,1\] or signed momentum
scalars. The module has no knowledge of regimes or allocations.

Signal Taxonomy

| **Signal** | **Source** | **Transformation** | **Output Range** | **Priority** |
|:---|:---|:---|:---|:---|
| ERP | FRED / Damodaran | Rolling 20yr percentile rank | \[0, 1\] | Tier-1 |
| HY Spread Level | FRED BAMLH0A0HYM2 | Rolling 20yr percentile rank | \[0, 1\] | Tier-1 |
| Spread Accel (α_S) | Derived from HY Spread | 20-day delta / 20 | bps/day | Tier-1 |
| Liquidity ROC | M2 / Fed Balance Sheet | 20-day rate of change | \[-∞, +∞\]% | Tier-1 |
| Market Breadth | S&P 500 constituents | % above 200d MA | \[0%, 100%\] | Tier-2 |
| QQQ Drawdown | Price vs rolling peak | Current DD magnitude | \[0%, 100%\] | Tier-2 |
| VIX Term Structure | CBOE VIX / VIX3M | Spot/3M ratio | \[0.5, 2.0\] | Tier-3 |
| Capitulation Score | Derived composite | Breadth + DD + VIX | \[0, 100\] | Tier-2 |

Momentum Vector Specification

For each level signal, the engine SHALL also output a signed momentum
scalar:

momentum_i = (signal_i - signal_i.rolling(60).mean()) /
signal_i.rolling(60).std()

\# Negative momentum on ERP = ERP rising (cheaper) = positive for risk
assets

\# Positive momentum on spread = spread widening = negative for risk
assets

ARCH NOTE The level and momentum of each signal carry opposite
implications for different signals. The RegimeClassifier — not the
SignalEngine — is responsible for directional interpretation.
SignalEngine outputs raw signed scalars without interpretation.

### 3.5 Module: RegimeClassifier

The classifier takes the signal vector and produces a probability
distribution over five regime states. Implementation MAY use any method
(logistic regression, gradient boosting, hidden Markov model) subject to
constraints below.

Implementation Constraints

SHALL NOT use a rule-based discrete classifier as primary output
(violates PRINCIPLE-01)

SHALL output calibrated probabilities, not raw scores. Calibration SHALL
be validated via Brier score on walk-forward test set

SHALL include an explicit uncertainty/entropy output derived from
P(regime) distribution

SHALL support regime-probability blending: no single regime may claim P
\> 0.95 without explicit confidence override requiring manual
acknowledgment

Hyperparameters SHALL be calibrated on data prior to 1995 in initial
deployment; walk-forward window expands annually

Regime Output Specification

| **Regime** | **P(Regime)** | **QQQ Cap** | **QLD Cap** | **Primary Gate Condition** |
|:---|:---|:---|:---|:---|
| BUST | Continuous \[0,1\] | **0.50x** | **0.00x** | spread_pct ≥ 0.90 OR (accel ≥ 15bps ∧ trend broken) |
| CAPITULATION | Continuous \[0,1\] | **0.80x** | **0.25x** | All 4: spread_pct≥0.85 ∧ erp_pct≥0.85 ∧ DD≥18% ∧ accel_decelerating |
| RECOVERY | Continuous \[0,1\] | 1.00x | 0.10x | Post-BUST: spread_accel ≤ 0 ∧ liquidity_roc \> 0 |
| MID_CYCLE | Continuous \[0,1\] | 1.00x | 0.00x | Default / no gate triggered |
| LATE_CYCLE | Continuous \[0,1\] | **0.80x** | **0.00x** | erp_pct ≤ 0.15 ∧ (spread_pct ≥ 0.65 OR breadth ≤ 40%) |

CRITICAL The thresholds in the table above are expressed in percentile
terms (e.g., spread_pct ≥ 0.90 = top 10% of historical spread readings).
These are NOT absolute bps values. Absolute equivalents will shift over
time as the rolling history window expands — this is by design.

### 3.6 Module: PositionSizer

The PositionSizer converts the regime probability distribution into a
smooth, dollar-anchored target allocation per asset. Allocations are
computed as dollar amounts, not percentages.

Position Sizing Formula

| **Component** | **Formula** | **Constraint** |
|:---|:---|:---|
| Danger Score | weighted_avg(erp_pct, spread_pct, dd_mag, breadth_decay) | \[0, 1\] monotone |
| Opportunity Score | f(capitulation_score, spread_decelerating, liquidity_inflecting) | \[0, 1\] |
| Base QQQ Weight | max_exp × (1 − danger_score^1.5) | Floor: 0.50x in BUST |
| QLD Bonus Weight | qld_max × opp_score × (1 − danger_score) | Zero unless regime ∈ {CAP, REC} |
| Path Correction | Position in \$ not %; anchored to reference_capital | Prevents leverage creep post-drawdown |
| Kelly Scaling | f(edge/variance + regime_uncertainty²) | Never full Kelly; cap at 0.5× Kelly |

Smoothing Constraint

The PositionSizer SHALL enforce a maximum single-day allocation delta of
10 percentage points of reference_capital per asset class. This prevents
whipsawing from daily signal oscillations from translating into
excessive trading costs.

max_daily_delta = reference_capital × 0.10

proposed_delta = target_allocation - current_allocation

executable_delta = clip(proposed_delta, -max_daily_delta,
+max_daily_delta)

### 3.7 Module: RiskController

The RiskController is the final enforcement gate. It receives the
PositionSizer's target allocation and either approves or blocks it. This
module owns all hard-limit veto logic. The RegimeClassifier and
PositionSizer are explicitly prohibited from implementing veto logic —
separation of concerns is mandatory.

Veto Conditions (Non-Overridable Without Level-2 Authorization)

QLD allocation \> 0 when P(BUST) \> 0.40 — automatic block, no override

QLD allocation \> 0 when P(LATE_CYCLE) \> 0.50 — automatic block, no
override

Total gross exposure \> 1.0× reference_capital when P(BUST) \> 0.60

Any position increase when VaR(95%, 10-day) \> 15% of reference_capital

Blood-Chip Override Channel

For new-cash deployment (not existing positions), the RiskController
SHALL support a separate DEPLOY_FAST pathway that bypasses standard BUST
position caps when ALL of the following are simultaneously true:

Funds are freshly deposited (not rebalanced from existing holdings)

spread_momentum ≤ 0 (spread decelerating — Fed intervention signal)

liquidity_roc \> +0.5% (liquidity expanding)

capitulation_score ≥ 30 (genuine panic, not routine decline)

When DEPLOY_FAST is active, new cash MAY be deployed into QQQ spot at up
to 1.0× of the new cash amount only. QLD remains blocked.

## 4. Mathematical Specification

### 4.1 Danger Score

danger_score = (

w_erp × erp_pct_rank + \# ERP near historical low = expensive

w_spread × spread_pct_rank + \# Spread near historical high = stress

w_dd × drawdown_pct + \# Raw drawdown magnitude

w_brd × (1 - breadth) \# Low breadth = internals deteriorating

) / (w_erp + w_spread + w_dd + w_brd)

Default weights: w_erp=0.30, w_spread=0.35, w_dd=0.20, w_brd=0.15

Weights are hyperparameters subject to walk-forward calibration.

### 4.2 Opportunity Score

opp_raw = (

0.40 × capitulation_score_normalized + \# \[0,1\]

0.35 × spread_decelerating_signal + \# binary: accel ≤ 0

0.25 × liquidity_inflecting_signal \# binary: roc turning positive

)

opportunity_score = opp_raw × (1 - danger_score) \# suppressed by active
danger

### 4.3 Kelly-Scaled Position

edge = E\[forward_return \| P(regime)\] \# regime-weighted expected
return

variance = σ²_historical + regime_entropy² \# explicit uncertainty
inflation

kelly_fraction = edge / variance

position_fraction = min(kelly_fraction × 0.5, regime_cap) \# half-Kelly
hard cap

position_dollars = position_fraction × reference_capital

### 4.4 Regime Entropy

H = -Σ P(regime_i) × log(P(regime_i)) \# Shannon entropy

H_max = log(5) ≈ 1.609 \# uniform distribution over 5 regimes

regime_uncertainty = H / H_max \# normalized to \[0, 1\]

\# At max uncertainty: position_fraction automatically halves

\# At certainty (one regime P=1.0): full Kelly applies (still capped by
regime_cap)

## 5. Backtesting and Validation Requirements

Backtesting is not optional and is not a post-hoc rationalization
exercise. It is a formal falsification process. The system SHALL fail
validation if walk-forward out-of-sample results are not produced before
deployment.

### 5.1 Validation Protocol

| **Test Type** | **Method** | **Acceptance Criterion** |
|:---|:---|:---|
| Walk-Forward | Calibrate pre-1995; test 1995–2010; validate 2010–present | No in-sample look-ahead permitted |
| Param Sensitivity | <span dir="rtl">±</span>20% shift on all thresholds; measure CAGR/MDD delta | Result degrades \< 25% under perturbation |
| Stress Scenarios | Japan-style deflation; USD reserve shock; sector-cap restructure | System does not catastrophically fail |
| Override Audit | Log every manual override with stated rationale | Override accuracy tracked; reported quarterly |
| Correlation Collapse | Simulate all-assets-to-1 correlation event | BUST gate fires within 3 trading days |

### 5.2 Required Metrics

CAGR, annualized volatility, Sharpe ratio, Sortino ratio (full period
and sub-periods)

Maximum drawdown (MDD), drawdown duration, recovery time

Regime identification accuracy vs ex-post labels (NBER recession dates
as ground truth for BUST)

Brier score for regime probability calibration

Transaction cost impact at assumed 0.05% round-trip cost

Leverage decay impact for all periods QLD was held (actual vs
theoretical 2× return)

### 5.3 Prohibited Backtest Practices

Using any data past the calibration cutoff to select parameters, even
informally

Excluding any historical crisis from the test set on the grounds it was
'unusual'

Reporting only full-period metrics; sub-period breakdown is mandatory

Assuming zero slippage or that historical bid-ask spreads apply to QLD
in crisis periods

**HARD CONSTRAINT** Any backtest that claims to 'avoid' 2008 and 2020
using parameters derived from data that includes those events is by
definition an in-sample result and SHALL NOT be presented as validation.

## 6. Operational Requirements

### 6.1 Execution Latency

Full signal-to-allocation pipeline SHALL complete within 30 seconds of
market close data availability

Output SHALL be produced daily regardless of regime; no outputs are
produced only 'when something changes'

Historical signal reconstruction SHALL be available for any date within
30 seconds

### 6.2 Data Staleness Handling

If any Tier-1 signal feed is stale \> 2 trading days, system SHALL enter
CONSERVATIVE mode: QLD blocked, QQQ capped at 0.70× reference_capital

CONSERVATIVE mode SHALL be logged as a distinct system state, not
silently absorbed into a regime classification

Operator SHALL receive alert within 60 minutes of staleness detection

### 6.3 Override Governance

Overrides are the system's primary operational risk. Architecture SHALL
enforce:

Level-1 override: operator may override non-veto allocations. Logged
automatically. Monthly accuracy review required.

Level-2 override: required to bypass any veto condition. Requires
written rationale minimum 200 characters. Separate log. Quarterly
review.

No override capability exists for: BUST→QLD prohibition, path-correction
anchor, walk-forward calibration freeze periods

### 6.4 Model Drift Detection

Rolling 90-day Brier score SHALL be computed continuously. If it exceeds
1.5× the walk-forward test Brier score, automatic alert and mandatory
model review

Signal percentile ranks SHALL be monitored for distribution shift via KS
test on a rolling 252-day window vs calibration period

Annual recalibration of hyperparameters using expanded walk-forward
window is mandatory, not optional

## 7. Known Limitations and Non-Requirements

This section documents what the system explicitly does NOT claim to do.
These are not gaps to be closed in future versions; they are epistemic
constraints on what systematic cycle-based allocation can achieve.

### 7.1 The System Cannot

Identify the precise date of cycle transitions in real time. It produces
probability distributions over states, not dates.

Predict the magnitude of a drawdown once a BUST or LATE_CYCLE regime is
confirmed. Position sizing assumes regime, not depth.

Outperform passive QQQ buy-and-hold in every sub-period. The system is
designed to reduce catastrophic drawdown at the cost of some upside
participation during late-cycle momentum phases.

Compensate for operator behavioral override drift. If overrides
systematically favor bullish positions in LATE_CYCLE, the system's risk
properties degrade to those of an unmanaged position. No architectural
control can prevent this; only governance can.

Remain calibrated through a structural break in the U.S. equity market
(e.g., permanent de-rating of technology sector multiples, loss of QQQ
as a relevant benchmark). Structural breaks invalidate rolling-window
percentile assumptions.

### 7.2 The Single Largest Residual Risk

No component of this architecture addresses the core behavioral failure
mode that the predecessor system correctly identified in its final
paragraph: the operator's willingness to execute system output when it
conflicts with prevailing market narrative.

This SRD specifies a system that will correctly output LATE_CYCLE and
require QLD liquidation while financial media reports record earnings
and the prevailing narrative attributes structural permanence to current
valuations. The system has no mechanism to compel execution.
Architecture ends here. Governance and execution discipline begin where
this document ends.

ARCHITECT NOTE The override audit trail specified in PRINCIPLE-06 is the
only architectural lever available. It creates an empirical feedback
loop: operators who consistently override the system in one direction
will accumulate a quantified track record of doing so. Whether that
track record produces behavioral change is outside the system's scope.
