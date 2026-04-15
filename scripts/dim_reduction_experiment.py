"""Dimensional reduction experiment: SPREAD_ANOMALY-only BOCPD.

Question: Can a +3.8σ VIX Z-score alone punch through NIG prior inertia?

Method:
  1. Build a 1D BOCPD engine using ONLY the spread_anomaly NIG prior
  2. Feed only SPREAD_ANOMALY as x_t (scalar, not 3D vector)
  3. Record P_cp at each step through 2008 Lehman crisis window
  4. Compare 1D P_cp vs 3D P_cp (from full engine)

If 1D engine fires → engine math is healthy, problem is ED/Fisher signal
If 1D engine silent → engine prior/tau too stiff, need structural fix

Usage:
  docker compose run --rm test python scripts/dim_reduction_experiment.py
"""

from __future__ import annotations

import copy
import logging

import numpy as np
import pandas as pd

from src.liquidity.config import load_config
from src.liquidity.data.panel_builder import build_pit_aligned_panel
from src.liquidity.engine.bocpd import BOCPDEngine
from src.liquidity.engine.hazard import compute_hazard, precompute_g_r
from src.liquidity.engine.nig import predictive_logpdf, update_nig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("dim_reduction")

SEGMENT_START = "2006-09-01"
SEGMENT_END   = "2008-12-31"
LEHMAN_WINDOW = ("2008-07-01", "2008-12-31")
BURN_IN       = 252


class BOCPD1D:
    """Minimal 1D BOCPD engine for a single observation dimension.

    Identical math to BOCPDEngine but D=1, using only one NIG prior.
    No code shared — this is a self-contained experimental implementation.
    """

    def __init__(self, config: dict, dim_key: str = "spread_anomaly"):
        h_cfg = config["hazard"]
        self._r_max = h_cfg["R_MAX"]
        self._g_r = precompute_g_r(
            r_max=self._r_max,
            r_stable=h_cfg["R_STABLE"],
            kappa=h_cfg["KAPPA_HAZARD"],
        )
        # Single-dimension prior: shape (1, 4)
        p = config["nig_priors"][dim_key]
        self._prior = np.array([[p["mu_0"], p["kappa_0"],
                                  p["alpha_0"], p["beta_0"]]])

        n = self._r_max + 1
        self._probs = np.zeros(n)
        self._probs[0] = 1.0
        self._stats = np.broadcast_to(self._prior, (n, 1, 4)).copy()
        self._t = 0

    def update(self, x_scalar: float, lambda_macro: float) -> float:
        """Run one BOCPD step with a scalar observation."""
        x_t = np.array([x_scalar])  # (1,)

        # Step 1: predictive log-density
        log_pred = predictive_logpdf(self._stats, x_t)
        log_pred_stable = log_pred - log_pred.max()
        pred = np.exp(log_pred_stable)

        # Step 2: hazard
        h = compute_hazard(self._g_r, lambda_macro, r_max=self._r_max)

        # Step 3: posterior
        new_probs = np.empty_like(self._probs)
        new_probs[0] = np.sum(self._probs * h * pred)
        new_probs[1:] = self._probs[:-1] * (1.0 - h[:-1]) * pred[:-1]

        # Step 4: normalize
        total = new_probs.sum()
        if total > 0:
            new_probs /= total
        else:
            new_probs[:] = 0.0
            new_probs[0] = 1.0

        # Step 5: NIG update
        new_stats = np.empty_like(self._stats)
        new_stats[0, :, :] = self._prior
        new_stats[1:, :, :] = update_nig(self._stats[:-1, :, :], x_t)

        self._probs = new_probs
        self._stats = new_stats
        self._t += 1

        return float(new_probs[0])


def main():
    config = load_config()

    # Build Pre-QE panel
    logger.info("Building Pre-QE panel...")
    panel = build_pit_aligned_panel(SEGMENT_START, SEGMENT_END)
    logger.info("Panel: %d rows", len(panel))

    # Instantiate engines
    engine_3d = BOCPDEngine(config)
    engine_1d = BOCPD1D(config, dim_key="spread_anomaly")

    # Run both engines in parallel
    records = []
    for i, (date, row) in enumerate(panel.iterrows()):
        x_3d = np.array([
            row["ED_ACCEL"],
            row["SPREAD_ANOMALY"],
            row["FISHER_RHO"],
        ])
        x_spread = row["SPREAD_ANOMALY"]
        lm = float(row["LAMBDA_MACRO"])

        p_cp_3d = engine_3d.update(x_3d, lm)
        p_cp_1d = engine_1d.update(x_spread, lm)

        records.append({
            "date":             date,
            "p_cp_3d":          p_cp_3d,
            "p_cp_1d":          p_cp_1d,
            "spread_anomaly":   x_spread,
            "ed_accel":         row["ED_ACCEL"],
            "fisher_rho":       row["FISHER_RHO"],
            "lambda_macro":     lm,
        })

    df = pd.DataFrame(records).set_index("date")

    # ── Lehman window analysis ──────────────────────────────
    w = df.loc[LEHMAN_WINDOW[0]:LEHMAN_WINDOW[1]]

    logger.info("=" * 70)
    logger.info("DIMENSIONAL REDUCTION EXPERIMENT: LEHMAN CRISIS WINDOW")
    logger.info("=" * 70)

    logger.info("\n  %-12s  %10s  %10s  %12s  %12s  %10s",
                "Date", "P_cp(3D)", "P_cp(1D)", "SPREAD", "ED_ACCEL", "λ_macro")
    logger.info("  " + "─" * 72)

    # Show key dates
    crisis_dates = pd.to_datetime([
        "2008-07-11",  # IndyMac collapses
        "2008-09-07",  # Fannie/Freddie conservatorship
        "2008-09-15",  # Lehman files
        "2008-09-16",  # AIG bailout
        "2008-09-29",  # TARP vote fails, -9% day
        "2008-10-06",  # VIX > 50
        "2008-10-10",  # VIX peak ~80
        "2008-11-20",  # Market bottom
    ])

    for d in crisis_dates:
        # Find nearest trading day
        nearest = w.index[w.index.get_indexer([d], method="nearest")]
        if len(nearest) > 0:
            r = w.loc[nearest[0]]
            logger.info("  %s  %10.6f  %10.6f  %12.4f  %12.6f  %10.6f",
                        nearest[0].strftime("%Y-%m-%d"),
                        r["p_cp_3d"], r["p_cp_1d"],
                        r["spread_anomaly"], r["ed_accel"], r["lambda_macro"])

    # Summary statistics
    logger.info("\n" + "=" * 70)
    logger.info("SUMMARY")
    logger.info("=" * 70)

    # Pre-crisis (Jul-Aug) vs Crisis (Sep-Dec)
    pre  = df.loc["2008-07-01":"2008-08-31"]
    crss = df.loc["2008-09-01":"2008-12-31"]

    logger.info("\n  %-25s  %12s  %12s", "", "Pre (Jul-Aug)", "Crisis (Sep-Dec)")
    logger.info("  " + "─" * 52)
    logger.info("  %-25s  %12.6f  %12.6f", "P_cp(3D) max",
                pre["p_cp_3d"].max(), crss["p_cp_3d"].max())
    logger.info("  %-25s  %12.6f  %12.6f", "P_cp(1D) max",
                pre["p_cp_1d"].max(), crss["p_cp_1d"].max())
    logger.info("  %-25s  %12.6f  %12.6f", "P_cp(3D) mean",
                pre["p_cp_3d"].mean(), crss["p_cp_3d"].mean())
    logger.info("  %-25s  %12.6f  %12.6f", "P_cp(1D) mean",
                pre["p_cp_1d"].mean(), crss["p_cp_1d"].mean())
    logger.info("  %-25s  %12.4f  %12.4f", "SPREAD max",
                pre["spread_anomaly"].max(), crss["spread_anomaly"].max())
    logger.info("  %-25s  %12.4f  %12.4f", "SPREAD mean",
                pre["spread_anomaly"].mean(), crss["spread_anomaly"].mean())

    # Threshold analysis
    for thresh in [0.10, 0.20, 0.30, 0.50, 0.70]:
        days_3d = (w["p_cp_3d"] > thresh).sum()
        days_1d = (w["p_cp_1d"] > thresh).sum()
        logger.info("  P_cp > %.2f:  3D=%3d days,  1D=%3d days", thresh, days_3d, days_1d)

    # Full window max
    logger.info("\n  FULL WINDOW MAX P_cp(3D): %.6f", w["p_cp_3d"].max())
    logger.info("  FULL WINDOW MAX P_cp(1D): %.6f", w["p_cp_1d"].max())

    first_1d_alarm = w[w["p_cp_1d"] > 0.30]
    if not first_1d_alarm.empty:
        logger.info("  1D FIRST ALARM (>0.30):   %s (%.1f days before Lehman)",
                    first_1d_alarm.index[0].strftime("%Y-%m-%d"),
                    (pd.Timestamp("2008-09-15") - first_1d_alarm.index[0]).days)
    else:
        logger.info("  1D FIRST ALARM (>0.30):   NEVER TRIGGERED")

    # ── VERDICT ─────────────────────────────────────────────
    max_1d = w["p_cp_1d"].max()
    logger.info("\n" + "=" * 70)
    if max_1d > 0.30:
        logger.info("VERDICT: ✅ 1D engine FIRES. Engine math is healthy.")
        logger.info("  The villain is ED_ACCEL and FISHER_RHO signal failure.")
        logger.info("  → Proceed to investigate feature generation logic.")
    else:
        logger.info("VERDICT: ❌ 1D engine SILENT. Engine prior/tau too stiff.")
        logger.info("  Even +3.8σ SPREAD_ANOMALY cannot punch through NIG inertia.")
        logger.info("  → Structural fix needed: tau, kappa_0, or prior beta.")
    logger.info("=" * 70)

    # Save full trace for plotting
    df.to_csv("artifacts/liquidity_backtest/dim_reduction_trace.csv")
    logger.info("Full trace saved to artifacts/liquidity_backtest/dim_reduction_trace.csv")


if __name__ == "__main__":
    main()
