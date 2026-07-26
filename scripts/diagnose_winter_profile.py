import sqlite3
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def analyze_profile(db_path, label):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    print(f"\n=======================================================")
    print(f"  {label} — HOURLY PROFILE FOR WINTER (Jan 15)")
    print(f"=======================================================")
    print("Hour | Htg_SP | Clg_SP | Zone_Temp | Mean_PMV | Comfort % (in [-0.5, 0.5])")
    print("-----+--------+--------+-----------+----------+---------------------------")
    
    for h in range(0, 24):
        query = """
            SELECT avg(heating_sp_c), avg(cooling_sp_c), avg(zone_temp_c), avg(zone_pmv),
                   count(case when zone_pmv between -0.5 and 0.5 then 1 end),
                   count(case when zone_pmv is not null then 1 end)
            FROM state_log
            WHERE sim_time_hours <= 360.0 AND (CAST(sim_time_hours AS INTEGER) % 24) = ?
        """
        row = cursor.execute(query, (h,)).fetchone()
        h_sp, c_sp, temp, pmv, ok, tot = row
        pct = (ok / tot * 100.0) if tot and tot > 0 else 0.0
        pmv_str = f"{pmv:8.2f}" if pmv is not None else "     N/A"
        print(f" {h:02d}:00 | {h_sp:6.1f} | {c_sp:6.1f} | {temp:9.2f} | {pmv_str} | {pct:5.1f}% ({ok}/{tot})")
    conn.close()

if __name__ == "__main__":
    analyze_profile("baseline_state.db", "UNMANAGED BASELINE")
    analyze_profile("sim_state.db", "AI CLOSED-LOOP CONTROL")
