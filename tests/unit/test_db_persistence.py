import os
import unittest
from datetime import date

import numpy as np

from src.models import SignalResult, TargetAllocationState
from src.store.db import save_signal


class TestDBPersistence(unittest.TestCase):
    def setUp(self):
        self.db_path = "data/test_signals_nan.db"
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_save_signal_with_nan_price_fails(self):
        """
        GIVEN: A SignalResult with NaN price.
        WHEN: save_signal is called.
        THEN: It should raise sqlite3.IntegrityError OR a descriptive ValueError (after fix).
        This test locks in the current crash point.
        """
        result = SignalResult(
            date=date(2026, 4, 1),
            price=np.nan,
            target_beta=0.5,
            probabilities={"BUST": 1.0},
            priors={"BUST": 1.0},
            entropy=0.0,
            stable_regime="BUST",
            target_allocation=TargetAllocationState(),
            logic_trace=[],
            explanation="Test NaN",
        )

        # DESIRED BEHAVIOR (Green): Raises ValueError (our defensive guard)
        with self.assertRaises(ValueError):
            save_signal(result, path=self.db_path)


if __name__ == "__main__":
    unittest.main()
