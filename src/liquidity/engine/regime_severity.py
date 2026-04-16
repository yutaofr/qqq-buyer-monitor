"""Regime-severity threshold calibration and normalization.

Offline calibration writes static thresholds; runtime only loads and applies
those constants. This keeps BOCPD online inference free of Monte Carlo work.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from src.liquidity.engine.bocpd import BOCPDEngine

_DIM_KEYS = ["ed_accel", "spread_anomaly", "fisher_rho"]
_RESOURCE_DIR = Path(__file__).parent.parent / "resources"


def regime_severity_fingerprint(config: dict) -> str:
    """Fingerprint all config fields that define calibrated thresholds."""
    sev_cfg = config["regime_severity"]
    payload = {
        "formula_version": 3,
        "nig_priors": config["nig_priors"],
        "hazard": config["hazard"],
        "macro_hazard": {
            "lambda_floor": config["macro_hazard"]["lambda_floor"],
            "lambda_ceil": config["macro_hazard"]["lambda_ceil"],
        },
        "overdrive": config.get("overdrive", {}),
        "forgetting": config.get("forgetting", {}),
        "weights": sev_cfg["weights"],
        "floor_quantile": sev_cfg["floor_quantile"],
        "floor_mc_paths": sev_cfg["floor_mc_paths"],
        "floor_mc_steps": sev_cfg["floor_mc_steps"],
        "floor_warmup": sev_cfg["floor_warmup"],
        "floor_seed": sev_cfg["floor_seed"],
        "ceil_multipliers": sev_cfg["ceil_multipliers"],
        "dimension_caps": sev_cfg["dimension_caps"],
        "resonance_method": sev_cfg.get("resonance_method", "participation_ratio"),
        "resonance_gamma": sev_cfg.get("resonance_gamma", 1.0),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def prior_predictive_sigma2(config: dict) -> np.ndarray:
    """Prior predictive Student-t scale implied by NIG priors."""
    priors = config["nig_priors"]
    vals = []
    for key in _DIM_KEYS:
        p = priors[key]
        vals.append(p["beta_0"] * (p["kappa_0"] + 1.0) / (p["alpha_0"] * p["kappa_0"]))
    return np.asarray(vals, dtype=np.float64)


def sample_prior_predictive(config: dict, rng: np.random.Generator) -> np.ndarray:
    """Sample one observation from the NIG prior predictive Student-t."""
    priors = config["nig_priors"]
    sigma2 = prior_predictive_sigma2(config)
    x = np.empty(len(_DIM_KEYS), dtype=np.float64)
    for i, key in enumerate(_DIM_KEYS):
        p = priors[key]
        nu = 2.0 * p["alpha_0"]
        x[i] = p["mu_0"] + np.sqrt(sigma2[i]) * rng.standard_t(df=nu)
    return x


def calibrate_regime_severity_thresholds(
    config: dict,
    *,
    mc_paths: int | None = None,
    mc_steps: int | None = None,
    warmup: int | None = None,
    seed: int | None = None,
) -> dict:
    """Generate floor/ceil thresholds from the model's own prior world."""
    sev_cfg = config["regime_severity"]
    mc_paths = int(mc_paths if mc_paths is not None else sev_cfg["floor_mc_paths"])
    mc_steps = int(mc_steps if mc_steps is not None else sev_cfg["floor_mc_steps"])
    warmup = int(warmup if warmup is not None else sev_cfg["floor_warmup"])
    seed = int(seed if seed is not None else sev_cfg["floor_seed"])
    if mc_paths < 1:
        raise ValueError("mc_paths must be >= 1.")
    if mc_steps <= warmup:
        raise ValueError("mc_steps must be greater than warmup.")

    rng = np.random.default_rng(seed)
    severities: list[float] = []
    lambda_macro = config["macro_hazard"]["lambda_floor"]
    for _ in range(mc_paths):
        engine = BOCPDEngine(config)
        for step in range(mc_steps):
            x_t = sample_prior_predictive(config, rng)
            engine.update(x_t, lambda_macro=lambda_macro)
            if step >= warmup:
                severities.append(float(engine.last_regime_diagnostics["regime_severity"]))

    floor = float(np.quantile(np.asarray(severities, dtype=np.float64), sev_cfg["floor_quantile"]))
    ceil = compute_variance_inflation_ceil(config)
    if ceil <= floor:
        raise ValueError(f"Calibrated ceil must exceed floor. floor={floor}, ceil={ceil}")

    return {
        "version": 1,
        "method": "prior_predictive_null",
        "seed": seed,
        "floor_quantile": sev_cfg["floor_quantile"],
        "mc_paths": mc_paths,
        "mc_steps": mc_steps,
        "warmup": warmup,
        "weights": sev_cfg["weights"],
        "ceil_method": "variance_inflation_scenario",
        "ceil_multipliers": sev_cfg["ceil_multipliers"],
        "dimension_caps": sev_cfg["dimension_caps"],
        "resonance_method": sev_cfg.get("resonance_method", "participation_ratio"),
        "resonance_gamma": sev_cfg.get("resonance_gamma", 1.0),
        "floor": floor,
        "ceil": ceil,
        "config_fingerprint": regime_severity_fingerprint(config),
    }


def compute_variance_inflation_ceil(config: dict) -> float:
    """Compute severity under a declared variance-inflation crisis scenario."""
    sev_cfg = config["regime_severity"]
    weights = sev_cfg["weights"]
    multipliers = sev_cfg["ceil_multipliers"]
    caps = sev_cfg["dimension_caps"]
    gamma = float(sev_cfg.get("resonance_gamma", 1.0))
    method = sev_cfg.get("resonance_method", "participation_ratio")
    weighted_log = 0.0
    total_weight = 0.0
    capped_logs = []
    cap_values = []
    for key in _DIM_KEYS:
        weight = float(weights[key])
        multiplier = float(multipliers[key])
        cap = float(caps.get(key, np.inf))
        if multiplier <= 0.0:
            raise ValueError(f"ceil multiplier must be positive for {key}.")
        if cap < 0.0:
            raise ValueError(f"dimension cap must be non-negative for {key}.")
        capped_log = min(max(0.0, np.log(multiplier)), cap)
        capped_logs.append(capped_log)
        cap_values.append(cap)
        weighted_log += weight * capped_log
        total_weight += weight
    if total_weight <= 0.0:
        raise ValueError("severity weights must sum to a positive value.")
    severity_base = float(1.0 - np.exp(-weighted_log / total_weight))
    if method in {"none", None}:
        return severity_base
    if method != "participation_ratio":
        raise ValueError(f"Unsupported regime_severity.resonance_method={method!r}")

    capped = np.asarray(capped_logs, dtype=np.float64)
    cap_arr = np.asarray(cap_values, dtype=np.float64)
    finite_positive_caps = np.isfinite(cap_arr) & (cap_arr > 0.0)
    resonance_input = np.zeros_like(capped, dtype=np.float64)
    resonance_input[finite_positive_caps] = capped[finite_positive_caps] / cap_arr[finite_positive_caps]
    resonance_input[~finite_positive_caps] = capped[~finite_positive_caps]
    total = float(np.sum(resonance_input))
    if total <= 0.0:
        return severity_base
    denom = float(np.sum(resonance_input * resonance_input))
    if denom <= 0.0:
        return severity_base
    pr = float(np.clip((total * total) / denom, 1.0, float(len(_DIM_KEYS))))
    return float(severity_base * (pr / float(len(_DIM_KEYS))) ** gamma)


def load_regime_severity_thresholds(config: dict) -> dict:
    """Load calibrated thresholds and verify they match the active config."""
    sev_cfg = config["regime_severity"]
    resource = _RESOURCE_DIR / sev_cfg["threshold_resource"]
    with open(resource) as f:
        thresholds = json.load(f)
    expected = regime_severity_fingerprint(config)
    actual = thresholds.get("config_fingerprint")
    if actual != expected:
        raise ValueError(
            "Regime severity threshold resource does not match active config. "
            f"expected={expected}, actual={actual}"
        )
    return thresholds


def normalize_regime_severity(raw: float, floor: float, ceil: float) -> float:
    """Map raw severity into [0, 1] after prior-predictive noise filtering."""
    if ceil <= floor:
        raise ValueError("ceil must be greater than floor.")
    return float(np.clip((raw - floor) / (ceil - floor), 0.0, 1.0))
