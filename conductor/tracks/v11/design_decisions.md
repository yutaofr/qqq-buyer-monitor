# ADR: v11 Probabilistic Monitor

> 日期: 2026-03-30
> 状态: Accepted

## ADR-1 从离散 regime 表切换到 posterior-first

决策：先输出 posterior，再做 sizing，再做 bucket。

理由：状态机无法表达“接近转折但不确定”的区域，而这恰恰是风险最高的地方。

## ADR-2 用 entropy 显式收费

决策：normalized entropy 进入 uncertainty penalty，直接压缩 `raw_target_beta`。

理由：不确定性如果不收费，模型就会在最不该自信的时候看起来最平滑。

## ADR-3 用行为守卫替代逻辑内嵌摩擦

决策：`BehavioralGuard` 独立管理 deadband、结算锁和 resurrection lock。

理由：把执行摩擦写进推断层会污染概率语义，也会让测试难以隔离。

## ADR-4 数据降级覆写必须回写状态

决策：任何 forced bucket 变化都同步给 execution guard。

理由：否则会出现“信号显示不需要动作，但内部状态与目标 bucket 已分叉”的严重一致性错误。

## ADR-5 生产边界排除期权现金放大

决策：`QQQ / QLD / Cash` 仍是生产边界；所有“凸性核弹”与“血与火”实验保留为研究归档。

理由：研究脚本可用于思想实验，但其现金流假设不满足生产可信度要求。

## ADR-6 文档分层

决策：

1. `conductor/tracks/v11/` 为规范层。
2. `docs/roadmap/v11_production_sop.md` 为运维层。
3. `docs/roadmap/v11_acceptance_report_2026-03-30.md` 为验收层。
4. 历史 POC 报告全部归档，不再作为实现依据。
