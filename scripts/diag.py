import sqlite3

conn = sqlite3.connect("sim_state.db")
rows = conn.execute("SELECT zone_name, zone_temp_c, zone_pmv, zone_iaq_vent_flow, hvac_elec_kw FROM state_log ORDER BY id DESC LIMIT 15").fetchall()
print("Latest 15 rows from state_log:")
for r in rows:
    print(r)

null_pmv = conn.execute("SELECT COUNT(*) FROM state_log WHERE zone_pmv IS NULL").fetchone()[0]
total = conn.execute("SELECT COUNT(*) FROM state_log").fetchone()[0]
print(f"\nPMV null count: {null_pmv}/{total} ({null_pmv/total*100:.1f}% NULL)")

zones = [r[0] for r in conn.execute("SELECT DISTINCT zone_name FROM state_log").fetchall()]
print(f"Distinct zones tracked: {zones}")

hvac_sample = conn.execute("SELECT sim_time_hours, hvac_elec_kw FROM state_log ORDER BY id DESC LIMIT 5").fetchall()
print(f"\nLatest HVAC kW readings: {hvac_sample}")

dec = conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
actions = conn.execute("SELECT COUNT(*) FROM action_queue WHERE applied=1").fetchone()[0]
print(f"\nTotal LLM decisions logged: {dec}")
print(f"Total actions applied to actuators: {actions}")
