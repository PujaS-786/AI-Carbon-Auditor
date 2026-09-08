from core.schema import RawRecord, SourceType, AuditStatus
from agents.normalization_agent import NormalizationAgent
from agents.calculation_agent import CalculationAgent
from agents.audit_agent import AuditAgent
from agents.orchestrator import PipelineOrchestrator

def test_normalization_units():
    agent = NormalizationAgent()

    # Test gallons to liters
    raw = RawRecord(
        record_id="INV-001",
        source_type=SourceType.INVOICE,
        source_file="test.csv",
        raw_data={
            "vendor": "Fleet Fuel Co",
            "activity": "fleet diesel",
            "quantity": "100",
            "unit": "gallons",
            "date": "2024-01-15"
        },
        raw_hash="testhash"
    )
    norm = agent.normalize(raw)
    assert norm.activity_type == "diesel_fuel_liters"
    assert round(norm.normalized_quantity, 2) == 378.54
    assert norm.normalized_unit == "liters"
    assert norm.date == "2024-01-15"

def test_calculation_emissions():
    norm_agent = NormalizationAgent()
    calc_agent = CalculationAgent()

    raw = RawRecord(
        record_id="UTIL-001",
        source_type=SourceType.UTILITY,
        source_file="test.json",
        raw_data={
            "provider": "ConEd",
            "service_type": "grid electricity",
            "consumption": 1000,
            "unit": "kWh",
            "date": "2024-02-01"
        },
        raw_hash="testhash"
    )
    norm = norm_agent.normalize(raw)
    calc = calc_agent.calculate(norm)

    assert calc.scope.value == "Scope 2"
    assert calc.category == "Purchased Electricity"
    assert calc.kg_co2e == 372.0
    assert calc.tonnes_co2e == 0.372
    assert calc.confidence_score >= 0.85

def test_audit_agent_anomaly_detection():
    audit_agent = AuditAgent()
    norm_agent = NormalizationAgent()
    calc_agent = CalculationAgent()

    # Outlier: 850,000 gallons of fleet fuel in single invoice (> 20,000 ceiling)
    raw_outlier = RawRecord(
        record_id="OUTLIER-01",
        source_type=SourceType.INVOICE,
        source_file="test.csv",
        raw_data={
            "vendor": "Super Fuels",
            "activity": "fleet diesel",
            "quantity": 850000,
            "unit": "gallons",
            "date": "2024-01-01"
        },
        raw_hash="testhash"
    )
    norm = norm_agent.normalize(raw_outlier)
    calc = calc_agent.calculate(norm)
    audit_res = audit_agent.audit_record(calc)

    assert audit_res.status == AuditStatus.FLAGGED_HITL
    assert audit_res.is_anomaly is True
    assert any("Statistical Outlier" in r or "High-Impact Outlier" in r for r in audit_res.flag_reasons)

def test_pipeline_orchestrator_execution():
    orchestrator = PipelineOrchestrator()
    raw = RawRecord(
        record_id="TEST-REC-99",
        source_type=SourceType.INVOICE,
        source_file="inline_test",
        raw_data={
            "vendor": "Clean Logistics",
            "activity": "freight trucking",
            "quantity": 500,
            "unit": "tonne_km",
            "date": "2024-03-10"
        },
        raw_hash="hash99"
    )
    calc = orchestrator.process_record(raw)
    assert calc is not None
    assert calc.record_id == "TEST-REC-99"
    assert orchestrator.record_statuses.get("TEST-REC-99") == AuditStatus.APPROVED
