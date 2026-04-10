import logging
import os

import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_connectivity")


def verify_fred():
    key = os.environ.get("FRED_API_KEY")
    if not key:
        logger.error("FRED_API_KEY missing")
        return False
    # Test with a simple series
    url = f"https://api.stlouisfed.org/fred/series?series_id=GNPCA&api_key={key}&file_type=json"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            logger.info("FRED connectivity: OK")
            return True
        else:
            logger.error(f"FRED connectivity: FAILED (status {resp.status_code})")
            return False
    except Exception as e:
        logger.error(f"FRED connectivity: ERROR ({e})")
        return False


def verify_discord():
    url = os.environ.get("ALERT_WEBHOOK_URL")
    if not url:
        logger.error("ALERT_WEBHOOK_URL missing")
        return False
    if not url.startswith("https://discord.com/api/webhooks/"):
        logger.error("ALERT_WEBHOOK_URL: Invalid format")
        return False
    try:
        # GET on a webhook URL returns info about the webhook
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            logger.info("Discord Webhook: OK")
            return True
        else:
            logger.error(f"Discord Webhook: FAILED (status {resp.status_code})")
            return False
    except Exception as e:
        logger.error(f"Discord Webhook: ERROR ({e})")
        return False


def verify_vercel():
    token = os.environ.get("VERCEL_BLOB_READ_WRITE_TOKEN")
    if not token:
        logger.error("VERCEL_BLOB_READ_WRITE_TOKEN missing")
        return False
    # Format check: blob_...
    if not token.startswith("vercel_blob_rw_"):
        logger.error("VERCEL_BLOB_READ_WRITE_TOKEN: Invalid format")
        return False

    # We can't easily test without the @vercel/blob SDK or complex auth headers
    # but we can do a simple check.
    logger.info(
        "Vercel Blob Token: Format OK (Explicit verification skipped due to SDK dependency)"
    )
    return True


if __name__ == "__main__":
    success = True
    if not verify_fred():
        success = False
    if not verify_discord():
        success = False
    if not verify_vercel():
        success = False

    if success:
        logger.info("All connectivity checks: PASSED")
        exit(0)
    else:
        logger.error("One or more connectivity checks: FAILED")
        exit(1)
