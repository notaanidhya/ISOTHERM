# System Architecture & Technical Documentation

## AI-Powered Autonomous Smart Building Optimization System

---

## 1. Executive Summary

This system is an **autonomous, closed-loop Building Management System (BMS)** that optimizes energy consumption and Time-of-Use (TOU) electricity cost ($) for a 5-zone commercial office building while maintaining occupant thermal comfort (Fanger PMV) and Indoor Air Quality (IAQ ventilation flow).

The system integrates **EnergyPlus 26.1** with a local open-source LLM (**Llama 3.1 8B Instruct** via Ollama) using the **Model Context Protocol (MCP)** and **pyenergyplus Runtime API**.

---

## 2. Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                            SYSTEM ARCHITECTURE                               │
│                                                                              │
│  ┌────────────────┐ 60 sim-min  ┌───────────────────┐  MCP Tool Calls ┌────┐│
│  │   EnergyPlus   │───callback─►│ Thread-Safe SQLite│◄───────────────│MCP ││
│  │ (Runtime API)  │◄──actuators─│   State Bus       │───────────────►│Server│
│  └────────────────┘   setpoints └─────────┬─────────┘  state/logs  └─┬──┘│
│                                           │                          │   │
│                                           ▼                          ▼   │
│  ┌────────────────┐                                       ┌────────────┐ │
│  │ Streamlit      │◄────────── reads decisions / metrics  │ LLM Agent  │ │
│  │ Dashboard      │                                       │ (Ollama)   │ │
│  └────────────────┘                                       └────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Technical Core Decisions

### A. Synchronous Callback-LLM Control Loop (Latency Management)
- **Problem**: EnergyPlus runs asynchronously at CPU speed, advancing simulated time faster than an LLM can return decisions.
- **Solution**: Inside the timestep callback (`callback_end_zone_timestep_after_zone_reporting`), when `sim_time_hours` reaches a 60-minute boundary, the **callback thread pauses synchronously** and executes the LLM agent turn.
- **Result**: Every 60-minute decision point receives an authentic, real-time AI setpoint update before EnergyPlus proceeds.

### B. True Per-Zone Independent Actuation Control
- **Problem**: Default `5ZoneAirCooled.idf` shares a single setpoint schedule across all 5 zones.
- **Solution**: `scripts/prepare_model.py` duplicates schedules into 5 per-zone schedule pairs (`Htg-SetP-Sch-SPACE1-1` ... `SPACE5-1` and `Clg-SetP-Sch-SPACE1-1` ... `SPACE5-1`) and re-links thermostats per zone.
- **Result**: The LLM has authentic per-zone control authority over 10 distinct actuator handles (2 per zone).

### C. FastMCP Tool-Calling & Error Self-Correction
- **Server**: FastMCP stdio server (`src/mcp_server/server.py`) exposing 6 tools:
  1. `get_building_state` — Current zone temps, PMV, IAQ flow, setpoints, HVAC power.
  2. `get_recent_history_tool` — Rolling 4-hour summary.
  3. `set_setpoints` — Set single zone heating/cooling setpoints with safety clamp.
  4. `set_all_setpoints` — Set setpoints for all 5 zones.
  5. `extract_runtime_errors` — Read tail of `eplusout.err` to surface runtime warnings/errors.
  6. `log_decision_tool` — Persist reasoning and action to SQLite decisions table.
- **Self-Correction**: If a setpoint action triggers warnings or instability in EnergyPlus, the LLM calls `extract_runtime_errors` to inspect the error log and correct its actions.

### D. Native EnergyPlus PMV Comfort & IAQ Tracking
- **PMV**: `scripts/prepare_model.py` configures `PEOPLE` objects with `Thermal_Comfort_Model_1_Type = "Fanger"` and required companion schedules (`Air-Vel-Sch` 0.1 m/s, `Clothing-Sch` 1.0 clo, `Work-Eff-Sch` 0.0). EnergyPlus natively outputs `Zone Thermal Comfort Fanger Model PMV` (-0.5 to +0.5 target).
- **IAQ Proxy**: Tracks `Zone Mechanical Ventilation Mass Flow Rate [kg/s]` to verify adequate fresh air supply (>0.01 kg/s) during occupied hours.

### E. Time-of-Use (TOU) Pricing & Carbon Optimization
- **TOU Rates**:
  - Off-Peak (22:00–08:00): **$0.05 / kWh**
  - Mid-Peak (08:00–12:00, 18:00–22:00): **$0.10 / kWh**
  - Peak Rate (12:00–18:00): **$0.15 / kWh**
- The LLM pre-cools/pre-heats zones during off-peak windows ($0.05/kWh) and relaxes setpoints during peak TOU windows ($0.15/kWh) to shave peak demand ($).

---

## 4. Evaluation Rubric Alignment

| Rubric Criterion | Weight | Technical Implementation |
|------------------|--------|--------------------------|
| **System Integration & Architecture** | **30%** | Synchronous callback control loop, thread-safe SQLite state bus, 10-layer reliability chain, dual-season representative week simulation |
| **Energy Efficiency & Cost Savings** | **25%** | Quantified kWh savings, Time-of-Use ($) cost savings, peak demand shaving (kW), exported to JSON & CSV |
| **Comfort & IAQ Maintenance** | **20%** | Native Fanger PMV comfort tracking (-0.5 to +0.5 compliance %), mechanical ventilation flow rate monitoring (>0.01 kg/s) |
| **Agentic Autonomy & Code Elegance** | **15%** | Dynamic MCP tool calling via Ollama `chat(tools=...)`, FastMCP stdio tools (`extract_runtime_errors`), Pydantic validation, safety clamps |
| **Presentation & Documentation** | **10%** | Architecture doc, physical `5ZoneAirCooled_AI_Optimized.idf` deliverable artifact, Streamlit dashboard, submission zip |

---

## 5. Physical Deliverables Included in Submission

1. `building_model/5ZoneAirCooled.idf` — Unmodified baseline building model.
2. `building_model/5ZoneAirCooled_Prepared.idf` — Model prepared with 5 per-zone setpoint schedules & Fanger PMV.
3. `building_model/5ZoneAirCooled_AI_Optimized.idf` — Physical Deliverable 2 artifact generated from LLM decisions.
4. `comparison_results.json` & `comparison_results.csv` — Quantified performance comparison metrics.
5. `Honeywell_Submission.zip` — Full packaged codebase and submission artifacts.
