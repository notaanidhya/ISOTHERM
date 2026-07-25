from src.config import ZONES
from src.agent.safety import clamp_setpoint, enforce_deadband

class ActuatorRegistry:
    def __init__(self):
        self.heating_actuators = {}
        self.cooling_actuators = {}
        self.initialized = False

    def init_handles(self, state, api):
        """Initializes 10 zone-specific actuator handles (5 heating, 5 cooling)."""
        for z in ZONES:
            htg_sch_name = f"Htg-SetP-Sch-{z}"
            clg_sch_name = f"Clg-SetP-Sch-{z}"

            h_htg = api.exchange.get_actuator_handle(state, "Schedule:Compact", "Schedule Value", htg_sch_name)
            h_clg = api.exchange.get_actuator_handle(state, "Schedule:Compact", "Schedule Value", clg_sch_name)

            self.heating_actuators[z] = h_htg
            self.cooling_actuators[z] = h_clg

        self.initialized = True
        print(f"[Actuators] 10 zone actuator handles initialized (5 heating, 5 cooling).")

    def set_zone_setpoint(self, state, api, zone_name: str, heating_c: float, cooling_c: float) -> tuple[float, float]:
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
