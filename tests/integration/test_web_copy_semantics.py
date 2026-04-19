from pathlib import Path


def test_frontend_avoids_investment_advice_wording():
    html_content = Path("src/web/public/index.html").read_text(encoding="utf-8")

    banned_phrases = [
        "建議加槓桿",
        "建議降槓桿",
        "ADD LEVERAGE",
        "REDUCE LEVERAGE",
        "最終執行目標",
        "QLD 技術權限狀態",
        "共振信號",
    ]

    for phrase in banned_phrases:
        assert phrase not in html_content, f"Frontend must not present advisory wording: {phrase}"


def test_frontend_explains_probability_dashboard_scope_and_limits():
    html_content = Path("src/web/public/index.html").read_text(encoding="utf-8")

    required_phrases = [
        "Daily Post-Close Cycle Stage Probability Dashboard",
        "Probability Dashboard, Not Auto-Trading",
        "Do not infer automatic leverage",
        "Boundary warnings are not ordinary stage calls",
    ]

    for phrase in required_phrases:
        assert phrase in html_content, (
            f"Frontend must explain semantic precedence with phrase: {phrase}"
        )
