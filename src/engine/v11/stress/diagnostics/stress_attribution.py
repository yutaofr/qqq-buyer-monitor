from __future__ import annotations

from src.engine.v11.stress.types import CombinedStressScore


class StressAttributor:
    """Daily component and interaction attribution for pi_stress."""

    def explain(
        self,
        *,
        components: dict[str, float],
        combined: CombinedStressScore,
        calibrated_score: float,
    ) -> dict[str, object]:
        ranked_terms = sorted(
            (
                (name, value)
                for name, value in combined.terms.items()
                if name != "intercept" and value > 0.0
            ),
            key=lambda item: item[1],
            reverse=True,
        )
        return {
            "components": {name: float(value) for name, value in components.items()},
            "terms": {name: float(value) for name, value in combined.terms.items()},
            "transformed_inputs": {
                name: float(value) for name, value in combined.transformed_inputs.items()
            },
            "linear_score": float(combined.linear_score),
            "raw_score": float(combined.raw_score),
            "calibrated_score": float(calibrated_score),
            "top_contributors": [
                {"term": name, "contribution": float(value)} for name, value in ranked_terms[:3]
            ],
            "joint_confirmation": {
                "price_market": float(combined.terms.get("interaction_price_market", 0.0)),
                "price_macro": float(combined.terms.get("interaction_price_macro", 0.0)),
                "market_macro": float(combined.terms.get("interaction_market_macro", 0.0)),
            },
        }
