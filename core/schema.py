from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone

class SourceType(str, Enum):
    INVOICE = "invoice"
    ERP = "erp"
    UTILITY = "utility"
    MANUAL = "manual"

class ScopeType(str, Enum):
    SCOPE_1 = "Scope 1"
    SCOPE_2 = "Scope 2"
    SCOPE_3 = "Scope 3"

class AuditStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    FLAGGED_HITL = "FLAGGED_HITL"
    RESOLVED = "RESOLVED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"

class RawRecord(BaseModel):
    record_id: str
    source_type: SourceType
    source_file: str
    raw_document_ref: str = ""
    raw_data: Dict[str, Any]
    ingested_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    raw_hash: str

class NormalizedRecord(BaseModel):
    record_id: str
    source_type: SourceType
    raw_document_ref: str = ""
    date: str
    supplier_or_facility: str
    activity_type: str
    original_quantity: float
    original_unit: str
    normalized_quantity: float
    normalized_unit: str
    conversion_factor_applied: float = 1.0
    notes: Optional[str] = None

class CalculatedRecord(BaseModel):
    record_id: str
    raw_document_ref: str = ""
    ledger_block_hash: Optional[str] = None
    date: str
    supplier_or_facility: str
    activity_type: str
    scope: ScopeType
    category: str
    activity_quantity: float
    activity_unit: str
    emission_factor_key: str
    emission_factor_value: float
    emission_factor_unit: str
    kg_co2e: float
    tonnes_co2e: float
    confidence_score: float

class AuditCheckResult(BaseModel):
    record_id: str
    raw_document_ref: str = ""
    status: AuditStatus
    confidence_score: float
    flag_reasons: List[str] = Field(default_factory=list)
    is_anomaly: bool = False
    audited_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class HITLReviewItem(BaseModel):
    record_id: str
    calculated_record: CalculatedRecord
    flag_reasons: List[str]
    confidence_score: float
    status: AuditStatus = AuditStatus.FLAGGED_HITL
    flagged_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resolved_by: Optional[str] = None
    resolved_at: Optional[str] = None
    reviewer_notes: Optional[str] = None
    adjusted_quantity: Optional[float] = None
    adjusted_kg_co2e: Optional[float] = None

class HITLResolutionRecord(BaseModel):
    record_id: str
    supplier_or_facility: str = ""
    activity_type: str = ""
    original_confidence: float
    decision: str  # approve, override, reject
    corrected_value: Optional[float] = None
    rationale: str
    resolved_by: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class LedgerBlock(BaseModel):
    index: int
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    record_id: str
    agent_name: str
    action: str
    payload_summary: Dict[str, Any]
    payload_hash: str
    previous_hash: str
    block_hash: str
