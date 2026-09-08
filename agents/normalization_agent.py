import re
from datetime import datetime, timezone
from typing import Dict, Any, Tuple
from core.schema import RawRecord, NormalizedRecord

class NormalizationAgent:
    """
    Normalization Agent:
    Standardizes units, dates, activity types, and supplier identifiers into uniform schemas.
    """

    UNIT_CONVERSIONS = {
        # Energy -> kWh
        "mwh": (1000.0, "kwh"),
        "megawatt_hour": (1000.0, "kwh"),
        "kwh": (1.0, "kwh"),
        "kilowatt_hour": (1.0, "kwh"),
        "therms": (1.0, "therms"), # kept for therms-specific factor
        "therm": (1.0, "therms"),
        "btu": (0.000293071, "kwh"),
        "gj": (277.778, "kwh"),

        # Fuel Volume -> Liters
        "gallons": (3.78541, "liters"),
        "gallon": (3.78541, "liters"),
        "gal": (3.78541, "liters"),
        "liters": (1.0, "liters"),
        "liter": (1.0, "liters"),
        "l": (1.0, "liters"),
        "m3": (1.0, "m3"),

        # Distance -> km
        "miles": (1.60934, "km"),
        "mile": (1.60934, "km"),
        "mi": (1.60934, "km"),
        "km": (1.0, "km"),
        "passenger_km": (1.0, "passenger_km"),
        "passenger_miles": (1.60934, "passenger_km"),

        # Weight / Freight -> kg or tonne_km
        "tonne_km": (1.0, "tonne_km"),
        "ton_miles": (1.45997, "tonne_km"),
        "kg": (1.0, "kg"),
        "lbs": (0.453592, "kg"),
        "pounds": (0.453592, "kg"),
        "metric_tons": (1000.0, "kg"),

        # Units
        "units": (1.0, "units"),
        "unit": (1.0, "units"),
        "pcs": (1.0, "units"),
        "devices": (1.0, "units")
    }

    def _normalize_date(self, raw_date_str: str) -> str:
        if not raw_date_str:
            return datetime.now(timezone.utc).strftime("%Y-%m-%d")

        raw_date_str = str(raw_date_str).strip()
        # Common date formats
        formats = [
            "%Y-%m-%d", "%Y/%m/%d",
            "%m/%d/%Y", "%m-%d-%Y",
            "%d/%m/%Y", "%d-%m-%Y",
            "%B %d, %Y", "%b %d, %Y"
        ]
        for fmt in formats:
            try:
                dt = datetime.strptime(raw_date_str, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue

        # Regex fallback for YYYY-MM-DD anywhere in string
        match = re.search(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', raw_date_str)
        if match:
            y, m, d = match.groups()
            return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"

        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _extract_activity_and_unit(self, raw_data: Dict[str, Any]) -> Tuple[str, float, str]:
        # Identify quantity
        raw_qty = None
        for key in ["quantity", "usage", "consumption", "amount_used", "volume", "distance", "units"]:
            if key in raw_data and raw_data[key] is not None:
                try:
                    raw_qty = float(raw_data[key])
                    break
                except (ValueError, TypeError):
                    continue

        if raw_qty is None:
            raw_qty = 1.0

        # Identify unit
        raw_unit = "unknown"
        for key in ["unit", "uom", "measurement_unit", "unit_of_measure"]:
            if key in raw_data and raw_data[key]:
                raw_unit = str(raw_data[key]).strip().lower()
                break

        # Identify activity / description
        raw_activity = ""
        for key in ["activity", "description", "service_type", "fuel_type", "category", "item"]:
            if key in raw_data and raw_data[key]:
                raw_activity = str(raw_data[key]).strip().lower()
                break

        return raw_activity, raw_qty, raw_unit

    def normalize(self, raw_record: RawRecord) -> NormalizedRecord:
        raw_data = raw_record.raw_data
        raw_activity, raw_qty, raw_unit = self._extract_activity_and_unit(raw_data)

        # Date normalization
        raw_date = raw_data.get("date") or raw_data.get("billing_date") or raw_data.get("transaction_date") or ""
        norm_date = self._normalize_date(str(raw_date))

        # Supplier / facility
        supplier = (
            raw_data.get("supplier") or
            raw_data.get("vendor") or
            raw_data.get("facility") or
            raw_data.get("provider") or
            "General Supplier"
        )

        # Unit Conversion
        clean_unit = raw_unit.replace(" ", "_").lower()
        if clean_unit in self.UNIT_CONVERSIONS:
            multiplier, standard_unit = self.UNIT_CONVERSIONS[clean_unit]
            normalized_qty = raw_qty * multiplier
            conversion_applied = multiplier
        else:
            # Check substrings
            matched = False
            for k, (mult, std_unit) in self.UNIT_CONVERSIONS.items():
                if k in clean_unit:
                    multiplier, standard_unit = mult, std_unit
                    normalized_qty = raw_qty * multiplier
                    conversion_applied = multiplier
                    matched = True
                    break
            if not matched:
                normalized_qty = raw_qty
                standard_unit = raw_unit
                conversion_applied = 1.0

        # Determine standardized activity type
        combined_text = f"{raw_activity} {raw_unit}".lower()
        if "flight" in combined_text or "air travel" in combined_text or "airline" in combined_text:
            activity_type = "air_travel_passenger_km"
            if standard_unit == "km":
                standard_unit = "passenger_km"
        elif "rail" in combined_text or "train" in combined_text:
            activity_type = "rail_travel_passenger_km"
            if standard_unit == "km":
                standard_unit = "passenger_km"
        elif "freight" in combined_text or "trucking" in combined_text or "logistics" in combined_text:
            if "air" in combined_text:
                activity_type = "freight_air_tonne_km"
            else:
                activity_type = "freight_truck_tonne_km"
        elif "gasoline" in combined_text or "petrol" in combined_text:
            activity_type = "gasoline_fuel_liters"
        elif "diesel" in combined_text or "fleet fuel" in combined_text:
            activity_type = "diesel_fuel_liters"
        elif "lpg" in combined_text or "propane" in combined_text:
            activity_type = "lpg_liters"
        elif "gas" in combined_text or "natural gas" in combined_text or "heating" in combined_text:
            if standard_unit == "therms":
                activity_type = "natural_gas_therm"
            elif standard_unit == "m3":
                activity_type = "natural_gas_m3"
            else:
                activity_type = "natural_gas_kwh"
        elif "solar" in combined_text or "green power" in combined_text or "renewable" in combined_text:
            activity_type = "electricity_grid_green_kwh"
        elif "electricity" in combined_text or "power" in combined_text or "electric" in combined_text or standard_unit == "kwh":
            activity_type = "electricity_grid_kwh"
        elif "laptop" in combined_text or "computer" in combined_text or "hardware" in combined_text or "server" in combined_text:
            activity_type = "it_hardware_unit"
        elif "waste" in combined_text or "trash" in combined_text or "landfill" in combined_text:
            activity_type = "waste_landfill_kg"
        else:
            activity_type = raw_activity or "unspecified_activity"

        return NormalizedRecord(
            record_id=raw_record.record_id,
            source_type=raw_record.source_type,
            raw_document_ref=raw_record.raw_document_ref,
            date=norm_date,
            supplier_or_facility=str(supplier),
            activity_type=activity_type,
            original_quantity=raw_qty,
            original_unit=raw_unit,
            normalized_quantity=round(normalized_qty, 4),
            normalized_unit=standard_unit,
            conversion_factor_applied=conversion_applied,
            notes=f"Converted {raw_qty} {raw_unit} -> {round(normalized_qty, 4)} {standard_unit}"
        )
