"""
Content Module - Drafting, summarization, and rewriting tools
"""

from ..module_base import ModuleManifest, register_module

manifest = ModuleManifest(
    name="content",
    version="0.1.0",
    description="Content authoring: drafting, summarization, rewriting, translation",
    tools=[
        "content_draft_article",
        "content_summarize_text",
        "content_rewrite",
    ],
    routes_prefix="/api/content",
)

register_module(manifest)


def get_manifest() -> ModuleManifest:
    return manifest
