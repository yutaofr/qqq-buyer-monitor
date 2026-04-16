#!/usr/bin/env python3
"""Offline calibration for regime-severity normalization thresholds.

This script intentionally runs outside the online BOCPD/backtest path. It
uses the same BOCPD engine as runtime inference, then writes static thresholds
to src/liquidity/resources/regime_severity_thresholds.json.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.liquidity.config import load_config
from src.liquidity.engine.regime_severity import calibrate_regime_severity_thresholds


DEFAULT_OUTPUT = Path("src/liquidity/resources/regime_severity_thresholds.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--mc-paths", type=int, default=None)
    parser.add_argument("--mc-steps", type=int, default=None)
    parser.add_argument("--warmup", type=int, default=None)
    parser.add_argument("--seed", type=int, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config()
    thresholds = calibrate_regime_severity_thresholds(
        config,
        mc_paths=args.mc_paths,
        mc_steps=args.mc_steps,
        warmup=args.warmup,
        seed=args.seed,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(thresholds, indent=2, sort_keys=True) + "\n")
    print(json.dumps(thresholds, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
