from src.config import ZONES, OCCUPIED_HOURS
from src.agent.safety import clamp_setpoint, enforce_deadband

class ActuatorRegistry:
    def __init__(self):
        self.heating_actuators = {}
        self.cooling_actuators = {}
        self.vent_actuators    = {}   # Phase 02: VAV minimum flow fraction
        self.vent_enabled      = False
        self.initialized       = False

    def init_handles(self, state, api):
        """Initializes 10 zone-specific setpoint actuators + 5 ventilation actuators."""
        for z in ZONES:
            htg_sch_name = f"Htg-SetP-Sch-{z}"
            clg_sch_name = f"Clg-SetP-Sch-{z}"

            h_htg = api.exchange.get_actuator_handle(state, "Schedule:Compact", "Schedule Value", htg_sch_name)
            h_clg = api.exchange.get_actuator_handle(state, "Schedule:Compact", "Schedule Value", clg_sch_name)

            self.heating_actuators[z] = h_htg
            self.cooling_actuators[z] = h_clg

            # Phase 02 — VAV Reheat minimum flow fraction actuator
            # Component name from eplusout.bnd: "SPACE1-1 VAV REHEAT", etc.
            vav_name = f"{z} VAV REHEAT"
            h_vent = api.exchange.get_actuator_handle(
                state, "AirTerminal:SingleDuct:VAV:Reheat",
                "Air Terminal VAV Damper Position", vav_name
            )
            if h_vent == -1:
                # Fallback: try Zone Air Terminal actuator type
                h_vent = api.exchange.get_actuator_handle(
                    state, "AirTerminal:SingleDuct:VAV:Reheat",
                    "Mass Flow Rate", vav_name
                )
            self.vent_actuators[z] = h_vent

        any_vent_ok = any(h != -1 for h in self.vent_actuators.values())
        self.vent_enabled = any_vent_ok

        self.initialized = True
        print(
            f"[Actuators] Setpoint handles: htg={list(self.heating_actuators.values())}, "
            f"clg={list(self.cooling_actuators.values())}"
        )
        print(
            f"[Actuators] Ventilation handles: {self.vent_actuators} "
            f"(vent_enabled={self.vent_enabled})"
        )

    def set_zone_setpoint(self, state, api, zone_name: str, heating_c: float, cooling_c: float) -> tuple:
        """Applies clamped setpoints with deadband enforcement to a specific zone's actuators."""
        h_clamped = clamp_setpoint(heating_c, "heating")
        c_clamped = clamp_setpoint(cooling_c, "cooling")
        h_safe, c_safe = enforce_deadband(h_clamped, c_clamped)

        h_act = self.heating_actuators.get(zone_name, -1)
        if h_act != -1:
            api.exchange.set_actuator_value(state, h_act, h_safe)

        c_act = self.cooling_actuators.get(zone_name, -1)
        if c_act != -1:
            api.exchange.set_actuator_value(state, c_act, c_safe)

        return h_safe, c_safe

    def set_zone_ventilation(self, state, api, zone_name: str, flow_fraction: float) -> float:
        """Sets VAV damper position / flow fraction (0.0–1.0) for a zone.
        1.0 = maximum ventilation, 0.1 = minimum (unoccupied purge rate).
        Returns the fraction that was applied (-1.0 if handle not available)."""
        if not self.vent_enabled:
            return -1.0
        fraction = max(0.0, min(1.0, flow_fraction))
        h = self.vent_actuators.get(zone_name, -1)
        if h != -1:
            api.exchange.set_actuator_value(state, h, fraction)
            return fraction
        return -1.0

    def apply_occupancy_ventilation(self, state, api, hour_of_day: int):
        """Automatically sets ventilation based on occupancy schedule.
        Called every timestep as a rule-based fallback (LLM can override via MCP tool).
        Occupied  → 0.8 (good IAQ)
        Unoccupied → 0.1 (minimum purge, saves fan energy)"""
        if not self.vent_enabled:
            return
        is_occupied = OCCUPIED_HOURS[0] <= hour_of_day < OCCUPIED_HOURS[1]
        fraction = 0.8 if is_occupied else 0.1
        for z in ZONES:
            self.set_zone_ventilation(state, api, z, fraction)
