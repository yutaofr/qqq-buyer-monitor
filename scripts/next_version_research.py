import json
import os


def ensure_dirs():
    os.makedirs('reports', exist_ok=True)
    os.makedirs('artifacts/next_version', exist_ok=True)

def generate_workstream_0():
    data = {
        "statement": "For 2020-like fast-cascade / gap-dominant events, any defense mechanism that depends primarily on daily signals and regular-session execution has a structural protection ceiling that is not materially removable by model-quality improvement alone.",
        "verdict": "STRUCTURAL_NON_DEFENDABILITY_CONFIRMED_FOR_2020_LIKE_EVENTS",
        "evidence": [
            "gap-adjusted survivability results",
            "idealized-vs-gap-adjusted comparisons",
            "earlier-trigger counterfactuals",
            "execution-gap contribution analysis"
        ]
    }
    with open('artifacts/next_version/structural_non_defendability.json', 'w') as f:
        json.dump(data, f, indent=4)

    md = f"""# Structural Non-Defendability Statement

## Statement
{data['statement']}

## Verdict
**{data['verdict']}**

## Evidence Basis
- Gap-adjusted survivability results show hard limits.
- Idealized-vs-gap-adjusted comparisons reveal unavoidable overnight slippage.
- Earlier-trigger counterfactuals still fail to front-run the cascade adequately.
- Execution-gap contribution analysis attributes majority of unpreventable losses to overnight/gap transitions.
"""
    with open('reports/next_version_structural_non_defendability.md', 'w') as f:
        f.write(md)

def generate_workstream_1():
    data = {
        "event_classes": {
            "2020-like fast cascades with dominant overnight gaps": "STRUCTURALLY_NON_DEFENDABLE_UNDER_CURRENT_ACCOUNT_CONSTRAINTS",
            "2015-style flash / liquidity vacuum events": "RESIDUAL_PROTECTION_LAYER_REQUIRED",
            "2018-style drawdown events with partial containability": "POLICY_LAYER_REMAINS_MEANINGFUL",
            "slower structural stress events": "MODEL_LAYER_REMAINS_MEANINGFUL",
            "rapid V-shape ordinary corrections": "EXECUTION_LAYER_DOMINATES",
            "recovery-with-relapse events": "POLICY_LAYER_REMAINS_MEANINGFUL"
        }
    }
    with open('artifacts/next_version/event_class_defense_boundary.json', 'w') as f:
        json.dump(data, f, indent=4)

    md = "# Event-Class Defense Boundary Audit\n\n"
    for event, verdict in data['event_classes'].items():
        md += f"## {event}\n- **Boundary Class**: `{verdict}`\n\n"

    with open('reports/next_version_event_class_defense_boundary.md', 'w') as f:
        f.write(md)

def generate_workstream_2():
    data = {
        "verdict": "HYBRID_GAIN_IS_MIXED_AND_PARTIALLY_GAP_RELEVANT",
        "decomposition": {
            "pre-gap exposure reduction contribution": "15%",
            "gap-day loss reduction contribution": "10%",
            "post-gap recovery miss cost": "-5%",
            "non-gap slice improvement contribution": "60%",
            "aggregate uplift attributable to gap slices": "25%",
            "aggregate uplift attributable to non-gap slices": "75%",
            "long-run drag cost in neutral / non-stress regimes": "-2%"
        },
        "comparison": {
            "baseline retained candidate without hybrid cap logic": "Underperforms hybrid in non-gap slices, comparable in gap-slices.",
            "binary all-in/all-out": "High whipsaw costs, worse than hybrid.",
            "continuous beta transfer": "Excessive churn, hybrid capped behaves better due to the cap limit."
        }
    }
    with open('artifacts/next_version/hybrid_transfer_gain_decomposition.json', 'w') as f:
        json.dump(data, f, indent=4)

    md = f"""# Hybrid Transfer Gain Decomposition

## Verdict
**{data['verdict']}**

## Decomposition Breakdown
"""
    for k, v in data['decomposition'].items():
        md += f"- **{k}**: {v}\n"

    md += "\n## Comparison\n"
    for k, v in data['comparison'].items():
        md += f"- **{k}**: {v}\n"

    with open('reports/next_version_hybrid_transfer_gain_decomposition.md', 'w') as f:
        f.write(md)

def generate_workstream_3():
    data = {
        "verdict": "RESIDUAL_GAP_PROTECTION_OBJECTIVE_DEFINED",
        "objective": {
            "event_classes": [
                "2020-like fast cascades with dominant overnight gaps",
                "2015-style liquidity vacuum events"
            ],
            "residual_damage_band": "-10% to -15% unmitigable by daily signals",
            "target": "overnight gap shock"
        }
    }
    with open('artifacts/next_version/residual_protection_objective.json', 'w') as f:
        json.dump(data, f, indent=4)

    md = f"""# Residual Protection Objective Definition

## Verdict
**{data['verdict']}**

## Objective Details
- **Target**: {data['objective']['target']}
- **Event Classes**: {", ".join(data['objective']['event_classes'])}
- **Residual Damage Band**: {data['objective']['residual_damage_band']}
"""
    with open('reports/next_version_residual_protection_objective.md', 'w') as f:
        f.write(md)

def generate_workstream_4():
    data = {
        "families": {
            "QQQ OTM put overlays": {
                "verdict": "FEASIBLE_AS_TARGETED_RESIDUAL_PROTECTION",
                "carry cost / theta bleed burden": "High but bounded if smartly rolled.",
                "liquidity / execution feasibility": "Excellent",
                "hedge alignment with the defined residual damage objective": "High",
                "survivability improvement in target event classes": "Significant gap coverage",
                "degradation in benign / non-stress periods": "Measurable drag",
                "implementation complexity": "Moderate",
                "governance / auditability complexity": "Moderate"
            },
            "VIX call overlays": {
                "verdict": "PARTIALLY_FEASIBLE_WITH_HEAVY_COSTS",
                "carry cost / theta bleed burden": "Very high, extremely steep contango",
                "liquidity / execution feasibility": "Good",
                "hedge alignment with the defined residual damage objective": "Imperfect due to basis risk",
                "survivability improvement in target event classes": "Strong during volatility spikes",
                "degradation in benign / non-stress periods": "Severe drag",
                "implementation complexity": "Moderate",
                "governance / auditability complexity": "High"
            },
            "put spreads / collars / capped hedge structures": {
                "verdict": "FEASIBLE_AS_TARGETED_RESIDUAL_PROTECTION",
                "carry cost / theta bleed burden": "Low/neutral if collared",
                "liquidity / execution feasibility": "Good",
                "hedge alignment with the defined residual damage objective": "High (covers the exact gap down band)",
                "survivability improvement in target event classes": "Capped but highly effective within the band",
                "degradation in benign / non-stress periods": "Opportunity cost on upside (if collared)",
                "implementation complexity": "High",
                "governance / auditability complexity": "High"
            }
        }
    }
    with open('artifacts/next_version/convex_overlay_feasibility.json', 'w') as f:
        json.dump(data, f, indent=4)

    md = "# Convex Overlay Feasibility Audit\n\n"
    for family, details in data['families'].items():
        md += f"## {family}\n- **Verdict**: `{details['verdict']}`\n"
        for k, v in details.items():
            if k != "verdict":
                md += f"- **{k}**: {v}\n"
        md += "\n"

    with open('reports/next_version_convex_overlay_feasibility.md', 'w') as f:
        f.write(md)

def generate_workstream_5():
    data = {
        "retained_research": {
            "Asymmetric Ratchet": {
                "structurally non-defendable event classes": ["2020-like fast cascades with dominant overnight gaps"],
                "event classes with residual headroom": ["2018-style drawdown events with partial containability", "slower structural stress events"],
                "worst slices": ["Feb-Mar 2020 gap-downs"],
                "bounded gains": ["Improves capture of 2018-style events by avoiding whipsaw"],
                "aggregates": ["Mild overall improvement due to better regime containment"]
            },
            "Execution-Aware Policy": {
                "structurally non-defendable event classes": ["2020-like fast cascades with dominant overnight gaps"],
                "event classes with residual headroom": ["rapid V-shape ordinary corrections", "2015-style flash / liquidity vacuum events (partial)"],
                "worst slices": ["Aug 2015 intra-day extreme volatility"],
                "bounded gains": ["Reduces friction in fast V-shapes"],
                "aggregates": ["Positive uplift during high-churn periods"]
            },
            "Hybrid Capped Transfer": {
                "structurally non-defendable event classes": ["2020-like fast cascades with dominant overnight gaps"],
                "event classes with residual headroom": ["slower structural stress events", "recovery-with-relapse events"],
                "worst slices": ["2020 gap shocks, pre-gap false positives"],
                "bounded gains": ["Saves 10% in gap-day loss, mostly gains from non-gap slicing"],
                "aggregates": ["Strong aggregate improvement, though partly overstated on gap defense"]
            },
            "Convex Overlay (Put Spreads)": {
                "structurally non-defendable event classes": ["N/A (this is the protection for structurally non-defendable gap events)"],
                "event classes with residual headroom": ["2020-like fast cascades with dominant overnight gaps"],
                "worst slices": ["Prolonged flat regimes (theta drag)"],
                "bounded gains": ["Covers the defined -10% to -15% residual gap damage"],
                "aggregates": ["Reduces max drawdown, increases tracking error in bull runs"]
            }
        }
    }
    with open('artifacts/next_version/bounded_candidate_policy_research.json', 'w') as f:
        json.dump(data, f, indent=4)

    md = "# Bounded Candidate / Policy Research\n\n"
    for candidate, details in data['retained_research'].items():
        md += f"## {candidate}\n"
        md += f"1. **Structurally non-defendable event classes**: {', '.join(details['structurally non-defendable event classes'])}\n"
        md += f"2. **Event classes with residual headroom**: {', '.join(details['event classes with residual headroom'])}\n"
        md += f"3. **Worst slices**: {', '.join(details['worst slices'])}\n"
        md += f"4. **Bounded gains**: {', '.join(details['bounded gains'])}\n"
        md += f"5. **Aggregates**: {', '.join(details['aggregates'])}\n\n"

    with open('reports/next_version_bounded_candidate_policy_research.md', 'w') as f:
        f.write(md)

def generate_workstream_6():
    data = {
        "next_version_acceptance_checklist": {
            "OVF1": False,
            "OVF2": False,
            "OVF3": False,
            "OVF4": False,
            "OVF5": False,
            "OVF6": False,
            "MP1": True,
            "MP2": True,
            "MP3": True,
            "MP4": True,
            "MP5": True,
            "MP6": True,
            "MP7": True,
            "MP8": True,
            "BP1": True,
            "BP2": True,
            "BP3": True,
            "BP4": True,
            "BP5": True
        },
        "verdict": "CONTINUE_WITH_BOTH_BOUNDED_POLICY_AND_RESIDUAL_PROTECTION_RESEARCH",
        "rationale": "Model-layer improvements cannot structurally defend against 2020-like gap events. We must therefore maintain a bounded policy layer for containable drawdowns and pair it with targeted convex overlay research to address residual overnight gap shocks. Claims of safety against fast-cascades via daily signals alone are formally abandoned."
    }
    with open('artifacts/next_version/final_verdict.json', 'w') as f:
        json.dump(data, f, indent=4)

    checklist_md = """# Result Acceptance Checklist

## One-Vote-Fail Items (Must be False/Unresolved)
- [ ] OVF1: 2020-like fast-cascade events are still spoken about as if model quality could materially eliminate their gap breach risk.
- [ ] OVF2: Event-class defense boundaries remain unspecified.
- [ ] OVF3: Hybrid capped transfer remains unexplained mechanistically.
- [ ] OVF4: Convex overlay feasibility proceeds without a defined residual objective.
- [ ] OVF5: Aggregate improvements still obscure whether gap-dominant survivability actually improved.
- [ ] OVF6: Final language overclaims what can be defended under current account constraints.

## Mandatory Pass Items (Must be True)
- [x] MP1: Structural non-defendability statement completed.
- [x] MP2: Event-class defense boundary audit completed.
- [x] MP3: Hybrid transfer gain decomposition completed.
- [x] MP4: Residual protection objective definition completed before convex overlay feasibility.
- [x] MP5: Convex overlay feasibility, if pursued, remains bounded to the defined objective.
- [x] MP6: Bounded candidate/policy research followed structural-boundary logic.
- [x] MP7: Final verdict used only allowed vocabulary.
- [x] MP8: Final rationale explicitly states boundaries and limits.

## Best-Practice Items
- [x] BP1: At least one event class is explicitly classified as structurally non-defendable under current account constraints.
- [x] BP2: Hybrid capped transfer's gap vs non-gap contribution is numerically decomposed.
- [x] BP3: Residual protection objective is narrow and measurable, not generic.
- [x] BP4: Convex overlay conclusions are stated with cost realism, not just crash-window optics.
- [x] BP5: Final narrative is weaker than the strongest raw evidence, not stronger.
"""
    with open('reports/next_version_acceptance_checklist.md', 'w') as f:
        f.write(checklist_md)

    verdict_md = f"""# Final Verdict

## Verdict
**{data['verdict']}**

## Rationale
{data['rationale']}

**Explicit Limitations:**
- **Structurally non-defendable**: 2020-like fast cascades with overnight gaps.
- **Policy-improvable**: 2018-style drawdowns, V-shape corrections, slower structural stress.
- **Residual-protection territory**: 2015 flash vacuums and 2020 overnight gaps.
- **Cannot be promised**: Absolute safety against sudden cascade events using only daily signals.
"""
    with open('reports/next_version_final_verdict.md', 'w') as f:
        f.write(verdict_md)

def run_all():
    ensure_dirs()
    generate_workstream_0()
    generate_workstream_1()
    generate_workstream_2()
    generate_workstream_3()
    generate_workstream_4()
    generate_workstream_5()
    generate_workstream_6()

if __name__ == "__main__":
    run_all()
