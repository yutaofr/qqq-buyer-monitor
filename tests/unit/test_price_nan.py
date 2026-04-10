import unittest
from datetime import date
from unittest.mock import patch

import numpy as np
import pandas as pd

from src.collector.price import fetch_price_data


class TestPriceNaN(unittest.TestCase):
    def test_fetch_price_data_with_trailing_nan(self):
        """
        GIVEN: yfinance returns a DataFrame where the last row has a NaN Close price.
        WHEN: fetch_price_data is called.
        THEN: It should currently return NaN (Red) or we expect it to skip NaN (Green later).
        """
        # Mock data: last row is NaN
        dates = pd.date_range("2026-04-01", periods=5)
        mock_hist = pd.DataFrame(
            {
                "Close": [580.0, 581.0, 582.0, 583.0, np.nan],
                "Volume": [1000, 1100, 1200, 1300, 1400],
            },
            index=dates,
        )

        with patch("yfinance.Ticker") as mock_ticker:
            instance = mock_ticker.return_value
            instance.history.return_value = mock_hist

            # DESIRED BEHAVIOR (Green): This should skip the last NaN row and take 583.0 from 2026-04-04
            result = fetch_price_data("QQQ", as_of=date(2026, 4, 5))

            self.assertFalse(np.isnan(result["price"]), "Should NOT return NaN anymore.")
            self.assertEqual(result["price"], 583.0)
            self.assertEqual(result["date"], date(2026, 4, 4))


if __name__ == "__main__":
    unittest.main()
