"""
LEAP Module - Consolidated from 5 LEAP forks (scaling, RWT, analytics, support, UDS)
"""

from ..module_base import ModuleManifest, register_module

manifest = ModuleManifest(
    name="leap",
    version="0.1.0",
    description="LEAP analytics: scaling analysis, RWT reporting, UDS queries, support reports",
    tools=[
        "leap_analyze_scaling",
        "leap_generate_rwt_report",
        "leap_query_uds",
        "leap_support_summary",
    ],
    routes_prefix="/api/leap",
)

register_module(manifest)


def get_manifest() -> ModuleManifest:
    return manifest
