import traceback
from pathlib import Path
from typing import List, Dict, Any, Union, Optional
from core.schema import (
    RawRecord, NormalizedRecord, CalculatedRecord,
    AuditStatus, SourceType
)
from core.audit_trail import audit_ledger
from hitl.review_queue import hitl_queue
from agents.ingestion_agent import IngestionAgent
from agents.normalization_agent import NormalizationAgent
from agents.calculation_agent import CalculationAgent
from agents.audit_agent import AuditAgent
from agents.reporting_agent import ReportingAgent

class PipelineOrchestrator:
    """
    Hierarchical Supervisor Orchestrator:
    Coordinates specialist agents, isolates record failures,
    enforces cryptographic audit logging for every stage, and triggers disclosures.
    """

    def __init__(self):
        self.ingestion_agent = IngestionAgent()
        self.normalization_agent = NormalizationAgent()
        self.calculation_agent = CalculationAgent()
        self.audit_agent = AuditAgent()
        self.reporting_agent = ReportingAgent()

        # In-memory record tracking
        self.processed_records: Dict[str, CalculatedRecord] = {}
        self.record_statuses: Dict[str, AuditStatus] = {}

    def process_record(self, raw_record: RawRecord) -> Optional[CalculatedRecord]:
        """
        Processes a single record through the hierarchical multi-agent pipeline.
        Implements strict per-record error isolation and cryptographic audit trail logging.
        """
        record_id = raw_record.record_id

        try:
            # 1. Log Ingestion in Cryptographic Ledger
            audit_ledger.append_block(
                record_id=record_id,
                agent_name="IngestionAgent",
                action="RECORD_INGESTED",
                payload_summary={
                    "source_type": raw_record.source_type.value,
                    "source_file": raw_record.source_file,
                    "raw_hash": raw_record.raw_hash
                }
            )

            # 2. Normalization Agent
            normalized = self.normalization_agent.normalize(raw_record)
            audit_ledger.append_block(
                record_id=record_id,
                agent_name="NormalizationAgent",
                action="DATA_NORMALIZED",
                payload_summary={
                    "standard_activity": normalized.activity_type,
                    "normalized_qty": normalized.normalized_quantity,
                    "normalized_unit": normalized.normalized_unit,
                    "date": normalized.date,
                    "conversion_applied": normalized.conversion_factor_applied
                }
            )

            # 3. Calculation Agent
            calculated = self.calculation_agent.calculate(normalized)
            calc_block = audit_ledger.append_block(
                record_id=record_id,
                agent_name="CalculationAgent",
                action="EMISSIONS_CALCULATED",
                payload_summary={
                    "scope": calculated.scope.value,
                    "category": calculated.category,
                    "factor_key": calculated.emission_factor_key,
                    "factor_value": calculated.emission_factor_value,
                    "kg_co2e": calculated.kg_co2e,
                    "tonnes_co2e": calculated.tonnes_co2e,
                    "confidence_score": calculated.confidence_score
                }
            )
            calculated.ledger_block_hash = calc_block.block_hash

            # 4. Audit Agent
            audit_result = self.audit_agent.audit_record(calculated)

            if audit_result.status == AuditStatus.APPROVED:
                self.record_statuses[record_id] = AuditStatus.APPROVED
                self.processed_records[record_id] = calculated

                audit_ledger.append_block(
                    record_id=record_id,
                    agent_name="AuditAgent",
                    action="AUDIT_VERIFIED_APPROVED",
                    payload_summary={
                        "status": "APPROVED",
                        "confidence": audit_result.confidence_score,
                        "notes": "Passed all automated consistency, outlier, and confidence gates."
                    }
                )
            else:
                # Flagged for Human-in-the-Loop review
                self.record_statuses[record_id] = AuditStatus.FLAGGED_HITL
                self.processed_records[record_id] = calculated
                hitl_queue.enqueue(
                    record=calculated,
                    flag_reasons=audit_result.flag_reasons,
                    confidence_score=audit_result.confidence_score
                )

                audit_ledger.append_block(
                    record_id=record_id,
                    agent_name="AuditAgent",
                    action="AUDIT_FLAGGED_FOR_HITL",
                    payload_summary={
                        "status": "FLAGGED_HITL",
                        "confidence": audit_result.confidence_score,
                        "flag_reasons": audit_result.flag_reasons,
                        "is_anomaly": audit_result.is_anomaly
                    }
                )

            return calculated

        except Exception as e:
            # Per-record isolation: log failure and continue batch without crashing
            stack = traceback.format_exc()
            self.record_statuses[record_id] = AuditStatus.FAILED
            audit_ledger.append_block(
                record_id=record_id,
                agent_name="OrchestratorSupervisor",
                action="RECORD_PROCESSING_FAILED",
                payload_summary={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "traceback": stack[:300]
                }
            )
            return None

    def run_file(self, file_path: Union[str, Path], source_hint: str = "auto") -> Dict[str, Any]:
        """
        Ingests a complete file through the supervisor pipeline and compiles disclosures.
        """
        raw_records = self.ingestion_agent.ingest_file(file_path, source_hint)
        self.audit_agent.reset_batch_state()

        successful_records = []
        failed_count = 0

        for r in raw_records:
            res = self.process_record(r)
            if res:
                successful_records.append(res)
            else:
                failed_count += 1

        # Generate disclosure report
        return self.compile_disclosure_report()

    def compile_disclosure_report(self) -> Dict[str, Any]:
        """
        Aggregates all approved and resolved records into the official board disclosure.
        """
        all_hitl = hitl_queue.get_all_items()
        resolved_items = [item for item in all_hitl if item.status == AuditStatus.RESOLVED]
        rejected_items = [item for item in all_hitl if item.status == AuditStatus.REJECTED]
        pending_items = [item for item in all_hitl if item.status == AuditStatus.FLAGGED_HITL]

        # Gather approved records: Auto-approved + HITL-resolved
        approved_map = {}
        for rec_id, rec in self.processed_records.items():
            if self.record_statuses.get(rec_id) == AuditStatus.APPROVED:
                approved_map[rec_id] = rec

        for item in resolved_items:
            approved_map[item.record_id] = item.calculated_record

        approved_list = list(approved_map.values())
        total_ingested = len(self.processed_records)

        return self.reporting_agent.generate_disclosure(
            approved_records=approved_list,
            total_records_count=total_ingested,
            hitl_flagged_count=len(pending_items) + len(resolved_items) + len(rejected_items),
            hitl_resolved_count=len(resolved_items),
            hitl_rejected_count=len(rejected_items)
        )

    def get_all_records_summary(self) -> List[Dict[str, Any]]:
        """Returns structured view of all records with their current lifecycle status."""
        records_summary = []
        for rec_id, rec in self.processed_records.items():
            status = self.record_statuses.get(rec_id, AuditStatus.PENDING)
            hitl_item = hitl_queue.get_item(rec_id)
            if hitl_item:
                status = hitl_item.status

            records_summary.append({
                "record_id": rec.record_id,
                "raw_document_ref": rec.raw_document_ref,
                "ledger_block_hash": rec.ledger_block_hash or "PENDING",
                "date": rec.date,
                "supplier_or_facility": rec.supplier_or_facility,
                "activity_type": rec.activity_type,
                "scope": rec.scope.value if hasattr(rec.scope, 'value') else str(rec.scope),
                "category": rec.category,
                "quantity": rec.activity_quantity,
                "unit": rec.activity_unit,
                "kg_co2e": rec.kg_co2e,
                "tonnes_co2e": rec.tonnes_co2e,
                "confidence_score": rec.confidence_score,
                "status": status.value if hasattr(status, 'value') else str(status),
                "flag_reasons": hitl_item.flag_reasons if hitl_item else []
            })
        return records_summary

# Singleton orchestrator instance
orchestrator = PipelineOrchestrator()
