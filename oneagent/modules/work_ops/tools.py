"""
Work Ops Module Tools - Email, Teams, SharePoint, DataSync
"""

import json
from typing import Dict, Any

from ...core.tools.registry import get_registry
from ...core.logging import get_logger

logger = get_logger("modules.work_ops.tools")


def register_work_ops_tools():
    """Register all work ops tools."""
    registry = get_registry()

    @registry.register(name="work_ops_scrape_emails", description="Scrape emails via Microsoft Graph API")
    def work_ops_scrape_emails(folder: str = "Inbox",
                                max_emails: int = 50,
                                filter_sender: str = "",
                                extract_issues: bool = True) -> str:
        """Scrape emails from Outlook via MS Graph."""
        return json.dumps({
            "folder": folder,
            "max_emails": max_emails,
            "status": "ready",
            "note": "Configure MS_GRAPH_CLIENT_ID and MS_GRAPH_CLIENT_SECRET in .env",
            "config_required": [
                "MS_GRAPH_CLIENT_ID",
                "MS_GRAPH_CLIENT_SECRET",
                "MS_GRAPH_TENANT_ID",
            ],
        })

    @registry.register(name="work_ops_scrape_teams", description="Scrape Microsoft Teams messages")
    def work_ops_scrape_teams(team_name: str = "",
                               channel_name: str = "",
                               max_messages: int = 100) -> str:
        """Scrape Teams messages via MS Graph."""
        return json.dumps({
            "team_name": team_name,
            "channel_name": channel_name,
            "max_messages": max_messages,
            "status": "ready",
            "note": "Uses same MS Graph credentials as email scraper",
        })

    @registry.register(name="work_ops_download_sharepoint", description="Download files from SharePoint")
    def work_ops_download_sharepoint(site_url: str = "",
                                      folder_path: str = "",
                                      file_pattern: str = "*",
                                      output_dir: str = "./downloads") -> str:
        """Download files from SharePoint."""
        return json.dumps({
            "site_url": site_url,
            "folder_path": folder_path,
            "file_pattern": file_pattern,
            "output_dir": output_dir,
            "status": "ready",
            "note": "Configure SHAREPOINT_SITE_URL and SHAREPOINT_CREDENTIALS in .env",
        })

    @registry.register(name="work_ops_run_datasync", description="Run data synchronization jobs")
    def work_ops_run_datasync(job_name: str = "",
                              source_db: str = "",
                              target_db: str = "",
                              dry_run: bool = True) -> str:
        """Run data synchronization job."""
        return json.dumps({
            "job_name": job_name,
            "source_db": source_db,
            "target_db": target_db,
            "dry_run": dry_run,
            "status": "ready",
        })

    logger.info("Registered 4 work_ops tools")
