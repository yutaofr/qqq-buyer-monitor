#!/usr/bin/env python3
"""VEGETATIVE STATE FORENSIC AUDIT

Read-only diagnostic. Touches ZERO engine code.
Reads the backtest execution_trace.csv + forensic_trace.jsonl
to determine exactly how badly the engine was blinded.
"""
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


def phase1_coma_audit(exec_path: Path) -> None:
    """PHASE 1: Regime distribution + position distribution."""
    print("=" * 78)
    print("  PHASE 1: THE COMA AUDIT — Regime & Position Distribution (2013–2026)")
    print("=" * 78)
    print()

    rows = []
    with open(exec_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    total = len(rows)
    print(f"  Total trading days in backtest: {total}")
    print()

    # ── Regime distribution (predicted_regime = what the engine CHOSE) ──
    regime_counter = Counter()
    for row in rows:
        regime_counter[row["predicted_regime"]] += 1

    print("  ┌─────────────────────────────────────────────────────────────┐")
    print("  │  PREDICTED REGIME DISTRIBUTION (engine's perception)       │")
    print("  ├─────────────┬──────────┬─────────┬────────────────────────┤")
    print("  │  Regime     │   Days   │   %     │  Bar                   │")
    print("  ├─────────────┼──────────┼─────────┼────────────────────────┤")
    for regime in ["MID_CYCLE", "LATE_CYCLE", "BUST", "RECOVERY"]:
        count = regime_counter.get(regime, 0)
        pct = count / total * 100 if total else 0
        bar = "█" * int(pct / 2)
        print(f"  │  {regime:11s} │ {count:6d}   │ {pct:5.1f}%  │ {bar:22s} │")
    print("  └─────────────┴──────────┴─────────┴────────────────────────┘")

    # ── Actual regime distribution (ground truth labels) ──
    actual_counter = Counter()
    for row in rows:
        actual_counter[row["actual_regime"]] += 1

    print()
    print("  ┌─────────────────────────────────────────────────────────────┐")
    print("  │  ACTUAL REGIME DISTRIBUTION (ground truth labels)          │")
    print("  ├─────────────┬──────────┬─────────┬────────────────────────┤")
    print("  │  Regime     │   Days   │   %     │  Bar                   │")
    print("  ├─────────────┼──────────┼─────────┼────────────────────────┤")
    for regime in ["MID_CYCLE", "LATE_CYCLE", "BUST", "RECOVERY"]:
        count = actual_counter.get(regime, 0)
        pct = count / total * 100 if total else 0
        bar = "█" * int(pct / 2)
        print(f"  │  {regime:11s} │ {count:6d}   │ {pct:5.1f}%  │ {bar:22s} │")
    print("  └─────────────┴──────────┴─────────┴────────────────────────┘")

    # ── Beta/Position distribution ──
    print()
    print("  ┌─────────────────────────────────────────────────────────────┐")
    print("  │  POSITION / BETA DISTRIBUTION                              │")
    print("  ├──────────────────────────┬──────────┬─────────┬────────────┤")
    print("  │  Category                │   Days   │   %     │  Bar       │")
    print("  ├──────────────────────────┼──────────┼─────────┼────────────┤")

    leverage_days = 0    # beta >= 1.5 (QLD territory)
    fullqq_days = 0      # 0.9 <= beta < 1.5 (QQQ)
    partial_days = 0     # 0.5 <= beta < 0.9
    defense_days = 0     # beta < 0.5
    floor_exact = 0      # beta == 0.5 exactly (floor-locked)

    beta_sum = 0.0
    beta_min = 999.0
    beta_max = -999.0

    for row in rows:
        beta = float(row["target_beta"])
        beta_sum += beta
        beta_min = min(beta_min, beta)
        beta_max = max(beta_max, beta)

        if beta >= 1.5:
            leverage_days += 1
        elif beta >= 0.9:
            fullqq_days += 1
        elif beta >= 0.5:
            partial_days += 1
        else:
            defense_days += 1

        if abs(beta - 0.5) < 0.001:
            floor_exact += 1

    cats = [
        ("QLD Leverage (β≥1.5)", leverage_days),
        ("QQQ Full (0.9≤β<1.5)", fullqq_days),
        ("Partial (0.5≤β<0.9)", partial_days),
        ("Defense (β<0.5)", defense_days),
    ]
    for name, count in cats:
        pct = count / total * 100 if total else 0
        bar = "█" * int(pct / 2)
        print(f"  │  {name:24s} │ {count:6d}   │ {pct:5.1f}%  │ {bar:10s} │")
    print("  └──────────────────────────┴──────────┴─────────┴────────────┘")

    print()
    print(f"  β statistics: mean={beta_sum/total:.4f}  min={beta_min:.4f}  max={beta_max:.4f}")
    print(f"  Floor-locked (β=0.500): {floor_exact} days ({floor_exact/total*100:.1f}%)")

    # ── Time series: regime by year ──
    print()
    print("  ┌────────────────────────────────────────────────────────────────────┐")
    print("  │  ANNUAL REGIME BREAKDOWN (predicted)                              │")
    print("  ├──────┬──────────────┬──────────────┬──────────────┬───────────────┤")
    print("  │ Year │  MID_CYCLE   │  LATE_CYCLE  │     BUST     │   RECOVERY    │")
    print("  ├──────┼──────────────┼──────────────┼──────────────┼───────────────┤")

    year_regime = defaultdict(lambda: Counter())
    year_beta = defaultdict(list)
    for row in rows:
        year = row["date"][:4]
        year_regime[year][row["predicted_regime"]] += 1
        year_beta[year].append(float(row["target_beta"]))

    for year in sorted(year_regime.keys()):
        yr_total = sum(year_regime[year].values())
        cells = []
        for regime in ["MID_CYCLE", "LATE_CYCLE", "BUST", "RECOVERY"]:
            c = year_regime[year].get(regime, 0)
            pct = c / yr_total * 100 if yr_total else 0
            cells.append(f"{c:4d} ({pct:4.0f}%)")
        print(f"  │ {year} │ {cells[0]:12s} │ {cells[1]:12s} │ {cells[2]:12s} │ {cells[3]:13s} │")
    print("  └──────┴──────────────┴──────────────┴──────────────┴───────────────┘")

    # ── Annual average beta ──
    print()
    print("  ┌──────────────────────────────────────────────────────┐")
    print("  │  ANNUAL AVERAGE BETA                                │")
    print("  ├──────┬──────────┬───────────────────────────────────┤")
    print("  │ Year │ Avg Beta │  Bar                              │")
    print("  ├──────┼──────────┼───────────────────────────────────┤")
    for year in sorted(year_beta.keys()):
        avg = sum(year_beta[year]) / len(year_beta[year]) if year_beta[year] else 0
        bar = "█" * int(avg * 20)
        color = "" if avg >= 0.8 else " ← ANEMIC" if avg >= 0.6 else " ← COMATOSE"
        print(f"  │ {year} │  {avg:.4f}  │ {bar:20s}{color:15s} │")
    print("  └──────┴──────────┴───────────────────────────────────┘")


def phase2_feature_death_toll(forensic_path: Path) -> None:
    """PHASE 2: Feature blindness rate from forensic trace."""
    print()
    print("=" * 78)
    print("  PHASE 2: FEATURE DEATH TOLL — Sensor Blindness Rate (2013–2026)")
    print("=" * 78)
    print()

    # Read forensic trace line by line (JSONL, can be large)
    feature_dead_days = defaultdict(int)  # feature -> count of days with quality=0
    feature_degraded_days = defaultdict(int)  # feature -> count of days with 0 < quality < 1
    feature_total_days = defaultdict(int)  # feature -> total days seen
    daily_dead_counts = []  # per-day count of dead features
    total_days = 0

    # All known engineered features (from the seeder contract)
    ALL_FEATURES = [
        "real_yield_structural_z", "move_21d", "breakeven_accel",
        "core_capex_momentum", "copper_gold_roc_126d", "usdjpy_roc_126d",
        "spread_21d", "liquidity_252d", "erp_absolute", "spread_absolute",
        "qqq_ma_ratio", "qqq_pv_divergence_z", "credit_acceleration",
        "pmi_momentum", "labor_slack", "liquidity_velocity",
    ]

    # Field-level quality from quality_audit.fields
    field_dead_days = defaultdict(int)
    field_total_days = defaultdict(int)

    with open(forensic_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            total_days += 1

            # Extract field-level quality from quality_audit
            qa = record.get("quality_audit", {})
            fields = qa.get("fields", {})
            for field_name, field_info in fields.items():
                field_total_days[field_name] += 1
                q = float(field_info.get("quality", 1.0))
                if q <= 0:
                    field_dead_days[field_name] += 1

            # Extract feature-level effective weights from v13_4_diagnostics
            # The diagnostics that live INSIDE quality_audit
            diag = record.get("v13_4_diagnostics", {})
            inner_diag = qa.get("v13_4_diagnostics", {})

            # Try to get feature weights (these map to engineered feature names)
            ew = diag.get("effective_weights", {}) or inner_diag.get("effective_weights", {})

            # Count dead features per day based on the diagnostics
            # Since feature_weights (quality-based) aren't stored in forensic trace,
            # we reconstruct from field quality → feature mapping
            FEATURE_TO_FIELD = {
                "spread_21d": "credit_spread",
                "spread_absolute": "credit_spread",
                "credit_acceleration": "credit_spread",
                "liquidity_252d": "net_liquidity",
                "liquidity_velocity": "net_liquidity",
                "real_yield_structural_z": "real_yield",
                "move_21d": "treasury_vol",
                "copper_gold_roc_126d": "copper_gold",
                "breakeven_accel": "breakeven",
                "core_capex_momentum": "core_capex",
                "usdjpy_roc_126d": "usdjpy",
                "erp_absolute": "erp_ttm",
                "qqq_ma_ratio": None,  # derived from price, always available
                "qqq_pv_divergence_z": None,  # derived from price
                "pmi_momentum": None,  # no field mapping — check if raw source exists
                "labor_slack": None,  # no field mapping
            }

            day_dead = 0
            for feat in ALL_FEATURES:
                feature_total_days[feat] += 1
                parent_field = FEATURE_TO_FIELD.get(feat)
                if parent_field and parent_field in fields:
                    q = float(fields[parent_field].get("quality", 1.0))
                    if q <= 0:
                        feature_dead_days[feat] += 1
                        day_dead += 1
                    elif q < 1.0:
                        feature_degraded_days[feat] += 1
                elif parent_field is None:
                    # Features without field mapping (price-derived or missing sources)
                    # pmi_momentum and labor_slack have NO source in field_specs
                    # They are ALWAYS missing in the historical macro dump
                    if feat in ("pmi_momentum", "labor_slack"):
                        # These are computed from raw sources not in field_specs
                        # Check if they appear in effective_weights with weight > 0
                        if feat not in ew or float(ew.get(feat, 0)) == 0:
                            feature_dead_days[feat] += 1
                            day_dead += 1
                else:
                    # Parent field not in quality audit at all
                    feature_dead_days[feat] += 1
                    day_dead += 1

            daily_dead_counts.append(day_dead)

    # ── Summary statistics ──
    avg_dead = sum(daily_dead_counts) / len(daily_dead_counts) if daily_dead_counts else 0
    n_features = len(ALL_FEATURES)

    print(f"  Total days audited: {total_days}")
    print(f"  Total features per day: {n_features}")
    print(f"  Daily average dead features: {avg_dead:.1f} / {n_features} ({avg_dead/n_features*100:.0f}%)")
    print()

    # ── Distribution of daily dead feature counts ──
    from collections import Counter as C
    dead_dist = C(daily_dead_counts)
    print("  ┌───────────────────────────────────────────────────────────────┐")
    print("  │  DAILY DEAD FEATURE COUNT DISTRIBUTION                      │")
    print("  ├─────────────────┬──────────┬─────────┬───────────────────────┤")
    print("  │  Dead Features  │   Days   │   %     │  Bar                  │")
    print("  ├─────────────────┼──────────┼─────────┼───────────────────────┤")
    for k in sorted(dead_dist.keys()):
        count = dead_dist[k]
        pct = count / total_days * 100 if total_days else 0
        bar = "█" * int(pct / 2)
        label = f"{k:2d} dead"
        if k == 0:
            label += " (HEALTHY)"
        elif k >= 3:
            label += " (BLIND)"
        print(f"  │  {label:15s} │ {count:6d}   │ {pct:5.1f}%  │ {bar:21s} │")
    print("  └─────────────────┴──────────┴─────────┴───────────────────────┘")

    # ── Top 5 most-dead features ──
    print()
    print("  ┌───────────────────────────────────────────────────────────────────────┐")
    print("  │  TOP FEATURE DEATH TOLL (sorted by blindness rate)                   │")
    print("  ├────┬──────────────────────────┬──────────┬─────────┬─────────────────┤")
    print("  │  # │  Feature                 │ Dead Days│   %     │  Status         │")
    print("  ├────┼──────────────────────────┼──────────┼─────────┼─────────────────┤")

    ranked = sorted(
        [(f, feature_dead_days[f], feature_total_days.get(f, total_days))
         for f in ALL_FEATURES],
        key=lambda x: x[1],
        reverse=True,
    )
    for i, (feat, dead, tot) in enumerate(ranked):
        pct = dead / tot * 100 if tot else 0
        degraded = feature_degraded_days.get(feat, 0)
        if pct > 95:
            status = "☠️  PERMANENT DEATH"
        elif pct > 50:
            status = "🔴 CHRONIC BLIND"
        elif pct > 10:
            status = "🟡 INTERMITTENT"
        elif degraded > 0:
            status = f"🟠 DEGRADED ({degraded}d)"
        else:
            status = "🟢 HEALTHY"
        print(f"  │ {i+1:2d} │ {feat:24s} │ {dead:6d}   │ {pct:5.1f}%  │ {status:15s} │")
    print("  └────┴──────────────────────────┴──────────┴─────────┴─────────────────┘")

    # ── Field-level quality ──
    print()
    print("  ┌───────────────────────────────────────────────────────────────┐")
    print("  │  RAW FIELD QUALITY (from quality_audit.fields)               │")
    print("  ├──────────────────────┬──────────┬─────────┬──────────────────┤")
    print("  │  Field               │ Dead Days│   %     │  Status          │")
    print("  ├──────────────────────┼──────────┼─────────┼──────────────────┤")
    for field in sorted(field_total_days.keys()):
        dead = field_dead_days.get(field, 0)
        tot = field_total_days[field]
        pct = dead / tot * 100 if tot else 0
        if pct > 50:
            status = "🔴 DATA DESERT"
        elif pct > 0:
            status = f"🟡 GAPS ({dead}d)"
        else:
            status = "🟢 FULL COVERAGE"
        print(f"  │  {field:20s} │ {dead:6d}   │ {pct:5.1f}%  │ {status:16s} │")
    print("  └──────────────────────┴──────────┴─────────┴──────────────────┘")


def main() -> int:
    exec_path = Path("artifacts/v12_audit/execution_trace.csv")
    forensic_path = Path("artifacts/v12_audit/forensic_trace.jsonl")

    if not exec_path.exists():
        print(f"FATAL: {exec_path} not found. Run backtest first.")
        return 1
    if not forensic_path.exists():
        print(f"FATAL: {forensic_path} not found. Run backtest first.")
        return 1

    phase1_coma_audit(exec_path)
    phase2_feature_death_toll(forensic_path)

    print()
    print("=" * 78)
    print("  AUTOPSY COMPLETE.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
