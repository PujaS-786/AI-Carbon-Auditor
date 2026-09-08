import json
from pathlib import Path
from typing import Optional, Tuple
from core.schema import NormalizedRecord, CalculatedRecord, ScopeType
from core.emission_factors import EMISSION_FACTORS, get_factor
from core.config import HITL_RESOLUTIONS_FILE

class CalculationAgent:
    """
    Calculation Agent:
    Applies authoritative GHG Protocol / EPA / DEFRA emission factors,
    calculates Scope 1/2/3 kgCO2e & metric tonnes, and computes confidence scores
    with adaptive feedback loop recalibration (§7).
    """

    def _get_feedback_adjustment(self, supplier: str, activity_type: str) -> float:
        """
        Dynamically adjusts confidence based on historical HITL resolution patterns (§7):
        - Frequently overridden suppliers/activities get lower baseline confidence (stricter audit).
        - Consistently approved suppliers/activities get higher baseline confidence.
        """
        if not HITL_RESOLUTIONS_FILE.exists():
            return 0.0

        try:
            overrides = 0
            approvals = 0
            sup_clean = supplier.strip().lower()
            act_clean = activity_type.strip().lower()

            with open(HITL_RESOLUTIONS_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    item = json.loads(line)
                    match_supplier = item.get("supplier_or_facility", "").strip().lower() == sup_clean
                    match_activity = item.get("activity_type", "").strip().lower() == act_clean

                    if match_supplier or match_activity:
                        decision = item.get("decision", "").lower()
                        if decision == "override":
                            overrides += 1
                        elif decision == "approve":
                            approvals += 1

            if overrides >= 2:
                return -0.10  # Tighten threshold
            elif approvals >= 3 and overrides == 0:
                return 0.05   # Rewarded trustworthiness
            return 0.0
        except Exception:
            return 0.0

    def _resolve_factor(self, record: NormalizedRecord) -> Tuple[str, dict, float]:
        """
        Resolves the appropriate emission factor and assigns a confidence weighting.
        Returns: (factor_key, factor_dict, factor_confidence)
        """
        activity = record.activity_type.lower()
        unit = record.normalized_unit.lower()

        # 1. Exact match in registry
        if activity in EMISSION_FACTORS:
            return activity, EMISSION_FACTORS[activity], 0.95

        # 2. Check compound keys (e.g. natural_gas + _ + kwh)
        composite = f"{activity}_{unit}"
        if composite in EMISSION_FACTORS:
            return composite, EMISSION_FACTORS[composite], 0.92

        # 3. Match by activity category keywords
        for key, factor_data in EMISSION_FACTORS.items():
            if activity in key or key in activity:
                return key, factor_data, 0.82

        # 4. Fallback based on unit
        if "kwh" in unit:
            return "electricity_grid_kwh", EMISSION_FACTORS["electricity_grid_kwh"], 0.70
        elif "liter" in unit or "l" == unit:
            return "diesel_fuel_liters", EMISSION_FACTORS["diesel_fuel_liters"], 0.65
        elif "km" in unit:
            return "air_travel_passenger_km", EMISSION_FACTORS["air_travel_passenger_km"], 0.65
        elif "therm" in unit:
            return "natural_gas_therm", EMISSION_FACTORS["natural_gas_therm"], 0.75

        # Default fallback
        return "electricity_grid_kwh", EMISSION_FACTORS["electricity_grid_kwh"], 0.50

    def calculate(self, record: NormalizedRecord) -> CalculatedRecord:
        factor_key, factor_data, factor_confidence = self._resolve_factor(record)

        quantity = record.normalized_quantity
        factor_val = factor_data["factor"]

        # Base emission calculation
        kg_co2e = quantity * factor_val
        tonnes_co2e = kg_co2e / 1000.0

        # Confidence calculation
        confidence = factor_confidence

        # Deductions
        if record.original_unit.lower() == "unknown":
            confidence -= 0.20
        if quantity <= 0:
            confidence -= 0.40
        if record.conversion_factor_applied != 1.0 and factor_confidence < 0.85:
            confidence -= 0.05

        # Feedback loop recalibration (§7)
        adjustment = self._get_feedback_adjustment(record.supplier_or_facility, record.activity_type)
        confidence += adjustment

        confidence = max(0.10, min(1.0, round(confidence, 2)))

        return CalculatedRecord(
            record_id=record.record_id,
            raw_document_ref=record.raw_document_ref,
            date=record.date,
            supplier_or_facility=record.supplier_or_facility,
            activity_type=record.activity_type,
            scope=factor_data["scope"],
            category=factor_data["category"],
            activity_quantity=round(quantity, 4),
            activity_unit=record.normalized_unit,
            emission_factor_key=factor_key,
            emission_factor_value=factor_val,
            emission_factor_unit=factor_data["unit"],
            kg_co2e=round(kg_co2e, 4),
            tonnes_co2e=round(tonnes_co2e, 6),
            confidence_score=confidence
        )
