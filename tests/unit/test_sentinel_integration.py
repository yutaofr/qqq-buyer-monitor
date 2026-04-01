import numpy as np

from src.engine.v11.sentinel import SentinelEngine


def test_sentinel_stale_data_handling():
    engine = SentinelEngine(span_base=100)

    p_macro = np.array([0.8, 0.1, 0.1, 0.0])
    mu_macro = np.array([0.01, 0.0]) # Simplified return vector

    # Normal data flow
    res = engine.update(r_t=0.001, v_t=0.1, p_macro=p_macro, mu_macro=mu_macro, stale_days=1, nominal_period=30)
    assert res["stale_decay"] == 1.0
    assert res["m_effective_edge"] == res["m_edge"]

    # Simulate data gap (stale for 60 days, nominal 30)
    # 30 days excess age. With 7 days half-life, decay should be approx 2^(-30/7) approx 0.05
    res_stale = engine.update(r_t=0.001, v_t=0.1, p_macro=p_macro, mu_macro=mu_macro, stale_days=60, nominal_period=30)
    assert res_stale["stale_decay"] < 0.1
    # Effective edge should be close to 1.0 because of decay
    assert np.isclose(res_stale["m_effective_edge"], 1.0, atol=0.1)

    # Simulate resumption (stale_days back to 1)
    # Low-pass filter should prevent it from jumping back to 1.0 instantly
    res_resumed = engine.update(r_t=0.001, v_t=0.1, p_macro=p_macro, mu_macro=mu_macro, stale_days=1, nominal_period=30)
    assert res_resumed["stale_decay"] < 1.0
    # Should be higher than previous stale decay but not 1.0
    assert res_resumed["stale_decay"] > res_stale["stale_decay"]

def test_sentinel_penalty_explosion_on_heteroskedasticity():
    # Test that Tikhonov + dm_sq triggers penalty correctly
    engine = SentinelEngine(span_base=50, ridge_lambda=1e-6)

    # Pre-heat with normal data
    for _ in range(100):
        engine.update(r_t=0.0, v_t=0.0, p_macro=np.array([0.25]*4), mu_macro=np.array([0.0, 0.0]))

    # Sudden explosion in return but volume stays zero (highly singular/surprising)
    res_surprise = engine.update(r_t=0.1, v_t=0.0, p_macro=np.array([0.25]*4), mu_macro=np.array([0.0, 0.0]))

    assert res_surprise["s_micro"] > 5.0 # Significant surprisal
    assert res_surprise["penalty"] > 50.0 # Significant penalty
