import os
import sys
import unittest

# Add scripts to path to import
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../scripts')))
from pi_stress_phase5_research import Phase5Research


class TestPhase5Research(unittest.TestCase):
    def setUp(self):
        self.research = Phase5Research(reports_dir="/tmp/reports", artifacts_dir="/tmp/artifacts")

    def test_run_metric_provenance_audit(self):
        result = self.research.run_metric_provenance_audit()
        self.assertIn("objective", result)
        self.assertIn("Gate_A_improvement", result["metrics"])

    def test_run_oos_contamination_audit(self):
        result = self.research.run_oos_contamination_audit()
        self.assertIn("window_inventory", result)
        self.assertFalse(result["blind_basket_analysis"]["clean_blind_basket_available"])

    def test_run_override_regime_relativity_audit(self):
        result = self.research.run_override_regime_relativity_audit()
        self.assertIn("high_vol_regime", result["volatility_buckets"])

    def test_run_gap_penalized_ttd_audit(self):
        result = self.research.run_gap_penalized_ttd_audit()
        self.assertIn("2015_August", result["windows"])
        self.assertTrue(result["windows"]["2015_August"]["breaches_survival_bounds"])

    def test_run_hysteresis_parameterization_audit(self):
        result = self.research.run_hysteresis_parameterization_audit()
        self.assertIn("tests", result)

    def test_run_full_adversarial_validation(self):
        result = self.research.run_full_adversarial_validation()
        self.assertIn("rapid_v_shape", result["evaluations"])

    def test_run_agent_capability_audit(self):
        result = self.research.run_agent_capability_audit()
        self.assertEqual(result["capability_rating"], "LOW")

    def test_run_failure_mode_register(self):
        result = self.research.run_failure_mode_register()
        self.assertTrue(any(f["name"] == "OOS contamination overhang" for f in result["failure_modes"]))

    def test_generate_acceptance_checklist(self):
        result = self.research.generate_acceptance_checklist()
        self.assertIn("OVF1", result["one_vote_fail_items"])
        self.assertIn("Unresolved", result["one_vote_fail_items"]["OVF1"])

    def test_determine_final_verdict(self):
        checklist = self.research.generate_acceptance_checklist()
        result = self.research.determine_final_verdict(checklist)
        self.assertEqual(result["verdict"], "DOWNGRADE_CONFIDENCE_AND_REWORK_CANDIDATE")

if __name__ == '__main__':
    unittest.main()
