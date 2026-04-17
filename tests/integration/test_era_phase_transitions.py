import inspect
import unittest
from pathlib import Path

import pandas as pd

from src.backtest import run_v11_audit

print(f"DIAG_BACKTEST_FILE: {inspect.getfile(run_v11_audit)}")


class TestEraPhaseTransitions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset_path = "data/macro_historical_dump.csv"
        cls.price_cache_path = "data/qqq_history_cache.csv"
        cls.output_dir = "artifacts/test_era_transitions"
        Path(cls.output_dir).mkdir(parents=True, exist_ok=True)

    def _run_window(self, start_date, end_date, subdir):
        # Run the audit for the specific period
        window_dir = Path(self.output_dir) / subdir
        window_dir.mkdir(parents=True, exist_ok=True)

        run_v11_audit(
            dataset_path=self.dataset_path,
            evaluation_start=start_date,
            artifact_dir=str(window_dir),
            experiment_config={
                "price_cache_path": self.price_cache_path,
                "allow_price_download": False,
                "price_end_date": end_date,
                "save_plots": False,  # Speed up
            },
        )
        # Read the probabilities trace
        prob_trace = pd.read_csv(window_dir / "probability_audit.csv", parse_dates=["date"])
        return prob_trace.set_index("date")

    def test_2020_covid_crash_momentum(self):
        """
        Verify that the system reacts to the March 2020 crash with high conviction momentum.
        """
        # Window: Late Feb to Early April 2020
        trace = self._run_window("2020-02-15", "2020-04-15", "2020_crash")

        # Calculate Momentum (1-day diff)
        bust_momentum = trace["prob_BUST"].diff()

        # 1. BUST onset should happen in March
        march_momentum = bust_momentum.loc["2020-03-01":"2020-03-20"]
        max_momentum = march_momentum.max()

        print(f"\n[2020 COVID] Max BUST Momentum: {max_momentum:.4f}")

        # Assert that we saw a 'Conviction Spike' (> 0.05 change in a single day)
        self.assertTrue(
            max_momentum > 0.05,
            f"Insufficient BUST momentum during COVID crash: {max_momentum:.4f}",
        )

        # 2. Transition to RECOVERY should follow the bottom (March 23)
        recovery_momentum = trace["prob_RECOVERY"].diff().loc["2020-03-23":"2020-04-05"]
        max_rec_momentum = recovery_momentum.max()
        print(f"[2020 COVID] Max RECOVERY Momentum: {max_rec_momentum:.4f}")
        self.assertTrue(max_rec_momentum > 0.04, "Insufficient RECOVERY momentum at 2020 bottom")

    def test_2022_regime_pivot_momentum(self):
        """
        Verify the transition to LATE_CYCLE/BUST during the 2022 tightening cycle.
        """
        # Window: Dec 2021 to June 2022
        trace = self._run_window("2021-12-15", "2022-03-15", "2022_pivot")

        # Transition from MID_CYCLE to LATE_CYCLE or BUST
        late_cycle_momentum = trace["prob_LATE_CYCLE"].diff().loc["2022-01-01":"2022-02-15"]
        max_lc_momentum = late_cycle_momentum.max()

        print(f"\n[2022 Pivot] Max LATE_CYCLE Momentum: {max_lc_momentum:.4f}")
        # Expected to see a steady shift
        self.assertTrue(
            max_lc_momentum > 0.03, "Insufficient LATE_CYCLE momentum during 2022 transition"
        )


if __name__ == "__main__":
    unittest.main()
