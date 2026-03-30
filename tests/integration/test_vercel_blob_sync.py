
import pandas as pd
import pytest
import os
from pathlib import Path
from unittest.mock import MagicMock, patch
import io

from src.output.web_exporter import export_feature_library_to_blob
from src.engine.v11.core.feature_library import FeatureLibraryManager

@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("VERCEL_BLOB_READ_WRITE_TOKEN", "fake-token")

def test_export_feature_library_to_blob_retry_logic(mock_env):
    """验证上传逻辑：包含标头校验与重试机制。"""
    with patch("src.output.web_exporter.requests.put") as mock_put:
        # 模拟前两次失败，第三次成功
        m1 = MagicMock()
        m1.status_code = 503
        m1.text = "Service Unavailable"
        
        m2 = MagicMock()
        m2.status_code = 200
        
        mock_put.side_effect = [m1, m2]
        
        # 创建临时测试文件
        test_csv = Path("data/v11_feature_library.csv")
        if not test_csv.exists():
            pd.DataFrame({"observation_date": ["2026-03-30"], "val": [1]}).to_csv(test_csv, index=False)
            
        success = export_feature_library_to_blob(library_path=str(test_csv))
        
        assert success is True
        assert mock_put.call_count == 2
        args, kwargs = mock_put.call_args
        assert kwargs["headers"]["authorization"] == "Bearer fake-token"
        assert kwargs["headers"]["x-add-random-suffix"] == "false"

def test_feature_library_manager_cloud_pull_and_merge(mock_env, tmp_path):
    """验证拉取逻辑：确保云端数据能正确与本地合并且去重。"""
    # 1. 准备本地数据
    local_path = tmp_path / "local_lib.csv"
    pd.DataFrame({
        "observation_date": ["2026-03-01", "2026-03-02"],
        "val": [10, 20]
    }).to_csv(local_path, index=False)
    
    # 2. 模拟云端数据 (其中 3-02 是重叠的，3-03 是新增的)
    cloud_content = pd.DataFrame({
        "observation_date": ["2026-03-02", "2026-03-03"],
        "val": [99, 30] # 3-02 的云端数据较新
    }).to_csv(index=False).encode("utf-8")
    
    with patch("src.engine.v11.core.feature_library.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = cloud_content
        mock_get.return_value = mock_resp
        
        manager = FeatureLibraryManager(storage_path=str(local_path), persist=False)
        
        # 3. 校验合并结果
        # 应该有 3 行数据：3-01, 3-02, 3-03
        assert len(manager.df) == 3
        # 校验去重逻辑 (keep='last' 确保了 3-02 取的是云端值 99)
        val_02 = manager.df[manager.df["observation_date"] == "2026-03-02"]["val"].iloc[0]
        assert val_02 == 99

def test_feature_library_manager_fallback_on_failure(mock_env, tmp_path):
    """验证自愈逻辑：云端 404 时应无缝使用本地数据。"""
    local_path = tmp_path / "local_lib.csv"
    pd.DataFrame({"observation_date": ["2026-03-01"], "val": [1]}).to_csv(local_path, index=False)
    
    with patch("src.engine.v11.core.feature_library.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp
        
        manager = FeatureLibraryManager(storage_path=str(local_path), persist=False)
        
        # 虽云端失败，但本地数据应加载成功
        assert len(manager.df) == 1
        assert manager.df.iloc[0]["val"] == 1
