import json
import threading
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timezone
from core.schema import CalculatedRecord, HITLReviewItem, HITLResolutionRecord, AuditStatus
from core.config import PROCESSED_DIR, HITL_RESOLUTIONS_FILE
from core.audit_trail import audit_ledger
from core.emission_factors import get_factor

_queue_lock = threading.RLock()
HITL_STORAGE_FILE = PROCESSED_DIR / "hitl_queue.json"

class HITLReviewQueue:
    """
    Human-in-the-Loop Review Queue:
    Holds anomalous or low-confidence records for human auditor review,
    supports adjustments, and logs every resolution into the cryptographic ledger.
    """

    def __init__(self, storage_file: Path = HITL_STORAGE_FILE):
        self.storage_file = Path(storage_file)
        self.queue: Dict[str, HITLReviewItem] = {}
        self._load()

    def _load(self):
        if self.storage_file.exists():
            try:
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    raw_data = json.load(f)
                    for k, v in raw_data.items():
                        self.queue[k] = HITLReviewItem.model_validate(v)
            except Exception:
                self.queue = {}

    def _save(self):
        with open(self.storage_file, 'w', encoding='utf-8') as f:
            serializable = {k: v.model_dump() for k, v in self.queue.items()}
            json.dump(serializable, f, indent=2)

    def enqueue(self, record: CalculatedRecord, flag_reasons: List[str], confidence_score: float) -> HITLReviewItem:
        with _queue_lock:
            item = HITLReviewItem(
                record_id=record.record_id,
                calculated_record=record,
                flag_reasons=flag_reasons,
                confidence_score=confidence_score,
                status=AuditStatus.FLAGGED_HITL
            )
            self.queue[record.record_id] = item
            self._save()
            return item

    def get_pending_items(self) -> List[HITLReviewItem]:
        with _queue_lock:
            return [item for item in self.queue.values() if item.status == AuditStatus.FLAGGED_HITL]

    def get_all_items(self) -> List[HITLReviewItem]:
        with _queue_lock:
            return list(self.queue.values())

    def get_item(self, record_id: str) -> Optional[HITLReviewItem]:
        with _queue_lock:
            return self.queue.get(record_id)

    def resolve_item(
        self,
        record_id: str,
        reviewer_name: str,
        action: str, # "approve", "override", "reject"
        reviewer_notes: str,
        adjusted_quantity: Optional[float] = None,
        adjusted_factor_key: Optional[str] = None,
        auto_save: bool = True
    ) -> HITLReviewItem:
        with _queue_lock:
            item = self.queue.get(record_id)
            if not item:
                raise KeyError(f"Record {record_id} not found in HITL queue.")

            action = action.lower()
            timestamp = datetime.now(timezone.utc).isoformat()
            item.resolved_by = reviewer_name
            item.resolved_at = timestamp
            item.reviewer_notes = reviewer_notes

            if action == "approve":
                item.status = AuditStatus.RESOLVED
                # Log to cryptographic ledger
                audit_ledger.append_block(
                    record_id=record_id,
                    agent_name=f"HITL_Reviewer({reviewer_name})",
                    action="HUMAN_RESOLVE_APPROVE",
                    payload_summary={
                        "resolution": "Approved without modification",
                        "notes": reviewer_notes,
                        "kg_co2e": item.calculated_record.kg_co2e,
                        "tonnes_co2e": item.calculated_record.tonnes_co2e
                    }
                )

            elif action == "override":
                item.status = AuditStatus.RESOLVED
                old_qty = item.calculated_record.activity_quantity
                old_kg = item.calculated_record.kg_co2e

                if adjusted_quantity is not None:
                    item.adjusted_quantity = adjusted_quantity
                    item.calculated_record.activity_quantity = adjusted_quantity

                if adjusted_factor_key:
                    new_factor = get_factor(adjusted_factor_key)
                    if new_factor:
                        item.calculated_record.emission_factor_key = adjusted_factor_key
                        item.calculated_record.emission_factor_value = new_factor["factor"]
                        item.calculated_record.emission_factor_unit = new_factor["unit"]
                        item.calculated_record.category = new_factor["category"]
                        item.calculated_record.scope = new_factor["scope"]

                # Recalculate
                new_kg = item.calculated_record.activity_quantity * item.calculated_record.emission_factor_value
                item.calculated_record.kg_co2e = round(new_kg, 4)
                item.calculated_record.tonnes_co2e = round(new_kg / 1000.0, 6)
                item.adjusted_kg_co2e = item.calculated_record.kg_co2e
                item.calculated_record.confidence_score = 1.0 # Certified by human reviewer

                audit_ledger.append_block(
                    record_id=record_id,
                    agent_name=f"HITL_Reviewer({reviewer_name})",
                    action="HUMAN_RESOLVE_OVERRIDE",
                    payload_summary={
                        "resolution": "Overridden by auditor",
                        "notes": reviewer_notes,
                        "previous_quantity": old_qty,
                        "new_quantity": item.calculated_record.activity_quantity,
                        "previous_kg_co2e": old_kg,
                        "new_kg_co2e": item.calculated_record.kg_co2e,
                        "new_tonnes_co2e": item.calculated_record.tonnes_co2e
                    }
                )

            elif action == "reject":
                item.status = AuditStatus.REJECTED
                audit_ledger.append_block(
                    record_id=record_id,
                    agent_name=f"HITL_Reviewer({reviewer_name})",
                    action="HUMAN_RESOLVE_REJECT",
                    payload_summary={
                        "resolution": "Rejected - Excluded from disclosures",
                        "notes": reviewer_notes
                    }
                )
            else:
                raise ValueError(f"Unknown resolution action: {action}")

            # Feedback Loop (§7): Capture structured resolution for confidence recalibration
            try:
                res_record = HITLResolutionRecord(
                    record_id=record_id,
                    supplier_or_facility=item.calculated_record.supplier_or_facility,
                    activity_type=item.calculated_record.activity_type,
                    original_confidence=item.confidence_score,
                    decision=action,
                    corrected_value=item.calculated_record.kg_co2e if action == "override" else None,
                    rationale=reviewer_notes,
                    resolved_by=reviewer_name,
                    timestamp=timestamp
                )
                with open(HITL_RESOLUTIONS_FILE, 'a', encoding='utf-8') as f:
                    f.write(res_record.model_dump_json() + "\n")
            except Exception:
                pass

            if auto_save:
                self._save()
            return item

    def resolve_all_pending(
        self,
        reviewer_name: str,
        action: str,  # "approve" or "reject"
        reviewer_notes: str = "Batch resolved via HITL queue"
    ) -> List[HITLReviewItem]:
        action_normalized = "approve" if action.lower() in ["approve", "accept"] else action.lower()
        with _queue_lock:
            pending = [item for item in self.queue.values() if item.status == AuditStatus.FLAGGED_HITL]
            resolved_list = []
            for item in pending:
                res = self.resolve_item(
                    record_id=item.record_id,
                    reviewer_name=reviewer_name,
                    action=action_normalized,
                    reviewer_notes=reviewer_notes,
                    auto_save=False
                )
                resolved_list.append(res)
            self._save()
            return resolved_list

# Singleton queue instance
hitl_queue = HITLReviewQueue()
