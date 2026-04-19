# Final Product Forward OOS Monitoring

Forward OOS logging records current stage state today and materializes realized-outcome hooks only when their future windows complete. The `recovery_relapsed` field is locked as a frozen OR-triggered 10-trading-day forward outcome and must not be changed retroactively after launch.

## Machine-Readable Snapshot
```json
{
  "decision": "FORWARD_OOS_MONITORING_IS_IN_PLACE",
  "integrity_rules": [
    "probabilities sum to 1",
    "dominant_stage present",
    "urgency present",
    "relapse_pressure present",
    "same market_date rows are not duplicated unless product_version, calibration_version, or ui_version differs",
    "recovery_relapsed follows the frozen OR-triggered 10-trading-day forward outcome contract"
  ],
  "log_path": "artifacts/final_product/forward_oos_monitoring_log.jsonl",
  "outcome_contract": {
    "recovery_relapsed": {
      "anchor_condition": "after any day with dominant_stage == RECOVERY",
      "definition_status": "FROZEN",
      "false_rule": "mark false only when no OR trigger occurs by the end of the completed 10-trading-day window",
      "field": "recovery_relapsed",
      "field_type": "boolean_or_null",
      "null_rule": "keep null for non-RECOVERY anchors and RECOVERY anchors with incomplete windows",
      "or_triggers": [
        "dominant_stage returns to STRESS",
        "FAST_CASCADE_BOUNDARY is triggered",
        "relapse_pressure == HIGH and secondary_stage == STRESS for at least 2 consecutive trading days"
      ],
      "retroactive_change_policy": "definition must not be changed retroactively after launch",
      "true_rule": "mark true when any OR trigger occurs inside the completed 10-trading-day window",
      "window_completion_rule": "requires 10 subsequent trading rows before materialization",
      "window_start": "next trading day after the RECOVERY anchor row",
      "window_trading_days": 10
    }
  },
  "sample_entry": {
    "action_relevance_band": "PREPARE_TO_ADJUST",
    "boundary_flag": false,
    "breadth_status": "weak",
    "calibration_version": "recovery_compliance_guarded",
    "dominant_stage": "RECOVERY",
    "hazard_percentile": 0.6752,
    "hazard_score": 0.44,
    "market_date": "2026-04-19",
    "next_10d_return": null,
    "next_5d_return": null,
    "product_version": "final-product-v1",
    "rationale_summary": "RECOVERY leads LATE_CYCLE by 5.0%. Urgency is HIGH; action relevance is PREPARE_TO_ADJUST. Hazard=0.44, breadth=0.45, volatility percentile=0.67. This is a cycle-stage probability read, not an automatic beta instruction.",
    "realized_drawdown_10d": null,
    "realized_drawdown_5d": null,
    "realized_stage_persistence_days": null,
    "recovery_relapsed": null,
    "relapse_pressure": "HIGH",
    "secondary_stage": "LATE_CYCLE",
    "stage_probabilities": {
      "EXPANSION": 0.11203951641120395,
      "FAST_CASCADE_BOUNDARY": 0.015766767101576675,
      "LATE_CYCLE": 0.3139986737313999,
      "RECOVERY": 0.3639452064363945,
      "STRESS": 0.194249836319425
    },
    "timestamp": "2026-04-19T08:34:00Z",
    "ui_version": "daily-probability-dashboard-v2",
    "urgency": "HIGH",
    "vol_status": "elevated"
  },
  "schema_fields": [
    "timestamp",
    "market_date",
    "dominant_stage",
    "secondary_stage",
    "stage_probabilities",
    "urgency",
    "action_relevance_band",
    "relapse_pressure",
    "hazard_score",
    "hazard_percentile",
    "breadth_status",
    "vol_status",
    "boundary_flag",
    "rationale_summary",
    "product_version",
    "calibration_version",
    "ui_version",
    "next_5d_return",
    "next_10d_return",
    "realized_drawdown_5d",
    "realized_drawdown_10d",
    "realized_stage_persistence_days",
    "recovery_relapsed"
  ],
  "summary": "A durable JSONL log records forward daily outputs, prevents duplicate rows for the same market date and schema versions, and materializes frozen outcome fields only when their forward windows complete."
}
```
