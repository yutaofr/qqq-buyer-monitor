import json
import unittest
from pathlib import Path
from typing import Any


def get_v13_4_feature_weight(feature_name: str, registry: dict[str, Any]) -> float:
    """
    SRD-v13.4 Feature Weight Mapping: Longest Prefix Match.
    Returns the weight of the longest matching prefix or DEFAULT_FALLBACK.
    """
    matrix = registry.get("feature_weight_matrix", {})
    fallback = matrix.get("DEFAULT_FALLBACK", 1.0)

    # Sort keys by length (descending) to ensure longest prefix match
    sorted_keys = sorted(
        [k for k in matrix.keys() if k != "DEFAULT_FALLBACK"], key=len, reverse=True
    )

    for key in sorted_keys:
        if feature_name.startswith(key):
            return float(matrix[key])

    return float(fallback)


def get_v13_4_quality_score(source_marker: str, registry: dict[str, Any]) -> float:
    """
    SRD-v13.4 Quality Transfer Function: Map source strings to float q_i.
    """
    mapping = registry.get("quality_transfer_function", {})

    # Direct match first
    if source_marker in mapping:
        return float(mapping[source_marker])

    # Prefix match (e.g., proxy:, synthetic:)
    sorted_prefixes = sorted([k for k in mapping.keys() if k.endswith(":")], key=len, reverse=True)
    for prefix in sorted_prefixes:
        if source_marker.startswith(prefix):
            return float(mapping[prefix])

    # Default to 0.0 if unknown or invalid
    return 0.0


class TestV13_4Config(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path("src/engine/v11/resources/v13_4_weights_registry.json")
        cls.registry = json.loads(path.read_text())

    def test_feature_weight_mapping(self):
        # 1. Direct matches (v13.7-ULTIMA keys)
        self.assertEqual(get_v13_4_feature_weight("spread_21d", self.registry), 2.5)
        self.assertEqual(get_v13_4_feature_weight("liquidity_252d", self.registry), 2.0)

        # 2. Lineage inheritance (Longest prefix match)
        self.assertEqual(get_v13_4_feature_weight("spread_21d_accel", self.registry), 2.5)
        self.assertEqual(get_v13_4_feature_weight("move_21d", self.registry), 1.5)

        # 3. Fallback
        self.assertEqual(get_v13_4_feature_weight("unseen_factor", self.registry), 1.0)

    def test_quality_transfer_function(self):
        # 1. Direct and literal matches
        self.assertEqual(get_v13_4_quality_score("direct", self.registry), 1.0)
        self.assertEqual(get_v13_4_quality_score("missing", self.registry), 0.0)
        self.assertEqual(get_v13_4_quality_score("nan", self.registry), 0.0)

        # 2. Prefix-based matches
        self.assertEqual(get_v13_4_quality_score("proxy:spy", self.registry), 0.7)
        self.assertEqual(get_v13_4_quality_score("synthetic:derived_liquidity", self.registry), 0.5)
        self.assertEqual(get_v13_4_quality_score("default:zero_bps", self.registry), 0.3)

        # 3. Invalid/Unknown
        self.assertEqual(get_v13_4_quality_score("garbage_source", self.registry), 0.0)


if __name__ == "__main__":
    unittest.main()
