# EcoChain 24 — Input / Output Specification

This document defines **what goes into the system, what comes out of it, where each lives on disk, and how the system stays resilient and improves itself over time.** Pair this with the PRD (scope) and README (architecture) — this file is the contract between "raw data in" and "board-ready disclosure out."

---

## 1. Design Principle: Two Dedicated Zones

The system is built around **one intake zone** and **one delivery zone**. Nothing is processed in place, and nothing is reported from a scratch folder. This keeps the pipeline predictable, auditable, and easy to automate (cron job, watched folder, or manual drag-and-drop all work the same way).

```
storage/
├── raw/            ◄── INPUT ZONE  (drop files here — untouched, immutable)
├── processed/       (internal working state — HITL queue snapshots, normalized cache)
├── ledger/          (internal — cryptographic audit trail, not user-facing input/output)
└── reports/         ◄── OUTPUT ZONE (disclosure-ready exports land here)
```

- **`storage/raw/`** is the only place users (or an upstream automation) ever *write* input into. Nothing here is ever edited or deleted by the pipeline — it's the immutable evidence trail an auditor can always point back to.
- **`storage/reports/`** is the only place the system ever *writes* final output for a human to consume. Everything else in `storage/` is internal machinery.
- The **web dashboard** and **CLI** are just two doors into the same two zones — see §5.

---

## 2. INPUT — What Goes In

### 2.1 Accepted source types (v1)

| Source | Format | Example | Where it lands |
|---|---|---|---|
| Supplier invoices | CSV, JSON, plain text | `sample_invoices.csv` | `storage/raw/invoices/` |
| ERP exports (travel, procurement, hardware) | CSV | `sample_erp.csv` | `storage/raw/erp/` |
| Utility bills (electricity, gas) | JSON | `sample_utility.json` | `storage/raw/utility/` |

> PDF invoices are parsed via the invoice parser but must still resolve to structured fields below before they enter the pipeline — OCR/extraction failures are treated as ingestion errors (see §6).

### 2.2 Minimum required fields per input record

Regardless of source format, every record must normalize to (or be rejected/flagged for missing) these fields before it can reach the Calculation Agent:

| Field | Type | Example | Notes |
|---|---|---|---|
| `record_id` | string | `INV-2026-0341` | Unique per source system; used for duplicate detection |
| `source_type` | enum | `invoice` / `erp` / `utility` | Set by ingestion agent |
| `supplier_id` | string | `SUP-0092` | Required for Scope 3 attribution |
| `activity_date` | date | `2026-03-14` | Normalized to ISO-8601 |
| `activity_type` | string | `natural_gas_therms`, `air_travel_km`, `grid_electricity_kwh` | Maps to an emission factor category |
| `quantity` | number | `1250.5` | Raw, pre-conversion |
| `unit` | string | `therms`, `kWh`, `gallons`, `km` | Normalized to canonical units |
| `currency` / `cost` | string/number | `USD`, `4820.00` | Optional but improves cross-checking |
| `raw_document_ref` | string (path) | `storage/raw/invoices/INV-2026-0341.csv` | **Never dropped** — this is the audit-trail anchor |

### 2.3 Example input (utility JSON)

```json
{
  "record_id": "UTIL-2026-0088",
  "supplier_id": "SUP-0451",
  "billing_period_start": "2026-02-01",
  "billing_period_end": "2026-02-28",
  "activity_type": "grid_electricity",
  "quantity": 48250,
  "unit": "kWh",
  "region_grid": "US-CAISO",
  "renewable_pct": 12.5
}
```

### 2.4 Example input (invoice CSV row)

```
record_id,supplier_id,invoice_date,description,quantity,unit,cost,currency
INV-2026-0341,SUP-0092,2026-03-14,"Diesel fuel delivery",1250.5,gallons,4820.00,USD
```

### 2.5 How input is submitted

| Mode | Mechanism |
|---|---|
| **Web dashboard** | "Ingest Sample Data" button, or a file-upload control that copies the file into `storage/raw/<type>/` and triggers the Orchestrator |
| **CLI** | `python app.py --cli --file <path>` — the file is copied into `storage/raw/` before processing begins (never processed from its original location) |
| **Automated / future** | A watched-folder or API endpoint that drops files into `storage/raw/` and calls the same Orchestrator entrypoint |

---

## 3. OUTPUT — What Comes Out

### 3.1 Output artifacts

| Artifact | Format | Location | Consumer |
|---|---|---|---|
| Consolidated disclosure report | PDF / CSV / JSON | `storage/reports/disclosure_<date>.{pdf,csv,json}` | ESG managers, board |
| Per-record audit result | JSON (in-app table) | Dashboard "Audited Records" tab | Analysts, auditors |
| HITL queue item | JSON | `storage/processed/hitl_queue.json` | Analysts (action required) |
| Cryptographic ledger | Append-only JSONL | `storage/ledger/audit_ledger.jsonl` | Auditors (integrity verification) |
| Chain verification result | JSON / on-screen badge | Dashboard "Verify Hash Chain" | Auditors |

### 3.2 Example output — audited emissions record

```json
{
  "record_id": "INV-2026-0341",
  "scope": "Scope 1",
  "activity_type": "diesel_combustion",
  "kgco2e": 12734.6,
  "tonnes_co2e": 12.73,
  "emission_factor_source": "EPA_2025_v3",
  "confidence_score": 0.93,
  "status": "audited",
  "raw_document_ref": "storage/raw/invoices/INV-2026-0341.csv",
  "ledger_block_hash": "8f3a1c...e02b",
  "processed_at": "2026-03-15T09:12:04Z"
}
```

### 3.3 Example output — HITL flagged record

```json
{
  "record_id": "UTIL-2026-0088",
  "reason_flagged": "confidence_below_threshold",
  "confidence_score": 0.61,
  "candidate_kgco2e": 24870.2,
  "anomaly_notes": "Quantity is 3.2x the supplier's 6-month average",
  "status": "pending_review",
  "assigned_to": null
}
```

### 3.4 Example output — ledger block

```json
{
  "block_index": 4821,
  "agent_name": "calculation_agent",
  "action": "CALCULATE",
  "payload_hash": "b6d1...",
  "previous_hash": "7ac9...",
  "block_hash": "8f3a1c...e02b",
  "timestamp": "2026-03-15T09:12:04Z"
}
```

### 3.5 Example output — board disclosure summary (top level)

```json
{
  "reporting_period": "2026-Q1",
  "total_tco2e": 18420.7,
  "by_scope": { "scope1": 6210.4, "scope2": 5100.1, "scope3": 7110.2 },
  "top_emitting_suppliers": [
    { "supplier_id": "SUP-0092", "tco2e": 1204.5 },
    { "supplier_id": "SUP-0451", "tco2e": 987.3 }
  ],
  "records_flagged_hitl": 14,
  "audit_chain_status": "VERIFIED"
}
```

### 3.6 How output is delivered

| Mode | Mechanism |
|---|---|
| **Web dashboard** | Live stat cards, searchable records table, HITL queue UI, ledger explorer — all read-only views over `storage/processed/` and `storage/ledger/` |
| **Export** | "Export" action writes PDF/CSV/JSON into `storage/reports/`, downloadable directly from the dashboard |
| **CLI** | Prints a summary to stdout and writes the same report files into `storage/reports/` |

---

## 4. End-to-End Data Flow (Input → Output)

```
storage/raw/*  (INPUT ZONE)
      │
      ▼
Ingestion Agent → Normalization Agent → Calculation Agent
      │                                        │
      ▼                                        ▼
 Ledger write                          confidence >= 0.85? ──No──► HITL Queue ──► Auditor resolves ──► Ledger write
      │                                        │Yes
      ▼                                        ▼
                              Audit Agent (outlier/duplicate check)
                                        │
                                        ▼
                              Reporting Agent
                                        │
                                        ▼
                        storage/reports/*  (OUTPUT ZONE)
```

Every arrow in this diagram also writes a block to `storage/ledger/audit_ledger.jsonl` — so any output can be traced back through every transformation to the original file in `storage/raw/`.

---

## 5. Making It "Effortless" for the User

- **One button, one command.** Dashboard: click "Ingest Sample Data" or drag a file in. CLI: one `--file` flag. No manual pre-processing, no schema mapping required for the three supported source types.
- **Format tolerance, not format rigidity.** The Normalization Agent — not the user — is responsible for reconciling units (`MWh` vs `kWh`), date formats, and category naming. Users should never need to pre-clean a file to match an internal schema.
- **Everything traceable without extra clicks.** Every row in the "Audited Records" table links back to its `raw_document_ref` and its ledger block automatically — the user never has to go dig for provenance.
- **Sensible defaults, explicit overrides.** HITL only interrupts the user when confidence is genuinely low (`< 0.85`) or an anomaly is detected — everything else flows straight through to the report.

---

## 6. Error Handling — Fail Small, Never Fail Silent

| Failure type | Behavior |
|---|---|
| Malformed/unparseable row | Record is skipped, logged with `status: "ingestion_error"`, original file is untouched in `storage/raw/`; pipeline continues with remaining records |
| Missing required field | Record is routed to HITL with `reason_flagged: "incomplete_data"` rather than guessed at |
| Duplicate `record_id` | Audit Agent flags it; second occurrence is held for HITL, never silently overwritten |
| Emission factor lookup fails (unknown activity type) | Record held with `status: "unmapped_activity"`; does **not** get a fabricated factor |
| Agent crash mid-record | Orchestrator isolates the failure to that record; ledger records the failure as its own block; the rest of the batch keeps processing (per Success Criteria in the PRD: *"a failure in one agent does not corrupt the audit trail or crash the pipeline"*) |
| Ledger write failure | Treated as fatal for that record only — the record is re-queued rather than allowed to report without a ledger entry, since an unlogged number is, by definition, not auditable |

**Principle:** the system degrades to *"fewer records processed, all of them still correct and traceable"* — never to *"all records processed, some of them silently wrong."*

---

## 7. Learning From Mistakes — The Feedback Loop

The system doesn't retrain a model, but it **does** get measurably better at flagging correctly over time:

1. **Every HITL resolution is captured**, not just applied: `{ original_confidence, auditor_decision (approve/adjust/reject), corrected_value, rationale }`.
2. This resolution history is stored (e.g. `storage/processed/hitl_resolutions.jsonl`) and is queryable by supplier, activity type, and emission factor version.
3. **Confidence scoring is recalibrated periodically** using this history: activity types or suppliers that are *frequently corrected* get their baseline confidence threshold tightened (harder to auto-pass); activity types that are *consistently approved as-is* can be trusted with a slightly lower review threshold, reducing analyst workload over time.
4. **Recurring anomaly patterns become new audit rules.** If the same anomaly type (e.g. "utility quantity > 3x rolling average") keeps getting resolved the same way, it's promoted from a one-off flag to a standing check in the Audit Agent.
5. **None of this touches the ledger's immutability.** Recalibration changes *future* thresholds and rules — it never rewrites past ledger blocks or past disclosures. The improvement loop lives entirely in `storage/processed/`, kept separate from the tamper-evident chain.

---

## 8. Quick Reference

| Question | Answer |
|---|---|
| Where do I put a new file? | `storage/raw/<invoices\|erp\|utility>/`, or upload via the dashboard |
| What's the minimum a file needs? | `record_id`, `supplier_id`, `activity_date`, `activity_type`, `quantity`, `unit` |
| Where do I find results? | Dashboard tabs, or `storage/reports/` for exported files |
| What if something's flagged? | Dashboard → HITL Review Queue → approve / adjust / reject with a rationale |
| How do I know the numbers weren't tampered with? | Dashboard → "Verify Hash Chain," or independently replay `storage/ledger/audit_ledger.jsonl` |
| Does the system get smarter? | Yes — via `storage/processed/hitl_resolutions.jsonl` driving periodic threshold/rule recalibration (§7), not model retraining |
