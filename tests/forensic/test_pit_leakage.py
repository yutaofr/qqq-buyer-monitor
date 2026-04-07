

import pandas as pd


def test_pit_leakage():
    df = pd.read_csv("data/macro_historical_dump.csv")
    df['observation_date'] = pd.to_datetime(df['observation_date'])
    df['effective_date'] = pd.to_datetime(df['effective_date'])

    # 1. 检查有效日期永远不早于观察日期
    leakage = df[df['effective_date'] < df['observation_date']]
    if not leakage.empty:
        print(f"FAILED: Found {len(leakage)} rows where effective_date < observation_date")
        print(leakage[['observation_date', 'effective_date']].head())
    else:
        print("PASSED: effective_date >= observation_date for all rows.")

    # 2. 检查月频数据的滞后 (30 BDay)
    # 对于 core_capex_mm 和 erp_ttm_pct
    # 我们检查是否有任何列在 effective_date 之前就发生了变化（非 NaN）

    print("\nAuditing Core Capex & ERP PIT Lags...")

    # 验证逻辑：对每一个 observation_date，其对应的值只能在 effective_date 时刻及之后出现在最终数据集的有效视图中
    # 这里我们直接检查 dump.csv 中的对应行。
    # 实际上 dump.csv 是以 effective_date 为主轴生成的 daily 视图（见 historical_macro_builder.py）

    # 我们找一个具体的危机点：2020-03
    # 2020-03-31 的观察数据
    # 它的有效日期应该是 2020-03-31 + 30 BDay ~= 2020-05-12
    # 我们检查 2020-04-15 这一行，它的 erp_ttm_pct 应该等于 2020-02-29 的观察值，而不是 2020-03-31 的。

    # 查找 2月和3月的样本观测值（我们假设它们在原始数据中是不同的）
    # 实际上我们可以检查 df 中值的变化点
    df_sorted = df.sort_values('observation_date')

    # 检查 erp_ttm_pct 的变化点
    df_erp_changes = df_sorted[df_sorted['erp_ttm_pct'].diff() != 0]
    # 如果观测日期和有效日期一致，则 diff 会在月初发生。
    # 如果有 30 BDay 滞后，则 diff 会在月中发生。

    for i in range(1, min(10, len(df_erp_changes))):
        obs_date = df_erp_changes.iloc[i]['observation_date']
        # 月度数据通常在月底观测
        if obs_date.day > 10: # 排除月初 ffill 带来的变动
             # 检查这个变动点落在哪里
             print(f"Value change detected at {obs_date.date()}, value={df_erp_changes.iloc[i]['erp_ttm_pct']:.4f}")

if __name__ == "__main__":
    test_pit_leakage()
