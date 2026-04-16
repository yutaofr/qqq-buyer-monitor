"""Global constants and configuration for QQQ Resonance Engine."""

ENGINE_VERSION = "v14.0-ULTIMA"

# 核心引擎 Burn-in 所需的最小连续交易日行数 (Market Integrity Constraint)
# Bayesian Engine Requirements (v16.4 SRE Hardening)
MIN_BURN_IN_DAYS = 1000            # Technical minimum for Bayesian transition stabilization
MIN_STRUCTURAL_WINDOW_DAYS = 1260   # 5-year statistical anchor for Z-Score factors
LOOKBACK_BUFFER_FACTOR = 1.25       # Buffer to absorb NaNs and market holidays
SENTINEL_FILE_PATH = "data/.bootstrap_deadletter"
