"""TDD: Doc-check — README must mention v7 dual-controller (Task 17)."""
from pathlib import Path


def test_readme_mentions_v7_risk_controller():
    text = Path("README.md").read_text(encoding="utf-8")
    assert "Risk Controller" in text, "README must document the v7 Risk Controller"


def test_readme_mentions_v7_deployment_controller():
    text = Path("README.md").read_text(encoding="utf-8")
    assert "Deployment Controller" in text, "README must document the v7 Deployment Controller"
