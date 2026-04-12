from pathlib import Path


def test_frontend_avoids_investment_advice_wording():
    html_content = Path("src/web/public/index.html").read_text(encoding="utf-8")

    banned_phrases = [
        "建議加槓桿",
        "建議降槓桿",
        "ADD LEVERAGE",
        "REDUCE LEVERAGE",
    ]

    for phrase in banned_phrases:
        assert phrase not in html_content, f"Frontend must not present advisory wording: {phrase}"


def test_frontend_explains_permission_precedence_over_resonance():
    html_content = Path("src/web/public/index.html").read_text(encoding="utf-8")

    required_phrases = [
        "QLD 技術權限狀態",
        "不構成投資建議",
        "共振信號",
        "最終以 QLD 權限層為準",
    ]

    for phrase in required_phrases:
        assert phrase in html_content, f"Frontend must explain semantic precedence with phrase: {phrase}"
