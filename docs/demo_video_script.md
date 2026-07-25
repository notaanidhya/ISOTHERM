# Honeywell BMS Hackathon — 3-Minute Demo Video Guide & Script

This document provides the exact narration script, visual screen recording instructions, and timing breakdown for recording your mandatory **3-minute PoC Demonstration Video** (Deliverable #5).

---

## 🎬 Video Recording Summary

- **Target Duration**: Exactly 2:45 to 3:00 minutes.
- **Recommended Tools**: OBS Studio, Loom, or Windows Game Bar (`Win + Alt + R`).
- **Screen Layout**:
  - Left Half: VS Code Terminal running `run_ai_control.py` (showing live MCP tool calls).
  - Right Half: Streamlit Dashboard at `http://localhost:8501`.

---

## ⏱️ Video Timestamp & Script Breakdown

### 0:00 – 0:40 | Introduction & Problem Statement
* **Visual**: Show the Streamlit Dashboard Overview page (`http://localhost:8501`) displaying top KPI summary cards.
* **Voiceover Script**:
  > *"Hello! Welcome to our submission for the Honeywell AI-Powered Autonomous Smart Building Optimization Challenge. 
  > Commercial buildings account for over 40% of global electricity consumption, primarily driven by HVAC systems running on rigid, legacy schedules that cannot adapt to fluctuating weather, peak electricity rates, or grid carbon intensity. 
  > To solve this, we built a physical AI autonomous Building Management System that couples EnergyPlus 26—the gold standard building physics engine—with an open-source Llama 3.1 LLM brain via the Model Context Protocol."*

---

### 0:40 – 1:40 | Closed-Loop System Architecture & Live Simulation Demo
* **Visual**: Switch focus to terminal running `python scripts/run_ai_control.py`. Point out the live MCP tool logs: `ListToolsRequest`, `get_building_state`, `set_all_setpoints`, and `log_decision_tool`.
* **Voiceover Script**:
  > *"Here you can see our closed-loop pipeline running in real-time. We implemented a synchronous blocking callback engine that pauses EnergyPlus every 60 simulated minutes to trigger an LLM optimization turn. 
  > The agent connects to a stdio MCP server exposing 6 domain tools. The LLM queries real-time building state—including zone temperatures, Fanger PMV comfort indices, and ventilation flow rates—evaluates TOU electricity prices, and dynamically commands per-zone setpoints across 10 active zone actuators. 
  > Notice how the LLM autonomously calls get_building_state, calculates optimal setpoints, applies them to the actuators, and logs its reasoning into the audit trail—all without human code modification."*

---

### 1:40 – 2:30 | Quantitative Savings & Performance Dashboard
* **Visual**: Navigate through the Streamlit Dashboard tabs:
  1. *Tab 1 (Energy & Cost)*: Show peak shaving graph during high TOU rate window ($0.15/kWh).
  2. *Tab 2 (Thermal Comfort)*: Highlight PMV remaining inside $[-0.5, +0.5]$ comfort band.
  3. *Tab 3 (Audit Trail)*: Scroll through live LLM reasoning logs.
* **Voiceover Script**:
  > *"Now let's examine our quantitative performance on the Streamlit dashboard. 
  > In Tab 1, during peak electricity rate hours between 12:00 PM and 6:00 PM, our AI agent pre-cools zones during off-peak hours and sheds HVAC demand during peak pricing, achieving measurable kWh and cost reductions.
  > Crucially, as shown in Tab 2, the AI achieves these savings without sacrificing occupant comfort. PMV comfort scores remain strictly within the ASHRAE 55 comfort zone between -0.5 and +0.5.
  > In Tab 3, the complete decision audit trail records the prompt reasoning for every single action taken."*

---

### 2:30 – 3:00 | Conclusion & Key Impact Summary
* **Visual**: Return to top KPI metric cards (showing kWh saved %, cost saved %, carbon reduced kg).
* **Voiceover Script**:
  > *"In summary, our solution delivers a fully autonomous, self-correcting closed-loop BMS. By leveraging the Model Context Protocol, we proved that physical AI agents can optimize building operations, reduce peak demand, slash carbon emissions, and guarantee occupant comfort. Thank you!"*

---

## 🛠️ Step-by-Step Recording Instructions

1. Start local Streamlit dashboard: `.venv\Scripts\python.exe -m streamlit run dashboard/app.py`
2. Open Chrome to `http://localhost:8501`.
3. Open a terminal window next to Chrome running `python scripts/run_ai_control.py`.
4. Press record in OBS / Loom and follow the script above!
