# Recovery HMM Variant Panorama

## Baseline Reference

- locked candidate decision: `DO_NOT_LIVE_INTEGRATE_YET`
- locked candidate shadow total return: `1.6235`
- locked candidate shadow Sharpe: `0.8449`
- locked candidate 2022 Q1 avg weight: `0.6960`
- locked candidate 2023 Q1 avg weight: `0.5874`

## Variant Ranking

### 1. recovery_accelerated

- decision: `DO_NOT_LIVE_INTEGRATE_YET`
- shadow total return: `2.1803`
- shadow Sharpe: `0.9062`
- vs locked candidate total return: `0.5569`
- vs locked candidate Sharpe: `0.0613`
- 2022 Q1 avg weight: `0.7710`
- 2023 Q1 avg weight: `0.8160`

### 2. orthogonal_consensus

- decision: `DO_NOT_LIVE_INTEGRATE_YET`
- shadow total return: `1.8103`
- shadow Sharpe: `0.8645`
- vs locked candidate total return: `0.1868`
- vs locked candidate Sharpe: `0.0196`
- 2022 Q1 avg weight: `0.7164`
- 2023 Q1 avg weight: `0.6771`

### 3. barbell_balance

- decision: `DO_NOT_LIVE_INTEGRATE_YET`
- shadow total return: `1.7303`
- shadow Sharpe: `0.8509`
- vs locked candidate total return: `0.1068`
- vs locked candidate Sharpe: `0.0060`
- 2022 Q1 avg weight: `0.7075`
- 2023 Q1 avg weight: `0.5694`

### 4. stress_hardened

- decision: `DO_NOT_LIVE_INTEGRATE_YET`
- shadow total return: `1.5657`
- shadow Sharpe: `0.8519`
- vs locked candidate total return: `-0.0578`
- vs locked candidate Sharpe: `0.0070`
- 2022 Q1 avg weight: `0.6596`
- 2023 Q1 avg weight: `0.5000`

### 5. fdas_guardrail

- decision: `DO_NOT_LIVE_INTEGRATE_YET`
- shadow total return: `1.4609`
- shadow Sharpe: `0.8104`
- vs locked candidate total return: `-0.1626`
- vs locked candidate Sharpe: `-0.0345`
- 2022 Q1 avg weight: `0.6102`
- 2023 Q1 avg weight: `0.5874`

## Conclusion

- `KEEP_SHADOW_ONLY_AND_CONTINUE_RESEARCH`
