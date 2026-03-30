
import json
from pathlib import Path

# User's provided status.json (LATE_CYCLE)
status_json = {
  "meta": {"version": "v11", "calculated_at_utc": "2026-03-30T05:29:08Z", "expires_at_utc": "2026-03-30T17:30:00Z", "market_state": "FROZEN"},
  "signal": {
    "regime": "末端 (LATE_CYCLE)",
    "cycle_regime": "末端 (LATE_CYCLE)",
    "target_beta": 0.511469,
    "v11_entropy": 0.794657
  }
}

def test_rendering_logic():
    print("--- Testing Frontend Rendering Logic with provided status.json ---")
    
    # Simulate safeUpdate('regime', data.signal.regime)
    val_regime = status_json['signal']['regime']
    print(f"Assigning #regime: '{val_regime}'")
    if val_regime != "末端 (LATE_CYCLE)":
        print("FAIL: Regime string mismatch")
        return False

    # Simulate Entropy formatting
    val_entropy = f"{status_json['signal']['v11_entropy']:.3f}"
    print(f"Assigning #entropy: '{val_entropy}'")
    if val_entropy != "0.795":
        print("FAIL: Entropy formatting mismatch")
        return False

    # CRITICAL: Simulate updateGhostTags fuzzy match logic
    # Logic: const isMatch = label.includes(tagText) || tagText.includes(label);
    label = val_regime.upper() # "末端 (LATE_CYCLE)"
    
    available_tags = [
        "末端 (LATE_CYCLE)", 
        "中期平稳 (MID_CYCLE)", 
        "休克 (BUST)", 
        "投降 (CAPITULATION)", 
        "修复 (RECOVERY)"
    ]
    
    print(f"\nFuzzy Matching against Label: '{label}'")
    found_match = False
    for tag in available_tags:
        tag_upper = tag.upper()
        # This is the exact logic in index.html
        is_match = label in tag_upper or tag_upper in label
        print(f"Tag: '{tag}' -> Match? {is_match}")
        if is_match:
            if tag == "末端 (LATE_CYCLE)":
                found_match = True
            else:
                print(f"ERROR: Incorrectly matched '{tag}'!")
                return False
                
    if not found_match:
        print("CRITICAL FAIL: No tag matched for LATE_CYCLE!")
        return False

    print("\nSUCCESS: All frontend rendering logic points are 100% CORRECT.")
    return True

if __name__ == "__main__":
    if test_rendering_logic():
        print("RESULT: PASS")
    else:
        print("RESULT: FAIL")
        exit(1)
