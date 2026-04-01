"""V12.1 Walk-Forward Optimization (WFO) Engine."""
from collections.abc import Callable, Sequence
from typing import Any

import numpy as np
import pandas as pd

from src.research.auditor import SentinelAuditor


class WFOEngine:
    """
    Framework for 7-year In-Sample / 1-year Out-of-Sample rolling optimization.
    Enforces Relative Survival Constraints.
    """
    def __init__(self,
                 is_years: int = 7,
                 oos_years: int = 1,
                 burn_in_years: int = 1):
        self.is_years = is_years
        self.oos_years = oos_years
        self.burn_in_years = burn_in_years
        self.auditor = SentinelAuditor(tolerance=0.05)

    def run_rolling_optimization(self,
                                 full_data: pd.DataFrame,
                                 param_grid: Sequence[dict[str, Any]],
                                 backtest_func: Callable[[pd.DataFrame, dict[str, Any]], pd.DataFrame]) -> dict:
        """
        Execute WFO loop.
        backtest_func: takes (data, params) and returns execution_df with returns.
        """
        full_data["observation_date"] = pd.to_datetime(full_data["observation_date"])
        start_date = full_data["observation_date"].min()
        end_date = full_data["observation_date"].max()

        current_train_end = start_date + pd.DateOffset(years=self.is_years)

        oos_results = []
        best_params_history = []

        while current_train_end + pd.DateOffset(years=self.oos_years) <= end_date:
            train_start = current_train_end - pd.DateOffset(years=self.is_years)
            test_end = current_train_end + pd.DateOffset(years=self.oos_years)

            print(f"WFO Window: Train {train_start.date()} to {current_train_end.date()} | Test to {test_end.date()}")

            train_data = full_data[(full_data["observation_date"] >= train_start) &
                                   (full_data["observation_date"] < current_train_end)]

            # 1. In-Sample Optimization with Survival Constraint
            best_params = self._optimize_is(train_data, param_grid, backtest_func)
            best_params_history.append({
                "train_end": current_train_end,
                "params": best_params
            })

            # 2. Out-of-Sample Forward Test
            test_data = full_data[(full_data["observation_date"] >= current_train_end) &
                                  (full_data["observation_date"] < test_end)]

            # Note: We need some history for Sentinel (Burn-in) even in OOS.
            # Usually we pass the final state of IS to OOS.
            oos_exec_df = backtest_func(test_data, best_params)
            oos_results.append(oos_exec_df)

            # Advance window
            current_train_end += pd.DateOffset(years=self.oos_years)

        if not oos_results:
            return {"error": "Not enough data for even one WFO cycle."}

        combined_oos = pd.concat(oos_results).sort_values("date")
        return {
            "combined_oos": combined_oos,
            "params_history": best_params_history
        }

    def _optimize_is(self, train_data: pd.DataFrame, param_grid: Sequence[dict[str, Any]], backtest_func: Callable) -> dict:
        """Find best params in IS window satisfying Relative Survival."""
        best_ir = -np.inf
        best_p = param_grid[0]

        for params in param_grid:
            exec_df = backtest_func(train_data, params)

            # Audit survival
            # We assume exec_df has 'return_l4' and 'return_base'
            audit = self.auditor.validate_relative_survival(
                exec_df.set_index("date")["return_l4"],
                exec_df.set_index("date")["return_base"]
            )

            if audit["all_passed"]:
                mean_ir = audit["annual_details"][list(audit["annual_details"].keys())[0]]["ir_with_l4"] # Simplified
                # Use mean IR across years as objective
                mean_ir = np.mean([v["ir_with_l4"] for v in audit["annual_details"].values()])

                if mean_ir > best_ir:
                    best_ir = mean_ir
                    best_p = params

        return best_p
