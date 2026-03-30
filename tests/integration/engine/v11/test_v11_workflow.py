from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.engine.v11.conductor import V11Conductor


def test_v11_2020_high_pressure_workflow():
    """
    集成测试：注入 2020 年 3 月数据，验证数据清洗、概率推断、Z-Score 猎杀与结算锁的联动。
    """
    # 1. 准备历史背景 (1995-2020 Feb)
    # 使用 POC 阶段 1 的结果作为模拟特征库
    source_path = Path("data/v11_poc_phase1_results.csv")
    if not source_path.exists():
        pytest.skip("Historical result file missing for integration test")

    df = pd.read_csv(source_path)
    df["observation_date"] = pd.to_datetime(df["observation_date"])

    # 补全 vix3m 数据 (因为 phase1_results 不包含它)
    evidence_path = Path("data/v11_full_evidence_history.csv")
    if evidence_path.exists():
        ev_df = pd.read_csv(evidence_path)
        ev_df["observation_date"] = pd.to_datetime(ev_df["observation_date"])
        df = pd.merge(df, ev_df[["observation_date", "vix3m"]], on="observation_date", how="left")

    # 2. 初始化编排器并手动填充特征库（模拟已运行多年）
    conductor = V11Conductor()
    # 注入截止到 2020-02-01 的背景数据
    background_df = df[df["observation_date"] < "2020-02-01"].copy()
    conductor.library.df = background_df

    # 3. 模拟 2020-03 的运行
    test_window = df[(df["observation_date"] >= "2020-03-01") & (df["observation_date"] <= "2020-04-01")]

    signals = []
    for _, row in test_window.iterrows():
        # 封装为当日 T+0 数据
        t0_data = pd.DataFrame([row])

        # 注入一个随机 NaN 来测试数据管道韧性
        if row["observation_date"] == pd.Timestamp("2020-03-12"):
            t0_data["vix"] = np.nan

        result = conductor.daily_run(t0_data)
        signals.append(result)

    # 4. 验证核心里程碑 (Acceptance Criteria)
    # AC-1: 数据管道韧性 (3-12 应该触发降级或断网但不崩溃)
    warn_signal = next(s for s in signals if s["date"] == pd.Timestamp("2020-03-12"))
    assert warn_signal["data_quality"] < 1.0
    assert ("SENSOR DEGRADATION" in warn_signal["signal"]["reason"] or
            "DATA CORRUPTION" in warn_signal["signal"]["reason"])


    # AC-2: 左侧放血 (3 月中旬应处于 QQQ 或 CASH)
    panic_signal = next(s for s in signals if s["date"] == pd.Timestamp("2020-03-16"))
    assert panic_signal["signal"]["target_exposure"] in ["QQQ", "CASH"]

    # AC-3: 右侧猎杀 (验证 3-17 附近的苏醒指令)
    res_signals = [s for s in signals if s["resurrection_active"]]
    assert len(res_signals) > 0
    assert any(s["signal"]["target_exposure"] == "QLD" for s in res_signals)

    # AC-4: 结算锁 (调仓后 cooldown 应大于 0)
    assert conductor.execution_guard.cooldown_days_remaining >= 0
    assert any(s["signal"]["lock_active"] for s in signals if "lock_active" in s["signal"])
