"""
Research Module - Consolidated from deep_researcher + saas_opportunity_finder
"""

from ..module_base import ModuleManifest, register_module

manifest = ModuleManifest(
    name="research",
    version="0.1.0",
    description="Deep research, web analysis, SaaS opportunity identification",
    tools=[
        "research_deep_search",
        "research_find_saas_opportunities",
        "research_summarize",
    ],
    routes_prefix="/api/research",
)

register_module(manifest)


def get_manifest() -> ModuleManifest:
    return manifest
