import numpy as np
import pandas as pd

from src.engine.v11.signal.data_degradation_pipeline import (
    DataDegradationPipeline,
    SignalDegradationOverrider,
)


def test_data_degradation_pipeline_clean():
    pipeline = DataDegradationPipeline()

    # 正常数据
    df = pd.DataFrame({
        "vix": [15.0, 16.0],
        "vix3m": [18.0, 19.0],
        "qqq_close": [300.0, 305.0],
        "credit_spread_bps": [400.0, 410.0]
    })

    clean_df, quality = pipeline.scrub_and_score(df)
    assert quality == 1.0
    assert not clean_df.isna().any().any()

def test_data_degradation_pipeline_shadow_proxy():
    pipeline = DataDegradationPipeline()

    # VIX3M 缺失，预期触发 VIX * 0.9 影子代理
    df = pd.DataFrame({
        "vix": [20.0, 30.0],
        "vix3m": [22.0, np.nan],
        "qqq_close": [300.0, 290.0],
        "credit_spread_bps": [400.0, 450.0]
    })

    clean_df, quality = pipeline.scrub_and_score(df)

    # v11 收敛口径：缺失并被代理修复比“单纯缺失”更差，质量分需要额外折损
    assert quality < 0.75
    # 但是 clean_df 里应该已经被 shadow proxy 填补了 (30.0 * 0.9 = 27.0)
    assert clean_df.iloc[-1]["vix3m"] == 27.0

def test_data_degradation_pipeline_ghost_print_and_spike():
    pipeline = DataDegradationPipeline()

    # VIX 幽灵报价 (5000) 和负值 (-5)
    df = pd.DataFrame({
        "vix": [15.0, 16.0, 15.5, 16.2, 15.8, 5000.0, -5.0],
        "vix3m": [18.0]*7,
        "qqq_close": [300.0]*7,
        "credit_spread_bps": [400.0]*7
    })

    clean_df, quality = pipeline.scrub_and_score(df)

    # 最后一行 (-5.0) 会被清理为 NaN，然后由前一日 (5000.0，但也被清理为 NaN) 的再前一日 (15.8) 填充？
    # 实际上 5000 和 -5 都会被设为 NaN。
    # 根据 ffill(limit=1)，索引 5 (5000) 会被 15.8 填补。
    # 索引 6 (-5) 会因为超过 limit=1 而保持 NaN。
    assert pd.isna(clean_df.iloc[-1]["vix"])
    # 只要有 NaN，质量分归零 (或者根据缺失率计算，最后一行的 vix 和衍生的 vix3m 都可能受影响)
    assert quality == 0.0

def test_signal_degradation_overrider():
    overrider = SignalDegradationOverrider(leverage_ban_threshold=0.8, blackout_threshold=0.5)

    original_signal = {"target_exposure": "QLD", "reason": "BULL MARKET", "action_required": False}

    # 1. 质量完美 -> 信号保持
    res1 = overrider.enforce_degradation(original_signal, 1.0)
    assert res1["target_exposure"] == "QLD"

    # 2. 质量轻微受损 (0.75) -> 剥夺杠杆
    res2 = overrider.enforce_degradation(original_signal, 0.75)
    assert res2["target_exposure"] == "QQQ"
    assert res2["action_required"] is True
    assert "LEVERAGE DISABLED" in res2["reason"]

    # 3. 质量严重受损 (0.0) -> 强制物理断网 (CASH)
    res3 = overrider.enforce_degradation(original_signal, 0.0)
    assert res3["target_exposure"] == "CASH"
    assert res3["action_required"] is True
    assert "FORCED CASH" in res3["reason"]

    # 4. 如果本来就是 CASH，断网时保持 CASH
    safe_signal = {"target_exposure": "CASH", "reason": "BEAR MARKET"}
    res4 = overrider.enforce_degradation(safe_signal, 0.0)
    assert res4["target_exposure"] == "CASH"


def test_data_degradation_pipeline_penalizes_anomalous_proxy_usage():
    pipeline = DataDegradationPipeline()

    df = pd.DataFrame({
        "vix": [15.0] * 24 + [5000.0],
        "vix3m": [18.0] * 25,
        "qqq_close": list(range(100, 125)),
        "credit_spread_bps": [400.0] * 25,
    })

    clean_df, quality = pipeline.scrub_and_score(df)

    assert quality < 1.0
    assert clean_df.iloc[-1]["vix"] > 0.0
    assert "vix" in pipeline.last_audit["anomalies"]
    assert "vix" in pipeline.last_audit["proxy_fields"]
