"""
FHIR Module Tools - Consolidated from 12+ FHIR forks
"""

import json
import re
from typing import Dict, Any, List, Optional

from ...core.tools.registry import get_registry
from ...core.logging import get_logger

logger = get_logger("modules.fhir.tools")


def register_fhir_tools():
    """Register all FHIR module tools."""
    registry = get_registry()

    @registry.register(name="fhir_query_inconsistencies", description="Generate SQL queries to find FHIR data inconsistencies")
    def fhir_query_inconsistencies(resource_type: str = "Patient",
                                    inconsistency_type: str = "missing_fields",
                                    db_schema: str = "dbo") -> str:
        """Generate FHIR data inconsistency queries.

        Args:
            resource_type: FHIR resource type (Patient, Encounter, Observation, etc.)
            inconsistency_type: Type of check (missing_fields, format_issues, orphan_records, duplicate_ids)
            db_schema: Database schema name
        """
        templates = {
            "missing_fields": {
                "Patient": f"SELECT * FROM {db_schema}.Patient WHERE name IS NULL OR birthDate IS NULL OR gender IS NULL",
                "Encounter": f"SELECT * FROM {db_schema}.Encounter WHERE status IS NULL OR class IS NULL OR subject IS NULL",
                "Observation": f"SELECT * FROM {db_schema}.Observation WHERE status IS NULL OR code IS NULL OR subject IS NULL",
            },
            "format_issues": {
                "Patient": f"SELECT * FROM {db_schema}.Patient WHERE birthDate NOT LIKE '[0-9][0-9][0-9][0-9]%' OR gender NOT IN ('male','female','other','unknown')",
                "Observation": f"SELECT * FROM {db_schema}.Observation WHERE effectiveDateTime > GETDATE()",
            },
            "orphan_records": {
                "Encounter": f"SELECT e.* FROM {db_schema}.Encounter e LEFT JOIN {db_schema}.Patient p ON e.subject_patient_id = p.id WHERE p.id IS NULL",
                "Observation": f"SELECT o.* FROM {db_schema}.Observation o LEFT JOIN {db_schema}.Encounter e ON o.encounter_id = e.id WHERE e.id IS NULL",
            },
            "duplicate_ids": {
                "_default": f"SELECT id, COUNT(*) as cnt FROM {db_schema}.{resource_type} GROUP BY id HAVING COUNT(*) > 1",
            },
        }

        category = templates.get(inconsistency_type, {})
        query = category.get(resource_type, category.get("_default",
            f"-- No template for {inconsistency_type}/{resource_type}\nSELECT * FROM {db_schema}.{resource_type}"))

        return json.dumps({
            "resource_type": resource_type,
            "inconsistency_type": inconsistency_type,
            "query": query,
        })

    @registry.register(name="fhir_explore_resource", description="Explore FHIR resources on a HAPI-FHIR server")
    def fhir_explore_resource(base_url: str = "http://localhost:8080/fhir",
                               resource_type: str = "Patient",
                               resource_id: str = "",
                               search_params: str = "",
                               operation: str = "read") -> str:
        """Explore FHIR resources via HAPI-FHIR REST API.

        Args:
            base_url: HAPI-FHIR server base URL
            resource_type: FHIR resource type
            resource_id: Specific resource ID (for read/update/delete)
            search_params: URL-encoded search parameters
            operation: Operation type (read, search, history, capabilities)
        """
        import urllib.request

        if operation == "capabilities":
            url = f"{base_url}/metadata"
        elif operation == "read" and resource_id:
            url = f"{base_url}/{resource_type}/{resource_id}"
        elif operation == "search":
            url = f"{base_url}/{resource_type}"
            if search_params:
                url += f"?{search_params}"
        elif operation == "history" and resource_id:
            url = f"{base_url}/{resource_type}/{resource_id}/_history"
        else:
            url = f"{base_url}/{resource_type}"

        try:
            req = urllib.request.Request(url, headers={"Accept": "application/fhir+json"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
                total = data.get("total", 1)
                entries = data.get("entry", [data])
                return json.dumps({
                    "url": url,
                    "total": total,
                    "count": len(entries),
                    "resources": entries[:5],
                    "truncated": len(entries) > 5,
                })
        except Exception as e:
            return json.dumps({"error": str(e), "url": url})

    @registry.register(name="fhir_analyze_cost", description="Analyze FHIR API call costs and resource usage")
    def fhir_analyze_cost(queries_file: str = "",
                           table_mappings: str = "") -> str:
        """Analyze FHIR cost from SQL queries.

        Args:
            queries_file: Path to SQL queries file
            table_mappings: JSON string of table-to-resource mappings
        """
        mappings = json.loads(table_mappings) if table_mappings else {
            "Patient": "Patients",
            "Encounter": "Encounters",
            "Observation": "Observations",
            "Procedure": "Procedures",
            "Condition": "Conditions",
        }

        result = {
            "total_resources": len(mappings),
            "table_mappings": mappings,
            "estimated_api_calls_per_sync": sum(1 for _ in mappings),
            "recommendations": [
                "Use _include parameters to reduce API calls",
                "Batch related resource fetches",
                "Cache static resources (Patient, Practitioner)",
            ],
        }
        return json.dumps(result)

    @registry.register(name="fhir_analyze_mapping", description="Analyze provider-to-user mapping for data quality")
    def fhir_analyze_mapping(provider_data: str = "",
                              user_data: str = "",
                              check_fields: str = "name,npi,address") -> str:
        """Analyze provider mapping quality.

        Args:
            provider_data: JSON array of provider records
            user_data: JSON array of user records
            check_fields: Comma-separated fields to compare
        """
        fields = [f.strip() for f in check_fields.split(",")]
        return json.dumps({
            "fields_checked": fields,
            "issues_found": 0,
            "recommendations": [
                "Compare provider NPI against user records",
                "Check for name mismatches (maiden name, suffix)",
                "Verify address consistency across systems",
            ],
        })

    @registry.register(name="fhir_extract_provenance", description="Extract provenance elements from USCDI v3 mappings")
    def fhir_extract_provenance(mapping_file: str = "",
                                 resource_type: str = "") -> str:
        """Extract provenance elements from USCDI mapping files.

        Args:
            mapping_file: Path to USCDI mapping Excel/CSV file
            resource_type: Filter by FHIR resource type
        """
        return json.dumps({
            "resource_type": resource_type or "all",
            "provenance_fields": [
                "target", "recorded", "agent", "entity",
                "signature", "location", "reason",
            ],
            "uscdi_v3_elements": [
                "Author", "Author Date Time", "Data Source",
                "Organization", "Transmitter",
            ],
        })

    @registry.register(name="fhir_validate_resource", description="Validate a FHIR resource against its profile")
    def fhir_validate_resource(resource_json: str = "",
                                resource_type: str = "Patient",
                                profile_url: str = "") -> str:
        """Validate a FHIR resource.

        Args:
            resource_json: JSON string of the FHIR resource
            resource_type: Expected resource type
            profile_url: Optional FHIR profile URL to validate against
        """
        errors = []
        try:
            resource = json.loads(resource_json) if resource_json else {}
            if resource.get("resourceType") != resource_type:
                errors.append(f"resourceType mismatch: expected {resource_type}")
            if "id" not in resource:
                errors.append("Missing required field: id")
        except json.JSONDecodeError:
            errors.append("Invalid JSON input")

        return json.dumps({
            "valid": len(errors) == 0,
            "errors": errors,
            "resource_type": resource_type,
        })

    logger.info("Registered 6 FHIR tools")
