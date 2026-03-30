import pandas as pd
import pytest
from src.engine.v11.conductor import V11Conductor
from src.engine.v11.utils.memory_booster import SovereignMemoryBooster

def test_v11_2020_high_pressure_workflow():
    """
    集成测试：利用 DNA 自愈能力注入 2020 年高压数据，验证全链路联动。
    """
    # 1. 确保核心记忆已初始化 (2010-2024)
    booster = SovereignMemoryBooster()
    booster.ensure_baseline(force=True)
    
    # 2. 实例化 Conductor (它会自动加载 2010-2024 记忆并进行 JIT 训练)
    conductor = V11Conductor()

    # 3. 准备 2020 年 3 月的测试窗口数据 (从刚刚生成的 baseline 中提取)
    macro_df = pd.read_csv("data/macro_historical_dump.csv", parse_dates=["observation_date"]).set_index("observation_date")
    test_window = macro_df[(macro_df.index >= "2020-03-01") & (macro_df.index <= "2020-05-01")]

    signals = []
    for date, row in test_window.iterrows():
        # 封装为当日 T+0 数据
        t0_data = pd.DataFrame([row])
        t0_data.index = [date]
        t0_data.index.name = "observation_date"

        # 注入一个随机 NaN 来测试数据管道韧性
        if date == pd.Timestamp("2020-03-12"):
            t0_data["credit_spread_bps"] = float('nan')

        result = conductor.daily_run(t0_data)
        
        # 模拟至少触发一次调仓以验证结算锁
        if date == test_window.index[0]:
             conductor.beta_mapper.current_beta = 0.0
        
        signals.append(result)

    # AC-1: 数据管道韧性 (3-12 数据质量应下降)
    warn_signal = next(s for s in signals if pd.to_datetime(s["date"]) == pd.Timestamp("2020-03-12"))
    assert warn_signal["data_quality"] < 1.0

    # AC-2: 风险识别 (3月中旬应对应高压环境)
    panic_signal = next(s for s in signals if pd.to_datetime(s["date"]) == pd.Timestamp("2020-03-16"))
    # 在 BUST 概率高时，Beta 应受到压制
    assert panic_signal["target_beta"] <= 1.0

    # AC-3: 右侧苏醒 (验证 2020 年 4 月后的 Recovery 状态)
    recovery_signals = [s for s in signals if s["probabilities"].get("RECOVERY", 0) > 0.3]
    assert len(recovery_signals) > 0

    # AC-4: 结算锁 (验证 cooldown 逻辑)
    assert any(s["signal"]["lock_active"] for s in signals)
