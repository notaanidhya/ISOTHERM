# ISOTHERM: Custom Voiceover Script for Your Recorded Video (Duration: 02:23)
**Honeywell Campus Connect — AI-Powered Autonomous Smart Building Optimization Challenge**
**Target Video File**: `Untitled design.mp4` (Duration: exactly 2 minutes 23 seconds / 143 seconds)
**Total Word Count**: ~315 words (Paced at ~130 words per minute — smooth, authoritative, broadcast-ready engineering pacing)

---

## 🎙️ Spoken Voiceover Script (Individual Submission — Aligned to Your 3 Video Sections)

### Section 1: Dashboard Navigation & System Architecture (0:00 – 0:50 | ~50 seconds)
*(Speak smoothly as your video navigates through the dashboard tabs and navigation panels)*

> **"Hello judges, I present ISOTHERM—an autonomous, closed-loop physical AI building management system built for the Honeywell Campus Connect challenge. As I navigate through the executive dashboard, you can see real-time telemetry and a quantitative scorecard. Commercial buildings waste up to thirty percent of their energy through static scheduling and simultaneous cooling and reheat.**
> 
> **To solve this, I decoupled a pyenergyplus C++ simulation engine from a local Llama 3.1 8B agent using a Model Context Protocol communication bus over zero-latency standard I/O pipes. Every three simulated hours, my system synchronously pauses physics evaluation to execute intelligent, tariff-aware setpoint commands across ten independent zone actuators."**

---

### Section 2: Live Closed-Loop Execution in Terminal (0:50 – 1:35 | ~45 seconds)
*(Speak with technical precision as your video shows `python scripts/run_simulation.py` executing in the terminal)*

> **"Here is my live closed-loop orchestration in action running `run_simulation.py`. As EnergyPlus advances at fifteen-minute intervals, it streams sensor telemetry—including zone temperatures, Fanger PMV comfort indices, and VAV mass flows—directly into an SQLite state bus.**
> 
> **Notice what happens at simulation Hour 3.0: a callback hook wakes the agent turn over stdio transport. The agent invokes `get_building_state`, evaluates a seven-quadrant canonical decision matrix against Time-of-Use tariffs, and calls `set_all_setpoints`. My defense-in-depth safety layer intercepts these commands, enforcing hard code clamps of sixteen to thirty degrees Celsius and a mandatory two-degree deadband across all five thermal zones before updating the building state."**

---

### Section 3: Tab 02 (Energy Demand & TOU Analytics) & Summer/Winter Callouts (1:35 – 2:23 | ~48 seconds)
*(Speak with enthusiasm and pride as your video switches to Tab 02, showing the summer/winter graphs and final callout boxes)*

> **"Now let's examine the verified quantitative impact on Tab 2: Energy Demand and TOU Analytics. Unlike typical AI demos, my numbers are mathematically reconciled against official EnergyPlus compilation meters down to zero point zero zero zero zero Joules across nine hundred and sixty logged rows.**
> 
> **Look at the summer profile switching: my season-aware prompt clamping achieved a one-hundred percent elimination of VAV simultaneous cooling and reheat waste—saving over three hundred kilowatt-hours of natural gas while maintaining thirty-four point five percent occupied comfort!**
> 
> **And look at the winter callouts: my AI uses the morning mid-peak tariff to warm the building's concrete mass. This acts as a thermal battery, allowing the building to coast during the expensive fifteen-cent afternoon peak tariff for a plus two point nine percentage point comfort win while shedding load! ISOTHERM proves that local LLMs, when constrained by thermodynamic safety interlocks, deliver verified, enterprise-grade building optimization. Thank you!"**

---

## 🎬 Tips for Recording Your Voiceover Over `Untitled design.mp4`

1. **Audio Setup**: Sit in a quiet room, open your microphone, and open your video file in your media player or video editor (Clipchamp, Premiere, or DaVinci Resolve).
2. **Reading Technique**: You don't need to read all 3 sections in one breath! Read Section 1, pause your video, take a sip of water, and then read Section 2.
3. **Micro-Adjusting Timeline in Your Editor**:
   * If you finish speaking Section 1 a few seconds before your video transitions to the terminal, simply add a 2-3 second freeze-frame or slow down the dashboard footage slightly in your video editor.
   * If your terminal recording in Section 2 finishes faster than your voice, slow down that video clip to 80% speed so the visual matches your words perfectly!
