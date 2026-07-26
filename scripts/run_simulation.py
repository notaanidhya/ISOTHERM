import sys
import os

# Ensure UTF-8 output encoding for Windows terminal
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

EP_PATH = r"C:\EnergyPlusV26-1-0"
if EP_PATH not in sys.path:
    sys.path.insert(0, EP_PATH)

from src.config import PREPARED_IDF_PATH, WEATHER_PATH, DB_PATH
from src.energyplus_runner.runner import run_synchronous_simulation

def main():
    print("================================================================")
    print("STARTING CLOSED-LOOP AI-POWERED SMART BUILDING CONTROL SYSTEM")
    print("================================================================")
    
    run_synchronous_simulation(
        idf_path=PREPARED_IDF_PATH,
        epw_path=WEATHER_PATH,
        output_dir="sim_output",
        db_path=DB_PATH
    )

if __name__ == "__main__":
    main()
