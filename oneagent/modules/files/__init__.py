"""
Files Module - Directory listing, file reading, and content search tools
"""

from ..module_base import ModuleManifest, register_module

manifest = ModuleManifest(
    name="files",
    version="0.1.0",
    description="Filesystem helpers: list directories, read files, search contents",
    tools=[
        "files_list_dir",
        "files_read_file",
        "files_search",
    ],
    routes_prefix="/api/files",
)

register_module(manifest)


def get_manifest() -> ModuleManifest:
    return manifest
