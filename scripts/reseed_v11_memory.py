import logging

from src.engine.v11.utils.memory_booster import SovereignMemoryBooster

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s – %(message)s")
logger = logging.getLogger(__name__)


def reseed():
    """Manual trigger for Sovereign Memory Bootstrap (DNA)."""
    print("=== Sovereign Memory Manual Reseed (v11 DNA) ===")
    booster = SovereignMemoryBooster()
    # Force reseed to apply latest characteristic fingerprints
    booster.ensure_baseline(force=True)
    print("Success. DNA memory reloaded.")


if __name__ == "__main__":
    reseed()
