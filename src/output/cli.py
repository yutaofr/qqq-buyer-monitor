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
_MAGENTA = "\033[95m"
_WHITE = "\033[97m"
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
    metadata = result.metadata or {}

    # 1. PANORAMA ENSEMBLE VERDICT (Top Priority)
    verdict = metadata.get("v14_ensemble_verdict", "NEUTRAL")
    verdict_label = metadata.get("v14_ensemble_verdict_label", verdict)
    s_beta = metadata.get("v14_standard_beta", result.target_beta)
    p_beta = metadata.get("v14_s4_protective_beta", 0.5)
    a_beta = metadata.get("v14_s5_aggressive_beta", result.target_beta)

    v_color = _YELLOW
    if verdict == "PROTECTIVE":
        v_color = _RED
    if verdict == "AGGRESSIVE":
        v_color = _GREEN

    print(f"\n{c(_BOLD)}{c(_MAGENTA)}=== QQQ PANORAMA ENSEMBLE VERDICT (v14.8) ==={r}")
    print(f"Status:  {c(_BOLD)}{c(v_color)}{verdict}{r}")
    if verdict_label != verdict:
        print(f"Label:   {c(_DIM)}{verdict_label}{r}")
    print(f"Action:  {c(_CYAN)}Target Beta {s_beta:.2f}x{r} (Standard Choice)")
    print(
        f"Options: {c(_BOLD)}{c(_WHITE)}[S4 Protective: {p_beta:.2f}x] | [S5 Aggressive: {a_beta:.2f}x]{r}"
    )
    print(f"{c(_DIM)}> Info: Beta 0.50 is the absolute physical floor (User Policy).{r}")
    print(f"{c(_BOLD)}---{r}")

    # 2. BAYESIAN MONITOR (Logic Source)
    print(f"\n{c(_BOLD)}=== QQQ PROBABILISTIC MONITOR (v12.0) ==={r}")
    print(f"Date:      {result.date}")
    print(f"Price:     ${result.price:.2f}")
    print(f"Target:    beta={result.target_beta:.2f}x | regime={result.stable_regime}")

    t = result.target_allocation
    print(
        "Reference: "
        f"Cash={t.target_cash_pct * 100:.1f}%, "
        f"QQQ={t.target_qqq_pct * 100:.1f}%, "
        f"QLD={t.target_qld_pct * 100:.1f}% | "
        f"Entropy={result.entropy:.3f}"
    )

    if ordered_probs:
        formatted = " | ".join(f"{name}={value:.2%}" for name, value in ordered_probs)
        print(f"Posterior: {formatted}")

    # 3. PIPELINE DIAGNOSTIC AUDIT
    print(f"\n{c(_CYAN)}Pipeline Diagnostic Audit (v14.8):{r}")

    baseline_prob = metadata.get("v14_baseline_prob")
    sidecar_prob = metadata.get("v14_sidecar_prob")

    def format_status(status: str) -> str:
        if status == "success":
            return f"{c(_GREEN)}{status}{r}"
        if "audit_failed" in status:
            return f"{c(_RED)}{c(_BOLD)}!!! {status} !!!{r}"
        if status == "insufficient_sample":
            return f"{c(_YELLOW)}{status}{r}"
        return f"{c(_DIM)}{status}{r}"

    if baseline_prob is not None:
        b_status = metadata.get("v14_baseline_status", "success")
        print(
            f"  Tractor (SPY Macro):  prob={baseline_prob:.2%} | status={format_status(b_status)}"
        )

    if sidecar_prob is not None:
        s_status = metadata.get("v14_sidecar_status", "success")
        print(f"  Sidecar (QQQ Tech):   prob={sidecar_prob:.2%} | status={format_status(s_status)}")

    print(f"\n{c(_CYAN)}Rationale:{r}")
    print(result.explanation)
    print(f"{c(_BOLD)}---{r}")
