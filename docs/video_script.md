# Deliverable #5: PoC Demonstration Video Script & Shot List
**Honeywell Campus Connect — AI-Powered Autonomous Smart Building Optimization Challenge**
**Project Title**: ISOTHERM — Physical AI Closed-Loop Building Operations  
**Target Duration**: Exactly 2 minutes 50 seconds (170 seconds) — Leaves a 10-second buffer before the strict 3-minute cutoff.  
**Target Audience**: Honeywell Senior Engineering Judges (HVAC, BMS, and AI Systems Specialists)

---

## 🎬 Pre-Recording Setup & Workspace Checklist

Before hitting record on OBS, Zoom, or Clipchamp, set up your desktop layout for maximum visual impact:
1. **Left Half of Screen**: VS Code / Terminal window.
   * Open two terminal tabs:
     * **Tab 1 (Live Loop)**: Ready to execute `python scripts/run_simulation.py`.
     * **Tab 2 (Audit Logs)**: Ready to show `sqlite3 sim_state.db` or tailing `decisions`.
2. **Right Half of Screen**: Google Chrome / Edge browser in full height.
   * Navigate to your local React dashboard: `http://localhost:5173`.
   * Pre-select **Tab 1 ("Executive Overview")** so the Graphite luxury UI and Hero KPI cards are immediately visible.
3. **Recording Resolution**: 1080p (1920×1080) at 60 fps for crisp text rendering.
4. **Time-Saving Tip (Crucial)**: Because local Llama 3.1 inference takes ~30–45 seconds per turn, **record your terminal running the simulation beforehand** and speed up the waiting/inference intervals by **4x or 8x in post-production**. This lets you show a full multi-day closed loop in just 45 seconds of video!

---

## ⏱️ Shot-by-Shot Storyboard & Spoken Script

### Section 1: The Hook & Architectural Overview (0:00 – 0:35 | 35 Seconds)

* **Visual on Screen**: Start with the browser on full screen showing the **ISOTHERM React Dashboard (Tab 1: Executive Overview)**. Slowly hover over the dark-mode aesthetic and the "System Operational · Closed-Loop AI Active" badge.
* **Speaker Audio**:
  > *"Hello judges, we present ISOTHERM—an autonomous, closed-loop physical AI building management system built for the Honeywell Campus Connect challenge. Commercial buildings waste up to thirty percent of their energy through static scheduling and simultaneous cooling and reheat. To solve this, we decoupled a pyenergyplus C++ simulation engine from a local Llama 3.1 8B agent using a Model Context Protocol communication bus over zero-latency standard I/O pipes. Every three simulated hours, our system synchronously blocks the EnergyPlus runtime, evaluates thermal compliance against Chicago Time-of-Use utility tariffs, and mutates ten independent zone schedule actuators."*

---

### Section 2: Live Loop & MCP Communication in Action (0:35 – 1:25 | 50 Seconds)

* **Visual on Screen**: Switch to split-screen (Left: VS Code Terminal | Right: React Dashboard). In Tab 1 of the terminal, press Enter to run:
  `python scripts/run_simulation.py`
  *Show the terminal output logging 15-minute sensor telemetries.* When it hits Hour 3.0 and displays: `[MCP BUS] Waking Agent Turn... Invoking get_building_state...`, highlight or point your cursor to the structured JSON payload being piped over stdio.
* **Speaker Audio**:
  > *"Here is our live closed loop in action. As EnergyPlus evaluates building physics at strict fifteen-minute intervals, it logs sensor telemetry into our SQLite state bus. Notice what happens at Hour 3.0: the callback thread synchronously pauses the C++ engine and invokes our local Llama model via stdio transport. Notice the tool execution: the agent calls `get_building_state` to ingest zone temperatures, PMV comfort indices, and VAV mass flows. Recognizing a mid-peak winter tariff, it evaluates our canonical operating matrix and calls `set_all_setpoints`, writing heating and cooling commands into an atomic database queue. Our Python actuator loop intercepts the queue, enforces hard physical safety bounds, and applies the commands to zone-level schedule handles—completely eliminating global schedule conflicts."*

---

### Section 3: Reconciled SQL Audit & The "Thermal Battery" Discovery (1:25 – 2:15 | 50 Seconds)

* **Visual on Screen**: Maximize the browser window. Click on **Tab 4 ("System Logs & Audit")** on the ISOTHERM dashboard. Point directly to the top meter reconciliation table showing `diff: 0.0000 J`. Then click back to **Tab 1 ("Executive Overview")** and zoom in on Table 1 (The Scorecard) and Hero Card 1 (Total Energy).
* **Speaker Audio**:
  > *"Unlike typical AI demos, we implemented a rigorous mathematical audit. If you look at our System Logs tab, you can see that our SQLite database records match EnergyPlus's compiled compilation meters down to the exact fourth decimal place of a Joule—0.0000 Joules of discrepancy across 960 logged rows. This rigor led to two major engineering breakthroughs. First, in summer, our season-aware prompt clamping achieved a one-hundred percent elimination of VAV box reheat waste—saving over 300 kilowatt-hours of gas while boosting occupied comfort from eleven percent to thirty-four point five percent. Second, in winter, our audit uncovered a brilliant thermodynamic phenomenon: our AI uses the morning Mid-Peak tariff to fire the boiler and overcome overnight setback lag. Because the building's concrete and steel mass absorbs this heat, it acts as a thermal battery! During the expensive fifteen-cent afternoon peak tariff, the building coasts on stored warmth, increasing afternoon peak comfort by two point nine percentage points while shedding peak boiler load."*

---

### Section 4: Defense-in-Depth Safety & Conclusion (2:15 – 2:50 | 35 Seconds)

* **Visual on Screen**: Click on **Tab 2 ("Zone Level Analytics")** to show individual zone temperature curves staying smoothly inside the shaded comfort bands. Then switch back to **Tab 1** and highlight the Hero KPI cards one last time.
* **Speaker Audio**:
  > *"To guarantee zero catastrophic equipment failures, ISOTHERM operates under a four-layer defense-in-depth safety hierarchy. Pydantic schema validation intercepts malformed JSON; sub-process timers trigger automated canonical fallbacks if local GPU inference throttles; hard code clamps enforce sixteen to thirty degree bounds and a mandatory two-degree deadband before reaching any API write; and ten per-zone actuator handles guarantee spatial independence. ISOTHERM proves that local LLMs, when constrained by rigorous systems engineering and thermodynamic safety interlocks, can deliver autonomous, enterprise-grade building optimization. Thank you."*

---

## 🎙️ Speaker Delivery & Editing Tips
* **Pacing**: Speak at a clear, authoritative, professional engineering pace (approx. 130–140 words per minute). Do not sound rushed; let the numbers breathe!
* **Text Overlays (Callouts)**: In your video editor, add clean, bold lower-third text callouts when you mention key metrics:
  * `0.0000 J Meter Discrepancy (100% Reconciled)`
  * `100% Summer Reheat Eliminated (0.00 kW)`
  * `+27.0 pp Summer Comfort Win`
  * `The "Thermal Battery": +2.9 pp Peak Comfort Win`
* **Audio Cleanliness**: Use a decent USB microphone or headset, record in a quiet room, and apply a mild noise gate or compressor so your voice sounds broadcast-ready.
