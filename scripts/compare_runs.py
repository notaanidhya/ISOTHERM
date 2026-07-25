import os
import sys
import json

# Ensure UTF-8 output encoding for Windows terminal
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import sqlite3
import pandas as pd
from src.config import DB_PATH, BASELINE_DB_PATH
from src.utils.carbon import get_tou_price, get_carbon_intensity

def analyze_db(db_path):
    if not os.path.exists(db_path):
        return None
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT sim_time_hours, zone_name, zone_temp_c, zone_pmv, zone_iaq_vent_flow, hvac_elec_kw, outdoor_temp_c FROM state_log", conn)
    conn.close()
    
    if df.empty:
        return None
        
    df['hour'] = df['sim_time_hours'].astype(int) % 24
    df['tou_price'] = df['hour'].apply(get_tou_price)
    df['carbon_g'] = df['hour'].apply(get_carbon_intensity)

    # Convert average kW per timestep (15 min = 0.25 hours) to kWh
    df['kwh'] = df['hvac_elec_kw'] * 0.25
    df['cost_usd'] = df['kwh'] * df['tou_price']
    df['carbon_kg'] = (df['kwh'] * df['carbon_g']) / 1000.0

    # PMV Comfort compliance (% of occupied hours where PMV is within [-0.5, +0.5])
    occupied = df[(df['hour'] >= 8) & (df['hour'] <= 18)]
    if not occupied.empty and occupied['zone_pmv'].notnull().any():
        pmv_valid = occupied[occupied['zone_pmv'].notnull()]
        in_range = pmv_valid[(pmv_valid['zone_pmv'] >= -0.5) & (pmv_valid['zone_pmv'] <= 0.5)]
        comfort_compliance_pct = (len(in_range) / len(pmv_valid)) * 100.0
    else:
        in_range = occupied[(occupied['zone_temp_c'] >= 20.0) & (occupied['zone_temp_c'] <= 24.5)]
        comfort_compliance_pct = (len(in_range) / len(occupied)) * 100.0 if not occupied.empty else 100.0

    iaq_ok = df[df['zone_iaq_vent_flow'] >= 0.005]
    iaq_compliance_pct = (len(iaq_ok) / len(df)) * 100.0 if not df.empty else 100.0

    return {
        "total_kwh": float(df['kwh'].sum()),
        "total_cost_usd": float(df['cost_usd'].sum()),
        "peak_kw": float(df['hvac_elec_kw'].max()),
        "total_carbon_kg": float(df['carbon_kg'].sum()),
        "comfort_compliance_pct": float(comfort_compliance_pct),
        "iaq_compliance_pct": float(iaq_compliance_pct),
        "record_count": len(df)
    }

def main():
    print("=========================================================")
    print("📊 GENERATING BASELINE VS AI PERFORMANCE COMPARISON")
    print("=========================================================")

    base_metrics = analyze_db(BASELINE_DB_PATH)
    ai_metrics = analyze_db(DB_PATH)

    if not base_metrics or not ai_metrics:
        print("Error: Missing database files or data.")
        return

    kwh_saved = base_metrics["total_kwh"] - ai_metrics["total_kwh"]
    kwh_saved_pct = (kwh_saved / base_metrics["total_kwh"]) * 100.0 if base_metrics["total_kwh"] > 0 else 0.0

    cost_saved = base_metrics["total_cost_usd"] - ai_metrics["total_cost_usd"]
    cost_saved_pct = (cost_saved / base_metrics["total_cost_usd"]) * 100.0 if base_metrics["total_cost_usd"] > 0 else 0.0

    peak_shaved = base_metrics["peak_kw"] - ai_metrics["peak_kw"]
    peak_shaved_pct = (peak_shaved / base_metrics["peak_kw"]) * 100.0 if base_metrics["peak_kw"] > 0 else 0.0

    carbon_saved = base_metrics["total_carbon_kg"] - ai_metrics["total_carbon_kg"]

    results = {
        "baseline": base_metrics,
        "ai_optimized": ai_metrics,
        "savings": {
            "energy_kwh_saved": kwh_saved,
            "energy_savings_pct": kwh_saved_pct,
            "cost_usd_saved": cost_saved,
            "cost_savings_pct": cost_saved_pct,
            "peak_kw_reduced": peak_shaved,
            "peak_reduction_pct": peak_shaved_pct,
            "carbon_kg_saved": carbon_saved
        }
    }

    json_path = os.path.join(PROJECT_ROOT, "comparison_results.json")
    csv_path = os.path.join(PROJECT_ROOT, "comparison_results.csv")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    df_res = pd.DataFrame([{
        "Metric": "HVAC Energy Consumption (kWh)",
        "Baseline": base_metrics["total_kwh"],
        "AI Optimized": ai_metrics["total_kwh"],
        "Savings": kwh_saved,
        "Savings (%)": kwh_saved_pct
    }, {
        "Metric": "Electricity Cost ($ USD)",
        "Baseline": base_metrics["total_cost_usd"],
        "AI Optimized": ai_metrics["total_cost_usd"],
        "Savings": cost_saved,
        "Savings (%)": cost_saved_pct
    }, {
        "Metric": "Peak Demand (kW)",
        "Baseline": base_metrics["peak_kw"],
        "AI Optimized": ai_metrics["peak_kw"],
        "Savings": peak_shaved,
        "Savings (%)": peak_shaved_pct
    }, {
        "Metric": "Comfort Compliance (%)",
        "Baseline": base_metrics["comfort_compliance_pct"],
        "AI Optimized": ai_metrics["comfort_compliance_pct"],
        "Savings": ai_metrics["comfort_compliance_pct"] - base_metrics["comfort_compliance_pct"],
        "Savings (%)": 0.0
    }, {
        "Metric": "IAQ Flow Monitored (%) [Uncontrolled]",
        "Baseline": base_metrics["iaq_compliance_pct"],
        "AI Optimized": ai_metrics["iaq_compliance_pct"],
        "Savings": ai_metrics["iaq_compliance_pct"] - base_metrics["iaq_compliance_pct"],
        "Savings (%)": 0.0
    }])
    df_res.to_csv(csv_path, index=False)

    print(f"\nSUCCESS: Comparison results exported:")
    print(f"  - JSON: {json_path}")
    print(f"  - CSV:  {csv_path}\n")
    print(f"💰 Energy Cost Savings:  ${cost_saved:.2f} ({cost_saved_pct:.1f}%)")
    print(f"⚡ HVAC Energy Savings: {kwh_saved:.2f} kWh ({kwh_saved_pct:.1f}%)")
    print(f"📉 Peak Demand Shaved:   {peak_shaved:.2f} kW ({peak_shaved_pct:.1f}%)")
    print(f"🌿 Carbon Avoided:      {carbon_saved:.2f} kg CO2")

if __name__ == "__main__":
    main()
