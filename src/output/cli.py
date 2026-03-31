"""CLI output formatting for QQQ v11 Bayesian Monitor."""
from __future__ import annotations

import logging

from src.models import SignalResult

logger = logging.getLogger(__name__)

# ANSI color codes
_BOLD = "\033[1m"
_DIM = "\033[2m"
_RED = "\033[91m"
_GREEN = "\033[92m"
_YELLOW = "\033[93m"
_BLUE = "\033[94m"
_CYAN = "\033[96m"
_RESET = "\033[0m"


def print_signal(
    result: SignalResult,
    use_color: bool = True,
    **kwargs,
) -> None:
    """Print a formatted v11 probabilistic signal summary to stdout."""

    def c(code: str) -> str:
        return code if use_color else ""

    r = c(_RESET)

    probs = result.probabilities or {}
    ordered_probs = sorted(probs.items(), key=lambda item: item[1], reverse=True)

    print(f"\n{c(_BOLD)}=== QQQ PROBABILISTIC MONITOR (v11.5) ==={r}")
    print(f"Date:      {result.date}")
    print(f"Price:     ${result.price:.2f}")
    print(
        "Target:    "
        f"beta={result.target_beta:.2f}x | "
        f"regime={result.stable_regime}"
    )

    t = result.target_allocation
    print(
        "Reference: "
        f"Cash={t.target_cash_pct*100:.1f}%, "
        f"QQQ={t.target_qqq_pct*100:.1f}%, "
        f"QLD={t.target_qld_pct*100:.1f}% | "
        f"Entropy={result.entropy:.3f}"
    )

    if ordered_probs:
        formatted = " | ".join(f"{name}={value:.2%}" for name, value in ordered_probs)
        print(f"Posterior: {formatted}")

    metadata = result.metadata or {}
    quality = metadata.get("quality_audit", {})
    if quality:
        anomalies = ", ".join(quality.get("anomalies", [])) or "none"
        print(f"Audit:     anomalies={anomalies}")

    print(f"\n{c(_CYAN)}Rationale:{r}")
    print(result.explanation)
    print(f"{c(_BOLD)}---{r}")
