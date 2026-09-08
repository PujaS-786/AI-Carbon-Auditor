import os
import sys
import argparse
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS

from core.config import (
    BASE_DIR, SAMPLE_DATA_DIR, RAW_DIR, RAW_INVOICES_DIR,
    RAW_ERP_DIR, RAW_UTILITY_DIR, REPORTS_OUTPUT_CSV, REPORTS_OUTPUT_JSON
)
from core.audit_trail import audit_ledger
from hitl.review_queue import hitl_queue
from agents.orchestrator import orchestrator

# Initialize Flask App
template_dir = BASE_DIR / "web" / "templates"
static_dir = BASE_DIR / "web" / "static"

app = Flask(
    __name__,
    template_folder=str(template_dir),
    static_folder=str(static_dir)
)
CORS(app)

# ----------------- Web UI & API Routes -----------------

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/health", methods=["GET"])
def health():
    chain = audit_ledger.get_chain()
    is_valid, msg, _ = audit_ledger.verify_chain_integrity()
    return jsonify({
        "status": "healthy",
        "system": "EcoChain 24 AI Carbon Auditor",
        "ledger_blocks": len(chain),
        "ledger_integrity": "OK" if is_valid else "CORRUPTED"
    })

@app.route("/api/records", methods=["GET"])
def get_records():
    return jsonify(orchestrator.get_all_records_summary())

@app.route("/api/hitl/queue", methods=["GET"])
def get_hitl_queue():
    items = hitl_queue.get_all_items()
    return jsonify([i.model_dump() for i in items])

@app.route("/api/hitl/resolve", methods=["POST"])
def resolve_hitl_record():
    data = request.get_json() or {}
    record_id = data.get("record_id")
    action = data.get("action")
    reviewer = data.get("reviewer_name", "Lead Sustainability Auditor")
    notes = data.get("notes", "Reviewed via auditor portal")
    adj_qty = data.get("adjusted_quantity")
    adj_factor = data.get("adjusted_factor_key")

    if not record_id or not action:
        return jsonify({"success": False, "error": "record_id and action are required"}), 400

    try:
        if adj_qty is not None and str(adj_qty).strip() != "":
            adj_qty = float(adj_qty)
        else:
            adj_qty = None

        resolved_item = hitl_queue.resolve_item(
            record_id=record_id,
            reviewer_name=reviewer,
            action=action,
            reviewer_notes=notes,
            adjusted_quantity=adj_qty,
            adjusted_factor_key=adj_factor if adj_factor else None
        )

        # Trigger disclosure re-aggregation
        disclosure = orchestrator.compile_disclosure_report()

        return jsonify({
            "success": True,
            "resolved_item": resolved_item.model_dump(),
            "updated_disclosure": disclosure
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/hitl/resolve_all", methods=["POST"])
def resolve_all_hitl():
    data = request.get_json() or {}
    action = data.get("action", "approve")
    reviewer = data.get("reviewer_name", "Lead Sustainability Auditor")
    notes = data.get("notes", f"Batch {action} via auditor portal")

    try:
        resolved_items = hitl_queue.resolve_all_pending(
            reviewer_name=reviewer,
            action=action,
            reviewer_notes=notes
        )
        disclosure = orchestrator.compile_disclosure_report()
        return jsonify({
            "success": True,
            "count": len(resolved_items),
            "action": action,
            "updated_disclosure": disclosure
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/ledger", methods=["GET"])
def get_ledger():
    chain = audit_ledger.get_chain()
    return jsonify([b.model_dump() for b in chain])

@app.route("/api/ledger/verify", methods=["GET"])
def verify_ledger():
    is_valid, msg, details = audit_ledger.verify_chain_integrity()
    return jsonify({
        "is_valid": is_valid,
        "message": msg,
        "chain_length": len(details),
        "details": details[-15:] # Return last 15 block checks
    })

@app.route("/api/reports/summary", methods=["GET"])
def get_report_summary():
    report = orchestrator.compile_disclosure_report()
    return jsonify(report)

@app.route("/api/reports/export/csv", methods=["GET"])
def export_csv():
    if not REPORTS_OUTPUT_CSV.exists():
        orchestrator.compile_disclosure_report()
    return send_file(REPORTS_OUTPUT_CSV, as_attachment=True, download_name="ecochain_carbon_disclosure.csv")

@app.route("/api/reports/export/json", methods=["GET"])
def export_json():
    report = orchestrator.compile_disclosure_report()
    as_download = request.args.get("download", "false").lower() == "true"
    if as_download:
        return send_file(REPORTS_OUTPUT_JSON, as_attachment=True, download_name="ecochain_carbon_disclosure.json")
    return jsonify(report)

@app.route("/api/ingest/direct", methods=["POST"])
def ingest_direct():
    data = request.get_json() or {}
    source_hint = data.get("source_type", "invoice").lower()

    # Case A: Raw text snippet (CSV or JSON)
    if "raw_text" in data and data["raw_text"].strip():
        import time
        raw_text = data["raw_text"].strip()
        target_dir = RAW_ERP_DIR if source_hint == "erp" else (RAW_UTILITY_DIR if source_hint == "utility" else RAW_INVOICES_DIR)
        ext = ".json" if raw_text.startswith(("[", "{")) else ".csv"
        fname = f"direct_snippet_{int(time.time())}{ext}"
        target_path = target_dir / fname
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(raw_text)

        report = orchestrator.run_file(target_path, source_hint=source_hint)
        return jsonify({
            "success": True,
            "filename": fname,
            "raw_document_ref": f"storage/raw/{target_dir.name}/{fname}",
            "summary": report.get("summary")
        })

    # Case B: Individual transaction fields
    from core.schema import SourceType
    st = SourceType.ERP if source_hint == "erp" else (SourceType.UTILITY if source_hint == "utility" else SourceType.INVOICE)
    raw_rec = orchestrator.ingestion_agent.ingest_direct_record(data, source_type=st)
    calc = orchestrator.process_record(raw_rec)
    report = orchestrator.compile_disclosure_report()
    return jsonify({
        "success": True,
        "record_id": raw_rec.record_id,
        "summary": report.get("summary")
    })

@app.route("/api/sample/load_named", methods=["POST"])
def load_named_sample():
    data = request.get_json() or {}
    filename = data.get("filename", "")
    hint = data.get("hint", "auto")

    target = SAMPLE_DATA_DIR / filename
    if not target.exists():
        return jsonify({"success": False, "error": f"Sample file {filename} not found"}), 404

    report = orchestrator.run_file(target, source_hint=hint)
    return jsonify({
        "success": True,
        "filename": filename,
        "summary": report.get("summary")
    })

@app.route("/api/ingest", methods=["POST"])
def ingest_custom_file():
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "No file part in request"}), 400

    uploaded_file = request.files['file']
    if not uploaded_file.filename:
        return jsonify({"success": False, "error": "Empty filename"}), 400

    fname = uploaded_file.filename
    lower_name = fname.lower()
    source_hint = request.form.get("source_hint", "").lower()

    # Route directly to dedicated input zone (§1 & §2.1)
    if "erp" in lower_name or source_hint == "erp":
        target_dir = RAW_ERP_DIR
        resolved_hint = "erp"
    elif "utility" in lower_name or "meter" in lower_name or source_hint == "utility":
        target_dir = RAW_UTILITY_DIR
        resolved_hint = "utility"
    else:
        target_dir = RAW_INVOICES_DIR
        resolved_hint = "invoice"

    target_path = target_dir / fname
    uploaded_file.save(target_path)

    try:
        report = orchestrator.run_file(target_path, source_hint=resolved_hint)
        return jsonify({
            "success": True,
            "filename": fname,
            "raw_document_ref": f"storage/raw/{target_dir.name}/{fname}",
            "summary": report.get("summary")
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/sample/ingest_all", methods=["POST"])
def ingest_all_samples():
    results = {}
    sample_files = [
        ("sample_invoices.csv", "invoice"),
        ("sample_erp.csv", "erp"),
        ("sample_utility.json", "utility")
    ]

    for fname, hint in sample_files:
        p = SAMPLE_DATA_DIR / fname
        if p.exists():
            rep = orchestrator.run_file(p, source_hint=hint)
            results[fname] = rep.get("summary")

    combined_report = orchestrator.compile_disclosure_report()
    return jsonify({
        "success": True,
        "ingested_files": results,
        "combined_disclosure": combined_report
    })

# ----------------- CLI Mode -----------------

def run_cli_mode(file_path: str):
    print("=" * 60)
    print("  EcoChain 24 — Autonomous AI Carbon Auditor (CLI Mode)")
    print("=" * 60)

    p = Path(file_path)
    if not p.exists():
        print(f"Error: File '{file_path}' does not exist.")
        sys.exit(1)

    print(f"\n[*] Ingesting and auditing: {p.name}")
    report = orchestrator.run_file(p)

    print("\n--- Carbon Disclosure Summary ---")
    summary = report.get("summary", {})
    scopes = report.get("scopes", {})
    print(f"Total Carbon Emissions: {summary.get('total_tonnes_co2e', 0):,.2f} tCO2e")
    print(f"Scope 1 (Direct):      {scopes.get('scope_1_direct_tco2e', 0):,.2f} tCO2e")
    print(f"Scope 2 (Electricity): {scopes.get('scope_2_electricity_tco2e', 0):,.2f} tCO2e")
    print(f"Scope 3 (Value Chain): {scopes.get('scope_3_value_chain_tco2e', 0):,.2f} tCO2e")
    print(f"Data Confidence:      {summary.get('average_confidence_rating')}")

    is_intact, msg, _ = audit_ledger.verify_chain_integrity()
    print(f"\nAudit Ledger Integrity: {'[VALID]' if is_intact else '[TAMPERED]'}")
    print(f"Ledger Status: {msg}")
    print("\nProcessing complete. Exiting.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EcoChain 24 AI Carbon Auditor")
    parser.add_argument("--cli", action="store_true", help="Run in CLI mode")
    parser.add_argument("--file", type=str, help="Source data file path to audit")
    parser.add_argument("--port", type=int, default=5000, help="Port to run web server on")

    args = parser.parse_args()

    if args.cli:
        target = args.file or str(SAMPLE_DATA_DIR / "sample_invoices.csv")
        run_cli_mode(target)
    else:
        print("\nStarting EcoChain 24 Web Dashboard on http://127.0.0.1:5000 ...")
        app.run(host="127.0.0.1", port=args.port, debug=False)
