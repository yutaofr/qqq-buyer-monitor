import pandas as pd


def debug():
    df = pd.read_csv("artifacts/panorama_trace.csv")
    df['date'] = df.iloc[:, 0]

    # Map columns based on header inspection
    # ,MID_CYCLE,LATE_CYCLE,BUST,RECOVERY,tractor_prob,sidecar_prob,sidecar_valid,
    # radar_stagflation_trap,radar_credit_crisis,radar_carry_unwind,radar_valuation_compression,
    # radar_deflationary_bust,radar_treasury_dislocation,radar_liquidity_drain,radar_growth_bust,
    # radar_reflation_rotation,radar_melt_up,res_action,res_confidence,liq_velocity,cdr,entropy

    # res_action is at index 18 (0-indexed) if the first col is empty index
    # But let's look at the columns names
    print(f"Columns: {df.columns.tolist()}")

    # We'll use the column names directly
    for i in range(1, len(df)):
        row = df.iloc[i]
        prev_row = df.iloc[i-1]

        mid_prob = float(row['MID_CYCLE'])
        late_prob = float(row['LATE_CYCLE'])
        bust_prob = float(row['BUST'])

        mid_delta = mid_prob - float(prev_row['MID_CYCLE'])
        # Acceleration would need 3 days, let's just assume it's positive for now or check if it satisfies the condition

        tractor_prob = float(row['tractor_prob'])
        sidecar_prob = float(row['sidecar_prob'])
        combined_risk = tractor_prob + sidecar_prob

        prev_tractor = float(prev_row['tractor_prob'])
        prev_sidecar = float(prev_row['sidecar_prob'])
        previous_combined_risk = prev_tractor + prev_sidecar
        risk_delta = combined_risk - previous_combined_risk

        effective_entropy = float(row['entropy'])
        previous_effective_entropy = float(prev_row['entropy'])
        entropy_delta = effective_entropy - previous_effective_entropy

        # Acceleration: we need 1 more day back for proper check
        if i < 2:
            continue
        prev_prev_row = df.iloc[i-2]
        prev_mid_delta = float(prev_row['MID_CYCLE']) - float(prev_prev_row['MID_CYCLE'])
        mid_accel = mid_delta - prev_mid_delta

        bust_delta = bust_prob - float(prev_row['BUST'])

        # Conditions (V14.9)
        risk_clear = combined_risk <= 0.18 and tractor_prob <= 0.10 and sidecar_prob <= 0.10
        risk_relief = risk_delta <= -0.02 or (previous_combined_risk >= 0.30 and combined_risk <= 0.18 and risk_delta <= -0.12)
        entropy_waterfall = previous_effective_entropy >= 0.55 and effective_entropy <= 0.52 and entropy_delta <= -0.12
        mid_cycle_surge = mid_prob >= 0.45 and mid_prob > late_prob and mid_delta >= 0.05 and (mid_accel > 0.0 or bust_delta <= -0.05)
        bust_retreat = bust_prob <= 0.18 or bust_delta <= -0.05

        if risk_clear and risk_relief and mid_cycle_surge and bust_retreat:
            # If everything BUT entropy waterfall is true, print it
            if not entropy_waterfall:
                print(f"[{row['date']}] BUY NEAR MISS (Entropy Waterfall Failure): entropy={effective_entropy:.3f}, prev_entropy={previous_effective_entropy:.3f}, delta={entropy_delta:.3f}")
            else:
                print(f"[{row['date']}] BUY SIGNAL DETECTED in debug script! Flags: rc={risk_clear}, rr={risk_relief}, ew={entropy_waterfall}, mcs={mid_cycle_surge}, br={bust_retreat}")

if __name__ == "__main__":
    debug()
