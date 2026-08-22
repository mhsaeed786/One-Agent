"""
Coding Module - Code generation, review, and explanation tools
"""

from ..module_base import ModuleManifest, register_module

manifest = ModuleManifest(
    name="coding",
    version="0.1.0",
    description="Code assistance: generation, review, refactoring, explanation",
    tools=[
        "coding_review_code",
        "coding_generate_snippet",
        "coding_explain",
    ],
    routes_prefix="/api/coding",
)

register_module(manifest)


def get_manifest() -> ModuleManifest:
    return manifest
