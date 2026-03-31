from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from src.output.web_exporter import export_feature_library_to_blob


@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("VERCEL_BLOB_READ_WRITE_TOKEN", "fake-token")

def test_export_feature_library_to_blob_uses_cloud_bridge(mock_env):
    """验证上传逻辑：通过 CloudPersistenceBridge 执行。"""
    with patch("src.store.cloud_manager.CloudPersistenceBridge.push_payload") as mock_push:
        mock_push.return_value = True

        # 创建临时测试文件
        test_csv = Path("data/v11_feature_library.csv")
        test_csv.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame({"observation_date": ["2026-03-30"], "val": [1]}).to_csv(test_csv, index=False)

        success = export_feature_library_to_blob(library_path=str(test_csv))

        assert success is True
        assert mock_push.call_count == 1
        args, kwargs = mock_push.call_args
        assert args[1] == "v11_feature_library.csv"
