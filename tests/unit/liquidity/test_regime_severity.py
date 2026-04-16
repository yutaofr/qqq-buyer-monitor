from __future__ import annotations

import json

import pytest

from src.liquidity.config import load_config
from src.liquidity.engine.regime_severity import (
    calibrate_regime_severity_thresholds,
    compute_variance_inflation_ceil,
    load_regime_severity_thresholds,
    normalize_regime_severity,
    regime_severity_fingerprint,
)


def _small_config() -> dict:
    config = load_config()
    config["regime_severity"] = {
        **config["regime_severity"],
        "floor_mc_paths": 2,
        "floor_mc_steps": 8,
        "floor_warmup": 3,
        "floor_seed": 123,
    }
    return config


def test_normalize_regime_severity_clips_noise_and_saturates():
    assert normalize_regime_severity(0.10, floor=0.20, ceil=0.60) == 0.0
    assert normalize_regime_severity(0.60, floor=0.20, ceil=0.60) == 1.0
    assert normalize_regime_severity(0.40, floor=0.20, ceil=0.60) == pytest.approx(0.5)


def test_variance_inflation_ceil_uses_declared_multipliers():
    config = load_config()

    ceil = compute_variance_inflation_ceil(config)

    assert 0.0 < ceil < 1.0


def test_calibration_is_deterministic_for_fixed_seed():
    config = _small_config()

    first = calibrate_regime_severity_thresholds(config)
    second = calibrate_regime_severity_thresholds(config)

    assert first["floor"] == second["floor"]
    assert first["ceil"] == second["ceil"]
    assert first["resonance_method"] == "participation_ratio"
    assert first["resonance_gamma"] == 1.0
    assert first["config_fingerprint"] == second["config_fingerprint"]


def test_fingerprint_changes_when_dimension_caps_change():
    config = load_config()
    baseline = regime_severity_fingerprint(config)
    config["regime_severity"] = {
        **config["regime_severity"],
        "dimension_caps": {
            **config["regime_severity"]["dimension_caps"],
            "spread_anomaly": 0.5,
        },
    }

    assert regime_severity_fingerprint(config) != baseline


def test_fingerprint_changes_when_resonance_gamma_changes():
    config = load_config()
    baseline = regime_severity_fingerprint(config)
    config["regime_severity"] = {
        **config["regime_severity"],
        "resonance_gamma": 2.0,
    }

    assert regime_severity_fingerprint(config) != baseline


def test_threshold_loader_rejects_fingerprint_mismatch(tmp_path, monkeypatch):
    config = load_config()
    resource = tmp_path / "thresholds.json"
    resource.write_text(
        json.dumps(
            {
                "floor": 0.1,
                "ceil": 0.5,
                "config_fingerprint": "wrong",
            }
        )
    )
    config["regime_severity"] = {
        **config["regime_severity"],
        "threshold_resource": resource.name,
    }

    monkeypatch.setattr(
        "src.liquidity.engine.regime_severity._RESOURCE_DIR",
        tmp_path,
    )

    with pytest.raises(ValueError, match="does not match active config"):
        load_regime_severity_thresholds(config)


def test_threshold_loader_accepts_matching_fingerprint(tmp_path, monkeypatch):
    config = load_config()
    resource = tmp_path / "thresholds.json"
    resource.write_text(
        json.dumps(
            {
                "floor": 0.1,
                "ceil": 0.5,
                "config_fingerprint": regime_severity_fingerprint(config),
            }
        )
    )
    config["regime_severity"] = {
        **config["regime_severity"],
        "threshold_resource": resource.name,
    }

    monkeypatch.setattr(
        "src.liquidity.engine.regime_severity._RESOURCE_DIR",
        tmp_path,
    )

    out = load_regime_severity_thresholds(config)

    assert out["floor"] == 0.1
    assert out["ceil"] == 0.5
