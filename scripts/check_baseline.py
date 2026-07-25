import sqlite3
import os

db_path = "baseline_state.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    total = conn.execute("SELECT COUNT(*) FROM state_log").fetchone()[0]
    null_pmv = conn.execute("SELECT COUNT(*) FROM state_log WHERE zone_pmv IS NULL").fetchone()[0]
    rows = conn.execute("SELECT sim_time_hours, zone_name, zone_temp_c, zone_pmv, zone_iaq_vent_flow, hvac_elec_kw FROM state_log ORDER BY id DESC LIMIT 10").fetchall()
    conn.close()
    
    print(f"=== Baseline DB Status ({db_path}) ===")
    print(f"Total Rows: {total}")
    print(f"PMV NULL count: {null_pmv}/{total} ({null_pmv/total*100:.1f}% NULL if total>0 else 0)")
    print("\nLatest 10 rows:")
    for r in rows:
        print(r)
else:
    print(f"{db_path} does not exist yet.")
