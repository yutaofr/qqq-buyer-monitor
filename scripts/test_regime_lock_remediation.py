import logging
import os

import numpy as np

from src.engine.v11.conductor import V11Conductor
from src.engine.v11.core.bayesian_inference import BayesianInferenceEngine
from src.engine.v11.core.prior_knowledge import PriorKnowledgeBase

# Setup logging
logging.basicConfig(level=logging.WARNING) # Reduce noise
logger = logging.getLogger(__name__)

def evaluate_config(anchor_floor, mid_inertia, bleed_eps=1e-15):
    prior_path = f"tmp/prior_{anchor_floor}_{mid_inertia}.json"
    if os.path.exists(prior_path): os.remove(prior_path)

    # Monkey-patch BayesianInferenceEngine for the floor and normalization
    original_infer = BayesianInferenceEngine.infer_gaussian_nb_posterior
    original_norm = BayesianInferenceEngine._normalize
    original_prior_norm = PriorKnowledgeBase._normalize

    def patched_norm(self, weights):
        if not weights: return {}
        sanitized = {str(k): max(0.0, float(v)) for k, v in weights.items()}
        total = float(sum(sanitized.values()))
        if total <= 0:
            n = len(sanitized)
            return {k: 1.0 / n for k in sanitized}
        # Inject custom bleed_eps
        return {k: (v + bleed_eps) / (total + (len(sanitized) * bleed_eps)) for k, v in sanitized.items()}

    # We need to reach into the method and change the hardcoded 0.5
    # Since we can't easily change the code on the fly without replace_file_content,
    # I'll just use a wrapper that detects when it's being called and I'll have to
    # actually edit the source code for the "final" fix.
    # For this experiment, I'll temporarily edit the source if I have to,
    # but let's see if I can do it via environment variables if the code supports it.

    # It seems the code doesn't support an env var for the anchor.
    # I will create a temporary version of the engine file for testing if needed,
    # but for now, let's just use the current code to confirm the 100% lock
    # once the circuit breaker is disabled.

    conductor = V11Conductor(
        training_cutoff="2018-01-01",
        prior_state_path=prior_path
    )

    from src.engine.baseline.data_loader import load_all_baseline_data
    data = load_all_baseline_data()
    eval_dates = data.index[(data.index >= "2026-01-01") & (data.index <= "2026-01-31")].unique()

    results = []
    for dt in eval_dates:
        # FORCE DISABLE CIRCUIT BREAKER
        conductor.high_entropy_streak = 0

        # Override inertia in memory if possible
        # self.prior_book is initialized, we can't easily change the logic without editing source.

        runtime = conductor.daily_run(data.loc[:dt])
        probs = runtime["probabilities"]
        results.append(probs.get("MID_CYCLE", 0.0))

    return np.mean(results), np.max(results), np.min(results)

if __name__ == "__main__":
    print("Evaluating BASELINE (Current Code, Circuit Breaker Disabled)...")
    mean_p, max_p, min_p = evaluate_config(0.5, 0.98)
    print(f"MID_CYCLE Prob - Mean: {mean_p:.6f}, Max: {max_p:.6f}, Min: {min_p:.6f}")
