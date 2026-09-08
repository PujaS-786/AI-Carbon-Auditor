import json
import pytest
from pathlib import Path
from core.config import (
    BASE_DIR, RAW_DIR, RAW_INVOICES_DIR, RAW_ERP_DIR, RAW_UTILITY_DIR,
    PROCESSED_DIR, HITL_RESOLUTIONS_FILE
)
from core.schema import AuditStatus, ScopeType, RawRecord, SourceType
from core.audit_trail import AuditLedger
from agents.ingestion_agent import IngestionAgent
from agents.normalization_agent import NormalizationAgent
from agents.calculation_agent import CalculationAgent
from agents.audit_agent import AuditAgent
from agents.orchestrator import PipelineOrchestrator
from hitl.review_queue import HITLReviewQueue

def test_case_1_scope_1_unit_conversion():
    """Case 1: Fuel gallons -> Liters normalization & Scope 1 calculation"""
    norm = NormalizationAgent()
    calc = CalculationAgent()

    raw = RawRecord(
        record_id="TC-01-DIESEL",
        source_type=SourceType.INVOICE,
        source_file="invoice_diesel.csv",
        raw_document_ref="storage/raw/invoices/invoice_diesel.csv",
        raw_data={
            "vendor": "Apex Fuel",
            "activity": "fleet diesel",
            "quantity": 100.0,
            "unit": "gallons",
            "date": "2026-03-01"
        },
        raw_hash="hash01"
    )

    normalized = norm.normalize(raw)
    assert normalized.normalized_unit == "liters"
    assert round(normalized.normalized_quantity, 2) == 378.54

    calculated = calc.calculate(normalized)
    assert calculated.scope == ScopeType.SCOPE_1
    assert calculated.category == "Mobile Combustion"
    assert calculated.kg_co2e > 0
    assert calculated.confidence_score >= 0.85

def test_case_2_scope_2_electricity():
    """Case 2: Grid Electricity kWh -> Scope 2 calculation"""
    norm = NormalizationAgent()
    calc = CalculationAgent()

    raw = RawRecord(
        record_id="TC-02-ELEC",
        source_type=SourceType.UTILITY,
        source_file="bill.json",
        raw_document_ref="storage/raw/utility/bill.json",
        raw_data={
            "provider": "ConEd Electric Grid",
            "service_type": "grid electricity",
            "consumption": 50000,
            "unit": "kWh",
            "billing_date": "2026-03-01"
        },
        raw_hash="hash02"
    )

    normalized = norm.normalize(raw)
    calculated = calc.calculate(normalized)

    assert calculated.scope == ScopeType.SCOPE_2
    assert calculated.category == "Purchased Electricity"
    assert calculated.confidence_score >= 0.85

def test_case_3_scope_3_travel_and_logistics():
    """Case 3: Business flight & freight logistics -> Scope 3 calculation"""
    norm = NormalizationAgent()
    calc = CalculationAgent()

    raw = RawRecord(
        record_id="TC-03-FLIGHT",
        source_type=SourceType.ERP,
        source_file="erp.csv",
        raw_document_ref="storage/raw/erp/erp.csv",
        raw_data={
            "vendor": "Delta Airlines",
            "description": "commercial flight NYC-LON",
            "quantity": 5570,
            "unit": "km",
            "transaction_date": "2026-03-01"
        },
        raw_hash="hash03"
    )

    normalized = norm.normalize(raw)
    calculated = calc.calculate(normalized)

    assert calculated.scope == ScopeType.SCOPE_3
    assert calculated.category == "Business Travel"
    assert calculated.confidence_score >= 0.85

def test_case_4_statistical_outlier_detection():
    """Case 4: Extreme outlier volume triggers HITL review"""
    norm = NormalizationAgent()
    calc = CalculationAgent()
    audit = AuditAgent()

    raw = RawRecord(
        record_id="TC-04-OUTLIER",
        source_type=SourceType.INVOICE,
        source_file="invoice_huge.csv",
        raw_document_ref="storage/raw/invoices/invoice_huge.csv",
        raw_data={
            "vendor": "Anomalous Fuels Unlimited",
            "activity": "fleet diesel",
            "quantity": 850000,
            "unit": "gallons",
            "date": "2026-03-01"
        },
        raw_hash="hash04"
    )

    normalized = norm.normalize(raw)
    calculated = calc.calculate(normalized)
    audit_res = audit.audit_record(calculated)

    assert audit_res.status == AuditStatus.FLAGGED_HITL
    assert audit_res.is_anomaly is True
    assert any("Outlier" in r for r in audit_res.flag_reasons)

def test_case_5_duplicate_detection():
    """Case 5: Detecting duplicate transactions in the same batch"""
    audit = AuditAgent()
    calc = CalculationAgent()
    norm = NormalizationAgent()

    def make_record(rec_id):
        raw = RawRecord(
            record_id=rec_id,
            source_type=SourceType.INVOICE,
            source_file="invoice.csv",
            raw_document_ref="storage/raw/invoices/invoice.csv",
            raw_data={
                "vendor": "Metro Logistics",
                "activity": "freight trucking",
                "quantity": 1000,
                "unit": "tonne_km",
                "date": "2026-03-01"
            },
            raw_hash=f"hash_{rec_id}"
        )
        return calc.calculate(norm.normalize(raw))

    rec1 = make_record("TC-05-A")
    rec2 = make_record("TC-05-B")

    res1 = audit.audit_record(rec1)
    res2 = audit.audit_record(rec2)

    assert res1.status == AuditStatus.APPROVED
    assert res2.status == AuditStatus.FLAGGED_HITL
    assert any("duplicate" in r.lower() for r in res2.flag_reasons)

def test_case_6_data_integrity_tamper_detection(tmp_path):
    """Case 6: Cryptographic hash chain detects tampering instantly"""
    test_ledger_path = tmp_path / "test_ledger.jsonl"
    ledger = AuditLedger(ledger_file=test_ledger_path)

    # Append two blocks
    b1 = ledger.append_block(
        record_id="REC-001",
        agent_name="TestAgent",
        action="CALCULATE",
        payload_summary={"emissions": 100.0}
    )
    b2 = ledger.append_block(
        record_id="REC-002",
        agent_name="TestAgent",
        action="CALCULATE",
        payload_summary={"emissions": 200.0}
    )

    # Verify intact chain
    is_valid, msg, _ = ledger.verify_chain_integrity()
    assert is_valid is True

    # Tamper with the ledger file (modify block 1 emissions)
    with open(test_ledger_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    tampered_line = lines[1].replace("100.0", "99999.0")
    lines[1] = tampered_line

    with open(test_ledger_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)

    # Re-verify integrity
    is_valid_after, msg_after, details = ledger.verify_chain_integrity()
    assert is_valid_after is False
    assert "tampering detected" in msg_after.lower() or "compromised" in msg_after.lower()
