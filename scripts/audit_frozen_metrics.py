import sqlite3
import os
import sys

# Ensure UTF-8 output encoding for Windows terminal
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def get_tou_price(hour: int) -> float:
    if 12 <= hour < 18:
        return 0.15  # Peak
    elif 8 <= hour < 12 or 18 <= hour < 22:
        return 0.08  # Mid-Peak
    else:
        return 0.05  # Off-Peak

def audit_db(db_path, label):
    if not os.path.exists(db_path):
        print(f"Error: {db_path} not found.")
        return {}

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Total rows
    total_rows = cursor.execute("SELECT count(*) FROM state_log").fetchone()[0]

    # Helper for comfort %
    def calc_comfort(season_cond, time_cond):
        query_total = f"""
            SELECT count(*) FROM state_log 
            WHERE zone_pmv IS NOT NULL 
              AND {season_cond} 
              AND {time_cond}
        """
        query_ok = f"""
            SELECT count(*) FROM state_log 
            WHERE zone_pmv BETWEEN -0.5 AND 0.5 
              AND {season_cond} 
              AND {time_cond}
        """
        tot = cursor.execute(query_total).fetchone()[0]
        ok = cursor.execute(query_ok).fetchone()[0]
        return (ok / tot * 100.0) if tot > 0 else 0.0, ok, tot

    # Seasons conditions
    win_cond = "sim_time_hours <= 360.0"
    sum_cond = "sim_time_hours >= 4344.0"
    all_cond = "1=1"

    # Time conditions
    occ_cond = "(CAST(sim_time_hours AS INTEGER) % 24) >= 8 AND (CAST(sim_time_hours AS INTEGER) % 24) <= 18"
    mid_cond = "(CAST(sim_time_hours AS INTEGER) % 24) >= 8 AND (CAST(sim_time_hours AS INTEGER) % 24) < 12"
    peak_cond = "(CAST(sim_time_hours AS INTEGER) % 24) >= 12 AND (CAST(sim_time_hours AS INTEGER) % 24) <= 18"
    unocc_cond = "(CAST(sim_time_hours AS INTEGER) % 24) < 8 OR (CAST(sim_time_hours AS INTEGER) % 24) > 18"

    # Calculate Comforts
    win_occ_pct, win_occ_ok, win_occ_tot = calc_comfort(win_cond, occ_cond)
    win_mid_pct, win_mid_ok, win_mid_tot = calc_comfort(win_cond, mid_cond)
    win_peak_pct, win_peak_ok, win_peak_tot = calc_comfort(win_cond, peak_cond)
    sum_occ_pct, sum_occ_ok, sum_occ_tot = calc_comfort(sum_cond, occ_cond)
    all_occ_pct, all_occ_ok, all_occ_tot = calc_comfort(all_cond, occ_cond)

    # Energy calculations (divide by 5 because 5 zones log identical whole-building HVAC power)
    cursor.execute("SELECT sim_time_hours, hvac_elec_kw, hvac_gas_kw FROM state_log")
    rows = cursor.fetchall()
    
    tot_kwh = 0.0
    elec_kwh = 0.0
    gas_kwh = 0.0
    tot_cost = 0.0
    elec_cost = 0.0
    gas_cost = 0.0
    max_kw = 0.0
    win_max_kw = 0.0
    sum_max_kw = 0.0

    # To avoid 5x duplication, we can group by sim_time_hours
    seen_hours = {}
    for r in rows:
        h_time, e_kw, g_kw = r[0], r[1], r[2]
        if h_time not in seen_hours:
            seen_hours[h_time] = (e_kw, g_kw)

    for h_time, (e_kw, g_kw) in seen_hours.items():
        hour_of_day = int(h_time) % 24
        price = get_tou_price(hour_of_day)
        
        e_kwh_step = e_kw * 0.25
        g_kwh_step = g_kw * 0.25
        t_kwh_step = e_kwh_step + g_kwh_step
        
        tot_kwh += t_kwh_step
        elec_kwh += e_kwh_step
        gas_kwh += g_kwh_step
        
        e_cost_step = e_kwh_step * price
        g_cost_step = g_kwh_step * price
        t_cost_step = e_cost_step + g_cost_step
        
        tot_cost += t_cost_step
        elec_cost += e_cost_step
        gas_cost += g_cost_step
        
        comb_kw = e_kw + g_kw
        if comb_kw > max_kw: max_kw = comb_kw
        if h_time <= 360.0 and comb_kw > win_max_kw: win_max_kw = comb_kw
        if h_time >= 4344.0 and comb_kw > sum_max_kw: sum_max_kw = comb_kw

    conn.close()

    return {
        "label": label,
        "total_rows": total_rows,
        "win_occ_pct": win_occ_pct,
        "win_mid_pct": win_mid_pct,
        "win_peak_pct": win_peak_pct,
        "sum_occ_pct": sum_occ_pct,
        "all_occ_pct": all_occ_pct,
        "tot_kwh": tot_kwh,
        "elec_kwh": elec_kwh,
        "gas_kwh": gas_kwh,
        "tot_cost": tot_cost,
        "elec_cost": elec_cost,
        "gas_cost": gas_cost,
        "max_kw": max_kw,
        "win_max_kw": win_max_kw,
        "sum_max_kw": sum_max_kw
    }

if __name__ == "__main__":
    print("=========================================================================")
    print("  ISOTHERM 100% GROUND-TRUTH SQL AUDIT OF FROZEN DATABASES")
    print("=========================================================================")
    
    base = audit_db("baseline_state.db", "Unmanaged Baseline")
    ai = audit_db("sim_state.db", "AI Closed-Loop Control")
    
    print(f"\n1. ENERGY CONSUMPTION & COST COMPARISON (Combined Winter Jan 15 + Summer Jul 1)")
    print(f"-------------------------------------------------------------------------")
    print(f"Metric                 | Baseline         | AI Control       | Delta / Savings")
    print(f"-----------------------+------------------+------------------+------------------")
    print(f"Total Energy (kWh)     | {base['tot_kwh']:12.2f}     | {ai['tot_kwh']:12.2f}     | {ai['tot_kwh']-base['tot_kwh']:+.2f} kWh ({(ai['tot_kwh']-base['tot_kwh'])/base['tot_kwh']*100:+.1f}%)")
    print(f"  - Electricity (kWh)  | {base['elec_kwh']:12.2f}     | {ai['elec_kwh']:12.2f}     | {ai['elec_kwh']-base['elec_kwh']:+.2f} kWh ({(ai['elec_kwh']-base['elec_kwh'])/base['elec_kwh']*100:+.1f}%)")
    print(f"  - Natural Gas (kWh)  | {base['gas_kwh']:12.2f}     | {ai['gas_kwh']:12.2f}     | {ai['gas_kwh']-base['gas_kwh']:+.2f} kWh ({(ai['gas_kwh']-base['gas_kwh'])/base['gas_kwh']*100:+.1f}%)")
    print(f"Total Operating Cost   | ${base['tot_cost']:11.2f}     | ${ai['tot_cost']:11.2f}     | ${ai['tot_cost']-base['tot_cost']:+.2f} ({(ai['tot_cost']-base['tot_cost'])/base['tot_cost']*100:+.1f}%)")
    print(f"  - Electricity Cost   | ${base['elec_cost']:11.2f}     | ${ai['elec_cost']:11.2f}     | ${ai['elec_cost']-base['elec_cost']:+.2f} ({(ai['elec_cost']-base['elec_cost'])/base['elec_cost']*100:+.1f}%)")
    print(f"  - Gas Cost           | ${base['gas_cost']:11.2f}     | ${ai['gas_cost']:11.2f}     | ${ai['gas_cost']-base['gas_cost']:+.2f} ({(ai['gas_cost']-base['gas_cost'])/base['gas_cost']*100:+.1f}%)")
    print(f"Absolute Peak Demand   | {base['max_kw']:12.2f} kW  | {ai['max_kw']:12.2f} kW  | {ai['max_kw']-base['max_kw']:+.2f} kW")
    print(f"  - Winter Peak (kW)   | {base['win_max_kw']:12.2f} kW  | {ai['win_max_kw']:12.2f} kW  | {ai['win_max_kw']-base['win_max_kw']:+.2f} kW")
    print(f"  - Summer Peak (kW)   | {base['sum_max_kw']:12.2f} kW  | {ai['sum_max_kw']:12.2f} kW  | {ai['sum_max_kw']-base['sum_max_kw']:+.2f} kW")

    print(f"\n2. THERMAL COMFORT COMPLIANCE SCORECARD (ASHRAE 55 PMV within [-0.5, +0.5])")
    print(f"-------------------------------------------------------------------------")
    print(f"TOU Window / Season    | Baseline         | AI Control       | Delta (pp)")
    print(f"-----------------------+------------------+------------------+------------------")
    print(f"Summer Occupied Overall| {base['sum_occ_pct']:11.1f}%      | {ai['sum_occ_pct']:11.1f}%      | {ai['sum_occ_pct']-base['sum_occ_pct']:+.1f} pp")
    print(f"Winter Occupied Overall| {base['win_occ_pct']:11.1f}%      | {ai['win_occ_pct']:11.1f}%      | {ai['win_occ_pct']-base['win_occ_pct']:+.1f} pp")
    print(f"  - Mid-Peak (08-12)   | {base['win_mid_pct']:11.1f}%      | {ai['win_mid_pct']:11.1f}%      | {ai['win_mid_pct']-base['win_mid_pct']:+.1f} pp")
    print(f"  - On-Peak  (12-18)   | {base['win_peak_pct']:11.1f}%      | {ai['win_peak_pct']:11.1f}%      | {ai['win_peak_pct']-base['win_peak_pct']:+.1f} pp")
    print(f"Combined Both Seasons  | {base['all_occ_pct']:11.1f}%      | {ai['all_occ_pct']:11.1f}%      | {ai['all_occ_pct']-base['all_occ_pct']:+.1f} pp")
    print("=========================================================================\n")
