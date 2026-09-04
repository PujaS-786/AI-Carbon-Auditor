# EcoChain 24 — Autonomous Multi-Agent AI Carbon Auditor

EcoChain 24 is a lightweight, zero-bloat, production-ready multi-agent system designed to audit Scope 1, 2, and 3 carbon emissions according to the GHG Protocol Corporate Standard. It ingests fragmented supplier, utility, and ERP data, normalizes units and categories, applies authoritative emission factors, audits for anomalies/outliers, routes questionable items to a Human-in-the-Loop (HITL) review queue, logs every state transition into a tamper-evident SHA-256 cryptographic audit ledger, and publishes board-ready disclosures.

---

## Key Features

1. **Hierarchical Multi-Agent Architecture**:
   - **Orchestrator**: Supervises sequential task routing, enforces ledger writes, and isolates per-record errors so one bad record does not halt the entire pipeline.
   - **Ingestion Agent**: Ingests multi-format data (Invoices, ERP procurement & travel exports, Utility bills in CSV, JSON, and text).
   - **Normalization Agent**: Standardizes units (`MWh`, `therms`, `BTU`, `gallons`, `liters`, `miles`, `km`, `tonne-km`), formats dates (ISO-8601), and categorizes activities.
   - **Calculation Agent**: Applies versioned emission factors (EPA, DEFRA, GHG Protocol) to calculate kgCO2e and metric tonnes CO2e while assigning confidence scores.
   - **Audit Agent**: Statistical outlier detection, negative number checking, duplicate record detection, and confidence validation.
   - **Reporting Agent**: Compiles board-ready disclosures, Scope 1/2/3 breakdown, supplier emitter rankings, and exports CSV/JSON summaries.

2. **Tamper-Evident SHA-256 Cryptographic Audit Ledger**:
   - Append-only hash-chained ledger (`storage/ledger/audit_ledger.jsonl`).
   - Every block contains `payload_hash`, `previous_hash`, `agent_name`, `action`, and `block_hash`.
   - Independent verification engine validates the entire chain from Genesis block to head, instantly detecting any payload or chain tampering.

3. **Human-in-the-Loop (HITL) Review Queue**:
   - Outliers and low-confidence records are automatically routed to a dedicated review queue.
   - Auditors can approve as-is, adjust activity quantities, reassign emission factors, or reject entries.
   - Every resolution generates a certified cryptographic ledger entry with the auditor's name and rationale.

4. **Modern Glassmorphic Web Dashboard & CLI**:
   - Clean, dark-mode responsive dashboard with zero build-tool requirements (vanilla CSS + JS).
   - Real-time stat cards, searchable audited records table, interactive HITL queue, and live ledger block explorer with one-click cryptographic integrity verification.
   - Dual-mode operation: Web UI (`python app.py`) or Headless CLI (`python app.py --cli --file <path>`).

---

## Architecture Flow

```
[Invoices | ERP | Utilities]
             │
             ▼
      [Ingestion Agent] ───────► (Logs INGEST to Cryptographic Ledger)
             │
             ▼
    [Normalization Agent] ─────► (Logs NORMALIZE to Cryptographic Ledger)
             │
             ▼
    [Calculation Agent] ───────► (Logs CALCULATE to Cryptographic Ledger)
             │
             ▼
       [Audit Agent]
        ┌────┴─────┐
   confidence    anomaly /
     >= 0.85     low confidence
        │              │
        │              ▼
        │       [HITL Review Queue]
        │              │ (Auditor approves/adjusts)
        └──────┬───────┘
               ▼
     [Cryptographic Ledger] ───► Append-only SHA-256 Block Chained
               │
               ▼
       [Reporting Agent] ──────► Board-Ready Disclosures & Exportable CSV/JSON
```

---

## Directory Structure

```
AI Carbon Auditor/
├── agents/
│   ├── orchestrator.py        # Supervisor agent routing & error isolation
│   ├── ingestion_agent.py     # Dispatches parsers & raw file preservation
│   ├── normalization_agent.py # Unit conversions & date standardizations
│   ├── calculation_agent.py   # Emission factor application & confidence scoring
│   ├── audit_agent.py         # Outlier, duplicate, & anomaly detection
│   └── reporting_agent.py     # Aggregation & disclosure generation
├── core/
│   ├── config.py              # Configuration constants & file paths
│   ├── schema.py              # Pydantic data models
│   ├── emission_factors.py    # Versioned EPA/DEFRA Scope 1, 2, 3 factors
│   └── audit_trail.py         # Cryptographic SHA-256 hash-chained ledger
├── hitl/
│   └── review_queue.py        # Flagged record management & auditor overrides
├── ingestion_sources/
│   ├── invoice_parser.py      # Invoices (CSV, JSON, text)
│   ├── erp_connector.py       # ERP travel & procurement exports
│   └── utility_connector.py   # Electricity & natural gas feeds
├── sample_data/
│   ├── sample_invoices.csv    # Sample supplier invoices
│   ├── sample_erp.csv         # Sample ERP business travel & hardware
│   └── sample_utility.json    # Sample utility grid & renewable bills
├── storage/
│   ├── raw/                   # Immutable raw source files
│   ├── processed/             # HITL queue state
│   ├── ledger/                # Append-only audit ledger (audit_ledger.jsonl)
│   └── reports/               # Latest disclosure reports (CSV & JSON)
├── web/
│   ├── templates/index.html   # Web dashboard UI
│   └── static/
│       ├── app.css            # Dark mode glassmorphic stylesheet
│       └── app.js             # Client-side reactivity & API communication
├── tests/
│   ├── test_audit_trail.py    # Ledger hashing, chaining & tamper tests
│   └── test_agents.py         # Agent unit & pipeline tests
├── app.py                     # Unified Flask web app & CLI runner
├── requirements.txt           # Minimal dependencies
└── README.md
```

---

## Getting Started

### 1. Requirements
- Python 3.10+ (tested on Python 3.14)
- Minimal dependencies (Flask, Pydantic, Pytest)

```bash
pip install -r requirements.txt
```

### 2. Launch the Web Dashboard
```bash
python app.py
```
Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser:
- Click **"Ingest Sample Data"** to automatically ingest Invoices, ERP, and Utilities in one click.
- Explore the **Audited Records** and **Board Disclosures**.
- Review flagged records in the **HITL Review Queue** and approve or adjust them.
- Click **"Verify Hash Chain"** in the **Cryptographic Audit Trail** tab to see real-time SHA-256 integrity validation.

### 3. Run via Command Line (CLI Mode)
Audit any file directly from your terminal:
```bash
python app.py --cli --file sample_data/sample_invoices.csv
```

### 4. Run Automated Tests
```bash
python -m pytest tests/ -v
```
All 7 unit and integration tests (including tamper detection) will run and verify chain integrity.
