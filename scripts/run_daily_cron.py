"""
run_daily_cron.py

每日实盘无头守护进程脚本 (Daily Headless Daemon)
用于 Crontab 每天收盘后自动执行。
它将拉取最近 3 年的数据（确保完整的 Burn-in 窗口），前向计算至最新交易日，
最后用中文输出极其明确的持仓状态与 QLD 买卖信号。
"""

import sys
import os
import json
import logging
import warnings
import requests
from datetime import datetime, timedelta

import pandas as pd
import numpy as np

from src.liquidity.data.panel_builder import build_pit_aligned_panel
from src.liquidity.config import load_config
from src.liquidity.engine.pipeline import LiquidityPipeline

# 屏蔽第三方库的烦人警告
warnings.filterwarnings("ignore", category=RuntimeWarning)
logging.getLogger("yfinance").setLevel(logging.CRITICAL)
logging.getLogger("src.liquidity").setLevel(logging.CRITICAL)

VERCEL_TOKEN = os.environ.get("VERCEL_BLOB_READ_WRITE_TOKEN")
STATE_URL = "https://blob.vercel-storage.com/qqq_engine_state.json"

def fetch_state():
    if not VERCEL_TOKEN:
        return None
    headers = {"Authorization": f"Bearer {VERCEL_TOKEN}"}
    try:
        # List blobs to find the latest state file URL
        res = requests.get("https://blob.vercel-storage.com?prefix=qqq_engine_state", headers=headers)
        if res.status_code == 200:
            blobs = res.json().get("blobs", [])
            if blobs:
                # Sort by uploadedAt descending
                latest_blob = max(blobs, key=lambda x: x["uploadedAt"])
                url = latest_blob["url"]
                
                # Download the actual JSON file
                state_res = requests.get(url)
                if state_res.status_code == 200:
                    return state_res.json()
    except Exception as e:
        print(f"[警告] 无法拉取云端状态: {e}")
    return None

def push_state(state_dict):
    if not VERCEL_TOKEN:
        print("[警告] 环境变量无 VERCEL_BLOB_READ_WRITE_TOKEN，跳过状态落盘。")
        return
    headers = {
        "Authorization": f"Bearer {VERCEL_TOKEN}",
        "x-api-version": "7"
    }
    try:
        res = requests.put(STATE_URL, headers=headers, json=state_dict)
        res.raise_for_status()
        print("✅ 引擎最新物理状态已成功硬入盘至 Vercel 公共云存储。")
    except Exception as e:
        print(f"❌ 状态落盘 Vercel 失败: {e}")

def main():
    config = load_config()
    pipeline = LiquidityPipeline(config, burn_in=252)

    # 1. 下载前一天的记忆快照，防御 FRED 回溯修订 (PIT 断点续传)
    print("正在连接 Vercel 寻址并唤醒前置量子阵列状态...")
    cloud_state = fetch_state()
    
    if cloud_state:
        pipeline.load_state(cloud_state["engine_state"])
        last_date = pd.to_datetime(cloud_state["last_timestamp"])
        start_date = (last_date + timedelta(days=1)).strftime("%Y-%m-%d")
        print(f"✅ 状态唤醒成功！记忆锁定至: {last_date.date()}")
    else:
        print("⚠️ 未找到云端快照，触发灾备模式 (Cold Start): 拉取最近 3 年数据重建状态...")
        start_date = (datetime.now() - timedelta(days=365 * 3)).strftime("%Y-%m-%d")

    end_date = datetime.now().strftime("%Y-%m-%d")
    
    if start_date >= end_date:
        print(f"✅ 今日 ({end_date}) 的观测数据此前已被吸收，无需重复计算。")
        sys.exit(0)
        
    print(f"正在拉取实盘市场数据 [{start_date} 到 {end_date}]...")
    
    try:
        panel, c_rets = build_pit_aligned_panel(start_date, end_date, config=config)
    except Exception as e:
        print(f"\n[错误] 数据拉取或构建失败: {e}")
        sys.exit(1)
        
    if panel.empty:
        print("\n[错误] 获取到的数据面板为空，请检查网络或 API。")
        sys.exit(1)

    rets_matrix = c_rets.to_numpy(dtype=float)
    
    prev_weight = 0.0
    latest_log = {}
    latest_date = None
    latest_row = None

    # 3. 极速推进事件流
    for i, (date, row) in enumerate(panel.iterrows()):
        
        # 记录前一天的 QLD 权重，用于判断当天的买卖动作
        if i == len(panel) - 1:
            prev_weight = pipeline._alloc.get_weight()

        obs = {
            "vix": float(row["VIXCLS"]),
            "walcl": float(row["WALCL"]),
            "rrp": float(row["RRPONTSYD"]),
            "tga": float(row["WTREGEN"]),
            "sofr": float(row["SOFR"]),
            "constituent_returns": rets_matrix[i, :],
            "qqq_price": float(row.get("QQQ_price", 0.0)),
            "qqq_sma200": float(row.get("QQQ_sma200", 0.0)),
        }
        
        weight, log = pipeline.step(timestamp=date, raw_obs=obs)
        latest_log = log
        latest_date = date
        latest_row = row

    # 4. 绝对落盘 (Bit-Identical Checkpointing)
    new_state = {
        "last_timestamp": str(latest_date),
        "engine_state": pipeline.dump_state()
    }
    push_state(new_state)

    # 4. 信号解析与中文渲染
    current_weight = latest_log.get("weight", 0.0)
    qld_alloc = latest_log.get("qld", 0.0)
    qqq_alloc = latest_log.get("qqq", 0.0)
    cash_alloc = latest_log.get("cash", 0.0)
    
    circuit_triggered = latest_log.get("circuit_breaker", False)
    momentum_lockout = latest_log.get("momentum_lockout", False)
    
    p_cp = latest_log.get("p_cp", 0.0)
    vol_cap = latest_log.get("vol_guard_cap", 2.0)
    qqq_price = latest_row.get("QQQ_price", 0.0)
    qqq_sma = latest_row.get("QQQ_sma200", 0.0)
    s_t = latest_log.get("s_t", 0.0)

    # 判定交易动作
    action_msg = "⚪️ 维持现状 (Hold)"
    
    if circuit_triggered:
        action_msg = "🚨 紧急清仓！底层宏观断裂，全量转为 CASH"
    elif momentum_lockout and prev_weight > 0.0:
        action_msg = "⚠️ 触发趋势大锁 (价格跌破年线)！强制去杠杆，卖出 QLD 退守 QQQ"
    elif current_weight > prev_weight:
        action_msg = f"🟢 买入指令！开始增加 QLD 杠杆头寸 (波动率与趋势确认安全)"
    elif current_weight < prev_weight:
        if current_weight == 0.0:
            action_msg = "🔴 降仓指令！宏观不确定性增加，完全清空 QLD 退回 QQQ"
        else:
            action_msg = "🟡 减仓指令！压力上升，正在降低 QLD 的暴露敞口"
    elif current_weight > 0.0:
        action_msg = "🔵 继续持有 QLD (满载杠杆运行中)"
    elif current_weight == 0.0 and cash_alloc == 0.0:
        action_msg = "🛡️ 继续持有 QQQ (底部摩擦中，暂不解封杠杆)"
        
    report_lines = []
    def log(msg=""):
        print(msg)
        report_lines.append(msg)

    log("\n" + "=" * 65)
    log(f" 🌀 QQQ流动性循环监测系统 - 每日实盘判定 ({latest_date.date()})")
    log("=" * 65)
    
    log("\n[物理引擎传感器底噪]")
    log(f" 👉 综合裂变概率 (P_cp) : {p_cp*100:.2f}%")
    log(f" 👉 平滑压力指数 (S_t)  : {s_t:.3f} (阈值 0.7 触发清仓)")
    log(f" 👉 波动率护盾上限      : {vol_cap:.2f}x 杠杆限制")
    trend_icon = "🟢" if qqq_price >= qqq_sma else "🔴"
    log(f" 👉 QQQ 趋势与年线对比  : ${qqq_price:.2f} / ${qqq_sma:.2f} {trend_icon}")

    log("\n[资金执行层架构状态]")
    if circuit_triggered:
        log(" 💥 熔断级警报 [ACTIVE]: 物理底线已被击穿，禁止任何股票暴露！")
    elif momentum_lockout:
        log(" 🔒 趋势锁死 [ACTIVE]: 运行在深水区 (SMA-200以下)，最高权限限制为 1.0 (QQQ)！")
    else:
        log(" 🟢 巡航模式: 未触发熔断与大锁，贝叶斯判定享有完全杠杆调度权。")

    log("\n[🎯 最终系统仓位分配]")
    log(f" • [QLD] TQQQ/两倍杠杆: {qld_alloc * 100:.1f}%")
    log(f" • [QQQ] 纳指基础持仓:   {qqq_alloc * 100:.1f}%")
    log(f" • [USD] 纯美元现金:     {cash_alloc * 100:.1f}%")

    log(f"\n⚡ QLD 买卖操作指示:")
    log(f"   >> {action_msg}")
    log("=" * 65 + "\n")

    # Send to Discord if webhook is configured
    discord_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if discord_url:
        payload = {
            "content": f"```text\n{chr(10).join(report_lines)}\n```"
        }
        try:
            resp = requests.post(discord_url, json=payload)
            resp.raise_for_status()
            print("Successfully pushed report to Discord.")
        except Exception as e:
            print(f"Failed to send webhook to Discord: {e}")

if __name__ == "__main__":
    main()
