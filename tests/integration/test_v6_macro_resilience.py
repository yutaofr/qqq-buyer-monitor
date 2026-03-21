import pytest
import requests
from unittest.mock import MagicMock, patch
from src.collector.macro import fetch_credit_spread
from src.collector.macro_v3 import fetch_real_yield

# Mock Treasury XML response
TREASURY_XML_MOCK = """<atom:feed xmlns:atom="http://www.w3.org/2005/Atom" 
    xmlns:d="http://schemas.microsoft.com/ado/2007/08/dataservices" 
    xmlns:m="http://schemas.microsoft.com/ado/2007/08/dataservices/metadata">
    <atom:entry>
        <m:properties>
            <d:NEW_DATE>2026-03-20T00:00:00</d:NEW_DATE>
            <d:BC_10YEAR>4.50</d:BC_10YEAR>
            <d:BC_3MONTH>3.50</d:BC_3MONTH>
        </m:properties>
    </atom:entry>
</atom:feed>"""

def mock_requests_get(url, *args, **kwargs):
    response = MagicMock()
    if "stlouisfed.org" in url:
        # Simulate FRED 500 Error
        response.status_code = 500
        response.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Server Error")
    elif "home.treasury.gov" in url:
        # Success for Treasury
        response.status_code = 200
        response.content = TREASURY_XML_MOCK.encode('utf-8')
    elif "chicagofed.org" in url:
        # Fail Chicago Fed to reach Treasury in credit spread chain
        response.status_code = 404
    else:
        response.status_code = 404
    return response

@patch('requests.get', side_effect=mock_requests_get)
def test_credit_spread_fallback_to_treasury(mock_get):
    """Verify credit spread falls back to Treasury when FRED and Chicago Fed fail."""
    spread = fetch_credit_spread()
    # YC Spread = 4.5 - 3.5 = 1.0
    # Synthetic = 350 + (1.0 - 1.0) * 125 = 350
    assert spread == 350.0
    assert mock_get.call_count >= 2 # At least FRED and Treasury (and maybe Chicago Fed)

@patch('requests.get', side_effect=mock_requests_get)
def test_real_yield_fallback_to_treasury(mock_get):
    """Verify real yield falls back to Treasury when FRED fails."""
    # We must patch yfinance to prevent live calls if Treasury also fails
    with patch('yfinance.Ticker') as mock_yf:
        val = fetch_real_yield()
        # Nominal 4.5 - 2.0 proxy = 2.5
        assert val == 2.5
