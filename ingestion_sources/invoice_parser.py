import csv
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any
from core.schema import RawRecord, SourceType

class InvoiceParser:
    """Parses invoices from CSV, JSON, or structured text formats."""

    @staticmethod
    def _compute_hash(data: Dict[str, Any]) -> str:
        s = json.dumps(data, sort_keys=True)
        return hashlib.sha256(s.encode('utf-8')).hexdigest()

    def parse_file(self, file_path: str | Path, raw_document_ref: str = "") -> List[RawRecord]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Invoice file not found: {path}")

        doc_ref = raw_document_ref or str(path)
        records = []
        if path.suffix.lower() == '.csv':
            records = self._parse_csv(path, doc_ref)
        elif path.suffix.lower() == '.json':
            records = self._parse_json(path, doc_ref)
        else:
            records = self._parse_text(path, doc_ref)
        return records

    def _parse_csv(self, path: Path, doc_ref: str) -> List[RawRecord]:
        records = []
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader):
                clean_row = {k.strip(): v.strip() for k, v in row.items() if k}
                record_id = clean_row.get("invoice_id") or clean_row.get("invoice_number") or f"INV-{path.stem}-{idx+1:04d}"
                raw_hash = self._compute_hash(clean_row)
                records.append(RawRecord(
                    record_id=record_id,
                    source_type=SourceType.INVOICE,
                    source_file=path.name,
                    raw_document_ref=doc_ref,
                    raw_data=clean_row,
                    raw_hash=raw_hash
                ))
        return records

    def _parse_json(self, path: Path, doc_ref: str) -> List[RawRecord]:
        records = []
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            items = data if isinstance(data, list) else data.get("invoices", [data])
            for idx, item in enumerate(items):
                record_id = item.get("invoice_id") or item.get("invoice_number") or f"INV-{path.stem}-{idx+1:04d}"
                raw_hash = self._compute_hash(item)
                records.append(RawRecord(
                    record_id=record_id,
                    source_type=SourceType.INVOICE,
                    source_file=path.name,
                    raw_document_ref=doc_ref,
                    raw_data=item,
                    raw_hash=raw_hash
                ))
        return records

    def _parse_text(self, path: Path, doc_ref: str) -> List[RawRecord]:
        # Fallback line-based format (e.g. INVOICE# | DATE | VENDOR | ACTIVITY | QTY | UNIT)
        records = []
        with open(path, 'r', encoding='utf-8') as f:
            for idx, line in enumerate(f):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 6:
                    row_data = {
                        "invoice_id": parts[0],
                        "date": parts[1],
                        "vendor": parts[2],
                        "activity": parts[3],
                        "quantity": parts[4],
                        "unit": parts[5]
                    }
                    raw_hash = self._compute_hash(row_data)
                    records.append(RawRecord(
                        record_id=parts[0],
                        source_type=SourceType.INVOICE,
                        source_file=path.name,
                        raw_document_ref=doc_ref,
                        raw_data=row_data,
                        raw_hash=raw_hash
                    ))
        return records
