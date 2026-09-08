import json
import tempfile
from pathlib import Path
from core.audit_trail import AuditLedger
from core.schema import LedgerBlock

def test_genesis_block_creation():
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger_path = Path(tmpdir) / "test_ledger.jsonl"
        ledger = AuditLedger(ledger_file=ledger_path)

        chain = ledger.get_chain()
        assert len(chain) == 1
        genesis = chain[0]
        assert genesis.index == 0
        assert genesis.record_id == "GENESIS"
        assert genesis.previous_hash == "0" * 64

        is_valid, msg, details = ledger.verify_chain_integrity()
        assert is_valid is True
        assert len(details) == 1

def test_sequential_block_chaining():
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger_path = Path(tmpdir) / "test_ledger.jsonl"
        ledger = AuditLedger(ledger_file=ledger_path)

        # Append block 1
        b1 = ledger.append_block(
            record_id="REC-001",
            agent_name="IngestionAgent",
            action="RECORD_INGESTED",
            payload_summary={"vendor": "Apex Fuels", "gallons": 500}
        )
        assert b1.index == 1
        assert b1.previous_hash == ledger.get_chain()[0].block_hash

        # Append block 2
        b2 = ledger.append_block(
            record_id="REC-001",
            agent_name="CalculationAgent",
            action="EMISSIONS_CALCULATED",
            payload_summary={"kg_co2e": 5105.0}
        )
        assert b2.index == 2
        assert b2.previous_hash == b1.block_hash

        # Verify integrity
        is_valid, msg, details = ledger.verify_chain_integrity()
        assert is_valid is True
        assert len(details) == 3

def test_tamper_detection():
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger_path = Path(tmpdir) / "test_ledger.jsonl"
        ledger = AuditLedger(ledger_file=ledger_path)

        ledger.append_block("REC-001", "Agent1", "ACTION_A", {"value": 100})
        ledger.append_block("REC-002", "Agent2", "ACTION_B", {"value": 200})

        # Tamper with block 1 in the file
        lines = []
        with open(ledger_path, 'r', encoding='utf-8') as f:
            for line in f:
                lines.append(json.loads(line))

        # Tamper payload of block 1 without updating payload_hash or block_hash
        lines[1]["payload_summary"]["value"] = 999999

        with open(ledger_path, 'w', encoding='utf-8') as f:
            for l in lines:
                f.write(json.dumps(l) + '\n')

        # Run verification - MUST detect tampering!
        is_valid, msg, details = ledger.verify_chain_integrity()
        assert is_valid is False
        assert "tampering detected at Block #1" in msg
