import shutil
from pathlib import Path
from typing import List, Dict, Any, Union
from core.schema import RawRecord, SourceType
from core.config import BASE_DIR, RAW_DIR, RAW_INVOICES_DIR, RAW_ERP_DIR, RAW_UTILITY_DIR
from ingestion_sources.invoice_parser import InvoiceParser
from ingestion_sources.erp_connector import ERPConnector
from ingestion_sources.utility_connector import UtilityConnector

class IngestionAgent:
    """
    Ingestion Agent:
    Parses multi-source files, archives raw copies immutably in typed landing zones,
    and produces standardized RawRecords with audit trail references.
    """

    def __init__(self):
        self.invoice_parser = InvoiceParser()
        self.erp_connector = ERPConnector()
        self.utility_connector = UtilityConnector()

    def _resolve_source_type(self, path: Path, source_hint: str) -> SourceType:
        source_hint = source_hint.lower().strip()
        if source_hint in ["invoice", "invoices"]:
            return SourceType.INVOICE
        elif source_hint in ["erp", "travel", "procurement"]:
            return SourceType.ERP
        elif source_hint in ["utility", "meter", "bill"]:
            return SourceType.UTILITY

        lower_name = path.name.lower()
        if "invoice" in lower_name:
            return SourceType.INVOICE
        elif "erp" in lower_name or "travel" in lower_name or "procurement" in lower_name:
            return SourceType.ERP
        elif "utility" in lower_name or "meter" in lower_name or "bill" in lower_name:
            return SourceType.UTILITY
        return SourceType.INVOICE

    def _get_target_dir(self, source_type: SourceType) -> Path:
        if source_type == SourceType.INVOICE:
            return RAW_INVOICES_DIR
        elif source_type == SourceType.ERP:
            return RAW_ERP_DIR
        elif source_type == SourceType.UTILITY:
            return RAW_UTILITY_DIR
        return RAW_DIR

    def ingest_file(self, file_path: Union[str, Path], source_hint: str = "auto") -> List[RawRecord]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found for ingestion: {path}")

        source_type = self._resolve_source_type(path, source_hint)
        target_dir = self._get_target_dir(source_type)
        target_file = target_dir / path.name

        # Preserve raw file immutably in typed raw subdirectory (INPUT ZONE)
        try:
            if path.resolve() != target_file.resolve() and not target_file.exists():
                shutil.copy2(path, target_file)
        except Exception:
            pass

        # Compute canonical relative reference (e.g. storage/raw/invoices/sample_invoices.csv)
        effective_path = target_file if target_file.exists() else path
        try:
            doc_ref = effective_path.relative_to(BASE_DIR).as_posix()
        except ValueError:
            doc_ref = effective_path.as_posix()

        if source_type == SourceType.INVOICE:
            return self.invoice_parser.parse_file(effective_path, raw_document_ref=doc_ref)
        elif source_type == SourceType.ERP:
            return self.erp_connector.parse_file(effective_path, raw_document_ref=doc_ref)
        elif source_type == SourceType.UTILITY:
            return self.utility_connector.parse_file(effective_path, raw_document_ref=doc_ref)
        else:
            return self.invoice_parser.parse_file(effective_path, raw_document_ref=doc_ref)

    def ingest_direct_record(self, raw_data: Dict[str, Any], source_type: SourceType = SourceType.MANUAL) -> RawRecord:
        import json, hashlib
        raw_hash = hashlib.sha256(json.dumps(raw_data, sort_keys=True).encode('utf-8')).hexdigest()
        record_id = raw_data.get("record_id") or f"MANUAL-{raw_hash[:8]}"
        return RawRecord(
            record_id=record_id,
            source_type=source_type,
            source_file="direct_api_input",
            raw_document_ref="direct_api_input",
            raw_data=raw_data,
            raw_hash=raw_hash
        )
