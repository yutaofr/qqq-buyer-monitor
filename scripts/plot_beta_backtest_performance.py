from __future__ import annotations

import os
import tempfile
from pathlib import Path

_CACHE_ROOT = Path(os.environ.get("XDG_CACHE_HOME", Path(tempfile.gettempdir()) / "codex-cache"))
_CACHE_ROOT.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("XDG_CACHE_HOME", str(_CACHE_ROOT))
_MPLCONFIGDIR = Path(os.environ.get("MPLCONFIGDIR", _CACHE_ROOT / "matplotlib"))
_MPLCONFIGDIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_MPLCONFIGDIR))


def plot_beta_backtest_performance() -> None:
    import pandas as pd

    from src.backtest import Backtester, _load_research_macro_dataset
    from src.collector.historical_macro_seeder import HistoricalMacroSeeder
    from src.output.backtest_plots import save_beta_backtest_figure

    cache_path = "data/qqq_history_cache.csv"
    if not os.path.exists(cache_path):
        print(f"Error: Run the backtester first to generate {cache_path}.")
        return

    qqq = pd.read_csv(cache_path, index_col=0, parse_dates=True)
    qqq.index = pd.to_datetime(qqq.index, utc=True)

    macro_df = _load_research_macro_dataset("data/macro_historical_dump.csv")
    seeder = HistoricalMacroSeeder(mock_df=macro_df)

    import logging

    logging.getLogger().setLevel(logging.ERROR)

    tester = Backtester(initial_capital=100_000)
    signal_daily_ts = tester.build_signal_timeseries(
        qqq,
        macro_seeder=seeder,
        registry_path="data/candidate_registry_v7.json",
    )

    if signal_daily_ts.empty:
        print("Failed to build signal_timeseries for stock-beta visualization.")
        return

    out_paths = [
        "artifacts/v8.1_beta_recommendation_performance.png",
        "docs/images/v8.1_beta_recommendation_performance.png",
    ]
    saved_paths = save_beta_backtest_figure(signal_daily_ts, None, out_paths)
    for path in saved_paths:
        print(f"Successfully generated visualization to: {path}")


if __name__ == "__main__":
    plot_beta_backtest_performance()
