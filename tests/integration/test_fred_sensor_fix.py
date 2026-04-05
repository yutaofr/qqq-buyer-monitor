import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Ensure we can import from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.engine.baseline.data_loader import fetch_baseline_series


class TestFredSensorRepro(unittest.TestCase):
    """
    Verification Test for FRED API daily isolation.
    """

    @patch("src.collector.macro.requests.get")
    def test_vixcls_skips_alfred_params(self, mock_get):
        """
        Verify that VIXCLS (Daily) now skips the ALFRED path and goes to the standard path.
        """
        # 1. Setup Mock for success
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "observations": [{"date": "2024-01-01", "value": "15.5"}]
        }
        mock_get.return_value = mock_response

        # 2. Execute
        result = fetch_baseline_series("VIXCLS")

        # 3. Verify
        self.assertIsNotNone(result, "Expected data for VIXCLS")

        # Verify that archival params are NOT in any call for this series
        for call in mock_get.call_args_list:
            url = call[0][0]
            self.assertNotIn(
                "realtime_start", url, f"Found archival param in URL for Daily series: {url}"
            )
            self.assertIn("series_id=VIXCLS", url)

    @patch("src.collector.macro.requests.get")
    def test_ipman_uses_alfred_params(self, mock_get):
        """
        Verify that IPMAN (Monthly) still uses the ALFRED path.
        """
        # 1. Setup Mock for success (ALFRED response usually has realtime_start columns)
        mock_response = MagicMock()
        mock_response.status_code = 200
        # ALFRED-like response
        mock_response.json.return_value = {
            "observations": [
                {
                    "date": "2024-01-01",
                    "value": "100.5",
                    "realtime_start": "2024-01-15",
                    "realtime_end": "9999-12-31",
                }
            ]
        }
        mock_get.return_value = mock_response

        # 2. Execute
        _ = fetch_baseline_series("IPMAN")

        # 3. Verify
        # It should have called FRED API with ALFRED params in the first attempt
        args, kwargs = mock_get.call_args_list[0]
        url = args[0]
        self.assertIn("realtime_start=1776-07-04", url)
        self.assertIn("series_id=IPMAN", url)

    def test_real_world_connectivity(self):
        """
        Verify that VIXCLS now fetches successfully with real credentials.
        """
        api_key = os.getenv("FRED_API_KEY")
        if not api_key:
            print("Skipping live test: FRED_API_KEY not found in environment.")
            return

        print("Running live verification for VIXCLS with current API key...")
        result = fetch_baseline_series("VIXCLS")
        # In current state, this is expected to return DATA because ALFRED params are gone
        self.assertIsNotNone(result, "Live API should return DATA for VIXCLS now.")
        print(f"Verified: result has {len(result)} rows.")


if __name__ == "__main__":
    unittest.main()
