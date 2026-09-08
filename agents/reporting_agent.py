import csv
import json
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict
from core.schema import CalculatedRecord, AuditStatus, ScopeType
from core.config import REPORTS_OUTPUT_JSON, REPORTS_OUTPUT_CSV, REPORTS_DIR
from core.audit_trail import audit_ledger

class ReportingAgent:
    """
    Reporting Agent:
    Compiles audited emissions into executive board-ready disclosures,
    calculates Scope 1/2/3 distributions, supplier rankings, and exports CSV/JSON summaries.
    """

    def __init__(self, output_dir: Path = REPORTS_DIR):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_disclosure(
        self,
        approved_records: List[CalculatedRecord],
        total_records_count: int,
        hitl_flagged_count: int,
        hitl_resolved_count: int,
        hitl_rejected_count: int
    ) -> Dict[str, Any]:
        scope_breakdown = {
            ScopeType.SCOPE_1.value: 0.0,
            ScopeType.SCOPE_2.value: 0.0,
            ScopeType.SCOPE_3.value: 0.0
        }
        category_breakdown = defaultdict(float)
        supplier_breakdown = defaultdict(float)
        monthly_breakdown = defaultdict(float)

        total_tonnes = 0.0
        total_kg = 0.0
        confidence_sum = 0.0

        for rec in approved_records:
            total_tonnes += rec.tonnes_co2e
            total_kg += rec.kg_co2e
            confidence_sum += rec.confidence_score

            scope_str = rec.scope.value if hasattr(rec.scope, 'value') else str(rec.scope)
            if scope_str in scope_breakdown:
                scope_breakdown[scope_str] += rec.tonnes_co2e

            category_breakdown[rec.category] += rec.tonnes_co2e
            supplier_breakdown[rec.supplier_or_facility] += rec.tonnes_co2e

            # Monthly aggregation (YYYY-MM)
            month_key = rec.date[:7] if len(rec.date) >= 7 else "Unknown"
            monthly_breakdown[month_key] += rec.tonnes_co2e

        avg_confidence = (confidence_sum / len(approved_records)) if approved_records else 1.0

        # Sort suppliers by emissions
        top_suppliers = sorted(
            [{"name": k, "tonnes_co2e": round(v, 4)} for k, v in supplier_breakdown.items()],
            key=lambda x: x["tonnes_co2e"],
            reverse=True
        )

        categories_summary = [
            {"category": k, "tonnes_co2e": round(v, 4)}
            for k, v in sorted(category_breakdown.items(), key=lambda x: x[1], reverse=True)
        ]

        monthly_summary = [
            {"month": k, "tonnes_co2e": round(v, 4)}
            for k, v in sorted(monthly_breakdown.items())
        ]

        # Check ledger status
        is_intact, ledger_msg, _ = audit_ledger.verify_chain_integrity()
        chain_length = len(audit_ledger.get_chain())

        report = {
            "meta": {
                "report_standard": "GHG Protocol Corporate Standard (Scope 1, 2 & 3)",
                "audit_trail_status": "VERIFIED_INTEGRITY" if is_intact else "INTEGRITY_COMPROMISED",
                "total_ledger_blocks": chain_length
            },
            "summary": {
                "total_tonnes_co2e": round(total_tonnes, 4),
                "total_kg_co2e": round(total_kg, 2),
                "average_confidence_rating": f"{round(avg_confidence * 100, 1)}%",
                "audit_readiness_score": "High (Grade A)" if avg_confidence >= 0.85 else "Medium (Grade B)",
                "records_disclosed": len(approved_records)
            },
            "scopes": {
                "scope_1_direct_tco2e": round(scope_breakdown[ScopeType.SCOPE_1.value], 4),
                "scope_2_electricity_tco2e": round(scope_breakdown[ScopeType.SCOPE_2.value], 4),
                "scope_3_value_chain_tco2e": round(scope_breakdown[ScopeType.SCOPE_3.value], 4)
            },
            "audit_pipeline_metrics": {
                "total_ingested_records": total_records_count,
                "auto_approved_records": len(approved_records) - hitl_resolved_count,
                "hitl_flagged_records": hitl_flagged_count,
                "hitl_resolved_records": hitl_resolved_count,
                "hitl_rejected_records": hitl_rejected_count
            },
            "categories": categories_summary,
            "monthly_trend": monthly_summary,
            "top_emitters": top_suppliers
        }

        # Save JSON output
        with open(REPORTS_OUTPUT_JSON, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)

        # Save CSV output of all disclosed records
        with open(REPORTS_OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                "Record ID", "Date", "Supplier/Facility", "Activity", "Scope",
                "Category", "Quantity", "Unit", "Emission Factor", "Factor Unit",
                "kg CO2e", "Tonnes CO2e", "Confidence"
            ])
            for rec in approved_records:
                scope_str = rec.scope.value if hasattr(rec.scope, 'value') else str(rec.scope)
                writer.writerow([
                    rec.record_id, rec.date, rec.supplier_or_facility, rec.activity_type,
                    scope_str, rec.category, rec.activity_quantity, rec.activity_unit,
                    rec.emission_factor_value, rec.emission_factor_unit,
                    rec.kg_co2e, rec.tonnes_co2e, rec.confidence_score
                ])

        return report
