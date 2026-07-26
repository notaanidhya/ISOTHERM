import os
import sys
import json
import sqlite3
import pandas as pd

# Ensure UTF-8 output encoding for Windows terminal
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.config import DB_PATH, BASELINE_DB_PATH
from src.utils.carbon import get_tou_price, get_carbon_intensity

def analyze_db(db_path):
    if not os.path.exists(db_path):
        return None
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(
        "SELECT sim_time_hours, zone_name, zone_temp_c, zone_pmv, zone_iaq_vent_flow, hvac_elec_kw, outdoor_temp_c FROM state_log",
        conn
    )
    conn.close()
    
    if df.empty:
        return None
        
    df['hour'] = df['sim_time_hours'].astype(int) % 24
    df['tou_price'] = df['hour'].apply(get_tou_price)
    df['carbon_g'] = df['hour'].apply(get_carbon_intensity)

    # Number of zones (each timestep logs 1 row per zone)
    n_zones = len(df['zone_name'].unique()) or 5

    # Convert average kW per timestep (15 min = 0.25 hours) to kWh per zone row
    # Divide by n_zones to get actual whole-building total kWh, cost, and carbon
    df['kwh_row'] = df['hvac_elec_kw'] * 0.25
    df['cost_row'] = df['kwh_row'] * df['tou_price']
    df['carbon_row'] = (df['kwh_row'] * df['carbon_g']) / 1000.0

    total_kwh = float(df['kwh_row'].sum()) / n_zones
    total_cost_usd = float(df['cost_row'].sum()) / n_zones
    total_carbon_kg = float(df['carbon_row'].sum()) / n_zones
    peak_kw = float(df['hvac_elec_kw'].max())

    # Occupied (08:00-18:00) vs Unoccupied (18:00-08:00) Energy Split
    df['is_occupied'] = (df['hour'] >= 8) & (df['hour'] <= 18)
    occupied_df = df[df['is_occupied']]
    unoccupied_df = df[~df['is_occupied']]

    occ_kwh = float(occupied_df['kwh_row'].sum()) / n_zones
    unocc_kwh = float(unoccupied_df['kwh_row'].sum()) / n_zones
    unocc_kwh_pct = (unocc_kwh / total_kwh * 100.0) if total_kwh > 0 else 0.0

    # Peak TOU Hours (12:00-18:00)
    peak_tou_df = df[(df['hour'] >= 12) & (df['hour'] <= 18)]
    peak_tou_kwh = float(peak_tou_df['kwh_row'].sum()) / n_zones
    peak_tou_cost = float(peak_tou_df['cost_row'].sum()) / n_zones

    # Comfort Compliance (Occupied hours PMV within [-0.5, +0.5])
    if not occupied_df.empty and occupied_df['zone_pmv'].notnull().any():
        pmv_valid = occupied_df[occupied_df['zone_pmv'].notnull()]
        in_range = pmv_valid[(pmv_valid['zone_pmv'] >= -0.5) & (pmv_valid['zone_pmv'] <= 0.5)]
        comfort_compliance_pct = (len(in_range) / len(pmv_valid)) * 100.0
        
        # Breakdown: cold vs hot
        too_cold_pct = (len(pmv_valid[pmv_valid['zone_pmv'] < -0.5]) / len(pmv_valid)) * 100.0
        too_hot_pct  = (len(pmv_valid[pmv_valid['zone_pmv'] > 0.5]) / len(pmv_valid)) * 100.0
        mean_pmv     = float(pmv_valid['zone_pmv'].mean())
    else:
        comfort_compliance_pct = 100.0
        too_cold_pct = 0.0
        too_hot_pct  = 0.0
        mean_pmv     = 0.0

    # Peak TOU Comfort Compliance
    if not peak_tou_df.empty and peak_tou_df['zone_pmv'].notnull().any():
        peak_pmv_valid = peak_tou_df[peak_tou_df['zone_pmv'].notnull()]
        peak_in_range = peak_pmv_valid[(peak_pmv_valid['zone_pmv'] >= -0.5) & (peak_pmv_valid['zone_pmv'] <= 0.5)]
        peak_comfort_pct = (len(peak_in_range) / len(peak_pmv_valid)) * 100.0
    else:
        peak_comfort_pct = comfort_compliance_pct

    # Per-Zone Comfort Breakdown
    per_zone_comfort = {}
    for zone, g in occupied_df.groupby('zone_name'):
        g_valid = g[g['zone_pmv'].notnull()]
        if not g_valid.empty:
            g_ok = g_valid[(g_valid['zone_pmv'] >= -0.5) & (g_valid['zone_pmv'] <= 0.5)]
            per_zone_comfort[zone] = {
                "comfort_pct": float(len(g_ok) / len(g_valid) * 100.0),
                "mean_pmv": float(g_valid['zone_pmv'].mean()),
                "mean_temp_c": float(g_valid['zone_temp_c'].mean())
            }

    iaq_ok = df[df['zone_iaq_vent_flow'] >= 0.005]
    iaq_compliance_pct = (len(iaq_ok) / len(df)) * 100.0 if not df.empty else 100.0

    return {
        "total_kwh": total_kwh,
        "total_cost_usd": total_cost_usd,
        "total_carbon_kg": total_carbon_kg,
        "peak_kw": peak_kw,
        "occupied_kwh": occ_kwh,
        "unoccupied_kwh": unocc_kwh,
        "unoccupied_kwh_pct": unocc_kwh_pct,
        "peak_tou_kwh": peak_tou_kwh,
        "peak_tou_cost_usd": peak_tou_cost,
        "comfort_compliance_pct": float(comfort_compliance_pct),
        "too_cold_pct": float(too_cold_pct),
        "too_hot_pct": float(too_hot_pct),
        "mean_pmv": mean_pmv,
        "peak_tou_comfort_pct": float(peak_comfort_pct),
        "per_zone_comfort": per_zone_comfort,
        "iaq_compliance_pct": float(iaq_compliance_pct),
        "record_count": len(df)
    }

def main():
    print("=========================================================")
    print("📊 GENERATING BASELINE VS AI PERFORMANCE COMPARISON")
    print("=========================================================")

    base = analyze_db(BASELINE_DB_PATH)
    ai   = analyze_db(DB_PATH)

    if not base or not ai:
        print("Error: Missing database files or data.")
        return

    kwh_saved     = base["total_kwh"] - ai["total_kwh"]
    kwh_saved_pct = (kwh_saved / base["total_kwh"]) * 100.0 if base["total_kwh"] > 0 else 0.0

    cost_saved     = base["total_cost_usd"] - ai["total_cost_usd"]
    cost_saved_pct = (cost_saved / base["total_cost_usd"]) * 100.0 if base["total_cost_usd"] > 0 else 0.0

    peak_shaved     = base["peak_kw"] - ai["peak_kw"]
    peak_shaved_pct = (peak_shaved / base["peak_kw"]) * 100.0 if base["peak_kw"] > 0 else 0.0

    carbon_saved     = base["total_carbon_kg"] - ai["total_carbon_kg"]
    carbon_saved_pct = (carbon_saved / base["total_carbon_kg"]) * 100.0 if base["total_carbon_kg"] > 0 else 0.0

    unocc_kwh_saved     = base["unoccupied_kwh"] - ai["unoccupied_kwh"]
    unocc_kwh_saved_pct = (unocc_kwh_saved / base["unoccupied_kwh"]) * 100.0 if base["unoccupied_kwh"] > 0 else 0.0

    results = {
        "baseline": base,
        "ai_optimized": ai,
        "savings": {
            "energy_kwh_saved": kwh_saved,
            "energy_savings_pct": kwh_saved_pct,
            "cost_usd_saved": cost_saved,
            "cost_savings_pct": cost_saved_pct,
            "peak_kw_reduced": peak_shaved,
            "peak_reduction_pct": peak_shaved_pct,
            "carbon_kg_saved": carbon_saved,
            "carbon_savings_pct": carbon_saved_pct,
            "unoccupied_kwh_saved": unocc_kwh_saved,
            "unoccupied_kwh_savings_pct": unocc_kwh_saved_pct
        }
    }

    json_path = os.path.join(PROJECT_ROOT, "comparison_results.json")
    csv_path  = os.path.join(PROJECT_ROOT, "comparison_results.csv")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    rows = [
        {
            "Metric": "Total HVAC Energy (kWh)",
            "Baseline": f"{base['total_kwh']:.2f}",
            "AI Optimized": f"{ai['total_kwh']:.2f}",
            "Delta": f"{kwh_saved:+.2f}",
            "Change (%)": f"{kwh_saved_pct:+.1f}%"
        },
        {
            "Metric": "Unoccupied Energy (kWh)",
            "Baseline": f"{base['unoccupied_kwh']:.2f}",
            "AI Optimized": f"{ai['unoccupied_kwh']:.2f}",
            "Delta": f"{unocc_kwh_saved:+.2f}",
            "Change (%)": f"{unocc_kwh_saved_pct:+.1f}%"
        },
        {
            "Metric": "Electricity Cost ($ USD)",
            "Baseline": f"${base['total_cost_usd']:.2f}",
            "AI Optimized": f"${ai['total_cost_usd']:.2f}",
            "Delta": f"${cost_saved:+.2f}",
            "Change (%)": f"{cost_saved_pct:+.1f}%"
        },
        {
            "Metric": "Peak Demand (kW)",
            "Baseline": f"{base['peak_kw']:.2f}",
            "AI Optimized": f"{ai['peak_kw']:.2f}",
            "Delta": f"{peak_shaved:+.2f}",
            "Change (%)": f"{peak_shaved_pct:+.1f}%"
        },
        {
            "Metric": "Carbon Emissions (kg CO2)",
            "Baseline": f"{base['total_carbon_kg']:.2f}",
            "AI Optimized": f"{ai['total_carbon_kg']:.2f}",
            "Delta": f"{carbon_saved:+.2f}",
            "Change (%)": f"{carbon_saved_pct:+.1f}%"
        },
        {
            "Metric": "Occupied Comfort PMV Compliance (%)",
            "Baseline": f"{base['comfort_compliance_pct']:.1f}%",
            "AI Optimized": f"{ai['comfort_compliance_pct']:.1f}%",
            "Delta": f"{ai['comfort_compliance_pct'] - base['comfort_compliance_pct']:+.1f}pp",
            "Change (%)": "N/A"
        },
        {
            "Metric": "Peak-Hour Comfort Compliance (%)",
            "Baseline": f"{base['peak_tou_comfort_pct']:.1f}%",
            "AI Optimized": f"{ai['peak_tou_comfort_pct']:.1f}%",
            "Delta": f"{ai['peak_tou_comfort_pct'] - base['peak_tou_comfort_pct']:+.1f}pp",
            "Change (%)": "N/A"
        },
        {
            "Metric": "IAQ Flow Monitored (%) [Schedule-driven]",
            "Baseline": f"{base['iaq_compliance_pct']:.1f}%",
            "AI Optimized": f"{ai['iaq_compliance_pct']:.1f}%",
            "Delta": f"{ai['iaq_compliance_pct'] - base['iaq_compliance_pct']:+.1f}pp",
            "Change (%)": "N/A"
        }
    ]

    df_res = pd.DataFrame(rows)
    df_res.to_csv(csv_path, index=False)

    print(f"\nSUCCESS: Comprehensive comparison exported:")
    print(f"  - JSON: {json_path}")
    print(f"  - CSV:  {csv_path}\n")

    print("=========================================================")
    print("📈 HEADLINE METRICS COMPARISON")
    print("=========================================================")
    print(f"💰 Energy Cost Savings:  ${cost_saved:+.2f} ({cost_saved_pct:+.1f}%)")
    print(f"⚡ Total HVAC Energy:    {kwh_saved:+.2f} kWh ({kwh_saved_pct:+.1f}%)")
    print(f"🌙 Unoccupied Energy:    {unocc_kwh_saved:+.2f} kWh ({unocc_kwh_saved_pct:+.1f}%)")
    print(f"📉 Peak Demand Shaved:   {peak_shaved:+.2f} kW ({peak_shaved_pct:+.1f}%)")
    print(f"🌿 Carbon Avoided:      {carbon_saved:+.2f} kg CO2 ({carbon_saved_pct:+.1f}%)")
    print(f"😊 Occupied Comfort:     {base['comfort_compliance_pct']:.1f}% → {ai['comfort_compliance_pct']:.1f}% ({ai['comfort_compliance_pct'] - base['comfort_compliance_pct']:+.1f}pp)")
    print(f"🔥 Peak-Hour Comfort:    {base['peak_tou_comfort_pct']:.1f}% → {ai['peak_tou_comfort_pct']:.1f}% ({ai['peak_tou_comfort_pct'] - base['peak_tou_comfort_pct']:+.1f}pp)")
    print("=========================================================")

if __name__ == "__main__":
    main()
