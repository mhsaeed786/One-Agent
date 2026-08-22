"""
Work Ops Module - Outlook/Teams scraper, SharePoint downloader, DataSync automation
"""

from ..module_base import ModuleManifest, register_module

manifest = ModuleManifest(
    name="work_ops",
    version="0.1.0",
    description="Work operations: email/Teams scraping, SharePoint downloads, data sync",
    tools=[
        "work_ops_scrape_emails",
        "work_ops_scrape_teams",
        "work_ops_download_sharepoint",
        "work_ops_run_datasync",
    ],
    routes_prefix="/api/work_ops",
)

register_module(manifest)


def get_manifest() -> ModuleManifest:
    return manifest
