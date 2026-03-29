import os

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import pandas as pd


def plot_dca_performance():
    cache_path = "data/qqq_history_cache.csv"
    if not os.path.exists(cache_path):
        print(f"Error: Run the backtester first to generate {cache_path}.")
        return

    # Load backtest history to re-construct basic navs for plotting
    qqq = pd.read_csv(cache_path, index_col=0, parse_dates=True)
    qqq.index = pd.to_datetime(qqq.index, utc=True)

    # We will invoke the backtester to get the full daily_timeseries
    import sys
    sys.path.append(os.getcwd())
    from src.backtest import Backtester, _load_research_macro_dataset
    from src.collector.historical_macro_seeder import HistoricalMacroSeeder

    macro_df = _load_research_macro_dataset("data/macro_historical_dump.csv")
    seeder = HistoricalMacroSeeder(mock_df=macro_df)

    import logging
    logging.getLogger().setLevel(logging.ERROR)

    tester = Backtester(initial_capital=10_000)
    summary = tester.simulate_portfolio(qqq, seeder, enable_dynamic_search=True, registry_path="data/candidate_registry_v7.json")
    daily_ts = summary.daily_timeseries

    if daily_ts is None or daily_ts.empty:
        print("Failed to run backtest or retrieve daily_timeseries.")
        return

    plt.style.use('dark_background')
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), gridspec_kw={'height_ratios': [3, 1]})

    # Plot 1: NAV Growth
    ax1.plot(daily_ts.index, daily_ts['nav'], label='v8.1 Tactical Model (DCA)', color='#00ff9d', linewidth=1.5)
    ax1.plot(daily_ts.index, daily_ts['baseline_nav'], label='Baseline Benchmark (DCA)', color='#ff3366', linewidth=1.5, alpha=0.7)

    # Highlight add events
    adds = daily_ts[daily_ts['deployment_state'] != 'DEPLOY_PAUSE']

    ax1.set_title(f'v8.1 QQQ Add-Timing Performance vs Baseline DCA\nAvg Cost Improvement: {summary.average_cost_improvement_vs_baseline_dca*100:.2f}% | Signal Beta: {summary.signal_beta:.2f}', fontsize=14, pad=15)
    ax1.set_ylabel('Portfolio NAV ($)', fontsize=12)
    ax1.yaxis.set_major_formatter(mtick.StrMethodFormatter('${x:,.0f}'))
    ax1.grid(True, alpha=0.2, linestyle='--')
    ax1.legend(loc='upper left')

    # Plot 2: Reserve Cash Depletion (Incremental Deployments)
    est_reserve_cash = (daily_ts['reserve_cash_pct'] / 100.0) * daily_ts['nav']
    ax2.fill_between(daily_ts.index, 0, est_reserve_cash, color='#00ccff', alpha=0.3, label='Reserve Cash Buffer')
    ax2.plot(daily_ts.index, est_reserve_cash, color='#00ccff', linewidth=1)

    # Mark states where deployment was paused
    pauses = daily_ts[daily_ts['deployment_state'] == 'DEPLOY_PAUSE']
    ax2.scatter(pauses.index, (pauses['reserve_cash_pct'] / 100.0 * pauses['nav']), color='#ff9900', s=10, label='Deploy Paused (Crisis/Rich)', zorder=5)

    ax2.set_title('Reserve Cash Deployments (100% Invested indicates $0 Balance)', fontsize=12, pad=10)
    ax2.set_ylabel('Cash ($)', fontsize=12)
    ax2.yaxis.set_major_formatter(mtick.StrMethodFormatter('${x:,.0f}'))
    ax2.grid(True, alpha=0.2, linestyle='--')
    ax2.legend(loc='upper right')

    plt.tight_layout()
    os.makedirs("artifacts", exist_ok=True)
    out_path = "artifacts/dca_timing_performance.png"
    plt.savefig(out_path, dpi=300, bbox_inches='tight', facecolor=fig.get_facecolor())
    print(f"Successfully generated visualization to: {out_path}")

if __name__ == "__main__":
    plot_dca_performance()
