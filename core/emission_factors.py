"""
Emission Factors Registry (Versioned)
Sources: EPA GHG Emission Factors Hub (2024), DEFRA Greenhouse Gas Reporting (2024), UK BEIS.
"""

from typing import Dict, Any, Optional
from core.schema import ScopeType

EMISSION_FACTOR_VERSION = "2024.1"

EMISSION_FACTORS: Dict[str, Dict[str, Any]] = {
    # SCOPE 1: Direct emissions from owned or controlled sources
    "natural_gas_kwh": {
        "scope": ScopeType.SCOPE_1,
        "category": "Stationary Combustion",
        "factor": 0.181,
        "unit": "kg_co2e_per_kwh",
        "description": "Natural gas combustion (energy basis)",
        "source": "DEFRA 2024"
    },
    "natural_gas_therm": {
        "scope": ScopeType.SCOPE_1,
        "category": "Stationary Combustion",
        "factor": 5.306,
        "unit": "kg_co2e_per_therm",
        "description": "Natural gas combustion (US therms)",
        "source": "EPA 2024"
    },
    "natural_gas_m3": {
        "scope": ScopeType.SCOPE_1,
        "category": "Stationary Combustion",
        "factor": 1.93,
        "unit": "kg_co2e_per_m3",
        "description": "Natural gas combustion (volume basis)",
        "source": "DEFRA 2024"
    },
    "diesel_fuel_liters": {
        "scope": ScopeType.SCOPE_1,
        "category": "Mobile Combustion",
        "factor": 2.687,
        "unit": "kg_co2e_per_liter",
        "description": "Diesel fuel consumed by company vehicles",
        "source": "EPA/DEFRA 2024"
    },
    "gasoline_fuel_liters": {
        "scope": ScopeType.SCOPE_1,
        "category": "Mobile Combustion",
        "factor": 2.314,
        "unit": "kg_co2e_per_liter",
        "description": "Motor gasoline combustion",
        "source": "EPA/DEFRA 2024"
    },
    "lpg_liters": {
        "scope": ScopeType.SCOPE_1,
        "category": "Stationary Combustion",
        "factor": 1.512,
        "unit": "kg_co2e_per_liter",
        "description": "Liquefied Petroleum Gas (LPG)",
        "source": "DEFRA 2024"
    },

    # SCOPE 2: Indirect emissions from purchased energy
    "electricity_grid_kwh": {
        "scope": ScopeType.SCOPE_2,
        "category": "Purchased Electricity",
        "factor": 0.372,
        "unit": "kg_co2e_per_kwh",
        "description": "Grid electricity average (location-based)",
        "source": "EPA eGRID 2024"
    },
    "electricity_grid_green_kwh": {
        "scope": ScopeType.SCOPE_2,
        "category": "Purchased Electricity",
        "factor": 0.015,
        "unit": "kg_co2e_per_kwh",
        "description": "Certified Renewable / Solar Power Purchase",
        "source": "GHG Protocol Scope 2"
    },
    "purchased_steam_kwh": {
        "scope": ScopeType.SCOPE_2,
        "category": "Purchased Heat & Steam",
        "factor": 0.170,
        "unit": "kg_co2e_per_kwh",
        "description": "District heating and steam",
        "source": "DEFRA 2024"
    },

    # SCOPE 3: Other indirect emissions (Value chain)
    "air_travel_passenger_km": {
        "scope": ScopeType.SCOPE_3,
        "category": "Business Travel",
        "factor": 0.184,
        "unit": "kg_co2e_per_passenger_km",
        "description": "Commercial passenger flight (average haul)",
        "source": "DEFRA 2024 with Radiative Forcing"
    },
    "rail_travel_passenger_km": {
        "scope": ScopeType.SCOPE_3,
        "category": "Business Travel",
        "factor": 0.035,
        "unit": "kg_co2e_per_passenger_km",
        "description": "Passenger train / rail travel",
        "source": "DEFRA 2024"
    },
    "freight_truck_tonne_km": {
        "scope": ScopeType.SCOPE_3,
        "category": "Upstream Transportation",
        "factor": 0.162,
        "unit": "kg_co2e_per_tonne_km",
        "description": "Heavy Goods Vehicle (HGV) road freight",
        "source": "DEFRA 2024"
    },
    "freight_air_tonne_km": {
        "scope": ScopeType.SCOPE_3,
        "category": "Upstream Transportation",
        "factor": 0.602,
        "unit": "kg_co2e_per_tonne_km",
        "description": "Cargo air freight",
        "source": "DEFRA 2024"
    },
    "it_hardware_unit": {
        "scope": ScopeType.SCOPE_3,
        "category": "Purchased Capital Goods",
        "factor": 210.0,
        "unit": "kg_co2e_per_unit",
        "description": "Laptop / desktop hardware lifecycle average",
        "source": "GHG Protocol Value Chain"
    },
    "waste_landfill_kg": {
        "scope": ScopeType.SCOPE_3,
        "category": "Waste Generated in Operations",
        "factor": 0.586,
        "unit": "kg_co2e_per_kg",
        "description": "Commercial municipal solid waste to landfill",
        "source": "EPA WARM 2024"
    }
}

def get_factor(key: str) -> Optional[Dict[str, Any]]:
    return EMISSION_FACTORS.get(key)

def list_all_factors() -> Dict[str, Dict[str, Any]]:
    return EMISSION_FACTORS
