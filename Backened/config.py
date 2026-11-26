# -*- coding: utf-8 -*-
"""
GridGuard AI Microgrid Configuration & Constants
IEEE 1547.4 & ISO 22301 Compliance Profiles
"""

# Battery Energy Storage System (BESS)
TOTAL_BESS_KWH = 1600.0
DEFAULT_SOC = 88.5
CONTINGENCY_SOC_FLOOR = 35.0  # Strict Tier-2 shed cutoff threshold (%)
CRITICAL_SOC_SHUTDOWN = 5.0   # Emergency BESS protection floor (%)

# Base Load Ratings (kW)
BASE_T1_KW = 112.5  # Critical Life-Safety (Vaccines, ICU, Surgery Lights, Comms)
BASE_T2_KW = 142.5  # Community Priority (Water treatment, Heating/Cooling Shelter)
BASE_T3_KW = 90.8   # Civic & Commercial (Decorative lights, EV charging, Laundromat)

# Emergency Generator Specifications (GS-1)
GENSET_RATED_KW = 500.0
GENSET_FUEL_CAPACITY_L = 1600.0
INITIAL_FUEL_L = 1420.0  # ~88% reserve
GENSET_CONSUMPTION_L_PER_HOUR = 85.0  # @ 80% prime load
GENSET_ATS_TRANSFER_TIME_SEC = 8.5

# Weather & Irradiance Profiles
WEATHER_PROFILES = {
    "sunny": {
        "solarKW": 482.4,
        "irradiance": "980 W/m²",
        "efficiency": 1.0,
        "label": "Optimal Generation",
        "trend": "+12.8%"
    },
    "cloudy": {
        "solarKW": 204.2,
        "irradiance": "415 W/m²",
        "efficiency": 0.42,
        "label": "Partial Cloud Cover",
        "trend": "-57.6%"
    },
    "stormy": {
        "solarKW": 58.1,
        "irradiance": "110 W/m²",
        "efficiency": 0.12,
        "label": "Storm Severe Overcast",
        "trend": "-88.0%"
    }
}

# Substation & Bus Electrical Parameters
NOMINAL_BUS_VOLTAGE_V = 480.0
NOMINAL_FREQUENCY_HZ = 60.00
SUBSTATION_NAME = "Substation 14-B"
FEEDER_NAME = "Feeder 14-B (230kV)"
BREAKER_ID = "CB-101"
STS_ID = "ATS-1"
FAILOVER_LATENCY_MS = 14.2