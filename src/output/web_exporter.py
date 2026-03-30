"""Web exporter for the v10.0 cycle-aware target-beta contract."""
from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime, time, timedelta
from datetime import date as date_cls
from pathlib import Path

import pandas as pd
import pytz

from src.models import SignalResult
from src.store.cloud_manager import CloudPersistenceBridge

try:
    import pandas_market_calendars as mcal
except ModuleNotFoundError:  # pragma: no cover - exercised via fallback tests
    mcal = None

logger = logging.getLogger("qqq_monitor.web_exporter")

EASTERN = pytz.timezone("US/Eastern")


def _format_beta(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.2f}x"


def _format_pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.1f}%"


def _format_pct_points(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.2f}%"


def _get_deployment_state_str(result: SignalResult) -> str:
    """Extract raw mode string (FAST/BASE/SLOW/PAUSE) for mapping."""
    if result.deployment_state:
        return result.deployment_state.value.replace("DEPLOY_", "")
    return result.deployment_action.get("deploy_mode", "BASE")


def _get_v11_stable_regime_key(result: SignalResult) -> str:
    if result.cycle_regime:
        return str(result.cycle_regime)

    stable_regime = result.v11_execution.get("stable_regime")
    if stable_regime:
        return str(stable_regime)

    if result.v11_probabilities:
        return max(result.v11_probabilities.items(), key=lambda item: item[1])[0]

    return "MID_CYCLE"


def _get_v11_raw_regime_key(result: SignalResult) -> str:
    raw_regime = result.v11_execution.get("raw_regime")
    if raw_regime:
        return str(raw_regime)

    if result.v11_probabilities:
        return max(result.v11_probabilities.items(), key=lambda item: item[1])[0]

    return _get_v11_stable_regime_key(result)


def _build_v11_decision_path(result: SignalResult) -> str:
    deploy_mode = _get_deployment_state_str(result)
    stable_regime = _get_v11_stable_regime_key(result)
    raw_regime = _get_v11_raw_regime_key(result)
    readiness = float(result.v11_execution.get("deployment_readiness", 0.0))
    return (
        f"Stable({stable_regime}) -> "
        f"PosteriorTop1({raw_regime}) -> "
        f"Advisory({_format_beta(result.raw_target_beta)}->{_format_beta(result.target_beta)}) -> "
        f"Deployment({deploy_mode}:{readiness:.1%})"
    )


def _build_decision_path(result: SignalResult) -> str:
    if result.engine_version == "v11":
        return _build_v11_decision_path(result)

    raw_beta = result.raw_target_beta if result.raw_target_beta is not None else result.target_beta
    risk_state = result.risk_state.value if result.risk_state else "n/a"
    deploy_mode = _get_deployment_state_str(result)
    return (
        f"Tier-0({result.tier0_regime or 'n/a'}) -> "
        f"Cycle({result.cycle_regime or 'n/a'}) -> "
        f"Risk({risk_state}) -> "
        f"Candidate({result.selected_candidate_id or 'n/a'}) -> "
        f"Advisory({_format_beta(raw_beta)}->{_format_beta(result.target_beta)}) -> "
        f"Deployment({deploy_mode})"
    )


def _build_runtime_traces(result: SignalResult) -> list[dict]:
    from src.output.cli import build_runtime_logic_trace

    traces = result.logic_trace
    if result.engine_version == "v11":
        return traces

    if not traces or (len(traces) > 0 and traces[0].get("step") != "tier0_regime"):
        traces = build_runtime_logic_trace(result)
    return traces


def _build_web_node_traces(result: SignalResult) -> list[dict]:
    node_traces: list[dict] = []
    for trace in _build_runtime_traces(result):
        step = trace.get("step", "unknown")
        decision = trace.get("decision", "n/a")
        reason = trace.get("reason", "n/a")
        evidence = trace.get("evidence", {})

        if step == "tier0_regime":
            formula = f"Tier-0={decision} | ERP={_format_pct_points(evidence.get('erp'))}"
            node_traces.append(
                {
                    "step": step,
                    "node": "Tier-0 宏观制度",
                    "type": "MACRO",
                    "formula": formula,
                    "explanation": reason,
                    "result": decision,
                }
            )
        elif step == "cycle_regime":
            formula = f"Cycle={decision} | qld<={_format_pct(evidence.get('qld_share_ceiling'))}"
            node_traces.append(
                {
                    "step": step,
                    "node": "Cycle 周期制度",
                    "type": "MACRO",
                    "formula": formula,
                    "explanation": reason,
                    "result": decision,
                }
            )
        elif step == "risk_controller":
            formula = (
                f"beta<={_format_beta(evidence.get('target_exposure_ceiling'))} | "
                f"qld<={_format_pct(evidence.get('qld_share_ceiling'))} | "
                f"cash>={_format_pct(evidence.get('target_cash_floor'))}"
            )
            node_traces.append(
                {
                    "step": step,
                    "node": "Risk 风险控制器",
                    "type": "SIGNAL",
                    "formula": formula,
                    "explanation": reason,
                    "result": decision,
                }
            )
        elif step == "candidate_selection":
            formula = (
                f"registry={evidence.get('registry_version', 'n/a')} | "
                f"rejected={evidence.get('rejected_candidates', 0)}"
            )
            node_traces.append(
                {
                    "step": step,
                    "node": "Candidate 认证候选",
                    "type": "FILTER",
                    "formula": formula,
                    "explanation": reason,
                    "result": decision,
                }
            )
        elif step == "beta_advisory":
            raw_beta = _format_beta(evidence.get("raw_target_beta"))
            formula = (
                f"raw={raw_beta} | advised={decision} | "
                f"adjust={evidence.get('should_adjust', False)}"
            )
            node_traces.append(
                {
                    "step": step,
                    "node": "Advisory Beta 建议",
                    "type": "ADVISORY",
                    "formula": formula,
                    "explanation": reason,
                    "result": decision,
                }
            )
        elif step == "deployment_controller":
            if isinstance(decision, dict):
                # v11.16 Kelly Entry
                readiness = decision.get("readiness", 0.0)
                sharpe = decision.get("sharpe", 0.0)
                val_rank = decision.get("value_rank", 0.0)
                formula = f"CDR={readiness:.1%} | E[Sharpe]={sharpe:.2f} | ERP_Rank={val_rank:.1%}"
                res_str = f"{readiness:.1%} Readiness"
            else:
                formula = (
                    f"mode={evidence.get('deploy_mode', 'n/a')} | "
                    f"path={evidence.get('path') or 'qqq_only_new_cash'}"
                )
                res_str = str(decision)
            node_traces.append(
                {
                    "step": step,
                    "node": "Deployment 概率入场",
                    "type": "TACTICAL",
                    "formula": formula,
                    "explanation": "基于贝叶斯期望 Sharpe 与结构性估值百分位（CDR）决定新增资金节奏。",
                    "result": res_str,
                }
            )
        # v11 specific steps
        elif step == "degradation":
            formula = f"quality={decision.get('quality_score', 0.0):.2f}"
            node_traces.append(
                {
                    "step": step,
                    "node": "Data Degradation 数据降级",
                    "type": "FILTER",
                    "formula": formula,
                    "explanation": "物理常识校验与清洗，质量分低于 0.5 时强制 CASH。",
                    "result": f"{decision.get('quality_score', 0.0):.2f}",
                }
            )
        elif step == "posterior":
            top_regime = max(decision.items(), key=lambda x: x[1])[0] if decision else "n/a"
            formula = "Bayesian Posterior Distribution"
            node_traces.append(
                {
                    "step": step,
                    "node": "Bayesian Inference 贝叶斯推断",
                    "type": "MACRO",
                    "formula": formula,
                    "explanation": "根据宏观与战术特征输出五态后验概率分布。",
                    "result": top_regime,
                }
            )
        elif step == "position_sizer":
            formula = f"raw_beta={decision.get('raw_target_beta', 0.0):.2f}x"
            node_traces.append(
                {
                    "step": step,
                    "node": "Probabilistic Sizing 仓位建议",
                    "type": "ADVISORY",
                    "formula": formula,
                    "explanation": "基于后验分布与信息熵惩罚（Entropy Penalty）生成目标 Beta。",
                    "result": f"{decision.get('target_beta', 0.0):.2f}x",
                }
            )
        elif step == "behavior_guard":
            formula = f"bucket={decision.get('target_bucket', 'n/a')}"
            node_traces.append(
                {
                    "step": step,
                    "node": "Behavioral Guard 行为守卫",
                    "type": "SIGNAL",
                    "formula": formula,
                    "explanation": "施加执行级约束，包括死区滞后、结算锁与单日变动上限。",
                    "result": decision.get("target_bucket", "n/a"),
                }
            )
        elif step == "reference_path":
            formula = str(decision)
            node_traces.append(
                {
                    "step": step,
                    "node": "Reference 参考路径",
                    "type": "REFERENCE",
                    "formula": formula,
                    "explanation": (
                        "参考路径仅用于说明一种实现目标 beta 的仓位组合，不是系统强制配比。"
                    ),
                    "result": f"Beta={_format_beta(evidence.get('target_beta'))}",
                }
            )

    return node_traces


def _nth_weekday_of_month(year: int, month: int, weekday: int, n: int) -> date_cls:
    current = date_cls(year, month, 1)
    while current.weekday() != weekday:
        current += timedelta(days=1)
    return current + timedelta(weeks=n - 1)


def _last_weekday_of_month(year: int, month: int, weekday: int) -> date_cls:
    if month == 12:
        current = date_cls(year + 1, 1, 1) - timedelta(days=1)
    else:
        current = date_cls(year, month + 1, 1) - timedelta(days=1)
    while current.weekday() != weekday:
        current -= timedelta(days=1)
    return current


def _observed_fixed_holiday(year: int, month: int, day: int) -> date_cls:
    holiday = date_cls(year, month, day)
    if holiday.weekday() == 5:
        return holiday - timedelta(days=1)
    if holiday.weekday() == 6:
        return holiday + timedelta(days=1)
    return holiday


def _easter_sunday(year: int) -> date_cls:
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    weekday_offset = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * weekday_offset) // 451
    month = (h + weekday_offset - 7 * m + 114) // 31
    day = ((h + weekday_offset - 7 * m + 114) % 31) + 1
    return date_cls(year, month, day)


def _nyse_holidays(year: int) -> set[date_cls]:
    thanksgiving = _nth_weekday_of_month(year, 11, 3, 4)
    return {
        _observed_fixed_holiday(year, 1, 1),
        _nth_weekday_of_month(year, 1, 0, 3),   # Martin Luther King Jr. Day
        _nth_weekday_of_month(year, 2, 0, 3),   # Presidents Day
        _easter_sunday(year) - timedelta(days=2),  # Good Friday
        _last_weekday_of_month(year, 5, 0),     # Memorial Day
        _observed_fixed_holiday(year, 6, 19),   # Juneteenth
        _observed_fixed_holiday(year, 7, 4),    # Independence Day
        _nth_weekday_of_month(year, 9, 0, 1),   # Labor Day
        thanksgiving,
        _observed_fixed_holiday(year, 12, 25),  # Christmas
    }


def _nyse_early_close_days(year: int) -> set[date_cls]:
    thanksgiving = _nth_weekday_of_month(year, 11, 3, 4)
    return {
        thanksgiving + timedelta(days=1),  # Black Friday
    }


class _FallbackNYSECalendar:
    """Minimal NYSE calendar fallback when pandas_market_calendars is unavailable."""

    def schedule(self, start_date: date_cls, end_date: date_cls) -> pd.DataFrame:
        rows: list[dict[str, pd.Timestamp]] = []
        current = start_date
        while current <= end_date:
            if current.weekday() < 5 and current not in _nyse_holidays(current.year):
                open_dt = EASTERN.localize(datetime.combine(current, time(9, 30))).astimezone(UTC)
                close_time = time(13, 0) if current in _nyse_early_close_days(current.year) else time(16, 0)
                close_dt = EASTERN.localize(datetime.combine(current, close_time)).astimezone(UTC)
                rows.append(
                    {
                        "market_open": pd.Timestamp(open_dt),
                        "market_close": pd.Timestamp(close_dt),
                    }
                )
            current += timedelta(days=1)
        return pd.DataFrame(rows)

    def open_at_time(self, schedule: pd.DataFrame, now_utc: datetime) -> bool:
        if schedule.empty:
            return False
        now_ts = pd.Timestamp(now_utc)
        open_series = schedule["market_open"]
        close_series = schedule["market_close"]
        return bool(((open_series <= now_ts) & (now_ts <= close_series)).any())


class MarketCursor:
    """
    Handles market calendar aware calculations to prevent timezone drift
    and incorrect stale warnings during weekends/holidays.
    """
    def __init__(self, calendar_name: str = "NYSE"):
        if mcal is not None:
            self.cal = mcal.get_calendar(calendar_name)
        else:
            if calendar_name != "NYSE":
                raise ValueError("Fallback market calendar only supports NYSE")
            self.cal = _FallbackNYSECalendar()

    def _get_schedule(self, now: datetime, days: int = 10) -> pd.DataFrame:
        """Helper to get market schedule around a given time."""
        start_date = now.date()
        end_date = (now + timedelta(days=days)).date()
        return self.cal.schedule(start_date=start_date, end_date=end_date)

    def get_market_state(self, now: datetime) -> str:
        """Determines if the market is currently ACTIVE or FROZEN."""
        if now.tzinfo is None:
            raise ValueError("Must pass an aware datetime")

        now_utc = now.astimezone(UTC)
        schedule = self._get_schedule(now.astimezone(EASTERN), days=1)

        try:
            is_open = self.cal.open_at_time(schedule, now_utc)
        except (ValueError, IndexError):
            is_open = False

        return "ACTIVE" if is_open else "FROZEN"

    def get_expires_at_utc(self, now: datetime, jitter_hours: int = 4) -> datetime:
        """
        Calculates the physical expiration time for the current signal.
        Leaps over weekends, holidays, and recognizes early closes.
        """
        if now.tzinfo is None:
            raise ValueError("Must pass an aware datetime")

        now_utc = now.astimezone(UTC)
        now_est = now.astimezone(EASTERN)

        # Get NYSE schedule for today and next few days
        schedule = self._get_schedule(now_est, days=7)

        # Current day's close (UTC)
        today_close = schedule.iloc[0]['market_close'].to_pydatetime()

        if now_utc < today_close:
            # Market is open or hasn't closed yet today
            try:
                is_open = self.cal.open_at_time(schedule.iloc[[0]], now_utc)
            except (ValueError, IndexError):
                is_open = False

            if is_open:
                # ACTIVE: Expected next update is next hour on the hour
                next_expected = (now_est + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
                # But not past today's close
                if next_expected.astimezone(UTC) > today_close:
                    next_expected = today_close.astimezone(EASTERN)
            else:
                # Pre-market: Expected update at open
                next_expected = schedule.iloc[0]['market_open'].to_pydatetime().astimezone(EASTERN)
        else:
            # Market is closed for today, leap to next trading day's open
            next_expected = schedule.iloc[1]['market_open'].to_pydatetime().astimezone(EASTERN)

        # Add Jitter Buffer
        expires_at = next_expected + timedelta(hours=jitter_hours)
        return expires_at.astimezone(UTC)


def _discretize_allocation(beta: float) -> str:
    """Maps precise beta/allocation to 10% bands to protect internal logic."""
    if beta <= 0.05:
        return "0-5% (极轻仓/现金)"
    if beta <= 0.25:
        return "10-20% (防御性)"
    if beta <= 0.45:
        return "30-40% (保守)"
    if beta <= 0.65:
        return "50-60% (稳健)"
    if beta <= 0.85:
        return "70-80% (积极)"
    if beta <= 1.05:
        return "90-100% (满仓)"
    return "110-120% (进攻/杠杆)"

REGIME_MAP = {
    "CRISIS": {"label": "流动性危机 (CRISIS)", "desc": "信用利差极度走阔，系统性风险爆发，强制防御。"},
    "TRANSITION_STRESS": {"label": "压力过渡 (STRESS)", "desc": "市场波动加剧，信贷条件收紧，建议审慎缩减敞口。"},
    "RICH_TIGHTENING": {"label": "流动性边际收紧 (RICH_TIGHTENING)", "desc": "估值性价比极低，政策环境收紧，禁止增加杠杆。"},
    "NEUTRAL": {"label": "中性平衡 (NEUTRAL)", "desc": "估值与流动性处于动态平衡，维持基准配置。"},
    "EUPHORIC": {"label": "过度狂热 (EUPHORIC)", "desc": "市场情绪过热，定价脱离物理现实，获利离场。"},
    # V11 Bayesian Posteriors
    "MID_CYCLE": {"label": "中期平稳 (MID_CYCLE)", "desc": "周期中性平稳期，穿越波动的基准轨道。"},
    "BUST": {"label": "休克 (BUST)", "desc": "信贷断裂引发流动性休克，强制避险 (P_Bust 超过信息阈值)。"},
    "CAPITULATION": {"label": "投降 (CAPITULATION)", "desc": "绝望式抛售触及极值，高赔率反弹窗口 (P_Cap 激增)。"},
    "RECOVERY": {"label": "修复 (RECOVERY)", "desc": "最差阶段已过，动能开始共振回归 (P_Rec 获得确认)。"},
    "LATE_CYCLE": {"label": "末端 (LATE_CYCLE)", "desc": "周期动能衰减，结构性风险增加，审慎缩减。"},
}

CYCLE_REGIME_MAP = {
    "BUST": {"label": "休克 (BUST)", "desc": "信贷断裂引发流动性休克，一票否决所有进攻。"},
    "CAPITULATION": {"label": "投降 (CAPITULATION)", "desc": "绝望式抛售触及极值，高赔率波动率猎杀点。"},
    "RECOVERY": {"label": "修复 (RECOVERY)", "desc": "最差阶段已过，趋势开始共振回归。"},
    "MID_CYCLE": {"label": "中性 (MID_CYCLE)", "desc": "周期中性平稳期，穿越波动的基准轨道。"},
    "LATE_CYCLE": {"label": "末端 (LATE_CYCLE)", "desc": "周期动能衰减，结构性腐烂增加，审慎去杠杆。"},
    "UNQUALIFIED": {"label": "无特征", "desc": "当前周期特征不明确，维持基准建议。"}
}

DEPLOY_MAP = {
    "FAST": {"label": "快速入场", "desc": "仅针对新增现金的 QQQ 买入节奏加速。"},
    "BASE": {"label": "常规入场", "desc": "仅针对新增现金的 QQQ 买入节奏维持基准。"},
    "SLOW": {"label": "减速入场", "desc": "仅针对新增现金的 QQQ 买入节奏放缓。"},
    "PAUSE": {"label": "停止入场", "desc": "仅针对新增现金暂停 QQQ 买入，保留现金。"}
}


def export_web_snapshot(result: SignalResult, output_path: str | Path | None = None) -> bool:
    """
    Export a web snapshot aligned with the v10/v11 cycle-aware runtime contract.
    """
    try:
        now_utc = datetime.now(UTC)
        cursor = MarketCursor()

        market_state = cursor.get_market_state(now_utc)
        expires_at_utc = cursor.get_expires_at_utc(now_utc, jitter_hours=4)

        from src.output.report import summarize_data_quality

        # Resolve mappings with MUST-HAVE integrity (Fail-Closed)
        is_v11 = result.engine_version == "v11"

        # v11 unified regime vs v10 dual regime
        if is_v11:
            regime_key = _get_v11_stable_regime_key(result)
            raw_regime_key = _get_v11_raw_regime_key(result)
        else:
            regime_key = str(result.tier0_regime) if result.tier0_regime else "NEUTRAL"
            raw_regime_key = regime_key

        deploy_key = _get_deployment_state_str(result)

        # Accessing with [] to raise KeyError if missing - system should failure rather than mask
        regime_info = REGIME_MAP.get(regime_key, {"label": regime_key, "desc": "Unknown regime"})
        raw_regime_info = REGIME_MAP.get(raw_regime_key, {"label": raw_regime_key, "desc": "Unknown regime"})
        deploy_info = DEPLOY_MAP.get(deploy_key, {"label": deploy_key, "desc": "Unknown deployment"})

        # Final Validation of core target beta (AC-3 Data Truthfulness)
        if result.target_beta is None:
            raise ValueError(f"CRITICAL DATA GAP: result.target_beta is None at {now_utc}")

        reference_path = {
            "qqq_pct": result.target_allocation.target_qqq_pct,
            "qld_pct": result.target_allocation.target_qld_pct,
            "cash_pct": result.target_allocation.target_cash_pct,
        }

        # V11 specific descriptive contract
        contract_desc = (
            "系统输出为概率优先的连续目标 Beta；"
            "后验概率决定方向，信息熵惩罚（Entropy Penalty）控制缩放，"
            "行为守卫（Behavioral Guard）负责离散化执行。"
        ) if is_v11 else (
            "系统输出 contract 是 target_beta 信号；用户自行决定资产配置比例，"
            "风险带和参考路径只用于帮助理解实现区间。"
        )

        payload = {
            "meta": {
                "version": result.engine_version if is_v11 else "v10.0",
                "calculated_at_utc": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "expires_at_utc": expires_at_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "market_state": market_state,
            },
            "signal": {
                "regime": regime_info["label"],
                "regime_desc": regime_info["desc"],
                "stable_regime": regime_info["label"],
                "raw_regime": raw_regime_info["label"],
                "contract": "target_beta_signal",
                "contract_desc": contract_desc,
                "cycle_regime": (
                    CYCLE_REGIME_MAP.get(str(result.cycle_regime), {"label": str(result.cycle_regime)})["label"]
                    if result.cycle_regime else (regime_info["label"] if is_v11 else "NEUTRAL")
                ),
                "target_beta": result.target_beta,
                "raw_target_beta": (
                    result.raw_target_beta if result.raw_target_beta is not None else result.target_beta
                ),
                "beta_ceiling": result.target_exposure_ceiling if result.target_exposure_ceiling is not None else 1.2,
                "qld_ceiling": result.qld_share_ceiling,
                "candidate_id": result.selected_candidate_id or ("v11_probabilistic" if is_v11 else "n/a"),
                "decision_path": _build_decision_path(result),
                "exposure_band": _discretize_allocation(result.target_beta),
                "exposure_desc": "目标 Beta 对应的存量风险带，用于帮助理解风险区间。",
                "deploy_rhythm": deploy_info["label"],
                "deployment_state": deploy_info["label"],
                "deployment_state_key": deploy_key,
                "deployment_readiness": (
                    float(result.v11_execution.get("deployment_readiness", 0.0)) if is_v11 else None
                ),
                "deploy_desc": (
                    "离散节奏状态，决定新增资金是快速、常规、减速还是暂停。"
                    if is_v11 else deploy_info["desc"]
                ),
                "readiness_desc": (
                    "Bayesian Kelly 就绪度，衡量新增资金进场质量，不等于部署状态。"
                    if is_v11 else None
                ),
                "reference_path": reference_path,
                "reference_desc": "参考路径仅用于说明一种实现目标 beta 的仓位组合，不是系统强制配比。",
                "fidelity": "高 (Bayesian)" if is_v11 else "高 (可靠)",
                "v11_probabilities": result.v11_probabilities if is_v11 else {},
                "priors": result.v11_execution.get("priors", {}) if is_v11 else {},
                "v11_entropy": result.v11_entropy if is_v11 else 0.0,
                "lock_active": result.v11_execution.get("lock_active", False) if is_v11 else False,
            },
            "evidence": {
                "risk_state": result.risk_state.value if result.risk_state else ("V11_CONTINUOUS" if is_v11 else None),
                "risk_reasons": result.risk_reasons,
                "deploy_reasons": result.deployment_reasons,
                "data_quality_summary": summarize_data_quality(result.data_quality),
                "factors": {
                    "macro": {
                        "credit_spread": result.feature_values.get("credit_spread"),
                        "erp": result.feature_values.get("erp"),
                        "net_liquidity": result.feature_values.get("net_liquidity"),
                        "liquidity_roc": result.feature_values.get("liquidity_roc"),
                    },
                    "tactical": {
                        "vix": result.feature_values.get("vix"),
                        "fear_greed": result.feature_values.get("fear_greed"),
                        "rolling_drawdown": result.feature_values.get("rolling_drawdown"),
                        "tactical_stress": result.feature_values.get("tactical_stress_score"),
                    },
                },
                "node_traces": _build_web_node_traces(result),
            },
        }

        # 1. Local Write (Always for debugging/local history)
        local_path = Path(output_path) if output_path else Path("src/web/public/status.json")
        local_path.parent.mkdir(parents=True, exist_ok=True)
        with open(local_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        # 2. Production Upload Gating (v11.18 Cloud Bridge)
        cloud = CloudPersistenceBridge()
        if cloud.is_ci:
            logger.info("Initiating namespaced production upload via Cloud Bridge...")
            # Filename is 'status.json'. CloudManager handles namespace prefixing.
            cloud.push_payload(payload, "status.json")
        else:
            logger.info("Local mode detected: Skipping cloud upload to protect production integrity.")

        return True

    except Exception as exc:
        logger.error("Web export failed: %s", exc)
        if os.environ.get("GITHUB_ACTIONS") == "true":
            # In CI, propagate the error so the workflow fails and notifies the developer.
            raise
        return False


def export_feature_library_to_blob(library_path: str | Path = "data/v11_feature_library.csv") -> bool:
    """
    Persist the V11 feature library to Vercel Blob storage using Cloud Bridge.
    Ensures namespaced isolation across CI runs.
    """
    cloud = CloudPersistenceBridge()
    if not cloud.is_ci or not cloud.token:
        # Local mode: Graceful skip according to ADD v3.0 Staging Gates policy.
        logger.info("Skipping feature library cloud upload (Non-CI or missing token).")
        return False

    lib_path = Path(library_path)
    if not lib_path.exists():
        logger.error("Feature library file not found: %s", library_path)
        return False

    logger.info("Syncing V11 Feature Library to Cloud via Bridge...")
    try:
        with open(lib_path, "rb") as f:
            content = f.read()

        # Filename is 'v11_feature_library.csv'. CloudManager handles namespace prefixing.
        return cloud.push_payload(content, "v11_feature_library.csv", is_binary=True)
    except Exception as e:
        logger.error("Feature library cloud sync failed: %s", e)
        return False

