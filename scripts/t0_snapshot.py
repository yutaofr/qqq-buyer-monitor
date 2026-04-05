import logging

from src.engine.baseline.execution import run_baseline_inference

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_t0_prediction():
    # This calls the production entry point
    results = run_baseline_inference()

    print("\n--- Current T+0 Risk State ---")
    print(f"Date: {results.get('date', 'Today')}")
    print(
        f"Mud Tractor (SPY) Risk: {results['tractor']['prob']:.4f} ({results['tractor']['status']})"
    )
    print(
        f"QQQ Sidecar (QQQ) Risk: {results['sidecar']['prob']:.4f} ({results['sidecar']['status']})"
    )

    # Check if they are passing audits
    print(f"Tractor Status: {results['tractor']['status']}")
    print(f"Sidecar Status: {results['sidecar']['status']}")


if __name__ == "__main__":
    get_t0_prediction()
