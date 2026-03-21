"""U.S. Treasury Data Collector: Yield Curve backup source."""
from __future__ import annotations

import logging
import requests
import xml.etree.ElementTree as ET
from datetime import date

logger = logging.getLogger(__name__)

TREASURY_XML_URL = "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml?data=daily_treasury_yield_curve&field_tdr_date_value={year}"

def fetch_treasury_yields() -> dict[str, float | None]:
    """
    Fetch the latest Daily Treasury Par Yield Curve Rates from home.treasury.gov.
    Returns a dict with '10Y' and '3M' yields.
    """
    current_year = date.today().year
    url = TREASURY_XML_URL.format(year=current_year)
    
    result = {"10Y": None, "3M": None, "date": None}
    
    try:
        logger.debug("Fetching Treasury Yields from XML: %s", url)
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        
        root = ET.fromstring(response.content)
        
        # XML Namespaces
        ns = {
            'atom': 'http://www.w3.org/2005/Atom',
            'd': 'http://schemas.microsoft.com/ado/2007/08/dataservices',
            'm': 'http://schemas.microsoft.com/ado/2007/08/dataservices/metadata'
        }
        
        entries = root.findall('atom:entry', ns)
        if not entries:
            # Try previous year if current year just started and is empty
            if date.today().month == 1 and date.today().day < 5:
                url = TREASURY_XML_URL.format(year=current_year - 1)
                response = requests.get(url, timeout=15)
                root = ET.fromstring(response.content)
                entries = root.findall('atom:entry', ns)
            
        if not entries:
            return result
            
        # Get the latest entry
        latest_entry = entries[-1]
        properties = latest_entry.find('.//m:properties', ns)
        
        ten_year_raw = properties.find('d:BC_10YEAR', ns).text
        three_month_raw = properties.find('d:BC_3MONTH', ns).text
        date_raw = properties.find('d:NEW_DATE', ns).text
        
        if ten_year_raw:
            result["10Y"] = float(ten_year_raw)
        if three_month_raw:
            result["3M"] = float(three_month_raw)
        if date_raw:
            result["date"] = date_raw.split('T')[0]
            
        logger.info("Fetched Treasury Yields (Backup): 10Y=%.2f%%, 3M=%.2f%% (Date: %s)", 
                    result["10Y"], result["3M"], result["date"])
        
    except Exception as exc:
        logger.warning("U.S. Treasury XML fetch failed: %s", exc)
        
    return result
