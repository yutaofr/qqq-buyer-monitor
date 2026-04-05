import numpy as np
from scipy.stats import norm


class TailRiskRadar:
    """
    v14 Fat-Tail Event Radar (肥尾事件雷达).
    Calculates 10 categories of tail risk indicators based on v12/v14 factor Z-scores.
    This is a presentation layer output and does not affect the core Bayesian inference.
    """

    SCENARIOS = {
        "stagflation_trap": {
            "name": "滞涨陷阱",
            "name_en": "Stagflation Trap",
            "icon": "🌋",
            "conditions": [
                ("breakeven_accel", "above", 0.0, 0.5),   # Inflation accel
                ("core_capex_momentum", "below", 0.0, 0.5), # Growth stagnation
            ],
            "description": "Fed cannot ease or tighten. EPS + Valuation double-hit."
        },
        "credit_crisis": {
            "name": "信用危机",
            "name_en": "Credit Crisis",
            "icon": "💣",
            "conditions": [
                ("spread_21d", "above", 1.5, 0.5),        # Spread spike
                ("spread_absolute", "above", 1.0, 0.5),   # Absolute level high
                ("liquidity_252d", "below", -0.5, 0.5),   # Liquidity contraction
            ],
            "description": "Funding chain breaks. Forced liquidation spiral."
        },
        "carry_unwind": {
            "name": "套息解体",
            "name_en": "Carry Unwind",
            "icon": "🌊",
            "conditions": [
                ("usdjpy_roc_126d", "below", -1.0, 0.5),  # Yen sharp appreciation
                ("spread_21d", "above", 0.5, 0.5),         # Credit starting to tighten
                ("copper_gold_roc_126d", "below", 0.0, 0.5), # Weak global demand
            ],
            "description": "Global leverage unwind. Systemic deleveraging storm."
        },
        "valuation_compression": {
            "name": "估值压缩",
            "name_en": "Valuation Compression",
            "icon": "📉",
            "conditions": [
                ("real_yield_structural_z", "above", 1.5, 0.5), # Real yield spike
                ("erp_absolute", "below", -0.5, 0.5),           # ERP compressed
            ],
            "description": "Discount rate kills duration. 2022 H1 repeat."
        },
        "deflationary_bust": {
            "name": "通缩式崩溃",
            "name_en": "Deflationary Bust",
            "icon": "❄️",
            "conditions": [
                ("breakeven_accel", "below", -1.5, 0.5),   # Inflation expectation collapse
                ("core_capex_momentum", "below", -1.0, 0.5), # Growth collapse
                ("spread_21d", "above", 1.5, 0.5),          # Credit deterioration
            ],
            "description": "Total recession. 2008/2020 mode."
        },
        "treasury_dislocation": {
            "name": "国债市场失灵",
            "name_en": "Treasury Dislocation",
            "icon": "⚡",
            "conditions": [
                ("move_21d", "above", 2.0, 0.5),           # Treasury vol spike
                ("real_yield_structural_z", "extreme", 2.0, 0.5), # Extreme yield move
            ],
            "description": "Valuation anchor lost. Liquidity vacuum."
        },
        "liquidity_drain": {
            "name": "流动性枯竭",
            "name_en": "Liquidity Drain",
            "icon": "🏜️",
            "conditions": [
                ("liquidity_252d", "below", -1.5, 0.5),    # Fed tightening (QT)
                ("spread_21d", "above", 0.5, 0.5),          # Credit tightening
            ],
            "description": "Passive fund outflows. Liquidity spiral."
        },
        "growth_bust": {
            "name": "成长预期坍塌",
            "name_en": "Growth Perfection Bust",
            "icon": "💥",
            "conditions": [
                ("erp_absolute", "below", -1.5, 0.5),       # Excessive valuation perfection
                ("core_capex_momentum", "below", -1.0, 0.5), # Capex retreat
            ],
            "description": "Davis Double-Hit. Perfection meets reality collapse."
        },
        "reflation_rotation": {
            "name": "再通胀换仓",
            "name_en": "Reflationary Rotation",
            "icon": "🔄",
            "conditions": [
                ("breakeven_accel", "above", 1.5, 0.5),    # Strong inflation accel
                ("copper_gold_roc_126d", "above", 1.0, 0.5), # Industrial demand frenzy
                ("real_yield_structural_z", "above", 1.0, 0.5), # Real yield rising
            ],
            "description": "Old economy recovery. Capital sucks away from tech."
        },
        "melt_up": {
            "name": "融涨泡沫顶峰",
            "name_en": "Melt-Up Complacency",
            "icon": "🎈",
            "conditions": [
                ("spread_absolute", "below", -1.5, 0.5),   # Credit priced to perfection
                ("erp_absolute", "below", -1.5, 0.5),      # Equity priced to perfection
                ("move_21d", "below", -1.0, 0.5),         # Volatility death
            ],
            "description": "Silent extreme euphoria. Any minor shock triggers avalanche."
        },
    }

    @staticmethod
    def _activation(z_value: float, direction: str, threshold: float, fuzz: float) -> float:
        """Calculate single condition activation density ∈ [0, 1]"""
        if direction == "above":
            return float(norm.cdf((z_value - threshold) / fuzz))
        elif direction == "below":
            return float(norm.cdf((threshold - z_value) / fuzz))
        elif direction == "extreme":
            # Extreme = Upper or Lower extreme (absolute move)
            a_up = float(norm.cdf((z_value - threshold) / fuzz))
            a_dn = float(norm.cdf((-threshold - z_value) / fuzz))
            return float(max(a_up, a_dn))
        return 0.0

    @classmethod
    def compute(cls, feature_zscores: dict | None) -> dict:
        """
        Compute probabilities for all 10 scenarios.

        Args:
            feature_zscores: Dict of factor Z-scores (e.g., from ProbabilitySeeder diagnostics)

        Returns:
            Dict of scenario probabilities and details.
        """
        if feature_zscores is None:
            return {k: {"probability": 0.0, "status": "no_data"} for k in cls.SCENARIOS}

        results = {}
        for key, scenario in cls.SCENARIOS.items():
            activations = []
            condition_details = []

            for factor, direction, threshold, fuzz in scenario["conditions"]:
                z = float(feature_zscores.get(factor, 0.0))
                a = cls._activation(z, direction, threshold, fuzz)
                activations.append(a)
                condition_details.append({
                    "factor": factor,
                    "value": round(z, 3),
                    "activation": round(a, 3),
                })

            # Geometric mean: all conditions must be somewhat active to get a high score.
            # Using sqrt-of-products approach (equivalent to geometric mean).
            # We add a small eps to prod to handle zeros gracefully if needed,
            # but geometric mean of 0 is 0, which is physically correct.
            prob = float(np.prod(activations) ** (1.0 / len(activations)))

            if prob >= 0.7:
                level = "CRITICAL"
            elif prob >= 0.5:
                level = "HIGH"
            elif prob >= 0.3:
                level = "ELEVATED"
            elif prob >= 0.15:
                level = "MODERATE"
            else:
                level = "LOW"

            results[key] = {
                "name": scenario["name"],
                "name_en": scenario["name_en"],
                "icon": scenario["icon"],
                "probability": round(prob, 4),
                "level": level,
                "conditions": condition_details
            }

        return results
