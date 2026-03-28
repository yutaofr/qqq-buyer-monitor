"""TDD: Doc-check — README must mention v7 dual-controller (Task 17)."""
from pathlib import Path


def test_readme_mentions_v7_risk_controller():
    text = Path("README.md").read_text(encoding="utf-8")
    assert "Risk Controller" in text, "README must document the v7 Risk Controller"


def test_readme_mentions_v7_deployment_controller():
    text = Path("README.md").read_text(encoding="utf-8")
    assert "Deployment Controller" in text, "README must document the v7 Deployment Controller"


def test_readme_cn_mentions_target_beta_as_primary_contract():
    text = Path("README-CN.md").read_text(encoding="utf-8")
    assert "只推荐 **组合级目标 beta**" in text


def test_readme_cn_mentions_deployment_controller_as_qqq_only_new_cash():
    text = Path("README-CN.md").read_text(encoding="utf-8")
    assert "新增现金" in text
    assert "QQQ" in text
