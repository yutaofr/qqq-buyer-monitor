import json
import os
import sys

# Add scripts directory to path to import the module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../scripts')))
import next_version_research


def test_ensure_dirs():
    next_version_research.ensure_dirs()
    assert os.path.exists('reports')
    assert os.path.exists('artifacts/next_version')

def test_generate_workstream_0():
    next_version_research.generate_workstream_0()
    assert os.path.exists('artifacts/next_version/structural_non_defendability.json')
    assert os.path.exists('reports/next_version_structural_non_defendability.md')
    with open('artifacts/next_version/structural_non_defendability.json') as f:
        data = json.load(f)
    assert data['verdict'] == 'STRUCTURAL_NON_DEFENDABILITY_CONFIRMED_FOR_2020_LIKE_EVENTS'

def test_generate_workstream_1():
    next_version_research.generate_workstream_1()
    with open('artifacts/next_version/event_class_defense_boundary.json') as f:
        data = json.load(f)
    assert data['event_classes']['2020-like fast cascades with dominant overnight gaps'] == 'STRUCTURALLY_NON_DEFENDABLE_UNDER_CURRENT_ACCOUNT_CONSTRAINTS'

def test_generate_workstream_6():
    next_version_research.generate_workstream_6()
    with open('artifacts/next_version/final_verdict.json') as f:
        data = json.load(f)
    assert data['verdict'] == 'CONTINUE_WITH_BOTH_BOUNDED_POLICY_AND_RESIDUAL_PROTECTION_RESEARCH'
    assert data['next_version_acceptance_checklist']['OVF1'] is False
    assert data['next_version_acceptance_checklist']['MP1'] is True
