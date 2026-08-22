"""
Files Module Tools - SCAFFOLD (live wiring deferred; needs provider credentials)

These tools follow the same structure as the other module tool registries
(leap/research/work_ops). The implementations return placeholder payloads for
now — connect them to the real filesystem/backend once credentials are available.
"""

import json
from typing import Dict, Any

from ...core.tools.registry import get_registry
from ...core.logging import get_logger

logger = get_logger("modules.files.tools")


def register_files_tools():
    """Register all files module tools."""
    registry = get_registry()

    @registry.register(name="files_list_dir", description="List the contents of a directory")
    def files_list_dir(path: str = ".",
                        pattern: str = "*") -> str:
        """List a directory. SCAFFOLD — returns a placeholder."""
        return json.dumps({
            "status": "scaffold",
            "tool": "files_list_dir",
            "path": path,
            "pattern": pattern,
            "entries": [],
            "note": "Live listing wiring deferred — connect to the filesystem backend once credentials are available.",
        })

    @registry.register(name="files_read_file", description="Read the contents of a file")
    def files_read_file(path: str = "",
                        max_bytes: int = 65536) -> str:
        """Read a file. SCAFFOLD — returns a placeholder."""
        return json.dumps({
            "status": "scaffold",
            "tool": "files_read_file",
            "path": path,
            "max_bytes": max_bytes,
            "content": "",
            "note": "Live reading wiring deferred — connect to the filesystem backend once credentials are available.",
        })

    @registry.register(name="files_search", description="Search for a term across files")
    def files_search(root: str = ".",
                      term: str = "",
                      file_glob: str = "*") -> str:
        """Search across files. SCAFFOLD — returns a placeholder."""
        return json.dumps({
            "status": "scaffold",
            "tool": "files_search",
            "root": root,
            "term": term,
            "file_glob": file_glob,
            "matches": [],
            "note": "Live search wiring deferred — connect to the filesystem backend once credentials are available.",
        })

    logger.info("Registered 3 files tools")
