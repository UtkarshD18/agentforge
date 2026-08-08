import os
import yaml
from enum import Enum
from typing import Dict, List, Any, Optional
from .manifest import CapabilityManifest

class PluginType(str, Enum):
    PROVIDER = "provider"
    ANALYZER = "analyzer"
    HOST = "host"
    GRAPH_BUILDER = "graph_builder"
    AGENT = "agent"

class PluginRegistry:
    def __init__(self) -> None:
        self._plugins: Dict[PluginType, Dict[str, Any]] = {pt: {} for pt in PluginType}
        self._manifests: Dict[str, CapabilityManifest] = {}

    def register_plugin(self, plugin_type: PluginType, plugin_id: str, instance: Any, manifest: CapabilityManifest) -> None:
        self._plugins[plugin_type][plugin_id] = {
            "instance": instance,
            "manifest": manifest
        }
        self._manifests[plugin_id] = manifest

    def get_plugin(self, plugin_type: PluginType, plugin_id: str) -> Optional[Any]:
        plug = self._plugins[plugin_type].get(plugin_id)
        return plug["instance"] if plug else None

    def get_plugin_manifest(self, plugin_id: str) -> Optional[CapabilityManifest]:
        return self._manifests.get(plugin_id)

    def list_plugins(self, plugin_type: PluginType) -> List[Dict[str, Any]]:
        return list(self._plugins[plugin_type].values())

    def scan_plugins(self, directory_path: str) -> None:
        if not os.path.exists(directory_path):
            return
        for root, dirs, files in os.walk(directory_path):
            if "manifest.yaml" in files:
                manifest_path = os.path.join(root, "manifest.yaml")
                try:
                    with open(manifest_path, "r", encoding="utf-8") as f:
                        data = yaml.safe_load(f)
                        manifest = CapabilityManifest(**data)
                        self._manifests[manifest.id] = manifest
                        try:
                            ptype = PluginType(manifest.type)
                            if manifest.id not in self._plugins[ptype]:
                                self._plugins[ptype][manifest.id] = {
                                    "manifest": manifest,
                                    "instance": None
                                }
                        except ValueError:
                            pass
                except Exception as e:
                    print(f"[PluginRegistry] Failed to parse manifest at {manifest_path}: {e}")
