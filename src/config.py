import os
import sys

# Ensure UTF-8 output encoding for Windows terminal
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Root project paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ENERGYPLUS_DIR = r"C:\EnergyPlusV26-1-0"

# Model paths
BASE_IDF_PATH = os.path.join(PROJECT_ROOT, "building_model", "5ZoneAirCooled.idf")
PREPARED_IDF_PATH = os.path.join(PROJECT_ROOT, "building_model", "5ZoneAirCooled_Prepared.idf")
OPTIMIZED_IDF_PATH = os.path.join(PROJECT_ROOT, "building_model", "5ZoneAirCooled_AI_Optimized.idf")
WEATHER_PATH = os.path.join(PROJECT_ROOT, "building_model", "USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw")

# Database path
DB_PATH = os.path.join(PROJECT_ROOT, "sim_state.db")
BASELINE_DB_PATH = os.path.join(PROJECT_ROOT, "baseline_state.db")

# Zones & Control constants
ZONES = ["SPACE1-1", "SPACE2-1", "SPACE3-1", "SPACE4-1", "SPACE5-1"]
OLLAMA_MODEL = "llama3.1:latest"

# Safety boundaries
SAFETY_BOUNDS = {
    "heating": (16.0, 24.0),
    "cooling": (22.0, 30.0),
}
MIN_DEADBAND = 2.0  # °C minimum gap between heating and cooling setpoints
