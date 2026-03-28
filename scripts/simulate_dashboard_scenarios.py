import os
import sys
from datetime import date
from pathlib import Path
from dataclasses import dataclass, field

# Add src to path
sys.path.append(os.getcwd())

from src.models import SignalResult, Tier1Result, Tier2Result, Signal, AllocationState
from src.models.risk import RiskState
from src.models.deployment import DeploymentState
from src.output.web_exporter import export_web_snapshot

def create_mock_result(
    tier0_regime="NEUTRAL",
    risk_state=RiskState.RISK_NEUTRAL,
    deploy_state=DeploymentState.DEPLOY_BASE,
    target_beta=1.0,
    risk_rules=[{"rule": "clean_macro"}],
    deploy_rules=[{"rule": "default_base"}],
    feature_values={}
):
    # Dummy results
    t1 = Tier1Result(score=50, drawdown_52w=None, ma200_deviation=None, vix=None, fear_greed=None, breadth=None)
    t2 = Tier2Result(adjustment=0, put_wall=None, call_wall=None, gamma_flip=None, support_confirmed=True, 
                    support_broken=False, upside_open=True, gamma_positive=True, gamma_source="bs", 
                    put_wall_distance_pct=0.0, call_wall_distance_pct=0.0)
    
    res = SignalResult(
        date=date.today(),
        price=560.0,
        signal=Signal.WATCH,
        final_score=100,
        tier1=t1,
        tier2=t2,
        explanation="Mock Simulation",
        tier0_regime=tier0_regime,
        risk_state=risk_state,
        deployment_state=deploy_state,
        target_beta=target_beta,
        risk_reasons=risk_rules,
        deployment_reasons=deploy_rules,
        deployment_action={"deploy_mode": deploy_state.name.replace("DEPLOY_", "") if hasattr(deploy_state, 'name') else "BASE"},
        data_quality={},
        feature_values={
            "credit_spread": 350,
            "erp": 3.0,
            "rolling_drawdown": 0.05,
            "net_liquidity": 6000,
            "liquidity_roc": 1.0,
            "vix": 15,
            "fear_greed": 50,
            "tactical_stress_score": 20,
            **feature_values
        }
    )
    return res

def run_simulations():
    output_dir = Path("src/web/public/simulations")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    scenarios = [
        # 1. Macro Crisis Veto
        {
            "name": "scenario_1_crisis_veto",
            "res": create_mock_result(
                tier0_regime="CRISIS",
                risk_state=RiskState.RISK_EXIT,
                deploy_state=DeploymentState.DEPLOY_PAUSE,
                target_beta=0.5,
                risk_rules=[{"rule": "tier0_crisis", "tier0_regime": "CRISIS"}],
                deploy_rules=[{"rule": "risk_ceiling", "risk_state": "RISK_EXIT"}]
            )
        },
        # 2. Rich Tightening Veto
        {
            "name": "scenario_2_rich_veto",
            "res": create_mock_result(
                tier0_regime="RICH_TIGHTENING",
                risk_state=RiskState.RISK_REDUCED,
                deploy_state=DeploymentState.DEPLOY_BASE,
                target_beta=0.8,
                risk_rules=[{"rule": "tier0_rich_tightening", "tier0_regime": "RICH_TIGHTENING"}],
                deploy_rules=[{"rule": "rich_tightening_base" if False else "default_base"}] # RICH base is now handled as default
            )
        },
        # 3. Technical Signal (No Veto)
        {
            "name": "scenario_3_tech_signal",
            "res": create_mock_result(
                tier0_regime="NEUTRAL",
                risk_state=RiskState.RISK_DEFENSE,
                deploy_state=DeploymentState.DEPLOY_SLOW,
                target_beta=0.7,
                risk_rules=[{"rule": "dual_stress", "stress_count": 2}],
                deploy_rules=[{"rule": "risk_ceiling"}] # Using existing ceiling rule
            )
        },
        # 4. Blood Chip Override (Crisis + Fast Entry)
        {
            "name": "scenario_4_blood_chip",
            "res": create_mock_result(
                tier0_regime="CRISIS",
                risk_state=RiskState.RISK_EXIT,
                deploy_state=DeploymentState.DEPLOY_FAST,
                target_beta=0.5,
                risk_rules=[{"rule": "tier0_crisis", "tier0_regime": "CRISIS"}],
                deploy_rules=[{"rule": "blood_chip_crisis_override", "path": "panic_exhaustion"}]
            )
        },
        # 5. Euphoric Mode
        {
            "name": "scenario_5_euphoric",
            "res": create_mock_result(
                tier0_regime="EUPHORIC",
                risk_state=RiskState.RISK_ON,
                deploy_state=DeploymentState.DEPLOY_FAST,
                target_beta=1.2,
                risk_rules=[{"rule": "tier0_euphoric", "tier0_regime": "EUPHORIC"}],
                deploy_rules=[{"rule": "default_base"}]
            )
        },
        # 6. Leverage ON (Stress Hierarchy Audit)
        {
            "name": "scenario_6_leverage_on",
            "res": create_mock_result(
                tier0_regime="NEUTRAL",
                risk_state=RiskState.RISK_ON,
                deploy_state=DeploymentState.DEPLOY_BASE,
                target_beta=1.2,
                risk_rules=[{"rule": "clean_macro"}],
                deploy_rules=[{"rule": "default_base"}]
            )
        },
        # 7. Data Corruption (Integrity Check Audit)
        {
            "name": "scenario_7_data_corruption",
            "res": create_mock_result(
                tier0_regime="NEUTRAL",
                risk_state=RiskState.RISK_ON,
                deploy_state=DeploymentState.DEPLOY_BASE,
                target_beta=1.0,
                feature_values={"credit_spread": None} # This should trigger the Integrity Error
            )
        }
    ]

    for s in scenarios:
        filename = f"src/web/public/simulations/{s['name']}.json"
        print(f"Generating {filename}...")
        try:
            export_web_snapshot(s['res'], output_path=filename)
        except Exception as e:
            print(f"Error in {s['name']}: {e}")

if __name__ == "__main__":
    run_simulations()
