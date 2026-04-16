"""Three-Era System Audit.

Audit 1 — Execution Reality (Pre-QE 2006-2008)
    Did AEMA smoothing translate P_cp=0.9998 into actual deleveraging?
    Inspects: p_cp, s_t, l_final, circuit_breaker, days_held in Lehman window.

Audit 2 — False Positive Audit (Post-COVID 2020-2025)
    Does λ=0.98 over-sensitize the engine in normal-but-volatile markets?
    Counts alarms, maps them to known market events, computes annual FPR.

Audit 3 — Decay Calibration Grid
    Sweeps λ ∈ {0.95..1.00} over Pre-QE + Post-COVID simultaneously.
    Finds the Pareto boundary: max Lehman detection × min false alarms.

Usage:
    docker compose run --rm test python scripts/three_era_audit.py
"""

from __future__ import annotations

import copy
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

from src.liquidity.backtest.runner import run_backtest
from src.liquidity.config import load_config
from src.liquidity.data.panel_builder import build_pit_aligned_panel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("three_era_audit")

OUTPUT_DIR = Path("artifacts/three_era_audit")
BURN_IN    = 252

# ── Segment definitions ──────────────────────────────────────────────────────
SEGMENTS = {
    "Pre-QE": {
        "start": "2006-09-01",
        "end":   "2008-12-31",
    },
    "Post-COVID": {
        "start": "2020-06-01",
        "end":   "2025-03-31",
    },
}

LEHMAN_DATE   = pd.Timestamp("2008-09-15")
LEHMAN_WINDOW = ("2008-07-01", "2008-12-31")

# ── Known market stress events for false-positive annotation ─────────────────
KNOWN_STRESS_EVENTS = {
    "COVID_Crash":   ("2020-02-01", "2020-05-31"),
    "Rate_Hike_22":  ("2022-01-01", "2022-12-31"),
    "SVB_Crisis":    ("2023-03-01", "2023-05-31"),
    "Aug24_Spike":   ("2024-08-01", "2024-08-31"),
}

# ── Lambda grid for Audit 3 ──────────────────────────────────────────────────
LAMBDA_GRID = [0.95, 0.96, 0.97, 0.98, 0.99, 0.995, 1.0]


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _synthesize_qld(qqq_ret: pd.Series) -> pd.Series:
    return qqq_ret * 2.0


def _build_panel(name: str, seg: dict) -> pd.DataFrame | None:
    try:
        panel = build_pit_aligned_panel(seg["start"], seg["end"])
        if panel["QLD_ret"].isna().any() or (panel["QLD_ret"] == 0).all():
            logger.warning("%s: synthesising QLD from 2×QQQ", name)
            panel["QLD_ret"] = _synthesize_qld(panel["QQQ_ret"])
        return panel
    except Exception as e:
        logger.error("Panel build failed for %s: %s", name, e)
        return None


def _run_segment(panel: pd.DataFrame, cfg: dict) -> dict:
    return run_backtest(panel, cfg, burn_in=BURN_IN)


def _alarm_count(log: pd.DataFrame, threshold: float = 0.30) -> int:
    """Count distinct alarm episodes (consecutive days above threshold = 1 episode)."""
    above = log["p_cp"] > threshold
    # count rising edges
    return int((above & ~above.shift(1, fill_value=False)).sum())


def _is_in_known_event(date: pd.Timestamp) -> str | None:
    for name, (s, e) in KNOWN_STRESS_EVENTS.items():
        if pd.Timestamp(s) <= date <= pd.Timestamp(e):
            return name
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Audit 1 — Execution Reality
# ─────────────────────────────────────────────────────────────────────────────

def audit_execution(result: dict, panel: pd.DataFrame) -> dict:
    """Forensic inspection of the Lehman window execution chain."""
    log = result["log"]
    nav = result["nav"]

    w_start, w_end = LEHMAN_WINDOW
    wlog  = log.loc[w_start:w_end]
    wnav  = nav.loc[w_start:w_end]
    wpan  = panel.loc[w_start:w_end]

    report: dict = {}

    # ── 1A: P_cp trajectory ───────────────────────────────────────────────
    p_cp = wlog["p_cp"]
    first_alarm = p_cp[p_cp > 0.30]
    if not first_alarm.empty:
        d = first_alarm.index[0]
        report["first_alarm_date"]      = str(d.date())
        report["lead_days_vs_lehman"]   = int((LEHMAN_DATE - d).days)
        report["alarm_before_lehman"]   = (LEHMAN_DATE - d).days > 0
    else:
        report["first_alarm_date"]      = None
        report["lead_days_vs_lehman"]   = None
        report["alarm_before_lehman"]   = False

    report["p_cp_lehman_week"] = float(p_cp.loc["2008-09-15":"2008-09-19"].max())
    report["p_cp_max_window"]  = float(p_cp.max())

    # ── 1B: AEMA smoothing response ───────────────────────────────────────
    s_t = wlog["s_t"]
    report["s_t_pre_lehman_avg"]    = float(s_t.loc[w_start:"2008-09-14"].mean())
    report["s_t_lehman_week"]       = float(s_t.loc["2008-09-15":"2008-09-19"].mean())
    report["s_t_post_lehman_avg"]   = float(s_t.loc["2008-09-22":"2008-10-31"].mean())
    report["s_t_min_window"]        = float(s_t.min())
    report["s_t_min_date"]          = str(s_t.idxmin().date())

    # ── 1C: Leverage response ─────────────────────────────────────────────
    l = wlog["l_final"]
    report["leverage_pre_lehman"]   = float(l.loc[w_start:"2008-09-14"].mean())
    report["leverage_lehman_week"]  = float(l.loc["2008-09-15":"2008-09-19"].mean())
    report["leverage_post_lehman"]  = float(l.loc["2008-09-22":"2008-10-31"].mean())
    report["leverage_min"]          = float(l.min())
    report["leverage_min_date"]     = str(l.idxmin().date())

    # ── 1D: Circuit breaker activations ───────────────────────────────────
    cb = wlog["circuit_breaker"]
    report["circuit_breaker_active_days"] = int(cb.sum())
    cb_on = cb[cb]
    report["circuit_breaker_first_date"] = (
        str(cb_on.index[0].date()) if not cb_on.empty else None
    )

    # ── 1E: Hold period lock ──────────────────────────────────────────────
    dh = wlog["days_held"]
    report["days_held_at_lehman_week"] = float(
        dh.loc["2008-09-15":"2008-09-19"].mean()
        if len(dh.loc["2008-09-15":"2008-09-19"]) > 0 else 0.0
    )
    report["hold_period_binding"] = report["days_held_at_lehman_week"] > 0

    # ── 1F: Volatility Guard ──────────────────────────────────────────────
    if "vol_guard_cap" in wlog.columns:
        vg = wlog["vol_guard_cap"]
        report["vol_guard_min_window"]  = float(vg.min())
        report["vol_guard_min_date"]    = str(vg.idxmin().date())
        # Average cap during deep crisis (Oct-Nov)
        report["vol_guard_oct_nov_avg"] = float(vg.loc["2008-10-01":"2008-11-30"].mean())

    # ── 1G: NAV drawdown ─────────────────────────────────────────────────
    if not wnav.empty:
        peak = wnav.expanding().max()
        dd   = (wnav - peak) / peak
        report["nav_mdd_window"]     = float(dd.min())
        report["nav_mdd_date"]       = str(dd.idxmin().date())
        report["nav_total_window"]   = float(
            (wnav.iloc[-1] - wnav.iloc[0]) / wnav.iloc[0]
        )

    # ── 1G: Tau trajectory ────────────────────────────────────────────────
    if "tau_t" in wlog.columns:
        tau = wlog["tau_t"]
        report["tau_t_lehman_week_avg"] = float(
            tau.loc["2008-09-15":"2008-09-19"].mean()
        )
        report["tau_t_min_window"]      = float(tau.min())

    return report


# ─────────────────────────────────────────────────────────────────────────────
# Audit 2 — False Positive Audit
# ─────────────────────────────────────────────────────────────────────────────

def audit_false_positives(result: dict) -> dict:
    """Classify every alarm episode in Post-COVID as TP or FP."""
    log = result["log"]
    nav = result["nav"]
    attr = result["attribution"]

    THRESHOLD = 0.30

    report: dict = {
        "total_return":    float(attr["total_return"]),
        "annualised_ret":  float(attr["annualised_ret"]),
        "sharpe":          float(attr["sharpe"]),
        "max_drawdown":    float(attr["max_drawdown"]),
        "n_trades":        int(attr["n_trades"]),
    }

    # Identify all alarm episodes
    above = log["p_cp"] > THRESHOLD
    rising = above & ~above.shift(1, fill_value=False)
    alarm_dates = log.index[rising]

    episodes = []
    for alarm_date in alarm_dates:
        # Find end of episode (first day back below threshold)
        after = log["p_cp"].loc[alarm_date:]
        below = after[after <= THRESHOLD]
        end_date = below.index[0] if not below.empty else log.index[-1]

        # Classify
        event_name = _is_in_known_event(alarm_date)
        is_tp = event_name is not None

        # NAV delta during episode
        nav_slice = nav.loc[alarm_date:end_date]
        nav_ret = float((nav_slice.iloc[-1] / nav_slice.iloc[0]) - 1) if len(nav_slice) > 1 else 0.0

        episodes.append({
            "alarm_date":   str(alarm_date.date()),
            "end_date":     str(end_date.date()),
            "duration_days": int((end_date - alarm_date).days),
            "known_event":  event_name,
            "is_true_positive": is_tp,
            "nav_return_during_episode": round(nav_ret, 4),
            "p_cp_max": float(log["p_cp"].loc[alarm_date:end_date].max()),
        })

    n_tp = sum(1 for e in episodes if e["is_true_positive"])
    n_fp = len(episodes) - n_tp
    fpr  = n_fp / len(episodes) if episodes else 0.0

    report["alarm_episodes"]    = episodes
    report["n_alarm_episodes"]  = len(episodes)
    report["n_true_positives"]  = n_tp
    report["n_false_positives"] = n_fp
    report["false_positive_rate"] = round(fpr, 3)

    # Annual alarm rate
    n_years = (log.index[-1] - log.index[0]).days / 365.25
    report["annual_alarm_rate"] = round(len(episodes) / n_years, 2)

    return report


# ─────────────────────────────────────────────────────────────────────────────
# Audit 3 — Decay Calibration Grid
# ─────────────────────────────────────────────────────────────────────────────

def audit_lambda_grid(
    panels: dict[str, pd.DataFrame],
    base_config: dict,
) -> list[dict]:
    """Sweep λ ∈ LAMBDA_GRID over Pre-QE and Post-COVID."""
    results = []

    for lam in LAMBDA_GRID:
        cfg = copy.deepcopy(base_config)
        cfg["forgetting"]["lambda"] = lam
        logger.info("── Grid: λ=%.3f ──────────────────────", lam)

        row: dict = {"lambda": lam}

        # Pre-QE: Lehman detection
        preqe_panel = panels["Pre-QE"]
        preqe_result = _run_segment(preqe_panel, cfg)
        preqe_log    = preqe_result["log"]
        preqe_attr   = preqe_result["attribution"]

        # Filter to Lehman window
        w_start, w_end = LEHMAN_WINDOW
        if not preqe_log.empty and w_start in preqe_log.index or True:
            try:
                lehman_log = preqe_log.loc[w_start:w_end]
                row["lehman_p_cp_max"]  = float(lehman_log["p_cp"].max()) if not lehman_log.empty else 0.0
                row["lehman_alarm"]     = row["lehman_p_cp_max"] > 0.30
            except Exception:
                row["lehman_p_cp_max"] = 0.0
                row["lehman_alarm"]    = False

        row["preqe_total_ret"]  = float(preqe_attr["total_return"])
        row["preqe_mdd"]        = float(preqe_attr["max_drawdown"])
        row["preqe_sharpe"]     = float(preqe_attr["sharpe"])
        row["preqe_n_trades"]   = int(preqe_attr["n_trades"])

        # Post-COVID: false alarm rate
        postcovid_panel  = panels["Post-COVID"]
        postcovid_result = _run_segment(postcovid_panel, cfg)
        postcovid_log    = postcovid_result["log"]
        postcovid_attr   = postcovid_result["attribution"]

        row["postcovid_total_ret"] = float(postcovid_attr["total_return"])
        row["postcovid_sharpe"]    = float(postcovid_attr["sharpe"])
        row["postcovid_mdd"]       = float(postcovid_attr["max_drawdown"])
        row["postcovid_n_trades"]  = int(postcovid_attr["n_trades"])
        row["postcovid_n_alarms"]  = _alarm_count(postcovid_log)

        results.append(row)
        logger.info(
            "  λ=%.3f │ Lehman P_cp=%.4f │ Pre-QE MDD=%.1f%% │ "
            "Post-COVID Sharpe=%.2f N_alarms=%d",
            lam,
            row["lehman_p_cp_max"],
            row["preqe_mdd"] * 100,
            row["postcovid_sharpe"],
            row["postcovid_n_alarms"],
        )

    return results


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def _sep(title: str):
    logger.info("=" * 60)
    logger.info(title)
    logger.info("=" * 60)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    config = load_config()

    _sep("BUILDING PANELS (cached after first run)")
    panels = {}
    for name, seg in SEGMENTS.items():
        panel = _build_panel(name, seg)
        if panel is None:
            logger.error("Cannot proceed without %s panel. Aborting.", name)
            return
        panels[name] = panel
        logger.info("  %s: %d rows, %s → %s", name, len(panel),
                    panel.index[0].date(), panel.index[-1].date())

    # ── Audit 1: Execution Reality ───────────────────────────────────────
    _sep("AUDIT 1 — EXECUTION REALITY (Pre-QE / Lehman)")
    preqe_result = _run_segment(panels["Pre-QE"], config)
    exec_report  = audit_execution(preqe_result, panels["Pre-QE"])

    logger.info("")
    logger.info("  ┌─ Alarm timing ──────────────────────────────────────")
    logger.info("  │  First alarm date:   %s", exec_report.get("first_alarm_date"))
    logger.info("  │  Lead vs Lehman:     %s days", exec_report.get("lead_days_vs_lehman"))
    logger.info("  │  Alarm before event: %s", exec_report.get("alarm_before_lehman"))
    logger.info("  │  P_cp Lehman week:   %.4f", exec_report.get("p_cp_lehman_week", 0))
    logger.info("  ├─ AEMA smoothing (s_t) ──────────────────────────────")
    logger.info("  │  Pre-Lehman avg:     %.4f", exec_report.get("s_t_pre_lehman_avg", 0))
    logger.info("  │  Lehman week:        %.4f", exec_report.get("s_t_lehman_week", 0))
    logger.info("  │  Post-Lehman avg:    %.4f", exec_report.get("s_t_post_lehman_avg", 0))
    logger.info("  │  s_t minimum:        %.4f on %s",
                exec_report.get("s_t_min_window", 0), exec_report.get("s_t_min_date"))
    logger.info("  ├─ Leverage (l_final) ────────────────────────────────")
    logger.info("  │  Pre-Lehman avg:     %.4f", exec_report.get("leverage_pre_lehman", 0))
    logger.info("  │  Lehman week:        %.4f", exec_report.get("leverage_lehman_week", 0))
    logger.info("  │  Post-Lehman avg:    %.4f", exec_report.get("leverage_post_lehman", 0))
    logger.info("  │  Minimum:            %.4f on %s",
                exec_report.get("leverage_min", 0), exec_report.get("leverage_min_date"))
    logger.info("  ├─ Circuit breaker ───────────────────────────────────")
    logger.info("  │  Active days:        %d", exec_report.get("circuit_breaker_active_days", 0))
    logger.info("  │  First activation:   %s", exec_report.get("circuit_breaker_first_date"))
    logger.info("  ├─ Volatility Guard ──────────────────────────────────")
    logger.info("  │  Min cap window:     %.4f on %s",
                exec_report.get("vol_guard_min_window", 1.0),
                exec_report.get("vol_guard_min_date"))
    logger.info("  │  Oct-Nov avg cap:    %.4f",
                exec_report.get("vol_guard_oct_nov_avg", 1.0))
    logger.info("  ├─ Hold period ───────────────────────────────────────")
    logger.info("  │  days_held Lehman wk: %.1f (binding=%s)",
                exec_report.get("days_held_at_lehman_week", 0),
                exec_report.get("hold_period_binding"))
    logger.info("  ├─ NAV outcome ───────────────────────────────────────")
    logger.info("  │  Window MDD:         %.1f%% on %s",
                exec_report.get("nav_mdd_window", 0) * 100,
                exec_report.get("nav_mdd_date"))
    logger.info("  │  Window total ret:   %.1f%%",
                exec_report.get("nav_total_window", 0) * 100)
    logger.info("  └─────────────────────────────────────────────────────")

    with open(OUTPUT_DIR / "audit1_execution.json", "w") as f:
        json.dump(exec_report, f, indent=2, default=str)

    # Save Pre-QE log for manual inspection
    preqe_result["log"].to_csv(OUTPUT_DIR / "preqe_log_lehman.csv")

    # ── Audit 2: False Positive Audit ─────────────────────────────────────
    _sep("AUDIT 2 — FALSE POSITIVE AUDIT (Post-COVID 2020-2025)")
    postcovid_result = _run_segment(panels["Post-COVID"], config)
    fp_report = audit_false_positives(postcovid_result)

    logger.info("")
    logger.info("  Performance: Return=+%.1f%%, Sharpe=%.2f, MDD=%.1f%%",
                fp_report["total_return"] * 100,
                fp_report["sharpe"],
                fp_report["max_drawdown"] * 100)
    logger.info("  Alarm episodes: %d total, %d TP, %d FP  (FPR=%.1f%%)",
                fp_report["n_alarm_episodes"],
                fp_report["n_true_positives"],
                fp_report["n_false_positives"],
                fp_report["false_positive_rate"] * 100)
    logger.info("  Annual alarm rate: %.2f / year", fp_report["annual_alarm_rate"])
    logger.info("")
    logger.info("  %-20s  %-8s  %-18s  %-8s  %s",
                "Alarm Date", "P_cp Max", "Known Event", "TP?", "NAV ret")
    logger.info("  " + "─" * 80)
    for ep in fp_report["alarm_episodes"]:
        logger.info("  %-20s  %-8.4f  %-18s  %-8s  %+.1f%%",
                    ep["alarm_date"],
                    ep["p_cp_max"],
                    ep["known_event"] or "UNKNOWN",
                    "✓" if ep["is_true_positive"] else "✗ FP",
                    ep["nav_return_during_episode"] * 100)

    with open(OUTPUT_DIR / "audit2_false_positives.json", "w") as f:
        json.dump(fp_report, f, indent=2, default=str)

    # ── Audit 3: λ Calibration Grid ───────────────────────────────────────
    _sep("AUDIT 3 — DECAY CALIBRATION GRID (λ sweep)")
    grid_results = audit_lambda_grid(panels, config)

    logger.info("")
    logger.info("  %-8s  %-12s  %-10s  %-10s  %-12s  %-10s  %-10s",
                "λ", "Lehman P_cp", "PreQE MDD", "PreQE Shp",
                "PC N_Alarms", "PC Sharpe", "PC MDD")
    logger.info("  " + "─" * 80)
    for row in grid_results:
        alarm_marker = "✓" if row["lehman_alarm"] else "✗"
        logger.info(
            "  %-8.3f  %s %-10.4f  %-10.1f%%  %-10.2f  %-12d  %-10.2f  %-10.1f%%",
            row["lambda"],
            alarm_marker,
            row["lehman_p_cp_max"],
            row["preqe_mdd"] * 100,
            row["preqe_sharpe"],
            row["postcovid_n_alarms"],
            row["postcovid_sharpe"],
            row["postcovid_mdd"] * 100,
        )

    # The Pareto-optimal λ: must have Lehman alarm + min false alarms
    detecting = [r for r in grid_results if r["lehman_alarm"]]
    if detecting:
        best = min(detecting, key=lambda r: r["postcovid_n_alarms"])
        logger.info("")
        logger.info("  Pareto optimal λ = %.3f", best["lambda"])
        logger.info("    Lehman P_cp   = %.4f", best["lehman_p_cp_max"])
        logger.info("    Post-COVID alarms = %d", best["postcovid_n_alarms"])
        logger.info("    Post-COVID Sharpe = %.2f", best["postcovid_sharpe"])
        logger.info("    Pre-QE MDD        = %.1f%%", best["preqe_mdd"] * 100)

    grid_df = pd.DataFrame(grid_results)
    grid_df.to_csv(OUTPUT_DIR / "audit3_lambda_grid.csv", index=False)

    with open(OUTPUT_DIR / "audit3_lambda_grid.json", "w") as f:
        json.dump(grid_results, f, indent=2, default=str)

    logger.info("")
    logger.info("All audit artifacts saved to %s/", OUTPUT_DIR)


if __name__ == "__main__":
    main()
