"""
Module Base - Shared infrastructure for all OneAgent modules
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
from pathlib import Path

from ..core.logging import get_logger

logger = get_logger("modules.base")

# Global module registry
_MODULE_REGISTRY: Dict[str, "ModuleManifest"] = {}


@dataclass
class ModuleManifest:
    """Manifest for a OneAgent module."""
    name: str
    version: str = "0.1.0"
    description: str = ""
    tools: List[str] = field(default_factory=list)
    routes_prefix: str = ""
    ui_page: str = ""
    dependencies: List[str] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)


def register_module(manifest: ModuleManifest) -> None:
    """Register a module in the global registry."""
    _MODULE_REGISTRY[manifest.name] = manifest
    logger.info(f"Registered module: {manifest.name} v{manifest.version}")


def get_module(name: str) -> Optional[ModuleManifest]:
    """Get a module manifest by name."""
    return _MODULE_REGISTRY.get(name)


def list_modules() -> List[ModuleManifest]:
    """List all registered modules."""
    return list(_MODULE_REGISTRY.values())


def auto_discover_modules(modules_dir: Optional[str] = None) -> List[ModuleManifest]:
    """Auto-discover and load all modules from the modules directory."""
    import importlib
    import pkgutil

    try:
        import oneagent.modules as modules_pkg
        pkg_path = modules_dir or str(Path(modules_pkg.__file__).parent)

        for importer, modname, ispkg in pkgutil.iter_modules([pkg_path]):
            if ispkg and modname not in ("__pycache__", "module_base"):
                try:
                    importlib.import_module(f"oneagent.modules.{modname}")
                except Exception as e:
                    logger.warning(f"Failed to load module {modname}: {e}")
    except Exception as e:
        logger.warning(f"Module discovery failed: {e}")

    return list_modules()
