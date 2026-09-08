# EcoChain 24 — Autonomous AI Carbon Auditor
## Comprehensive System Reference, User Manual & Technical Specification

---

## 1. Executive Summary: What is EcoChain 24?

**EcoChain 24** is an enterprise-grade, multi-agent AI system designed for autonomous corporate Greenhouse Gas (GHG) accounting, real-time ESG compliance auditing, and cryptographic provenance verification. 

It autonomously ingests messy, heterogeneous corporate activity records (fuel invoices, ERP travel and procurement reports, utility electricity meter feeds), normalizes disparate units of measurement, maps activities to official GHG Protocol emission factors, audits data for anomalies and fraud, and commits every audited transaction to an immutable SHA-256 cryptographic hash chain.

---

## 2. What Problem Does It Solve?

### The Traditional Problem (Manual ESG Accounting)
1. **The "Greenwashing" & Audit Risk Crisis**:
   - Modern sustainability reporting under regulations like **EU CSRD** (Corporate Sustainability Reporting Directive), **SEC Climate Disclosure Rules**, and **California SB 253/261** requires auditable financial-grade proof of carbon emissions.
   - Traditional carbon accounting relies on disconnected spreadsheets, manual copy-pasting, and unverified estimates, leading to widespread miscalculation, regulatory fines, and public reputational damage.
2. **Unit Mismatch & Human Error**:
   - Invoices arrive in arbitrary international units (e.g., US liquid gallons vs. imperial gallons vs. liters; therms vs. cubic meters; miles vs. kilometers; short tons vs. metric tonnes). A single conversion error can distort corporate carbon disclosures by orders of magnitude.
3. **Lack of Audit Provenance (Chain of Custody)**:
   - When an auditor asks, *"Where did this Scope 1 emission figure originate?"*, traditional systems cannot trace back to the exact source invoice file without days of manual forensic searching.
4. **Data Anomalies & Fraud Go Undetected**:
   - Duplicate billing, sudden volume spikes (e.g., a fuel vendor billing 990,000 gallons instead of 990), negative consumption values, or unregistered vendors frequently slip into disclosures unnoticed.
5. **No Structured Feedback Loop**:
   - When human auditors adjust or reject numbers, those manual corrections are lost in emails and never fed back into the calculation engine to improve future confidence ratings.

### The EcoChain 24 Solution
- **Autonomous Multi-Agent Architecture**: 5 specialized agents (Ingestion, Normalization, Calculation, Audit, and Supervisor Orchestrator) work in a deterministic pipeline.
- **Two-Zone Immutable Storage**: Ingested files land immutably in typed directories (`storage/raw/invoices/`, `storage/raw/erp/`, `storage/raw/utility/`) and are never overwritten or deleted.
- **Cryptographic Audit Ledger**: Every action, calculation, and human override creates a linked SHA-256 block pointing to the prior block's hash. Any modification invalidates the chain.
- **Human-In-The-Loop (HITL) Queue**: Anomalous transactions are quarantined with full reason codes, offering single-click or batch resolutions ("Accept All" / "Reject All" / "Adjust & Override").
- **Dynamic AI Feedback Loop**: Human resolutions are logged to `storage/processed/hitl_resolutions.jsonl` and dynamically recalibrate the AI confidence scoring engine.

---

## 3. Scientific Units of Measurement: Why & How They Are Used

Every numerical value in EcoChain 24 adheres to international GHG Protocol standards. The table below details why each unit was chosen:

| Metric / Parameter | Unit Used | Why This Unit Was Chosen | Conversion / Standard |
| :--- | :--- | :--- | :--- |
| **Fleet Liquid Fuel** | `liters` (L) | DEFRA and EPA emission factors for mobile combustion (diesel, petrol) are scientifically calibrated in kilograms of CO2e per liter. | $1\text{ US Gallon} = 3.78541\text{ Liters}$ |
| **Grid Electricity** | `kWh` | Standard metric kilowatt-hour used across international electricity grid balancing authorities and smart meter tariffs. | $1\text{ MWh} = 1,000\text{ kWh}$ |
| **Natural Gas Heating** | `kWh` (converted from therms / $m^3$) | Natural gas is billed in volume ($m^3$) or thermal heat units ($\text{therms}$). Converting to equivalent energy ($\text{kWh}$) provides cross-utility parity. | $1\text{ therm} \approx 29.3001\text{ kWh}$ |
| **Air / Rail Travel** | `passenger_km` | ICAO (International Civil Aviation Organization) calculates passenger footprint based on distance traveled per passenger. | $1\text{ mile} = 1.60934\text{ km}$ |
| **Road Truck Freight** | `tonne_km` | Global GLEC (Global Logistics Emissions Council) framework standard: transporting 1 metric tonne of freight across 1 kilometer. | $\text{tonnes} \times \text{distance (km)}$ |
| **Intermediate Emissions** | $\text{kg CO}_2\text{e}$ | Kilograms of Carbon Dioxide Equivalent. Retains 4 decimal places during internal calculations to prevent compounding truncation errors. | Direct multiplication of activity $\times$ emission factor |
| **Executive Reporting** | $\text{tCO}_2\text{e}$ (Metric Tonnes) | Official global corporate reporting unit mandated by GHG Protocol, ISO 14064, and SEC. Prevents unreadable multi-million kg figures. | $1\text{ tCO}_2\text{e} = 1,000\text{ kg CO}_2\text{e}$ |
| **Data Confidence** | Percentage ($0\% - 100\%$) | Probabilistic score computed from schema completeness, unit certainty, vendor registry status, and outlier distance. | Score between $0.0$ and $1.0$, rendered as $\%$ |

---

## 4. UI Layout & Every Single Button Explained

The EcoChain 24 Web Dashboard operates on `http://127.0.0.1:5000`.

### 4.1 Header & Metric Hero Cards (Always Visible at Top)

At the very top of the dashboard, six KPI summary cards display real-time corporate footprint aggregates:

1. **Total Carbon Footprint Card**:
   - **Value**: Total emissions in metric tonnes ($\text{tCO}_2\text{e}$).
   - **Footnote**: Sum of Scope 1, Scope 2, and Scope 3 emissions.
2. **Scope 1 (Direct Emissions) Card**:
   - **Value**: Emissions from direct company combustion (fleet diesel, stationary natural gas heating).
3. **Scope 2 (Purchased Electricity) Card**:
   - **Value**: Emissions from utility electricity grids and district cooling/heating.
4. **Scope 3 (Value Chain & Travel) Card**:
   - **Value**: Emissions from employee flights, rail travel, enterprise IT hardware, and third-party logistics.
5. **Cryptographic Ledger Card**:
   - **Value**: Count of verified, immutable SHA-256 blocks currently chained in the ledger.
   - **Footnote**: Status tag reading `Chain Valid` (green) or `Tampered` (red).
6. **Audit Confidence Card**:
   - **Value**: Average percentage confidence (e.g. `95%` or `100%`).
   - **Footnote**: Regulatory readiness badge (`Grade A Readiness`, `Grade B`, or `Audit Review Advised`).

---

### 4.2 Top Action Banner Buttons

Located immediately below the metric cards:

1. **`Ingest Sample Data (Invoices + ERP + Utility)` Button (`#btn-ingest-sample`)**:
   - **Action**: Triggers autonomous ingestion of all standard sample files (`sample_invoices.csv`, `sample_erp.csv`, `sample_utility.json`) through the multi-agent pipeline.
   - **Feedback**: Displays a live spinner ("Ingesting Multi-Source Data..."), pops a success toast notification, updates all dashboard cards, and switches automatically to the "Audited Records" table.
2. **`Upload Source File (CSV/JSON)` Button / Label (`#file-upload-input`)**:
   - **Action**: Opens the native OS file picker to allow uploading any custom `.csv` or `.json` file from your device.
   - **Behavior**: Directs the file into its canonical landing zone in `storage/raw/<type>/`, runs normalization, calculation, and auditing, and binds the transaction to the ledger.
3. **`Export Disclosures CSV` Button**:
   - **Action**: Initiates an immediate browser file download of the official audited carbon disclosure ledger as `ecochain_carbon_disclosure.csv`.

---

### 4.3 Tab Navigation Bar

Switches between the 5 primary functional modules of the auditor:

1. **`Data Intake Zone` Button (`data-tab="tab-intake"`)**: Navigates to the intake, drag-and-drop, manual input, and test dataset library tab.
2. **`Audited Records` Button (`data-tab="tab-records"`)**: Navigates to the normalized and verified transaction data grid.
3. **`HITL Review Queue` Button (`data-tab="tab-hitl"`)**: Navigates to the Human-In-The-Loop review station. Displays a dynamic badge count of pending flagged items.
4. **`Cryptographic Audit Trail` Button (`data-tab="tab-ledger"`)**: Navigates to the SHA-256 blockchain ledger inspection view.
5. **`Board Disclosures` Button (`data-tab="tab-disclosure"`)**: Navigates to the executive board greenhouse gas disclosure summary.

---

## 5. Detailed Tab Breakdown

### Tab 1: Data Intake Zone (`#tab-intake`)

Provides multiple channels for feeding data into the autonomous auditor.

#### Column 1: Dropzone & Ingestion Channel
- **Target Ingestion Category Select Dropdown (`#intake-source-hint`)**:
  - `Auto-Detect by filename & headers`: The system automatically inspects headers (e.g. presence of `kwh`, `flight`, `invoice`).
  - `Supplier Invoices (storage/raw/invoices/)`: Forces landing into the invoice raw directory.
  - `ERP Travel & Procurement (storage/raw/erp/)`: Forces landing into the ERP raw directory.
  - `Utility Smart Meter (storage/raw/utility/)`: Forces landing into the utility raw directory.
- **Drag & Drop Zone (`#intake-dropzone`)**:
  - Dragging files over turns the border emerald. Dropping files triggers immediate processing.
- **`Browse Files` Button**:
  - Triggers the file selection dialog for the dropzone.

#### Column 2: Manual Single Transaction Entry Form (`#form-manual-entry`)
Allows ad-hoc entry of individual transactions:
- **`Supplier / Facility` Input (`#manual-vendor`)**: Name of the vendor, airline, utility, or facility (e.g., `Apex Fuel Logistics`).
- **`Activity Date` Input (`#manual-date`)**: Date picker (`YYYY-MM-DD`).
- **`Activity Type` Dropdown (`#manual-activity`)**: Selects the activity:
  - Diesel Fleet Fuel (`diesel_fuel_liters`)
  - Purchased Grid Electricity (`electricity_grid_kwh`)
  - Certified Solar / Green Power (`electricity_grid_green_kwh`)
  - Natural Gas Heating (`natural_gas_therm`)
  - Commercial Flight (`air_travel_passenger_km`)
  - Rail Travel (`rail_travel_passenger_km`)
  - Road Truck Freight (`freight_truck_tonne_km`)
  - Enterprise IT Laptops (`it_hardware_unit`)
  - Landfill Waste (`waste_landfill_kg`)
- **`Quantity` Input (`#manual-qty`)**: Numerical activity volume (e.g. `1500`).
- **`Unit` Input (`#manual-unit`)**: Unit string (e.g. `gallons`, `kWh`, `miles`, `liters`).
- **`Audit & Chain Transaction` Button (`#btn-submit-manual`)**: Submits the form, passes through normalization, calculation, audit verification, and ledger logging.

#### Row 2: Pre-Loaded Test Datasets Library
Four pre-configured scenario runners for instant demonstration:
- **`Run Scope 1 Test` Button**: Ingests `test_scope1_fuels.csv` (fleet diesel, stationary natural gas, gasoline, propane).
- **`Run Scope 2 Test` Button**: Ingests `test_scope2_utilities.json` (electricity meters, solar green tariff feeds).
- **`Run Scope 3 Test` Button**: Ingests `test_scope3_supplychain.csv` (flights, rail freight, IT hardware procurement).
- **`Run Anomaly Test` Button**: Ingests `test_anomalies_and_duplicates.csv` (contains a 990,000-gallon volume spike, duplicate invoice IDs, negative quantity, and unregistered vendors to intentionally populate the HITL Queue).

#### Row 3: Raw CSV / JSON Snippet Paste
- **Textarea (`#raw-snippet-text`)**: Paste raw rows directly from spreadsheets or JSON arrays.
- **Format Dropdown (`#raw-snippet-hint`)**: Choose `Invoice Format`, `ERP Format`, or `Utility Format`.
- **`Ingest Raw Snippet` Button (`#btn-submit-snippet`)**: Saves the text snippet into an immutable file in `storage/raw/<type>/` and processes it.

---

### Tab 2: Audited Records (`#tab-records`)

Displays the full grid of normalized and verified corporate activity records.

#### Interactive Controls:
- **Scope Filter Dropdown (`#filter-scope`)**: Filter table rows by `All Scopes`, `Scope 1`, `Scope 2`, or `Scope 3`.
- **Search Records Input (`#search-records`)**: Real-time substring filter across Supplier names, Record IDs, and Activity Types.

#### Audited Records Table Columns Explained:

| Column # | Header Name | Meaning & Contents | Example |
| :---: | :--- | :--- | :--- |
| **1** | **Record ID** | Unique canonical identifier assigned upon ingestion. | `REC-A1B2C3D4` |
| **2** | **Date** | Date the activity or invoice occurred (`YYYY-MM-DD`). | `2026-03-10` |
| **3** | **Supplier / Facility** | Name of the third-party vendor, airline, or internal facility. | `Titan Fuel Logistics` |
| **4** | **Activity Type** | Standardized activity classification mapped by the Normalization Agent. | `diesel_fuel_liters` |
| **5** | **Scope** | Greenhouse Gas Protocol classification (`Scope 1`, `Scope 2`, `Scope 3`). | `Scope 1` (Pill) |
| **6** | **Activity Quantity** | Normalized numerical quantity with standardized unit. | `3,785.41 liters` |
| **7** | **Emissions ($\text{tCO}_2\text{e}$)** | Calculated emissions in metric tonnes of $\text{CO}_2$ equivalent ($4$ decimals). | `10.1449` |
| **8** | **Confidence** | Data reliability rating derived from data completeness, vendor reputation, and outlier analysis. | `95%` |
| **9** | **Audit Status** | Operational state badge: `APPROVED`, `FLAGGED_HITL`, `RESOLVED`, or `REJECTED`. | Green/Amber/Purple badge |
| **10** | **Audit Provenance** | Immutable file reference path + SHA-256 block hash badge. Proves origin and block proof. | `storage/raw/invoices/...`<br>`#e3b0c442...` |

---

### Tab 3: HITL Review Queue (`#tab-hitl`)

Quarantines records flagged by the Audit Agent for human review before inclusion in regulatory disclosures.

#### Batch Action Buttons (Top Right of Queue Header):
- **`Accept All Pending` Button (`#btn-hitl-accept-all`)**:
  - Displays count: e.g. `Accept All (3)`.
  - Prompts for confirmation: *"Are you sure you want to ACCEPT all 3 pending flagged records?"*
  - Automatically approves all pending records as-is, updates their confidence to $1.0$ (certified by auditor), writes individual blocks to the cryptographic ledger, appends to `storage/processed/hitl_resolutions.jsonl`, and updates board disclosures.
  - Gracefully disables with a tooltip when zero items are pending.
- **`Reject All Pending` Button (`#btn-hitl-reject-all`)**:
  - Displays count: e.g. `Reject All (3)`.
  - Prompts for confirmation: *"Are you sure you want to REJECT all 3 pending flagged records?"*
  - Marks all pending records as `REJECTED`, excludes them from board disclosures, appends rejection blocks to the ledger, and logs feedback history.

#### Individual Flagged Record Card Details:
Each flagged item renders with an amber highlight card showing:
- **Header**: Record ID, Supplier Name, Timestamp of flagging.
- **Emission Figure**: Calculated $\text{tCO}_2\text{e}$, Scope, and Category.
- **Flag Reasons Box**: Specific audit check failures in red bullets (e.g., *"Statistical anomaly: 990000.0 exceeds category mean by 5.2 standard deviations"*, *"Duplicate invoice detected"*, *"Vendor not found in approved registry"*).
- **Card Action Buttons**:
  1. **`Adjust & Override` Button**: Opens the Auditor Override Modal to modify the activity quantity or swap the emission factor key.
  2. **`Reject Record` Button**: Rejects the individual transaction, removing it from disclosure totals.
  3. **`Approve As-Is` Button**: Certifies the individual transaction despite warnings (e.g. if the auditor confirms a massive legitimate bulk purchase).

#### Auditor Override Modal (`#override-modal`):
- **`Adjusted Activity Quantity` Input**: Allows auditor to correct typos (e.g., changing $990,000$ to $990$).
- **`Select New Emission Factor` Dropdown**: Allows reclassifying the activity to another factor.
- **`Auditor Rationale & Notes` Textarea**: Mandatory note explaining the regulatory justification for the override.
- **`Save & Override` Button**: Saves adjustments, recalculates $\text{tCO}_2\text{e}$, sets confidence to $100\%$, and logs an `HUMAN_RESOLVE_OVERRIDE` block to the cryptographic chain.

---

### Tab 4: Cryptographic Audit Trail (`#tab-ledger`)

Provides real-time mathematical proof that the audit ledger has not been tampered with.

#### Header Buttons:
- **`Verify Hash Chain` / `Check Chain Integrity` Button (`#btn-verify-chain`)**:
  - Recalculates the SHA-256 hash of every single block sequentially from Genesis block `#0` to the tip.
  - Verifies that $\text{Block}[i].\text{previous\_hash} == \text{Block}[i-1].\text{block\_hash}$.
  - Displays a toast: *"Cryptographic audit chain intact. Verified N blocks successfully."*
- **`View JSON Ledger` Button (`#btn-view-json`)**:
  - Opens a dark-mode modal containing the raw JSON structure of the entire cryptographic ledger for external auditor export.

#### Ledger Table Columns Explained:

| Column # | Header Name | Meaning & Contents | Example |
| :---: | :--- | :--- | :--- |
| **1** | **Block Index** | Monotonically increasing block index starting at Genesis `#0`. | `#162` |
| **2** | **Timestamp** | Coordinated Universal Time (UTC) timestamp formatted `HH:MM:SS`. | `20:24:39` |
| **3** | **Record ID** | ID of the transaction or `SYSTEM` for genesis. | `REC-5D88A72B` |
| **4** | **Agent / Actor** | Specific agent or auditor that wrote the block. | `CalculationAgent`<br>`HITL_Reviewer(...)` |
| **5** | **Action** | Cryptographic event type (`GENESIS_INIT`, `CALCULATION_COMPLETE`, `HUMAN_RESOLVE_OVERRIDE`, etc.). | `CALCULATION_COMPLETE` |
| **6** | **Previous Hash** | SHA-256 hash of the preceding block (first 10 chars shown, hover for full 64-char string). | `7f8a9e1d4b...` |
| **7** | **Block Hash** | Cryptographic SHA-256 hash of this block's data payload combined with the previous hash. | `4c2b98a0f1...` (Green badge) |

---

### Tab 5: Board Disclosures (`#tab-disclosure`)

Generates executive-ready corporate carbon disclosures compliant with SEC and CSRD frameworks.

#### Header Buttons:
- **`Download Official JSON` Button**: Downloads `ecochain_carbon_disclosure.json`.
- **`Download Official CSV` Button**: Downloads `ecochain_carbon_disclosure.csv`.

#### Tables & Views:
1. **Emissions by Activity Category Table**:
   - **Category Column**: Activity classification (e.g., `Mobile Combustion`, `Purchased Electricity`, `Business Travel`, `Stationary Combustion`, `Capital Goods`).
   - **Tonnes $\text{CO}_2\text{e}$ Column**: Total aggregated emissions in metric tonnes.
2. **Top Emitting Suppliers / Facilities Table**:
   - **Supplier / Facility Name Column**: Top 5 highest carbon contributors ranked descending.
   - **Tonnes $\text{CO}_2\text{e}$ Column**: Metric tonnes contributed by that specific supplier.

---

## 6. Mathematical Formulas & Emission Factors Reference

### 6.1 Fundamental Carbon Formula
$$\text{Emissions (kg CO}_2\text{e)} = \text{Normalized Activity Quantity} \times \text{Emission Factor Value}$$

$$\text{Reported Emissions (tCO}_2\text{e)} = \frac{\text{Emissions (kg CO}_2\text{e)}}{1000}$$

### 6.2 Pre-Configured Official Emission Factors

| Factor Key | Category | Scope | Factor Value | Unit | Source Standard |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `diesel_fuel_liters` | Mobile Combustion | **Scope 1** | $2.68$ | $\text{kg CO}_2\text{e} / \text{liter}$ | UK DEFRA / EPA |
| `gasoline_fuel_liters` | Mobile Combustion | **Scope 1** | $2.31$ | $\text{kg CO}_2\text{e} / \text{liter}$ | UK DEFRA |
| `natural_gas_kwh` | Stationary Combustion | **Scope 1** | $0.185$ | $\text{kg CO}_2\text{e} / \text{kWh}$ | EPA / DEFRA |
| `propane_liters` | Stationary Combustion | **Scope 1** | $1.51$ | $\text{kg CO}_2\text{e} / \text{liter}$ | UK DEFRA |
| `electricity_grid_kwh` | Purchased Electricity | **Scope 2** | $0.42$ | $\text{kg CO}_2\text{e} / \text{kWh}$ | US EPA eGRID National Avg |
| `electricity_grid_green_kwh` | Purchased Electricity | **Scope 2** | $0.015$ | $\text{kg CO}_2\text{e} / \text{kWh}$ | Solar Green PPA Lifecycle |
| `air_travel_passenger_km` | Business Travel | **Scope 3** | $0.15$ | $\text{kg CO}_2\text{e} / \text{passenger-km}$ | ICAO Aviation Model |
| `rail_travel_passenger_km` | Business Travel | **Scope 3** | $0.035$ | $\text{kg CO}_2\text{e} / \text{passenger-km}$ | UK DEFRA Rail |
| `freight_truck_tonne_km` | Upstream Transportation | **Scope 3** | $0.105$ | $\text{kg CO}_2\text{e} / \text{tonne-km}$ | GLEC Framework |
| `it_hardware_unit` | Capital Goods | **Scope 3** | $250.0$ | $\text{kg CO}_2\text{e} / \text{unit}$ | Dell / Apple LCA Average |
| `waste_landfill_kg` | Waste Generated | **Scope 3** | $0.58$ | $\text{kg CO}_2\text{e} / \text{kg}$ | EPA WARM Model |

---

## 7. Cryptographic Hash Calculation Formula

Each block in the audit ledger is computed deterministically using standard SHA-256:

$$\text{Block Data} = \{\text{index}, \text{timestamp}, \text{record\_id}, \text{agent\_name}, \text{action}, \text{previous\_hash}, \text{payload\_summary}\}$$

$$\text{Block Hash} = \text{SHA-256}(\text{Canonical JSON String of Block Data})$$

Any modification of past transactions, quantities, or dates alters that block's hash, which immediately breaks all downstream hashes and triggers `[TAMPERED]` in both CLI and Web UI verification.

---

## 8. Directory & Storage Architecture

```
AI-Carbon-Auditor/
│
├── storage/
│   ├── raw/                           # ZONE 1: Immutable Raw Input (Read-Only)
│   │   ├── invoices/                  # Fuel & supplier invoices (CSV/JSON)
│   │   ├── erp/                       # Travel & procurement records
│   │   └── utility/                   # Smart meter electricity feeds
│   │
│   ├── processed/                     # ZONE 2: Verified Outputs
│   │   ├── audit_ledger.json          # Cryptographic SHA-256 block ledger
│   │   ├── hitl_queue.json            # Active quarantined review items
│   │   ├── hitl_resolutions.jsonl     # Append-only feedback learning log
│   │   ├── ecochain_carbon_disclosure.csv
│   │   └── ecochain_carbon_disclosure.json
│
├── agents/                            # Multi-Agent Pipeline
│   ├── ingestion_agent.py             # Validates & routes files immutably
│   ├── normalization_agent.py         # Unit conversion & standard mapping
│   ├── calculation_agent.py           # Emissions math & dynamic confidence
│   ├── audit_agent.py                 # Anomaly detection, duplicates, limits
│   └── orchestrator.py                # Pipeline supervisor & aggregator
│
├── core/
│   ├── schema.py                      # Pydantic data schemas & enums
│   ├── emission_factors.py            # Global GHG emission factor tables
│   ├── audit_ledger.py                # SHA-256 cryptographic blockchain
│   └── config.py                      # Global paths & thresholds
│
├── hitl/
│   └── review_queue.py                # HITL Queue management & batch resolver
│
├── web/
│   ├── static/                        # CSS styles, vanilla JS frontend
│   └── templates/                     # index.html responsive dashboard
│
├── sample_data/                       # Pre-loaded benchmark scenario files
└── app.py                             # Flask Web Server & CLI runner
```

---

## 9. Verification & CLI Usage

### Running via Web Dashboard:
```powershell
python app.py
```
Open `http://127.0.0.1:5000` in any web browser.

### Running via CLI Mode:
```powershell
python app.py --cli --file sample_data/sample_invoices.csv
```

### Running Automated Test Suite:
```powershell
python -m pytest
```
All 18 tests cover ingestion routing, unit normalization, emission factors math, anomaly detection, ledger chaining, tamper detection, feedback loops, and batch HITL resolution endpoints.
