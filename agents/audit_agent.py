from typing import List, Set, Tuple
from core.schema import CalculatedRecord, AuditCheckResult, AuditStatus
from core.config import CONFIDENCE_THRESHOLD

class AuditAgent:
    """
    Audit Agent:
    Performs comprehensive automated verification, outlier detection,
    confidence validation, and duplicate checking before any record enters disclosures.
    """

    # Reasonable single-transaction upper bounds per category for outlier checks
    CATEGORY_UPPER_BOUNDS = {
        "Purchased Electricity": 1_000_000, # kWh
        "Stationary Combustion": 200_000,   # kWh / therms
        "Mobile Combustion": 20_000,        # liters
        "Business Travel": 25_000,          # passenger_km (approx max round-the-world flight leg)
        "Upstream Transportation": 50_000,  # tonne_km
        "Purchased Capital Goods": 500,     # units
        "Waste Generated in Operations": 100_000 # kg
    }

    def __init__(self, confidence_threshold: float = CONFIDENCE_THRESHOLD):
        self.confidence_threshold = confidence_threshold
        self.seen_signatures: Set[str] = set()

    def reset_batch_state(self):
        self.seen_signatures.clear()

    def audit_record(self, record: CalculatedRecord) -> AuditCheckResult:
        flag_reasons: List[str] = []
        is_anomaly = False

        # 1. Negative or Zero Checks
        if record.activity_quantity <= 0:
            flag_reasons.append(f"Invalid non-positive activity quantity: {record.activity_quantity}")
            is_anomaly = True

        if record.kg_co2e <= 0:
            flag_reasons.append(f"Invalid non-positive emissions value: {record.kg_co2e} kgCO2e")
            is_anomaly = True

        # 2. Category Benchmark Outlier Check
        benchmark = self.CATEGORY_UPPER_BOUNDS.get(record.category)
        if benchmark and record.activity_quantity > benchmark:
            flag_reasons.append(
                f"Statistical Outlier: Activity quantity {record.activity_quantity:,.1f} {record.activity_unit} "
                f"exceeds single-transaction ceiling of {benchmark:,.1f} for {record.category}"
            )
            is_anomaly = True

        # Extreme single record emissions check (> 500 metric tonnes in single invoice)
        if record.tonnes_co2e > 500.0:
            flag_reasons.append(
                f"High-Impact Outlier: {record.tonnes_co2e:,.2f} tCO2e exceeds automatic approval ceiling of 500 tCO2e"
            )
            is_anomaly = True

        # 3. Duplicate Detection within batch
        signature = f"{record.supplier_or_facility.strip().lower()}_{record.date}_{record.activity_type}_{record.activity_quantity}"
        if signature in self.seen_signatures:
            flag_reasons.append(f"Potential duplicate record: matching supplier, date, and activity detected in batch")
            is_anomaly = True
        else:
            self.seen_signatures.add(signature)

        # 4. Supplier data quality
        if not record.supplier_or_facility or record.supplier_or_facility.lower() == "general supplier":
            flag_reasons.append("Missing explicit supplier or facility identifier")

        # 5. Confidence Threshold
        if record.confidence_score < self.confidence_threshold:
            flag_reasons.append(
                f"Low confidence score: {record.confidence_score:.2f} is below required threshold of {self.confidence_threshold:.2f}"
            )

        # Determine Final Status
        if flag_reasons or is_anomaly:
            status = AuditStatus.FLAGGED_HITL
        else:
            status = AuditStatus.APPROVED

        return AuditCheckResult(
            record_id=record.record_id,
            status=status,
            confidence_score=record.confidence_score,
            flag_reasons=flag_reasons,
            is_anomaly=is_anomaly
        )
