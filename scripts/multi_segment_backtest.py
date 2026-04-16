"""Multi-segment backtest with Lehman crisis diagnostics.

Runs Pre-QE (2006-2008) and QE-Era (2009-2019) segments using real data.
Generates detailed diagnostic reports for the Lehman crisis window.

Data constraints handled:
  - SOFR: unavailable before 2018 → falls back to TEDRATE (TED Spread)
  - QLD: unavailable before 2006-06 → synthesised as 2×QQQ daily return

Usage:
  docker compose run --rm test python scripts/multi_segment_backtest.py
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd

from src.liquidity.backtest.runner import run_backtest
from src.liquidity.config import load_config
from src.liquidity.data.panel_builder import build_pit_aligned_panel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("multi_segment")

# ── Segment definitions ─────────────────────────────────────
SEGMENTS = {
    "Pre-QE": {
        "start": "2006-09-01",  # QLD launched 2006-06, need lookback
        "end":   "2008-12-31",
        "note":  "Includes Lehman crisis (2008-09-15)",
    },
    "QE-Era": {
        "start": "2009-06-01",
        "end":   "2019-12-31",
        "note":  "ZIRP, QE1-QE3, long bull market",
    },
    "Post-COVID": {
        "start": "2020-06-01",
        "end":   "2025-03-31",
        "note":  "Recovery → Inflation → Rate hikes",
    },
}

# Lehman crisis window for diagnostics
LEHMAN_WINDOW = ("2008-07-01", "2008-12-31")
LEHMAN_DATE   = pd.Timestamp("2008-09-15")


BURN_IN = 252
OUTPUT_DIR = Path("artifacts/liquidity_backtest")


def _synthesize_qld_returns(qqq_ret: pd.Series) -> pd.Series:
    """Synthesize QLD-like returns from QQQ: 2× daily return.

    In reality QLD has tracking error and financing costs,
    but for backtest purposes 2× is a reasonable approximation.
    """
    return qqq_ret * 2.0


def run_segment(name: str, seg: dict, config: dict) -> dict | None:
    """Run a single segment backtest."""
    logger.info("=" * 60)
    logger.info("SEGMENT: %s [%s → %s]", name, seg["start"], seg["end"])
    logger.info("Note: %s", seg["note"])
    logger.info("=" * 60)

    try:
        panel = build_pit_aligned_panel(seg["start"], seg["end"])
    except Exception as e:
        logger.error("Failed to build panel for %s: %s", name, e)
        return None

    # Check if QLD_ret has data (pre-2006 it won't)
    if panel["QLD_ret"].isna().any() or (panel["QLD_ret"] == 0).all():
        logger.warning("QLD returns missing — synthesising from 2×QQQ")
        panel["QLD_ret"] = _synthesize_qld_returns(panel["QQQ_ret"])

    logger.info("Panel: %d rows, %s → %s", len(panel),
                panel.index[0].date(), panel.index[-1].date())

    # Run backtest
    result = run_backtest(panel, config, burn_in=BURN_IN)

    # Print summary
    attr = result["attribution"]
    log = result["log"]
    logger.info("─── %s Results ───", name)
    logger.info("  Total return:  %.1f%%", attr["total_return"] * 100)
    logger.info("  CAGR:          %.1f%%", attr["annualised_ret"] * 100)
    logger.info("  Sharpe:        %.2f", attr["sharpe"])
    logger.info("  Max Drawdown:  %.1f%%", attr["max_drawdown"] * 100)
    logger.info("  N trades:      %d", attr["n_trades"])
    logger.info("  QLD days:      %d / %d", (log["qld"] > 0).sum(), len(log))

    return result


def lehman_diagnostics(result: dict, panel: pd.DataFrame) -> dict:
    """Generate detailed diagnostics for the Lehman crisis window.

    Returns a dict of diagnostic findings for reporting.
    """
    log = result["log"]
    nav = result["nav"]

    # Filter to Lehman window
    w_start, w_end = LEHMAN_WINDOW
    window_log = log.loc[w_start:w_end]
    window_nav = nav.loc[w_start:w_end]
    window_panel = panel.loc[w_start:w_end]

    if window_log.empty:
        return {"error": "Lehman window not in backtest range"}

    findings = {}

    # ── Diagnostic 1: Temporal precedence (τ_lead) ──────────
    p_cp = window_log["p_cp"]
    first_alarm = p_cp[p_cp > 0.30]
    if not first_alarm.empty:
        alarm_date = first_alarm.index[0]
        lead_days = (LEHMAN_DATE - alarm_date).days
        findings["tau_lead_days"] = lead_days
        findings["first_alarm_date"] = str(alarm_date.date())
        findings["alarm_preceded_lehman"] = lead_days > 0
    else:
        findings["tau_lead_days"] = None
        findings["first_alarm_date"] = None
        findings["alarm_preceded_lehman"] = False

    # ── Diagnostic 2: Dimensional attribution ───────────────
    # Which observation dimension was elevated during crisis?
    lehman_week = window_panel.loc["2008-09-12":"2008-09-19"]
    pre_crisis  = window_panel.loc[w_start:"2008-08-31"]

    if not lehman_week.empty and not pre_crisis.empty:
        for dim in ["ED_ACCEL", "SPREAD_ANOMALY", "FISHER_RHO"]:
            pre_mean = pre_crisis[dim].mean()
            crisis_mean = lehman_week[dim].mean()
            crisis_max  = lehman_week[dim].max()
            findings[f"dim_{dim}_pre_mean"]    = float(pre_mean)
            findings[f"dim_{dim}_crisis_mean"]  = float(crisis_mean)
            findings[f"dim_{dim}_crisis_max"]   = float(crisis_max)
            findings[f"dim_{dim}_amplification"] = float(
                crisis_mean / pre_mean if abs(pre_mean) > 1e-10 else float("inf")
            )

    # ── Diagnostic 3: λ_macro trajectory ────────────────────
    lambda_m = window_panel["LAMBDA_MACRO"]
    findings["lambda_macro_jul_aug_avg"] = float(
        lambda_m.loc["2008-07-01":"2008-08-31"].mean()
    )
    findings["lambda_macro_sep_avg"] = float(
        lambda_m.loc["2008-09-01":"2008-09-30"].mean()
    )
    findings["lambda_macro_pre_elevated"] = (
        findings["lambda_macro_jul_aug_avg"] > 0.005
    )

    # ── Diagnostic 4: P_cp trajectory ───────────────────────
    findings["p_cp_max_jul_aug"] = float(p_cp.loc["2008-07-01":"2008-08-31"].max())
    findings["p_cp_max_sep"]     = float(p_cp.loc["2008-09-01":"2008-09-30"].max())
    findings["p_cp_max_oct_dec"] = float(
        p_cp.loc["2008-10-01":"2008-12-31"].max()
        if "2008-10-01" in p_cp.index or len(p_cp.loc["2008-10-01":]) > 0
        else 0.0
    )
    findings["p_cp_mean_window"] = float(p_cp.mean())

    # ── Diagnostic 5: AEMA (s_t) at Lehman ──────────────────
    s_t = window_log["s_t"]
    findings["s_t_at_lehman_week"] = float(
        s_t.loc["2008-09-15":"2008-09-19"].mean()
        if len(s_t.loc["2008-09-15":"2008-09-19"]) > 0 else 0.0
    )
    findings["s_t_max_window"] = float(s_t.max())

    # ── Diagnostic 6: Leverage behaviour ────────────────────
    l_final = window_log["l_final"]
    findings["leverage_pre_crisis_avg"] = float(
        l_final.loc[w_start:"2008-08-31"].mean()
    )
    findings["leverage_lehman_week"] = float(
        l_final.loc["2008-09-15":"2008-09-19"].mean()
        if len(l_final.loc["2008-09-15":"2008-09-19"]) > 0 else 0.0
    )
    findings["leverage_min_window"] = float(l_final.min())

    # ── Diagnostic 7: NAV protection ────────────────────────
    if not window_nav.empty:
        nav_peak = window_nav.max()
        nav_trough = window_nav.min()
        findings["nav_drawdown_in_window"] = float(
            (nav_trough - nav_peak) / nav_peak if nav_peak > 0 else 0.0
        )

    # ── Diagnostic 8: Causal Overdrive LL Gain ──────────────────
    if "ll_spread_actual" in window_log.columns:
        ll_actual = window_log["ll_spread_actual"]
        ll_base   = window_log["ll_spread_base"]
        tau_t     = window_log["tau_t"]

        # Max signal amplification (peak log-likelihood difference)
        ll_diff = ll_actual - ll_base
        if not ll_diff.empty:
            ll_diff.idxmax()

        findings["overdrive_peak_tau_t"] = float(tau_t.min()) # Min tau = max sensitivity

        # Lehman week specific
        lehman_w_actual = ll_actual.loc["2008-09-15":"2008-09-19"]
        lehman_w_base   = ll_base.loc["2008-09-15":"2008-09-19"]
        lehman_w_tau    = tau_t.loc["2008-09-15":"2008-09-19"]

        if not lehman_w_actual.empty:
            findings["ll_spread_lehman_wk_base"] = float(lehman_w_base.mean())
            findings["ll_spread_lehman_wk_actual"] = float(lehman_w_actual.mean())
            findings["ll_spread_lehman_wk_gain"] = float((lehman_w_actual - lehman_w_base).mean())
            findings["tau_t_lehman_wk_avg"] = float(lehman_w_tau.mean())

    return findings


def main():
    config = load_config()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    all_results = {}

    for name, seg in SEGMENTS.items():
        result = run_segment(name, seg, config)
        if result is not None:
            all_results[name] = result

            # Save NAV series
            result["nav"].to_csv(OUTPUT_DIR / f"nav_{name.lower().replace('-', '_')}.csv")
            result["log"].to_csv(OUTPUT_DIR / f"log_{name.lower().replace('-', '_')}.csv")

    # ── Lehman crisis diagnostics ──────────────────────────
    if "Pre-QE" in all_results:
        logger.info("=" * 60)
        logger.info("LEHMAN CRISIS DIAGNOSTICS")
        logger.info("=" * 60)

        # Rebuild panel for diagnostics (need raw features)
        panel = build_pit_aligned_panel(
            SEGMENTS["Pre-QE"]["start"],
            SEGMENTS["Pre-QE"]["end"],
        )

        diagnostics = lehman_diagnostics(all_results["Pre-QE"], panel)

        for k, v in sorted(diagnostics.items()):
            logger.info("  %-35s: %s", k, v)

        # Save diagnostics
        with open(OUTPUT_DIR / "lehman_diagnostics.json", "w") as f:
            json.dump(diagnostics, f, indent=2, default=str)

    # ── Cross-segment comparison ───────────────────────────
    logger.info("=" * 60)
    logger.info("CROSS-SEGMENT COMPARISON")
    logger.info("=" * 60)
    logger.info("  %-14s %8s %8s %8s %8s %8s",
                "Segment", "Return", "CAGR", "Sharpe", "MDD", "Trades")
    logger.info("  " + "─" * 56)
    for name, result in all_results.items():
        a = result["attribution"]
        logger.info(
            "  %-14s %+7.1f%% %+7.1f%% %7.2f %7.1f%% %7d",
            name,
            a["total_return"] * 100,
            a["annualised_ret"] * 100,
            a["sharpe"],
            a["max_drawdown"] * 100,
            a["n_trades"],
        )

    logger.info("Results saved to %s/", OUTPUT_DIR)


if __name__ == "__main__":
    main()
