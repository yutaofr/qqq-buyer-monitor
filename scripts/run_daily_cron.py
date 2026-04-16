"""
run_daily_cron.py

每日实盘无头守护进程脚本 (Daily Headless Daemon)
用于 Crontab 每天收盘后自动执行。
它将拉取最近 3 年的数据（确保完整的 Burn-in 窗口），前向计算至最新交易日，
最后用中文输出极其明确的持仓状态与 QLD 买卖信号。
"""

import json
import logging
import os
import sys
import warnings
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import requests

from src.liquidity.config import load_config
from src.liquidity.data.panel_builder import build_pit_aligned_panel
from src.liquidity.engine.pipeline import LiquidityPipeline

# 屏蔽第三方库的烦人警告
warnings.filterwarnings("ignore", category=RuntimeWarning)
logging.getLogger("yfinance").setLevel(logging.CRITICAL)
logging.getLogger("src.liquidity").setLevel(logging.CRITICAL)

VERCEL_TOKEN = os.environ.get("VERCEL_BLOB_READ_WRITE_TOKEN")
STATE_URL = "https://blob.vercel-storage.com/qqq_engine_state.json"


def sanitize_for_json(obj):
    """Recursively convert numpy types to standard Python types for JSON serialization."""
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_json(i) for i in obj]
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, (np.int64, np.int32)):
        return int(obj)
    return obj


def fetch_state():
    if not VERCEL_TOKEN:
        return None
    headers = {"Authorization": f"Bearer {VERCEL_TOKEN}"}
    try:
        # List blobs to find the latest state file URL
        res = requests.get(
            "https://blob.vercel-storage.com?prefix=qqq_engine_state", headers=headers
        )
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


def _delete_all_state_blobs(auth_headers: dict) -> int:
    """删除 Vercel Blob 中所有以 qqq_engine_state 为前缀的旧文件，返回删除数量。"""
    list_url = "https://blob.vercel-storage.com?prefix=qqq_engine_state&api-version=7"
    try:
        res = requests.get(list_url, headers=auth_headers)
        res.raise_for_status()
        blobs = res.json().get("blobs", [])
        if not blobs:
            return 0
        # Vercel Blob 批量删除：DELETE with JSON body {"urls": [...]}
        blob_urls = [b["url"] for b in blobs]
        del_res = requests.delete(
            "https://blob.vercel-storage.com?api-version=7",
            headers={**auth_headers, "Content-Type": "application/json"},
            data=json.dumps({"urls": blob_urls}).encode("utf-8"),
        )
        del_res.raise_for_status()
        return len(blob_urls)
    except Exception as e:
        print(f"[警告] 清理旧 Blob 文件失败（不影响本次上传）: {e}")
        return 0


def push_state(state_dict):
    if not VERCEL_TOKEN:
        print("[警告] 环境变量无 VERCEL_BLOB_READ_WRITE_TOKEN，跳过状态落盘。")
        return

    auth_headers = {"Authorization": f"Bearer {VERCEL_TOKEN}"}

    # Step 1: 先删除所有历史快照，防止文件无限堆积
    deleted = _delete_all_state_blobs(auth_headers)
    if deleted > 0:
        print(f"🗑️ 已清理 {deleted} 个历史 Blob 文件。")

    # Step 2: 上传新快照
    # Vercel Blob REST API: PUT /[filename]?api-version=7
    # Body must be raw bytes; Content-Type must be set explicitly.
    upload_url = f"{STATE_URL}?api-version=7"
    upload_headers = {
        **auth_headers,
        "Content-Type": "application/json",
    }
    try:
        clean_state = sanitize_for_json(state_dict)
        payload_bytes = json.dumps(clean_state).encode("utf-8")
        res = requests.put(upload_url, headers=upload_headers, data=payload_bytes)
        res.raise_for_status()
        print(f"✅ 引擎最新物理状态已成功硬入盘至 Vercel 公共云存储。(size={len(payload_bytes)} bytes)")
    except Exception as e:
        print(f"❌ 状态落盘 Vercel 失败: {e}")


def generate_and_send_report(latest_log, latest_date, latest_row, prev_weight):
    """根据状态机日志生成中文报告并推送到 Discord。"""
    if not latest_log:
        print("[警告] 状态机日志为空，跳过报告生成。")
        return

    current_weight = latest_log.get("weight", 0.0)
    qld_alloc = latest_log.get("qld", 0.0)
    qqq_alloc = latest_log.get("qqq", 0.0)
    cash_alloc = latest_log.get("cash", 0.0)

    circuit_triggered = latest_log.get("circuit_breaker", False)
    momentum_lockout = latest_log.get("momentum_lockout", False)

    p_cp = latest_log.get("p_cp", 0.0)
    vol_cap = latest_log.get("vol_guard_cap", 2.0)

    # 兼容 dict 或 Series
    if hasattr(latest_row, "get"):
        qqq_price = latest_row.get("QQQ_price", 0.0)
        qqq_sma = latest_row.get("QQQ_sma200", 0.0)
    else:
        qqq_price = 0.0
        qqq_sma = 0.0

    s_t = latest_log.get("s_t", 0.0)

    # 判定交易动作
    action_msg = "⚪️ 维持现状 (Hold)"

    if circuit_triggered:
        action_msg = "🚨 紧急清仓！底层宏观断裂，全量转为 CASH"
    elif momentum_lockout and prev_weight > 0.0:
        action_msg = "⚠️ 触发趋势大锁 (价格跌破年线)！强制去杠杆，卖出 QLD 退守 QQQ"
    elif current_weight > prev_weight:
        action_msg = "🟢 买入指令！开始增加 QLD 杠杆头寸 (波动率与趋势确认安全)"
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

    def log_print(msg=""):
        print(msg)
        report_lines.append(msg)

    log_print("\n" + "=" * 65)
    log_print(f" 🌀 QQQ流动性循环监测系统 - 每日实务判定 ({pd.to_datetime(latest_date).date()})")
    log_print("=" * 65)

    log_print("\n[物理引擎传感器底噪]")
    log_print(f" 👉 综合裂变概率 (P_cp) : {p_cp * 100:.2f}%")
    log_print(f" 👉 平滑压力指数 (S_t)  : {s_t:.3f} (阈值 0.7 触发清仓)")
    log_print(f" 👉 波动率护盾上限      : {vol_cap:.2f}x 杠杆限制")
    trend_icon = "🟢" if qqq_price >= qqq_sma else "🔴"
    log_print(f" 👉 QQQ 趋势与年线对比  : ${qqq_price:.2f} / ${qqq_sma:.2f} {trend_icon}")

    log_print("\n[资金执行层架构状态]")
    if circuit_triggered:
        log_print(" 💥 熔断级警报 [ACTIVE]: 物理底线已被击穿，禁止任何股票暴露！")
    elif momentum_lockout:
        log_print(" 🔒 趋势锁死 [ACTIVE]: 运行在深水区 (SMA-200以下)，最高权限限制为 1.0 (QQQ)！")
    else:
        log_print(" 🟢 巡航模式: 未触发熔断与大锁，贝叶斯判定享有完全杠杆调度权。")

    log_print("\n[🎯 最终系统仓位分配]")
    log_print(f" • [QLD] TQQQ/两倍杠杆: {qld_alloc * 100:.1f}%")
    log_print(f" • [QQQ] 纳指基础持仓:   {qqq_alloc * 100:.1f}%")
    log_print(f" • [USD] 纯美元现金:     {cash_alloc * 100:.1f}%")

    log_print("\n⚡ QLD 买卖操作指示:")
    log_print(f"   >> {action_msg}")
    log_print("=" * 65 + "\n")

    # Send to Discord if webhook is configured
    discord_url = os.environ.get("ALERT_WEBHOOK_URL")
    if discord_url:
        payload = {"content": f"```text\n{chr(10).join(report_lines)}\n```"}
        try:
            resp = requests.post(discord_url, json=payload)
            resp.raise_for_status()
            print("Successfully pushed report to Discord.")
        except Exception as e:
            print(f"Failed to send webhook to Discord: {e}")


def main():
    config = load_config()
    pipeline = LiquidityPipeline(config, burn_in=252)

    # 1. 下载前一天的记忆快照，防御 FRED 回溯修订 (PIT 断点续传)
    print("正在连接 Vercel 寻址并唤醒前置量子阵列状态...")
    cloud_state = fetch_state()

    latest_log = {}
    latest_date = None
    latest_row = {}
    prev_weight = 0.0
    panel = None

    if cloud_state:
        pipeline.load_state(cloud_state["engine_state"])
        last_date = pd.to_datetime(cloud_state["last_timestamp"])
        start_date = (last_date + timedelta(days=1)).strftime("%Y-%m-%d")
        print(f"✅ 状态唤醒成功！记忆锁定至: {last_date.date()}")
        # 从快照恢复最后的上下文（用于 skip 模式下的报告生成）
        latest_log = cloud_state.get("latest_log", {})
        latest_date = last_date
        latest_row = cloud_state.get("latest_row", {})
        prev_weight = cloud_state.get("prev_weight", 0.0)
    else:
        print("⚠️ 未找到云端快照，触发灾备模式 (Cold Start): 拉取最近 3 年数据重建状态...")
        start_date = (datetime.now() - timedelta(days=365 * 3)).strftime("%Y-%m-%d")

    end_date = datetime.now().strftime("%Y-%m-%d")
    should_skip_calc = start_date > end_date

    if should_skip_calc:
        if cloud_state:
            print(f"✅ 今日 ({end_date}) 的观测数据此前已被吸收，进入直接报告模式。")
        else:
            print("❌ 严重错误: 既无云端状态也无新数据可跑。")
            sys.exit(1)
    else:
        print(f"正在拉取实盘市场数据 [{start_date} 到 {end_date}]...")
        try:
            panel, c_rets = build_pit_aligned_panel(start_date, end_date, config=config)
        except Exception as e:
            print(f"\n[错误] 数据拉取或构建失败: {e}")
            sys.exit(1)

        if panel.empty:
            print(f"✅ 今日 ({end_date}) 的观测数据尚未就绪或为非交易日，进入直接报告模式。")
        else:
            rets_matrix = c_rets.to_numpy(dtype=float)

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

                weight, log_diag = pipeline.step(timestamp=date, raw_obs=obs)
                latest_log = log_diag
                latest_date = date
                latest_row = row

            # 4. 绝对落盘 (Bit-Identical Checkpointing)
            new_state = {
                "last_timestamp": str(latest_date),
                "engine_state": pipeline.dump_state(),
                "latest_log": latest_log,
                "latest_row": latest_row.to_dict() if hasattr(latest_row, "to_dict") else latest_row,
                "prev_weight": prev_weight,
            }
            push_state(new_state)

    # 5. 信号解析与中文渲染
    generate_and_send_report(latest_log, latest_date, latest_row, prev_weight)


if __name__ == "__main__":
    main()
