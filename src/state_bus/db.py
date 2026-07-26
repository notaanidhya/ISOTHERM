import os
import sqlite3
import threading
from src.config import DB_PATH

_db_lock = threading.Lock()

def get_connection(db_path=DB_PATH):
    """Returns a fresh thread-safe SQLite connection with timeout and autocommit."""
    conn = sqlite3.connect(db_path, timeout=10.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path=DB_PATH, reset=False):
    """Initializes the 3 SQLite tables for sensor data, pending actions, and LLM decisions."""
    if reset and os.path.exists(db_path):
        try:
            os.remove(db_path)
            print(f"Removed stale database at: {db_path}")
        except Exception as e:
            print(f"Warning clearing database {db_path}: {e}")

    with _db_lock:
        with get_connection(db_path) as conn:
            cursor = conn.cursor()
            
            # Table 1: Real-time sensor snapshots
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS state_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sim_time_hours REAL NOT NULL,
                wall_time TEXT NOT NULL,
                zone_name TEXT NOT NULL,
                zone_temp_c REAL,
                zone_pmv REAL,
                zone_iaq_vent_flow REAL,
                heating_sp_c REAL,
                cooling_sp_c REAL,
                hvac_elec_kw REAL,
                hvac_gas_kw REAL DEFAULT 0.0,
                outdoor_temp_c REAL,
                solar_irradiance REAL
            );
            """)
            try:
                cursor.execute("ALTER TABLE state_log ADD COLUMN hvac_gas_kw REAL DEFAULT 0.0")
            except Exception:
                pass
            
            # Table 2: Action queue (written by LLM / MCP tool, consumed by EnergyPlus callback)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS action_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                zone_name TEXT NOT NULL,
                heating_setpoint_c REAL NOT NULL,
                cooling_setpoint_c REAL NOT NULL,
                applied INTEGER DEFAULT 0
            );
            """)
            
            # Table 3: Decisions audit log
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sim_time_hours REAL NOT NULL,
                wall_time TEXT NOT NULL,
                state_snapshot TEXT NOT NULL,
                llm_reasoning TEXT NOT NULL,
                action_taken TEXT NOT NULL,
                energy_before_kwh REAL,
                cost_before_usd REAL,
                comfort_violations INTEGER,
                model_used TEXT
            );
            """)
            conn.commit()
    print(f"Database initialized at: {db_path}")

if __name__ == "__main__":
    init_db()
