import csv
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any
from core.schema import RawRecord, SourceType

class ERPConnector:
    """Connects and extracts records from ERP exports (Procurement, Travel, Logistics)."""

    @staticmethod
    def _compute_hash(data: Dict[str, Any]) -> str:
        s = json.dumps(data, sort_keys=True)
        return hashlib.sha256(s.encode('utf-8')).hexdigest()

    def parse_file(self, file_path: str | Path, raw_document_ref: str = "") -> List[RawRecord]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"ERP file not found: {path}")

        doc_ref = raw_document_ref or str(path)
        records = []
        if path.suffix.lower() == '.csv':
            with open(path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for idx, row in enumerate(reader):
                    clean_row = {k.strip(): v.strip() for k, v in row.items() if k}
                    record_id = clean_row.get("transaction_id") or clean_row.get("erp_ref") or f"ERP-{path.stem}-{idx+1:04d}"
                    raw_hash = self._compute_hash(clean_row)
                    records.append(RawRecord(
                        record_id=record_id,
                        source_type=SourceType.ERP,
                        source_file=path.name,
                        raw_document_ref=doc_ref,
                        raw_data=clean_row,
                        raw_hash=raw_hash
                    ))
        elif path.suffix.lower() == '.json':
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                items = data if isinstance(data, list) else data.get("transactions", [data])
                for idx, item in enumerate(items):
                    record_id = item.get("transaction_id") or item.get("erp_ref") or f"ERP-{path.stem}-{idx+1:04d}"
                    raw_hash = self._compute_hash(item)
                    records.append(RawRecord(
                        record_id=record_id,
                        source_type=SourceType.ERP,
                        source_file=path.name,
                        raw_document_ref=doc_ref,
                        raw_data=item,
                        raw_hash=raw_hash
                    ))
        return records
