# EcoChain 24 — Architecture Document

## 1. High-Level App Flow

```
[Data Sources]
  Invoices (PDF/CSV) | ERP Exports | Utility Data
        │
        ▼
[Ingestion Agent] ── parses & extracts raw records
        │
        ▼
[Normalization Agent] ── standardizes units, dates, categories
        │
        ▼
[Calculation Agent] ── applies emission factors → Scope 1/2/3 values
        │
        ▼
[Audit Agent] ── checks anomalies, duplicates, confidence score
        │
   ┌────┴─────┐
   │           │
confidence   confidence
  HIGH          LOW / anomaly
   │              │
   │              ▼
   │       [HITL Review Queue] ── human resolves/approves
   │              │
   └──────┬───────┘
          ▼
[Audit Trail Logger] ── hashes + chains every step (tamper-evident ledger)
          │
          ▼
[Reporting Agent] ── generates disclosures, dashboards, exports
          │
          ▼
[Output: Reports / Dashboard / Export Files]
```

**Orchestrator** sits above all agents (hierarchical supervisor pattern): assigns tasks, handles retries/timeouts, and enforces that no record skips the audit-trail step.

## 2. Architecture Pattern

- **Hierarchical multi-agent**: one Orchestrator/Supervisor agent coordinates specialist agents (Ingestion, Normalization, Calculation, Audit, Reporting). Specialist agents do not call each other directly — all communication passes through the Orchestrator to keep the flow traceable and debuggable.
- **Event-driven handoff**: each agent completes a unit of work, writes a result + hash record, and emits an event for the next stage. This keeps agents decoupled and independently retryable.
- **Immutable audit ledger**: every agent action produces a log entry containing `hash(current_data + previous_hash)`, forming a chained, tamper-evident trail (append-only, never overwritten).

## 3. Folder & File Structure

```
ecochain24/
├── agents/
│   ├── orchestrator.py          # supervises task routing & retries
│   ├── ingestion_agent.py       # parses invoices/ERP/utility data
│   ├── normalization_agent.py   # standardizes schema/units
│   ├── calculation_agent.py     # Scope 1/2/3 emission calculations
│   ├── audit_agent.py           # anomaly detection, confidence scoring
│   └── reporting_agent.py       # generates disclosures/exports
│
├── core/
│   ├── schema.py                # shared data models (Pydantic/dataclasses)
│   ├── emission_factors.py      # reference emission factor tables
│   ├── audit_trail.py           # hash-chaining + ledger read/write
│   └── config.py                # environment/config loader
│
├── hitl/
│   ├── review_queue.py          # queue for flagged records
│   └── review_api.py            # endpoints for human reviewers
│
├── ingestion_sources/
│   ├── invoice_parser.py
│   ├── erp_connector.py
│   └── utility_connector.py
│
├── storage/
│   ├── raw/                     # original unmodified source files
│   ├── processed/                # normalized records
│   └── ledger/                  # append-only hash-chained audit log
│
├── reports/
│   └── templates/                # report/dashboard templates
│
├── tests/
│   ├── test_agents/
│   └── test_audit_trail.py
│
├── logs/                         # runtime/error logs (not the audit ledger)
├── .env.example
├── requirements.txt
└── README.md
```

## 4. Tech Stack

| Layer | Suggested Tech |
|---|---|
| Agent orchestration | Python + LangGraph or a simple custom supervisor loop |
| LLM/agent reasoning | Claude API (tool use / structured outputs) |
| Data validation | Pydantic |
| Backend/API | FastAPI |
| Storage (records) | PostgreSQL |
| Audit ledger | Append-only table or lightweight hash-chained log file (SHA-256) |
| File parsing | pdfplumber / openpyxl / pandas |
| HITL UI | React (or simple FastAPI + Jinja templates for v1) |
| Task queue (optional, for scale) | Celery + Redis |
| Reporting/export | pandas + WeasyPrint (PDF) or existing docx/pdf skill tooling |

Keep the stack minimal in v1 — add queueing/scale infrastructure only once volume requires it.

## 5. What to Avoid

- **Don't let agents write directly to the audit ledger from multiple threads/processes without locking** — causes broken hash chains.
- **Don't let specialist agents call each other directly** — bypasses the Orchestrator and breaks traceability.
- **Don't silently auto-correct anomalous data** — always route to HITL instead of guessing.
- **Don't overwrite or delete raw source files** — keep raw data immutable; only processed copies are transformed.
- **Don't hardcode emission factors in code** — keep them in a versioned, referenceable table so calculations stay auditable and updatable.
- **Don't skip confidence scoring** — every calculated record needs a confidence value, even if defaulted, so the Audit Agent can route correctly.
- **Don't mix currencies/units silently** — normalize explicitly and log the conversion applied.
- **Avoid tight coupling between agents and one LLM provider** — abstract the "agent call" layer so models can be swapped.
- **Don't let the pipeline stop entirely on one bad record** — isolate failures per record, not per batch.

## 6. Error Handling Strategy

- **Per-record isolation**: a parsing/calculation failure on one record must not halt the batch — log it, mark it `failed`, continue processing others.
- **Retry with backoff**: transient failures (API timeouts, file I/O) retried up to N times with exponential backoff before escalating.
- **Structured error logging**: every failure logs `agent_name`, `record_id`, `error_type`, `timestamp`, `stack_trace` to `logs/`, separate from the audit ledger.
- **Fail-safe defaults**: if an agent cannot produce a confident result, it must default to "flag for HITL" rather than guessing or dropping the record.
- **Audit trail integrity checks**: before appending a new ledger entry, verify the previous hash matches; if broken, halt writes and alert (indicates tampering or corruption).
- **Schema validation at every boundary**: use Pydantic (or similar) to validate data entering and leaving each agent — reject/flag malformed records early rather than letting bad data propagate.
- **Idempotent processing**: reprocessing the same source file/record should not create duplicate ledger entries — use record hashes/IDs to detect duplicates.
- **Observability**: expose a simple health/status endpoint showing per-agent success/failure counts, queue depth, and last successful run — so failures are visible, not silent.

## 7. Notes for Efficient, Low-Error Operation

- Keep each agent's responsibility narrow and single-purpose — easier to test, retry, and debug in isolation.
- Version the emission factor tables and schema so historical audits remain reproducible even after updates.
- Write unit tests for the audit-trail hash chain first — it's the integrity backbone of the whole system.
- Start with synchronous, sequential processing in v1; only introduce async/parallel agent execution once correctness is proven.
