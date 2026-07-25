import sys
from src.config import ZONES

class SensorRegistry:
    def __init__(self):
        self.temp_handles = {}
        self.pmv_handles = {}
        self.iaq_handles = {}
        self.outdoor_temp_handle = -1
        self.hvac_power_handle = -1
        self.is_meter_handle = False
        self.initialized = False

    def init_handles(self, state, api):
        """Initializes API variable handles for all 5 zones and outdoor environment."""
        for z in ZONES:
            # 1. Zone Air Temperature
            h_temp = api.exchange.get_variable_handle(state, "Zone Air Temperature", z)
            self.temp_handles[z] = h_temp
            
            # 2. Zone Fanger PMV (Try multiple key variations: People name vs Zone name)
            h_pmv = api.exchange.get_variable_handle(state, "Zone Thermal Comfort Fanger Model PMV", f"{z} PEOPLE 1")
            if h_pmv == -1:
                h_pmv = api.exchange.get_variable_handle(state, "Zone Thermal Comfort Fanger Model PMV", f"{z} PEOPLE")
            if h_pmv == -1:
                h_pmv = api.exchange.get_variable_handle(state, "Zone Thermal Comfort Fanger Model PMV", z)
            self.pmv_handles[z] = h_pmv
            
            # 3. Zone Mechanical Ventilation Mass Flow Rate (IAQ proxy)
            h_iaq = api.exchange.get_variable_handle(state, "Zone Mechanical Ventilation Mass Flow Rate", z)
            if h_iaq == -1:
                h_iaq = api.exchange.get_variable_handle(state, "Zone Mechanical Ventilation Standard Density Volume Flow Rate", z)
            self.iaq_handles[z] = h_iaq

        # Outdoor Drybulb Temp
        self.outdoor_temp_handle = api.exchange.get_variable_handle(
            state, "Site Outdoor Air Drybulb Temperature", "Environment"
        )
        
        # HVAC Power Handle (Variable preferred over meter for instantaneous demand rate in W)
        self.hvac_power_handle = api.exchange.get_variable_handle(state, "Facility Total HVAC Electricity Demand Rate", "Whole Building")
        if self.hvac_power_handle == -1:
            self.hvac_power_handle = api.exchange.get_variable_handle(state, "Facility Total HVAC Electricity Demand Rate", "Environment")
        if self.hvac_power_handle == -1:
            self.hvac_power_handle = api.exchange.get_variable_handle(state, "Facility Total Electricity Demand Rate", "Whole Building")
        if self.hvac_power_handle == -1:
            self.hvac_power_handle = api.exchange.get_meter_handle(state, "Electricity:HVAC")
            self.is_meter_handle = True
        else:
            self.is_meter_handle = False

        self.initialized = True
        meter_name = "N/A"
        if self.is_meter_handle and self.hvac_power_handle != -1:
            try:
                meter_name = api.exchange.get_meter_name(state, self.hvac_power_handle)
            except Exception:
                meter_name = "Electricity:HVAC"
        print(f"[Sensors] Handles initialized for 5 zones. Outdoor: {self.outdoor_temp_handle}, HVAC Power handle: {self.hvac_power_handle} (is_meter={self.is_meter_handle}, meter_name='{meter_name}'), PMV handles: {self.pmv_handles}")

    def read_zone_sensors(self, state, api, zone_name: str) -> dict:
        """Reads temperature, PMV, and IAQ flow rate for a given zone."""
        temp = None
        pmv = None
        iaq = None

        h_t = self.temp_handles.get(zone_name, -1)
        if h_t != -1:
            temp = api.exchange.get_variable_value(state, h_t)

        h_p = self.pmv_handles.get(zone_name, -1)
        if h_p != -1:
            pmv = api.exchange.get_variable_value(state, h_p)

        h_i = self.iaq_handles.get(zone_name, -1)
        if h_i != -1:
            iaq = api.exchange.get_variable_value(state, h_i)

        return {
            "temp_c": temp,
            "pmv": pmv,
            "iaq_vent_flow": iaq
        }

    def read_environment_sensors(self, state, api) -> dict:
        """Reads outdoor temperature and overall HVAC power demand."""
        outdoor_temp = None
        hvac_kw = 0.0

        if self.outdoor_temp_handle != -1:
            outdoor_temp = api.exchange.get_variable_value(state, self.outdoor_temp_handle)

        if self.hvac_power_handle != -1:
            if self.is_meter_handle:
                # Meter value returns Joules per timestep -> convert to average kW (900 seconds)
                joules = api.exchange.get_meter_value(state, self.hvac_power_handle)
                hvac_kw = joules / 900.0 / 1000.0 if joules > 0 else 0.0
            else:
                # Variable value returns instantaneous Demand Rate in Watts -> convert to kW
                watts = api.exchange.get_variable_value(state, self.hvac_power_handle)
                hvac_kw = watts / 1000.0 if watts > 0 else 0.0

        return {
            "outdoor_temp_c": outdoor_temp,
            "hvac_power_kw": hvac_kw
        }

