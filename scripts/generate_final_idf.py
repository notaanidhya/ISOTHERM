import os
import sys
import json
import sqlite3
from eppy.modeleditor import IDF

# Ensure UTF-8 output encoding for Windows terminal
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.config import PREPARED_IDF_PATH, OPTIMIZED_IDF_PATH, DB_PATH, ENERGYPLUS_DIR, ZONES

IDD_FILE = os.path.join(ENERGYPLUS_DIR, "Energy+.idd")

def generate_optimized_idf():
    print("=========================================================")
    print("🏗️ GENERATING PHYSICAL DELIVERABLE 2: AI OPTIMIZED IDF")
    print("=========================================================")

    if not os.path.exists(DB_PATH):
        print(f"Error: {DB_PATH} not found.")
        return

    # Read decisions from SQLite
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT action_taken FROM decisions").fetchall()
    conn.close()

    if not rows:
        print("No decision records found in DB.")
        return

    # Aggregate setpoints by zone
    zone_htg_setpoints = {z: 21.0 for z in ZONES}
    zone_clg_setpoints = {z: 24.0 for z in ZONES}

    for row in rows:
        try:
            actions = json.loads(row[0]) if isinstance(row[0], str) else row[0]
            if isinstance(actions, list):
                for act in actions:
                    z = act.get("zone_name") or act.get("zone")
                    if z in ZONES:
                        zone_htg_setpoints[z] = float(act.get("heating_c", 21.0))
                        zone_clg_setpoints[z] = float(act.get("cooling_c", 24.0))
        except Exception:
            pass

    IDF.setiddname(IDD_FILE)
    idf = IDF(PREPARED_IDF_PATH)

    for z in ZONES:
        htg_sch = idf.getobject("SCHEDULE:COMPACT", f"Htg-SetP-Sch-{z}")
        clg_sch = idf.getobject("SCHEDULE:COMPACT", f"Clg-SetP-Sch-{z}")

        htg_val = zone_htg_setpoints[z]
        clg_val = zone_clg_setpoints[z]

        if htg_sch:
            htg_sch.Field_4 = htg_val
            print(f"  + Updated {htg_sch.Name} default setpoint to {htg_val}°C")

        if clg_sch:
            clg_sch.Field_4 = clg_val
            print(f"  + Updated {clg_sch.Name} default setpoint to {clg_val}°C")

    idf.saveas(OPTIMIZED_IDF_PATH)
    print(f"\nSUCCESS: Physical deliverable 2 created at: {OPTIMIZED_IDF_PATH}")

if __name__ == "__main__":
    generate_optimized_idf()
