import json
import logging
import os
import time
from pathlib import Path

import requests

logger = logging.getLogger(__name__)


class CloudPersistenceBridge:
    """
    v11.18 Cloud Persistence Bridge.
    Handles two-way sync between local data files and Vercel Blob Storage.
    Implements Namespace Isolation (Branch-Locking).
    """

    def __init__(self, token: str | None = None):
        self.token = token or os.environ.get("VERCEL_BLOB_READ_WRITE_TOKEN")
        self.is_ci = os.environ.get("GITHUB_ACTIONS") == "true"
        self.branch = os.environ.get("GITHUB_REF_NAME", "local")

        # 1. Namespace Calculation
        if self.branch == "main":
            self.namespace = "prod"
        else:
            # Sanitize branch name for path safety
            clean_branch = self.branch.replace("/", "_").replace(" ", "_")
            self.namespace = f"staging/{clean_branch}"

        self.base_api_url = "https://blob.vercel-storage.com"
        self.headers = (
            {"authorization": f"Bearer {self.token}", "x-api-version": "7"} if self.token else {}
        )

    def _get_remote_path(self, local_filename: str) -> str:
        """Applies namespace prefix to the filename."""
        return f"{self.namespace}/{local_filename}"

    def _list_blob_url_map(self, limit: int = 1000) -> dict[str, str]:
        """List cloud blobs across paginated responses and map pathname to download URL."""
        url_map: dict[str, str] = {}
        cursor: str | None = None
        seen_cursors: set[str] = set()

        while True:
            list_url = f"{self.base_api_url}?limit={limit}"
            if cursor:
                list_url = f"{list_url}&cursor={cursor}"

            list_resp = requests.get(list_url, headers=self.headers, timeout=10)
            list_resp.raise_for_status()
            payload = list_resp.json()
            blobs = payload.get("blobs", [])
            url_map.update(
                {
                    blob["pathname"]: blob["downloadUrl"]
                    for blob in blobs
                    if blob.get("pathname") and blob.get("downloadUrl")
                }
            )

            next_cursor = payload.get("cursor") or payload.get("nextCursor")
            if not next_cursor:
                break
            if next_cursor in seen_cursors:
                logger.error("Repeated blob cursor encountered: %s", next_cursor)
                break

            seen_cursors.add(next_cursor)
            cursor = str(next_cursor)

        return url_map

    def pull_state(self, local_files: list[str]) -> bool:
        """
        Pull listed files from the cloud namespace.
        Falls back to local seeds if files are missing in the cloud (404).
        """
        if not self.is_ci or not self.token:
            logger.info("Local/Non-CI mode: Skipping cloud pull.")
            return True

        logger.info("Initiating cloud state pull for namespace: %s", self.namespace)

        # 1. Fetch current blob list to find URLs
        try:
            # Map path/pathname to downloadUrl.
            # Vercel Blob uses 'pathname' as the original stable identifier.
            url_map = self._list_blob_url_map(limit=1000)
        except Exception as e:
            logger.error(
                "Failed to list cloud blobs: %s. Refusing to continue with stale runtime state.", e
            )
            return False

        for filename in local_files:
            remote_path = self._get_remote_path(filename)
            download_url = url_map.get(remote_path)

            local_path = Path(filename)
            local_path.parent.mkdir(parents=True, exist_ok=True)

            if not download_url:
                logger.warning(
                    "Cloud file miss: %s (404). Using local repository seed.", remote_path
                )
                continue

            try:
                logger.info("Downloading %s from %s", remote_path, download_url)
                file_resp = requests.get(download_url, timeout=30)
                file_resp.raise_for_status()
                with open(local_path, "wb") as f:
                    f.write(file_resp.content)
                logger.info("Successfully RESTORED %s from Cloud.", filename)
            except Exception as e:
                logger.error("Failed to download %s: %s", remote_path, e)
                return False

        return True

    def push_state(self, local_files: list[str]) -> bool:
        """
        Push listed files to the cloud namespace.
        Atomic overwrite strategy (x-add-random-suffix: false).
        """
        if not self.is_ci or not self.token:
            logger.info("Local/Non-CI mode: Skipping cloud push.")
            return True

        logger.info("Initiating cloud state push for %s files...", len(local_files))

        for filename in local_files:
            local_path = Path(filename)
            if not local_path.exists():
                logger.warning("Local file missing, skipping push: %s", filename)
                continue

            with open(local_path, "rb") as f:
                content = f.read()

            self.push_payload(content, filename, is_binary=True)

        return True

    def push_payload(self, payload: dict | bytes, filename: str, is_binary: bool = False) -> bool:
        """
        Push in-memory payload to the cloud namespace.
        """
        if not self.is_ci or not self.token:
            return True

        remote_path = self._get_remote_path(filename)
        put_url = f"{self.base_api_url}/{remote_path}"

        put_headers = self.headers.copy()
        put_headers.update(
            {
                "x-add-random-suffix": "false",
                "x-access": "public",
                "content-type": "application/json; charset=utf-8"
                if not is_binary
                else "application/octet-stream",
            }
        )

        if not is_binary and isinstance(payload, dict):
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        else:
            data = payload

        max_retries = 3
        for attempt in range(max_retries):
            try:
                resp = requests.put(put_url, data=data, headers=put_headers, timeout=30)
                resp.raise_for_status()
                logger.info("Successfully PERSISTED %s to Cloud.", remote_path)
                return True
            except Exception as e:
                logger.error(
                    "Vercel Blob Upload Attempt %d failed for %s: %s", attempt + 1, remote_path, e
                )
                if attempt == max_retries - 1:
                    raise
                time.sleep(2**attempt)

        return False
