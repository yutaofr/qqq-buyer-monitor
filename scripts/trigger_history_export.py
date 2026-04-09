
import os
import sys

# Add src to path
sys.path.append(os.getcwd())

from src.output.web_exporter import export_history_json

if __name__ == "__main__":
    print("Exporting history.json from signals.db...")
    success = export_history_json()
    if success:
        print("Success: history.json exported to src/web/public/history.json")
    else:
        print("Error: History export failed (check if database is seeded).")
