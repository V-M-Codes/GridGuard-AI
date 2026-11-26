# -*- coding: utf-8 -*-
"""
GridGuard AI Microgrid Autonomous Simulation & Telemetry Engine
Compliant with IEEE 1547.4 (Microgrid Islanding) and ISO 22301 (Resilience Protocols)
"""

import time
import math
from datetime import datetime, timezone
from typing import Dict, Any, List
from .config import (
    TOTAL_BESS_KWH, DEFAULT_SOC, CONTINGENCY_SOC_FLOOR,
    BASE_T1_KW, BASE_T2_KW, BASE_T3_KW,
    GENSET_RATED_KW, INITIAL_FUEL_L,
    WEATHER_PROFILES, FAILOVER_LATENCY_MS,
    NOMINAL_BUS_VOLTAGE_V, NOMINAL_FREQUENCY_HZ
)


class MicrogridEngine:
    def __init__(self):
        self.is_outage_active: bool = False
        self.current_weather: str = "sunny"
        self.current_soc: float = DEFAULT_SOC
        self.total_bess_kwh: float = TOTAL_BESS_KWH

        # Emergency Genset state
        self.genset_mode: str = "AUTO"  # AUTO | MANUAL
        self.genset_running: bool = False
        self.genset_kw: float = 0.0
        self.genset_fuel_liters: float = INITIAL_FUEL_L
        self.is_cranking: bool = False

        # Event log
        self.event_logs: List[Dict[str, Any]] = []
        self._init_default_logs()

        # Cached calculation results
        self.state: Dict[str, Any] = {}
        self.recalculate()

    def _get_utc_timestamp(self) -> str:
        return datetime.now(timezone.utc).strftime("%H:%M:%S UTC")

    def append_log(self, message: str, level: str = "normal") -> Dict[str, Any]:
        """
        Append an IEC 61850 GOOSE event to the telemetry decision stream.
        Levels: alert | warn | success | normal
        """
        entry = {
            "timestamp": self._get_utc_timestamp(),
            "iso_time": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "message": message
        }
        self.event_logs.append(entry)
        if len(self.event_logs) > 200:
            self.event_logs.pop(0)
        return entry

    def _init_default_logs(self):
        self.append_log("Microgrid synced to Substation 14B. Voltage angle delta: 0.12 deg.", "normal")
        self.append_log("PV Arrays producing 482.4 kW. BESS absorbs excess 85.2 kW.", "normal")
        self.append_log("Contingency check: Tier 1, 2, and 3 fully energized. Frequency stable at 60.02 Hz.", "success")
        self.append_log("Autonomous AI Agent: Solar generation surplus. Islanding protection in STANDBY. Tier-2 cutoff armed at 35% SoC.", "normal")

    def recalculate(self) -> Dict[str, Any]:
        """
        Core physics & dispatch calculations:
        1. Solar generation from irradiance profiles
        2. Tri-Tier load priority evaluation
        3. Automatic Genset crank logic (SoC < 35% during islanding)
        4. Energy balance, battery charging/discharging, and utility net exchange
        5. Battery autonomy runtime estimation
        """
        weather = WEATHER_PROFILES.get(self.current_weather, WEATHER_PROFILES["sunny"])
        solar_kw = weather["solarKW"]

        # Tri-tier load shedding hierarchy
        active_t1 = BASE_T1_KW
        # Tier 2 sheds if islanded and BESS SoC drops below 35% contingency floor
        active_t2 = 0.0 if (self.is_outage_active and self.current_soc < CONTINGENCY_SOC_FLOOR) else BASE_T2_KW
        # Tier 3 sheds immediately to 0 kW on grid outage
        active_t3 = 0.0 if self.is_outage_active else BASE_T3_KW

        total_demand = active_t1 + active_t2 + active_t3

        # Genset Auto-Crank Logic
        auto_genset_engaged = (self.is_outage_active and self.current_soc < CONTINGENCY_SOC_FLOOR and self.genset_mode == "AUTO")
        effective_genset_active = self.genset_running or auto_genset_engaged

        if effective_genset_active:
            self.genset_kw = min(total_demand + 50.0, GENSET_RATED_KW) if self.is_outage_active else 250.0
        else:
            self.genset_kw = 0.0

        total_generation = solar_kw + self.genset_kw
        net_balance = total_generation - total_demand

        battery_kw = 0.0
        grid_kw = 0.0

        if not self.is_outage_active:
            # Grid connected: battery absorbs up to 85.2 kW, remainder exported to utility
            if net_balance >= 0:
                battery_kw = min(net_balance, 85.2)
                grid_kw = net_balance - battery_kw
            else:
                battery_kw = max(net_balance, -150.0)
                grid_kw = net_balance - battery_kw
        else:
            # Islanded mode: grid isolated (0 kW), battery balances the deficit/surplus
            grid_kw = 0.0
            battery_kw = net_balance

        # Usable battery capacity and runtime forecasts
        usable_kwh = (self.current_soc / 100.0) * self.total_bess_kwh
        rt_tier1 = round(usable_kwh / active_t1, 1) if active_t1 > 0 else 999.0
        t1_t2_load = active_t1 + BASE_T2_KW
        rt_tier1_tier2 = round(usable_kwh / t1_t2_load, 1) if t1_t2_load > 0 else 999.0

        # AI Dispatch Advisory
        if self.is_outage_active:
            if self.current_soc < CONTINGENCY_SOC_FLOOR:
                ai_text = (
                    f"EMERGENCY PROTOCOL ENGAGED: Microgrid islanded. Storage dropped below strict 35% threshold "
                    f"({self.current_soc:.1f}%). Tier 2 shed enacted. Tier 3 receiving 0.0 kW. Life-safety power "
                    f"reserved 100% for Tier 1 medical assets ({active_t1:.1f} kW). Generator Unit GS-1 auto-crank "
                    f"active ({self.genset_kw:.0f} kW). Tier 1 autonomy: {rt_tier1} hours."
                )
            else:
                ai_text = (
                    f"ISLANDED MICROGRID MODE: Utility grid disconnected. Tier 3 shed immediately to 0.0 kW "
                    f"(saved {BASE_T3_KW:.1f} kW). Solar generation ({solar_kw:.0f} kW) and BESS SoC "
                    f"({self.current_soc:.1f}% > 35%) powering Tier 1 & Tier 2 community shelters. "
                    f"Contingency floor armed at 35%."
                )
        else:
            pct_satisfied = int((solar_kw / max(total_demand, 1.0)) * 100)
            ai_text = (
                f"Solar irradiance at {weather['irradiance']}. System connected to utility grid with zero curtailment. "
                f"Current microgrid generation satisfies {pct_satisfied}% of local load. Energy reserves optimal for severe weather readiness."
            )

        sufficiency_pct = round((solar_kw / (BASE_T1_KW + BASE_T2_KW + BASE_T3_KW)) * 100.0, 1)

        self.state = {
            "isOutageActive": self.is_outage_active,
            "operatingMode": "ISLANDED (EMERGENCY) – OUTAGE DETECTED" if self.is_outage_active else "NORMAL GRID CONNECTED (100% STABLE)",
            "currentWeather": self.current_weather,
            "weatherProfile": weather,
            "solar": {
                "kw": round(solar_kw, 1),
                "irradiance": weather["irradiance"],
                "inverter1KW": round(solar_kw * 0.502, 1),
                "inverter2KW": round(solar_kw * 0.498, 1),
                "trend": weather["trend"]
            },
            "bess": {
                "soc": round(self.current_soc, 1),
                "capacityKWh": self.total_bess_kwh,
                "currentKWh": int(usable_kwh),
                "powerKW": round(battery_kw, 1),
                "status": f"CHARGING +{battery_kw:.1f}kW" if battery_kw >= 0 else f"DISCHARGING {battery_kw:.1f}kW",
                "healthPct": 99.4,
                "contingencyFloorPct": CONTINGENCY_SOC_FLOOR
            },
            "grid": {
                "connected": not self.is_outage_active,
                "status": "ISLANDED (EMERGENCY)" if self.is_outage_active else "CONNECTED",
                "powerKW": round(grid_kw, 1),
                "flowMode": "ISOLATED" if self.is_outage_active else ("EXPORT" if grid_kw >= 0 else "IMPORT"),
                "breaker": "CB-101 TRIPPED OPEN" if self.is_outage_active else "CB-101 CLOSED",
                "voltageKV": 0.0 if self.is_outage_active else 13.8,
                "feederStatus": "0.0 kV (DEAD)" if self.is_outage_active else "Feeder 14-B (230kV) Net Export: 51.4 kW"
            },
            "loads": {
                "totalDemandKW": round(total_demand, 1),
                "tier1": {
                    "name": "Healthcare & Emergency Comms",
                    "priority": "Highest (Unconditionally Protected)",
                    "kw": round(active_t1, 1),
                    "status": "ENERGIZED (100% AUTONOMY)",
                    "breaker": "CB-T1 CLOSED",
                    "appliances": [
                        {"name": "Vaccine Refrigerator Banks (Clinic)", "kw": 22.0, "active": True},
                        {"name": "Intensive Care Units (ICU) & Monitors", "kw": 54.5, "active": True},
                        {"name": "Pathway & Trauma Surgical Lights", "kw": 14.0, "active": True},
                        {"name": "Satcom & VHF Emergency Radio Hub", "kw": 22.0, "active": True}
                    ]
                },
                "tier2": {
                    "name": "Shelters & Clean Water",
                    "priority": "Community Priority",
                    "kw": round(active_t2, 1),
                    "status": "SHED (BESS < 35%)" if (self.is_outage_active and self.current_soc < CONTINGENCY_SOC_FLOOR) else "ENERGIZED",
                    "breaker": "CB-T2 TRIPPED OPEN" if (self.is_outage_active and self.current_soc < CONTINGENCY_SOC_FLOOR) else "CB-T2 CLOSED",
                    "appliances": [
                        {"name": "Municipal Water Treatment & Pumps", "kw": 58.0, "active": active_t2 > 0},
                        {"name": "Community Center Cooling & Heat Shelter", "kw": 52.0, "active": active_t2 > 0},
                        {"name": "Public Emergency Device Charging Bank", "kw": 32.5, "active": active_t2 > 0}
                    ]
                },
                "tier3": {
                    "name": "Civic & Commercial",
                    "priority": "Non-Critical (First Shed)",
                    "kw": round(active_t3, 1),
                    "status": "DISCONNECTED (ZERO POWER 0.0 kW)" if self.is_outage_active else "ENERGIZED (GRID CONNECTED)",
                    "breaker": "CB-T3 TRIPPED OPEN" if self.is_outage_active else "CB-T3 CLOSED",
                    "appliances": [
                        {"name": "Civic Decorative & Monument Lighting", "kw": 18.2, "active": active_t3 > 0},
                        {"name": "Unoccupied Municipal HVAC Chillers", "kw": 38.6, "active": active_t3 > 0},
                        {"name": "Commercial EV Plaza Chargers (1-4)", "kw": 24.0, "active": active_t3 > 0},
                        {"name": "Community Laundromat & Dryer Bank", "kw": 10.0, "active": active_t3 > 0}
                    ]
                }
            },
            "genset": {
                "unit": "GS-1",
                "model": "Caterpillar 500kW Dual-Fuel Tier 4 Clean Genset",
                "mode": self.genset_mode,
                "running": effective_genset_active,
                "powerKW": round(self.genset_kw, 1),
                "loadPct": int((self.genset_kw / GENSET_RATED_KW) * 100),
                "fuelPct": int((self.genset_fuel_liters / 1600.0) * 100),
                "fuelLiters": int(self.genset_fuel_liters),
                "status": "AUTO-RUNNING (SoC < 35%)" if auto_genset_engaged else ("RUNNING (MANUAL)" if self.genset_running else "STANDBY (READY)"),
                "autoCrankTrigger": "BESS SoC < 35% in Islanding"
            },
            "telemetry": {
                "frequencyHz": NOMINAL_FREQUENCY_HZ + 0.02,
                "busVoltageV": NOMINAL_BUS_VOLTAGE_V + 0.1,
                "powerFactor": 0.98,
                "thdPct": 1.4,
                "latencyMs": FAILOVER_LATENCY_MS,
                "stsStatus": "SYNCHRONIZED"
            },
            "runtime": {
                "tier1Hours": rt_tier1,
                "tier1Tier2Hours": rt_tier1_tier2,
                "solarLoopSustainable": solar_kw >= total_demand
            },
            "resilience": {
                "criticalLoadSurvival": "> 72.0 hrs",
                "energyNotServedKWh": 0.0,
                "solarSelfSufficiencyPct": sufficiency_pct,
                "failoverLatencyMs": FAILOVER_LATENCY_MS
            },
            "aiAdvisory": ai_text,
            "timestamp": self._get_utc_timestamp(),
            "isoTimestamp": datetime.now(timezone.utc).isoformat()
        }
        return self.state

    def simulate_outage(self) -> Dict[str, Any]:
        """Trigger grid outage simulation and dynamic sub-cycle islanding"""
        self.is_outage_active = True
        self.append_log(
            "Substation 14B Loss of Potential detected. Static transfer switch ATS-1 initiated seamless disconnect in 14.2ms.",
            "alert"
        )
        self.append_log(
            "Microgrid entered autonomous ISLANDED mode. TIER 3 NON-CRITICAL LOADS DISCONNECTED IMMEDIATELY – ZERO POWER SUPPLIED (0.0 kW).",
            "warn"
        )
        if self.current_soc < CONTINGENCY_SOC_FLOOR:
            self.append_log(
                f"BESS SoC is below {CONTINGENCY_SOC_FLOOR}% contingency floor ({self.current_soc:.1f}%). Disconnecting Tier 2; Unit GS-1 Generator auto-cranking.",
                "alert"
            )
        return self.recalculate()

    def restore_grid(self) -> Dict[str, Any]:
        """Restore main grid interconnection and re-energize all tiers"""
        self.is_outage_active = False
        self.genset_running = False
        self.append_log("Utility 230kV Feeder voltage restored & verified within IEEE 1547 phase sync limits.", "success")
        self.append_log("Static breaker CB-101 closed. Microgrid resynchronized with main utility grid. All tiers re-energized.", "success")
        return self.recalculate()

    def set_weather(self, weather_type: str) -> Dict[str, Any]:
        """Change solar weather condition (sunny | cloudy | stormy)"""
        if weather_type in WEATHER_PROFILES:
            self.current_weather = weather_type
            profile = WEATHER_PROFILES[weather_type]
            self.append_log(
                f"Weather condition shifted to {weather_type.upper()} ({profile['irradiance']}). PV Array generation recalculated to {profile['solarKW']} kW.",
                "normal"
            )
        return self.recalculate()

    def set_soc(self, soc_val: float) -> Dict[str, Any]:
        """Simulate BESS State of Charge adjustment"""
        self.current_soc = max(5.0, min(100.0, float(soc_val)))
        if self.current_soc < 20.0:
            self.append_log(f"CRITICAL STORAGE WARNING: BESS level degraded to {self.current_soc:.1f}%. Immediate curtailment mandatory.", "alert")
        elif self.current_soc < CONTINGENCY_SOC_FLOOR:
            self.append_log(f"BESS dropped below 35% threshold ({self.current_soc:.1f}%). Automated Tier-2 load shedding rule triggered.", "warn")
        else:
            self.append_log(f"Simulation: BESS SoC manually set to {self.current_soc:.1f}%. Evaluating contingency logic.", "normal")
        return self.recalculate()

    def test_crank_genset(self) -> Dict[str, Any]:
        """Initiate 10-second manual test crank on Backup Genset GS-1"""
        self.append_log("Genset Unit GS-1 manual crank cycle initiated. Testing starter battery and fuel pressure...", "warn")
        self.append_log("Genset Unit GS-1 crank test PASSED. Engine speed: 1800 RPM, oil pressure: 58 PSI. System back to STANDBY.", "success")
        return self.recalculate()

    def toggle_genset_mode(self, mode: str = None) -> Dict[str, Any]:
        """Toggle between AUTO and MANUAL generator crank mode"""
        if mode in ["AUTO", "MANUAL"]:
            self.genset_mode = mode
        else:
            self.genset_mode = "MANUAL" if self.genset_mode == "AUTO" else "AUTO"

        if self.genset_mode == "AUTO":
            self.append_log("Generator switched to AUTO mode. Contingency crank armed at BESS SoC < 35%.", "normal")
        else:
            self.append_log("Generator switched to MANUAL mode. Automated 35% SoC crank interlock paused.", "warn")
        return self.recalculate()

    def toggle_genset_emergency(self, force_state: bool = None) -> Dict[str, Any]:
        """Emergency Run manual override for Genset Unit GS-1"""
        if force_state is not None:
            self.genset_running = force_state
        else:
            self.genset_running = not self.genset_running

        if self.genset_running:
            self.append_log("EMERGENCY RUN OVERRIDE ENGAGED: Unit GS-1 cranked to prime speed. ATS-2 synchronizing bus.", "alert")
        else:
            self.append_log("Emergency Run manual command revoked. Unit GS-1 entering automated cooldown cycle.", "normal")
        return self.recalculate()

    def execute_drill(self, duration: str = "30m") -> Dict[str, Any]:
        """Execute automated ISO 22301 Black-Start Resilience Drill"""
        self.append_log(f"INITIATING ISO 22301 MANUAL RESILIENCE DRILL: Window {duration}. IEEE 1547.4 black-start trip engaging.", "warn")
        self.simulate_outage()
        self.append_log("Drill automated sequence completed successfully. All critical life-safety metrics maintained.", "success")
        return self.recalculate()

    def reset(self) -> Dict[str, Any]:
        """Reset simulation back to baseline nominal state"""
        self.is_outage_active = False
        self.current_weather = "sunny"
        self.current_soc = DEFAULT_SOC
        self.genset_running = False
        self.genset_mode = "AUTO"
        self.append_log("Simulation reset to baseline nominal parameters. 35% SoC contingency floor armed.", "normal")
        return self.recalculate()