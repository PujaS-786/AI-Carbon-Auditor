"""
EcoChain 24 — Autonomous AI Carbon Auditor Demonstration Script
Runs an end-to-end audit pass across all 3 source types (Invoices, ERP, Utility),
demonstrates anomaly detection, HITL resolution, ledger verification, and disclosure reporting.
"""

from pathlib import Path
from core.config import SAMPLE_DATA_DIR, HITL_RESOLUTIONS_FILE, REPORTS_OUTPUT_JSON
from core.audit_trail import audit_ledger
from hitl.review_queue import hitl_queue
from agents.orchestrator import orchestrator

def print_banner(title: str):
    print("\n" + "=" * 65)
    print(f"  {title}")
    print("=" * 65)

def run_demo():
    print_banner("EcoChain 24 — AI Carbon Auditor Live Demonstration")

    # Step 1: Ingest Invoices
    print("\n[Stage 1] Ingesting & Auditing Supplier Invoices...")
    inv_path = SAMPLE_DATA_DIR / "sample_invoices.csv"
    rep_inv = orchestrator.run_file(inv_path, source_hint="invoice")
    print(f"  [+] Processed: {inv_path.name}")
    print(f"  [+] Subtotal Emissions: {rep_inv['summary']['total_tonnes_co2e']:,.2f} tCO2e")

    # Step 2: Ingest ERP Data
    print("\n[Stage 2] Ingesting & Auditing ERP Procurement/Travel Records...")
    erp_path = SAMPLE_DATA_DIR / "sample_erp.csv"
    rep_erp = orchestrator.run_file(erp_path, source_hint="erp")
    print(f"  [+] Processed: {erp_path.name}")
    print(f"  [+] Subtotal Emissions: {rep_erp['summary']['total_tonnes_co2e']:,.2f} tCO2e")

    # Step 3: Ingest Utility Bills
    print("\n[Stage 3] Ingesting & Auditing Utility Smart Meter Feeds...")
    util_path = SAMPLE_DATA_DIR / "sample_utility.json"
    rep_util = orchestrator.run_file(util_path, source_hint="utility")
    print(f"  [+] Processed: {util_path.name}")
    print(f"  [+] Subtotal Emissions: {rep_util['summary']['total_tonnes_co2e']:,.2f} tCO2e")

    # Step 4: Review HITL Flagged Items
    print_banner("Human-In-The-Loop (HITL) Review Queue")
    pending = hitl_queue.get_pending_items()
    print(f"Found {len(pending)} flagged items requiring human auditor review:")
    for item in pending:
        print(f"  * Record: {item.record_id} | Supplier: {item.calculated_record.supplier_or_facility}")
        print(f"    Reasons: {', '.join(item.flag_reasons)}")
        print(f"    Confidence: {item.confidence_score * 100:.0f}%")

    # Step 5: Simulate Auditor Resolution
    if pending:
        target = pending[0]
        print(f"\n[Action] Auditor resolving record {target.record_id} via override...")
        resolved = hitl_queue.resolve_item(
            record_id=target.record_id,
            reviewer_name="Lead Sustainability Auditor",
            action="override",
            reviewer_notes="Corrected data entry error; normalized to actual meter consumption.",
            adjusted_quantity=1500.0
        )
        print(f"  [+] Status changed to: {resolved.status.value}")
        print(f"  [+] New calculated kgCO2e: {resolved.calculated_record.kg_co2e:,.2f}")

    # Step 6: Final Board Disclosure Report
    final_report = orchestrator.compile_disclosure_report()
    summary = final_report["summary"]
    scopes = final_report["scopes"]

    print_banner("Final Executive Board Carbon Disclosure")
    print(f"Reporting Standard:      {final_report['meta']['report_standard']}")
    print(f"Total Carbon Footprint:  {summary['total_tonnes_co2e']:,.2f} tCO2e ({summary['total_kg_co2e']:,.1f} kgCO2e)")
    print(f"Scope 1 (Direct Fuels):  {scopes['scope_1_direct_tco2e']:,.2f} tCO2e")
    print(f"Scope 2 (Electricity):   {scopes['scope_2_electricity_tco2e']:,.2f} tCO2e")
    print(f"Scope 3 (Supply Chain):  {scopes['scope_3_value_chain_tco2e']:,.2f} tCO2e")
    print(f"Average Confidence:      {summary['average_confidence_rating']}")
    print(f"Audit Readiness Grade:   {summary['audit_readiness_score']}")
    print(f"Report exported to:      {REPORTS_OUTPUT_JSON}")

    # Step 7: Cryptographic Hash Chain Verification
    print_banner("Cryptographic Ledger Integrity Check")
    is_valid, msg, chain = audit_ledger.verify_chain_integrity()
    print(f"Ledger Status:    {'[SECURE / VERIFIED]' if is_valid else '[CORRUPTED]'}")
    print(f"Verification Msg: {msg}")
    print(f"Total Blocks:     {len(chain)}")
    print("=" * 65 + "\n")

if __name__ == "__main__":
    run_demo()
