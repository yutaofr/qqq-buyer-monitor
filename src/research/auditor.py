"""V12.1 Auditing module for Relative Survival Constraints and WFO."""
import numpy as np
import pandas as pd

from src.utils.stats import calculate_annual_metrics


class SentinelAuditor:
    """
    Auditor to enforce V12.1 Relative Survival Constraints.
    """
    def __init__(self, tolerance: float = 0.05):
        self.tolerance = tolerance

    def validate_relative_survival(self, with_l4_returns: pd.Series, base_macro_returns: pd.Series) -> dict:
        """
        Validates that adding Layer 4 doesn't significantly degrade performance in any natural year.
        Constraint: Annual_IR(With_L4) >= Annual_IR(Base_Macro) - tolerance
        """
        # Ensure indices are datetime
        with_l4_returns.index = pd.to_datetime(with_l4_returns.index)
        base_macro_returns.index = pd.to_datetime(base_macro_returns.index)

        years = sorted(with_l4_returns.index.year.unique())
        results = {}
        all_passed = True

        for year in years:
            y_l4 = with_l4_returns[with_l4_returns.index.year == year]
            y_base = base_macro_returns[base_macro_returns.index.year == year]

            m_l4 = calculate_annual_metrics(y_l4)
            m_base = calculate_annual_metrics(y_base)

            diff = m_l4["ir"] - m_base["ir"]
            passed = diff >= -self.tolerance

            if not passed:
                all_passed = False

            results[year] = {
                "ir_with_l4": m_l4["ir"],
                "ir_base": m_base["ir"],
                "diff": diff,
                "passed": passed
            }

        return {
            "all_passed": all_passed,
            "annual_details": results,
            "mean_diff": np.mean([r["diff"] for r in results.values()])
        }
