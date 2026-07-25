import json
import datetime
from src.state_bus.db import get_connection, _db_lock, DB_PATH
from src.config import ZONES

def insert_state_log(sim_time_hours, zone_name, temp_c, pmv, vent_flow, heating_sp, cooling_sp, hvac_kw, outdoor_temp, solar, db_path=DB_PATH):
    wall_time = datetime.datetime.now().isoformat()
    with _db_lock:
        with get_connection(db_path) as conn:
            conn.execute("""
            INSERT INTO state_log 
            (sim_time_hours, wall_time, zone_name, zone_temp_c, zone_pmv, zone_iaq_vent_flow, heating_sp_c, cooling_sp_c, hvac_elec_kw, outdoor_temp_c, solar_irradiance)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (sim_time_hours, wall_time, zone_name, temp_c, pmv, vent_flow, heating_sp, cooling_sp, hvac_kw, outdoor_temp, solar))
            conn.commit()

def insert_action(zone_name, heating_sp_c, cooling_sp_c, db_path=DB_PATH):
    created_at = datetime.datetime.now().isoformat()
    with _db_lock:
        with get_connection(db_path) as conn:
            conn.execute("""
            INSERT INTO action_queue (created_at, zone_name, heating_setpoint_c, cooling_setpoint_c, applied)
            VALUES (?, ?, ?, ?, 0)
            """, (created_at, zone_name, heating_sp_c, cooling_sp_c))
            conn.commit()

def get_pending_actions(db_path=DB_PATH):
    with _db_lock:
        with get_connection(db_path) as conn:
            rows = conn.execute("SELECT * FROM action_queue WHERE applied = 0").fetchall()
            return [dict(r) for r in rows]

def mark_action_applied(action_id, db_path=DB_PATH):
    with _db_lock:
        with get_connection(db_path) as conn:
            conn.execute("UPDATE action_queue SET applied = 1 WHERE id = ?", (action_id,))
            conn.commit()

def get_latest_state(db_path=DB_PATH):
    with _db_lock:
        with get_connection(db_path) as conn:
            zones_data = []
            for z in ZONES:
                row = conn.execute("""
                SELECT * FROM state_log WHERE zone_name = ? ORDER BY id DESC LIMIT 1
                """, (z,)).fetchone()
                if row:
                    zones_data.append(dict(row))
            return zones_data

def get_recent_history(hours=4, db_path=DB_PATH):
    with _db_lock:
        with get_connection(db_path) as conn:
            latest_row = conn.execute("SELECT sim_time_hours FROM state_log ORDER BY id DESC LIMIT 1").fetchone()
            if not latest_row:
                return []
            current_time = latest_row["sim_time_hours"]
            min_time = max(0.0, current_time - hours)
            rows = conn.execute("""
            SELECT zone_name, CAST(sim_time_hours AS INT) as hour, AVG(zone_temp_c) as avg_temp, AVG(zone_pmv) as avg_pmv, AVG(zone_iaq_vent_flow) as avg_iaq, AVG(hvac_elec_kw) as avg_hvac_kw, AVG(outdoor_temp_c) as avg_outdoor
            FROM state_log
            WHERE sim_time_hours >= ?
            GROUP BY zone_name, hour
            ORDER BY hour DESC
            """, (min_time,)).fetchall()
            return [dict(r) for r in rows]

def insert_decision(sim_time_hours, state_snapshot, llm_reasoning, action_taken, energy_before_kwh=0.0, cost_before_usd=0.0, comfort_violations=0, model_used="llama3.1:8b-instruct", db_path=DB_PATH):
    wall_time = datetime.datetime.now().isoformat()
    with _db_lock:
        with get_connection(db_path) as conn:
            conn.execute("""
            INSERT INTO decisions 
            (sim_time_hours, wall_time, state_snapshot, llm_reasoning, action_taken, energy_before_kwh, cost_before_usd, comfort_violations, model_used)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                sim_time_hours,
                wall_time,
                json.dumps(state_snapshot) if not isinstance(state_snapshot, str) else state_snapshot,
                llm_reasoning,
                json.dumps(action_taken) if not isinstance(action_taken, str) else action_taken,
                energy_before_kwh,
                cost_before_usd,
                comfort_violations,
                model_used
            ))
            conn.commit()
