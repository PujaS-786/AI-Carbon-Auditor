import os
import json
import pytest
from pathlib import Path
from core.config import (
    BASE_DIR, RAW_DIR, RAW_INVOICES_DIR, RAW_ERP_DIR, RAW_UTILITY_DIR,
    PROCESSED_DIR, HITL_RESOLUTIONS_FILE, SAMPLE_DATA_DIR
)
from core.schema import AuditStatus
from agents.ingestion_agent import IngestionAgent
from agents.normalization_agent import NormalizationAgent
from agents.calculation_agent import CalculationAgent
from agents.orchestrator import PipelineOrchestrator
from hitl.review_queue import HITLReviewQueue
from app import app

def test_input_landing_zones_routing():
    """Verify files land in typed subdirectories per INPUT_OUTPUT_SPEC.md §2.1"""
    ingestion = IngestionAgent()

    # Invoice
    inv_file = SAMPLE_DATA_DIR / "sample_invoices.csv"
    if inv_file.exists():
        records = ingestion.ingest_file(inv_file, source_hint="invoice")
        assert len(records) > 0
        assert (RAW_INVOICES_DIR / "sample_invoices.csv").exists()
        assert "storage/raw/invoices/sample_invoices.csv" in records[0].raw_document_ref

    # ERP
    erp_file = SAMPLE_DATA_DIR / "sample_erp.csv"
    if erp_file.exists():
        records = ingestion.ingest_file(erp_file, source_hint="erp")
        assert len(records) > 0
        assert (RAW_ERP_DIR / "sample_erp.csv").exists()
        assert "storage/raw/erp/sample_erp.csv" in records[0].raw_document_ref

    # Utility
    util_file = SAMPLE_DATA_DIR / "sample_utility.json"
    if util_file.exists():
        records = ingestion.ingest_file(util_file, source_hint="utility")
        assert len(records) > 0
        assert (RAW_UTILITY_DIR / "sample_utility.json").exists()
        assert "storage/raw/utility/sample_utility.json" in records[0].raw_document_ref

def test_raw_document_ref_pipeline_traceability():
    """Verify raw_document_ref propagates across all pipeline stages per §2.2 & §5"""
    orchestrator = PipelineOrchestrator()
    inv_file = SAMPLE_DATA_DIR / "sample_invoices.csv"

    orchestrator.run_file(inv_file, source_hint="invoice")
    summaries = orchestrator.get_all_records_summary()

    assert len(summaries) > 0
    for s in summaries:
        assert "raw_document_ref" in s
        assert "storage/raw/invoices/" in s["raw_document_ref"]
        assert "ledger_block_hash" in s
        assert s["ledger_block_hash"] is not None

def test_hitl_resolution_log_feedback_loop(tmp_path):
    """Verify HITL resolutions are logged to hitl_resolutions.jsonl per §7"""
    test_queue_file = tmp_path / "test_hitl_queue.json"
    queue = HITLReviewQueue(storage_file=test_queue_file)

    # Ingest a file to get a record
    orchestrator = PipelineOrchestrator()
    inv_file = SAMPLE_DATA_DIR / "sample_invoices.csv"
    orchestrator.run_file(inv_file)

    # Pick an item from queue
    items = queue.get_all_items()
    if not items:
        # Enqueue dummy calculated record
        from core.schema import CalculatedRecord, ScopeType
        dummy = CalculatedRecord(
            record_id="TEST-FEEDBACK-001",
            raw_document_ref="storage/raw/invoices/test.csv",
            date="2026-03-15",
            supplier_or_facility="Test Supplier Anomalous",
            activity_type="diesel_fuel_liters",
            scope=ScopeType.SCOPE_1,
            category="Mobile Combustion",
            activity_quantity=50000.0,
            activity_unit="liters",
            emission_factor_key="diesel_fuel_liters",
            emission_factor_value=2.68,
            emission_factor_unit="kgCO2e/liter",
            kg_co2e=134000.0,
            tonnes_co2e=134.0,
            confidence_score=0.60
        )
        item = queue.enqueue(dummy, ["Statistical outlier"], 0.60)
        target_id = item.record_id
    else:
        target_id = items[0].record_id

    # Resolve with override
    resolved = queue.resolve_item(
        record_id=target_id,
        reviewer_name="Senior Auditor",
        action="override",
        reviewer_notes="Corrected meter over-reporting by 50%",
        adjusted_quantity=25000.0
    )

    assert resolved.status == AuditStatus.RESOLVED
    assert resolved.adjusted_quantity == 25000.0

    # Check that hitl_resolutions.jsonl was appended
    assert HITL_RESOLUTIONS_FILE.exists()
    with open(HITL_RESOLUTIONS_FILE, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]
        last_entry = json.loads(lines[-1])
        assert last_entry["record_id"] == target_id
        assert last_entry["decision"] == "override"
        assert last_entry["resolved_by"] == "Senior Auditor"

def test_api_upload_routes_to_raw_landing_zone():
    """Verify Web upload stores file in storage/raw/ directly without scratch deletion"""
    client = app.test_client()

    csv_content = b"invoice_id,supplier,date,activity,quantity,unit,cost,currency\nINV-WEB-001,Web Vendor,2026-03-01,diesel fuel,100,liters,200,USD\n"
    data = {
        'file': (io_bytes := __import__('io').BytesIO(csv_content), 'web_upload_invoice.csv'),
        'source_hint': 'invoice'
    }

    res = client.post('/api/ingest', data=data, content_type='multipart/form-data')
    assert res.status_code == 200
    res_json = res.get_json()
    assert res_json["success"] is True

    target_saved_file = RAW_INVOICES_DIR / "web_upload_invoice.csv"
    assert target_saved_file.exists()

def test_hitl_resolve_all_endpoint():
    """Verify batch Accept All / Reject All endpoint functionality"""
    client = app.test_client()
    from hitl.review_queue import hitl_queue
    from core.schema import CalculatedRecord, ScopeType

    # Enqueue a dummy test item
    dummy = CalculatedRecord(
        record_id="BATCH-TEST-999",
        raw_document_ref="storage/raw/invoices/test.csv",
        date="2026-03-01",
        supplier_or_facility="Batch Test Vendor",
        activity_type="diesel_fuel_liters",
        scope=ScopeType.SCOPE_1,
        category="Mobile Combustion",
        activity_quantity=100.0,
        activity_unit="liters",
        emission_factor_key="diesel_fuel_liters",
        emission_factor_value=2.68,
        emission_factor_unit="kgCO2e/liter",
        kg_co2e=268.0,
        tonnes_co2e=0.268,
        confidence_score=0.60
    )
    hitl_queue.enqueue(dummy, ["Batch test check"], 0.60)

    # Test Accept All
    res = client.post('/api/hitl/resolve_all', json={'action': 'approve'})
    assert res.status_code == 200
    res_data = res.get_json()
    assert res_data['success'] is True
    assert res_data['count'] >= 1
