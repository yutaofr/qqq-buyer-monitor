import numpy as np
import pytest
from src.engine.v11.sentinel import SmoothDivergenceEngine, ProbabilityCalibrator, calculate_jsd

def test_smooth_divergence_tanh_mapping():
    engine = SmoothDivergenceEngine(span=100, vol_floor=0.01)
    
    # Fill with some normal signals
    for _ in range(50):
        engine.calculate_alignment_score(0.0)
        
    # Large positive signal should give positive score close to 1
    score_pos = engine.calculate_alignment_score(10.0)
    assert 0.5 < score_pos <= 1.0
    
    # Large negative signal should give negative score close to -1
    score_neg = engine.calculate_alignment_score(-10.0)
    assert -1.0 <= score_neg < -0.5

def test_vol_floor_prevents_singularity():
    # vol_floor=0.1
    engine = SmoothDivergenceEngine(span=100, vol_floor=0.1)
    
    # Constant signals (std = 0)
    for _ in range(50):
        engine.calculate_alignment_score(1.0)
        
    # Even if std is 0, we should not get NaN or infinity because of vol_floor
    score = engine.calculate_alignment_score(1.1) # 0.1 diff
    # Mean changes slightly, but score should be around tanh(1.0)
    assert 0.7 < score < 0.8
    assert not np.isnan(score)

def test_jsd_bounds():
    p = np.array([0.9, 0.1])
    q = np.array([0.1, 0.9])
    
    jsd = calculate_jsd(p, q)
    assert 0 <= jsd <= np.log(2)
    
    # Same distribution should have 0 JSD
    assert np.isclose(calculate_jsd(p, p), 0.0)

def test_probability_calibrator_weight():
    calibrator = ProbabilityCalibrator(gamma=10.0, threshold=0.25)
    
    # Perfect prediction (Brier Score = 0) should have high weight
    assert calibrator.calculate_confidence_weight(0.0) > 0.9
    
    # Random guess (Brier Score = 0.25 for 4 classes, actually Brier for 2 classes random 0.5^2+0.5^2=0.5? No, Brier score def differs)
    # If p=[0.25]*4, y=[1,0,0,0], MeanSqErr = (0.75^2 + 0.25^2 * 3) / 4 = (0.5625 + 0.0625*3)/4 = 0.75/4 = 0.1875
    # Wait, Brier Score for multi-class is often sum of squares. SRD says 0.25.
    
    # At threshold, weight should be 0.5
    assert np.isclose(calibrator.calculate_confidence_weight(0.25), 0.5)
    
    # High Brier Score should have low weight
    assert calibrator.calculate_confidence_weight(0.5) < 0.1
