import json
import hashlib
import threading
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timezone
from core.config import LEDGER_FILE, GENESIS_PREVIOUS_HASH
from core.schema import LedgerBlock

_ledger_lock = threading.Lock()

class AuditLedger:
    """
    Cryptographic SHA-256 Hash-Chained Audit Ledger.
    Ensures complete tamper resistance and full traceability for all carbon auditing actions.
    """

    def __init__(self, ledger_file: Path = LEDGER_FILE):
        self.ledger_file = Path(ledger_file)
        self.ledger_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.ledger_file.exists():
            self._initialize_genesis()

    def _hash_payload(self, payload: Dict[str, Any]) -> str:
        canonical_json = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()

    def _compute_block_hash(
        self,
        index: int,
        timestamp: str,
        record_id: str,
        agent_name: str,
        action: str,
        payload_hash: str,
        previous_hash: str
    ) -> str:
        header = f"{index}|{timestamp}|{record_id}|{agent_name}|{action}|{payload_hash}|{previous_hash}"
        return hashlib.sha256(header.encode('utf-8')).hexdigest()

    def _initialize_genesis(self):
        """Creates the immutable Genesis block if ledger is empty."""
        with _ledger_lock:
            if self.ledger_file.exists() and self.ledger_file.stat().st_size > 0:
                return

            genesis_timestamp = datetime.now(timezone.utc).isoformat()
            payload = {"system": "EcoChain 24", "message": "Genesis Block - Audit Ledger Initialized"}
            payload_hash = self._hash_payload(payload)
            previous_hash = GENESIS_PREVIOUS_HASH
            block_hash = self._compute_block_hash(
                index=0,
                timestamp=genesis_timestamp,
                record_id="GENESIS",
                agent_name="SystemBoot",
                action="INITIALIZE_LEDGER",
                payload_hash=payload_hash,
                previous_hash=previous_hash
            )

            genesis_block = LedgerBlock(
                index=0,
                timestamp=genesis_timestamp,
                record_id="GENESIS",
                agent_name="SystemBoot",
                action="INITIALIZE_LEDGER",
                payload_summary=payload,
                payload_hash=payload_hash,
                previous_hash=previous_hash,
                block_hash=block_hash
            )

            with open(self.ledger_file, 'w', encoding='utf-8') as f:
                f.write(genesis_block.model_dump_json() + '\n')

    def get_chain(self) -> List[LedgerBlock]:
        """Reads all blocks from the persistent append-only ledger."""
        blocks = []
        if not self.ledger_file.exists():
            return blocks

        with _ledger_lock:
            with open(self.ledger_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        blocks.append(LedgerBlock.model_validate_json(line))
        return blocks

    def get_last_block(self) -> Optional[LedgerBlock]:
        chain = self.get_chain()
        return chain[-1] if chain else None

    def append_block(
        self,
        record_id: str,
        agent_name: str,
        action: str,
        payload_summary: Dict[str, Any]
    ) -> LedgerBlock:
        """
        Appends a new cryptographically chained block to the audit ledger.
        Thread-safe and tamper-evident.
        """
        with _ledger_lock:
            chain = []
            if self.ledger_file.exists():
                with open(self.ledger_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            chain.append(LedgerBlock.model_validate_json(line))

            if not chain:
                self._initialize_genesis()
                chain = self.get_chain()

            last_block = chain[-1]
            new_index = last_block.index + 1
            timestamp = datetime.now(timezone.utc).isoformat()
            payload_hash = self._hash_payload(payload_summary)
            previous_hash = last_block.block_hash

            block_hash = self._compute_block_hash(
                index=new_index,
                timestamp=timestamp,
                record_id=record_id,
                agent_name=agent_name,
                action=action,
                payload_hash=payload_hash,
                previous_hash=previous_hash
            )

            new_block = LedgerBlock(
                index=new_index,
                timestamp=timestamp,
                record_id=record_id,
                agent_name=agent_name,
                action=action,
                payload_summary=payload_summary,
                payload_hash=payload_hash,
                previous_hash=previous_hash,
                block_hash=block_hash
            )

            with open(self.ledger_file, 'a', encoding='utf-8') as f:
                f.write(new_block.model_dump_json() + '\n')

            return new_block

    def verify_chain_integrity(self) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """
        Independently verifies the entire cryptographic chain.
        Returns:
            (is_valid, summary_message, detailed_block_status)
        """
        chain = self.get_chain()
        if not chain:
            return False, "Ledger is empty", []

        details = []

        # Check Genesis
        genesis = chain[0]
        if genesis.previous_hash != GENESIS_PREVIOUS_HASH:
            return False, f"Genesis block corrupted: previous_hash {genesis.previous_hash} does not match expected genesis hash", details

        expected_gen_hash = self._compute_block_hash(
            index=genesis.index,
            timestamp=genesis.timestamp,
            record_id=genesis.record_id,
            agent_name=genesis.agent_name,
            action=genesis.action,
            payload_hash=genesis.payload_hash,
            previous_hash=genesis.previous_hash
        )
        if genesis.block_hash != expected_gen_hash:
            return False, f"Genesis block header hash mismatch at index 0", details

        details.append({
            "index": 0,
            "status": "VALID",
            "block_hash": genesis.block_hash,
            "record_id": genesis.record_id
        })

        for i in range(1, len(chain)):
            current = chain[i]
            prev = chain[i - 1]

            # 1. Verify index sequence
            if current.index != prev.index + 1:
                msg = f"Broken sequence: Block #{current.index} immediately follows #{prev.index}"
                details.append({"index": current.index, "status": "TAMPERED", "error": msg})
                return False, msg, details

            # 2. Verify payload hash
            recomputed_payload_hash = self._hash_payload(current.payload_summary)
            if current.payload_hash != recomputed_payload_hash:
                msg = f"Payload tampering detected at Block #{current.index}. Stored hash {current.payload_hash} does not match actual payload."
                details.append({"index": current.index, "status": "TAMPERED", "error": msg})
                return False, msg, details

            # 3. Verify previous hash chaining
            if current.previous_hash != prev.block_hash:
                msg = f"Chain link broken at Block #{current.index}. Previous hash does not match Block #{prev.index}'s hash."
                details.append({"index": current.index, "status": "TAMPERED", "error": msg})
                return False, msg, details

            # 4. Verify current block hash
            expected_block_hash = self._compute_block_hash(
                index=current.index,
                timestamp=current.timestamp,
                record_id=current.record_id,
                agent_name=current.agent_name,
                action=current.action,
                payload_hash=current.payload_hash,
                previous_hash=current.previous_hash
            )
            if current.block_hash != expected_block_hash:
                msg = f"Header hash corrupted at Block #{current.index}."
                details.append({"index": current.index, "status": "TAMPERED", "error": msg})
                return False, msg, details

            details.append({
                "index": current.index,
                "status": "VALID",
                "block_hash": current.block_hash,
                "record_id": current.record_id
            })

        return True, f"Cryptographic audit chain intact. Verified {len(chain)} blocks successfully.", details

    def get_record_history(self, record_id: str) -> List[LedgerBlock]:
        """Retrieves complete chronological audit history for a single record."""
        return [b for b in self.get_chain() if b.record_id == record_id]

# Singleton ledger instance
audit_ledger = AuditLedger()
