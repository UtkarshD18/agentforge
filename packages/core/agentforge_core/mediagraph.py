import time
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from agentforge_core.di import get_container
from agentforge_core.storage import GraphRepository, Entity

class MediaNodeProvenance(BaseModel):
    """
    Tracks metadata origins (which analyzer ran, when, and its confidence rating).
    """
    created_by: str                       # e.g., 'motion_analyzer_v1'
    timestamp: float = Field(default_factory=time.time)
    confidence: float = 1.0               # Value range 0.0 to 1.0
    version: str = "1.0"
    revision: int = 1

class MediaNode(BaseModel):
    """
    Agnostic Base Class representing a node inside the Media Graph.
    Can be persistent as an Entity in SQLite.
    """
    uri: str
    type: str = "generic_node"
    provenance: MediaNodeProvenance
    metadata: Dict[str, Any] = Field(default_factory=dict)

class TemporalNode(MediaNode):
    """
    Spatial/Temporal Node mapping attributes bound to specific time intervals.
    Used for shots, scenes, transcript words, and silence gaps.
    """
    type: str = "temporal_node"
    start_seconds: float
    end_seconds: float

class SpatialNode(MediaNode):
    """
    Node mapping attributes bound to coordinate bounding boxes.
    Used for face tracking, objects, or text overlays.
    """
    type: str = "spatial_node"
    bounding_box: List[float] = Field(default_factory=list) # [x_min, y_min, x_max, y_max]

class SemanticNode(MediaNode):
    """
    Classification metadata node.
    Used for colors, emotion scores, hook ratings, and CTA details.
    """
    type: str = "semantic_node"
    label: str
    score: float = 1.0

class MediaGraphRepository:
    """
    Registry coordinator. Converts MediaNode structures into StorageRepository
    Entity rows and creates adjacency graph relationship edges.
    """
    def __init__(self, storage_repo: Optional[GraphRepository] = None) -> None:
        self._storage_repo = storage_repo

    def _get_repo(self) -> GraphRepository:
        if self._storage_repo:
            return self._storage_repo
        return get_container().resolve(GraphRepository)

    def save_node(self, graph_uri: str, node: MediaNode, parent_uri: Optional[str] = None) -> None:
        """
        Saves a MediaNode to database and relates it to the root graph and parent nodes.
        """
        repo = self._get_repo()
        
        # Save node as Entity
        entity = Entity(
            uri=node.uri,
            type=node.type,
            metadata=node.model_dump()
        )
        repo.save_entity(entity)
        
        # Relate to the main MediaGraph root
        repo.relate_entities(graph_uri, node.uri, "contains")
        
        # Relate to optional parent context (e.g. FaceNode inside ShotNode)
        if parent_uri:
            repo.relate_entities(parent_uri, node.uri, "parent_of")

    def get_node(self, uri: str) -> Optional[MediaNode]:
        """
        Loads a single MediaNode and validates its specific type.
        """
        repo = self._get_repo()
        entity = repo.get_entity(uri)
        if not entity:
            return None
            
        m = entity.metadata
        if entity.type == "temporal_node":
            return TemporalNode.model_validate(m)
        elif entity.type == "spatial_node":
            return SpatialNode.model_validate(m)
        elif entity.type == "semantic_node":
            return SemanticNode.model_validate(m)
        return MediaNode.model_validate(m)

    def get_graph_nodes(self, graph_uri: str, relationship: str = "contains") -> List[MediaNode]:
        """
        Retrieves all child MediaNode elements related to the root graph.
        """
        repo = self._get_repo()
        related = repo.get_related_entities(graph_uri, relationship)
        
        nodes = []
        for entity in related:
            node = self.get_node(entity.uri)
            if node:
                nodes.append(node)
        return nodes

class GraphBuilder:
    """
    Centralized builder to construct MediaNode models from raw analyzer result values,
    ensuring standardized provenance and schemas.
    """
    @staticmethod
    def build_shot_node(
        index: int,
        start_seconds: float,
        end_seconds: float,
        creator: str,
        confidence: float = 1.0,
        revision: int = 1,
        metadata: Optional[Dict[str, Any]] = None
    ) -> TemporalNode:
        prov = MediaNodeProvenance(created_by=creator, confidence=confidence, revision=revision)
        return TemporalNode(
            uri=f"node://shot/{index}?rev={revision}",
            provenance=prov,
            start_seconds=start_seconds,
            end_seconds=end_seconds,
            metadata=metadata or {}
        )

    @staticmethod
    def build_face_node(
        index: int,
        bounding_box: List[float],
        creator: str,
        confidence: float = 1.0,
        revision: int = 1,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SpatialNode:
        prov = MediaNodeProvenance(created_by=creator, confidence=confidence, revision=revision)
        return SpatialNode(
            uri=f"node://face/{index}?rev={revision}",
            provenance=prov,
            bounding_box=bounding_box,
            metadata=metadata or {}
        )

    @staticmethod
    def build_color_node(
        palette_id: str,
        label: str,
        score: float,
        creator: str,
        revision: int = 1,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SemanticNode:
        prov = MediaNodeProvenance(created_by=creator, revision=revision)
        return SemanticNode(
            uri=f"node://colors/{palette_id}?rev={revision}",
            provenance=prov,
            label=label,
            score=score,
            metadata=metadata or {}
        )

    @staticmethod
    def build_transcript_node(
        clip_name: str,
        start_seconds: float,
        end_seconds: float,
        text: str,
        confidence: float,
        creator: str,
        revision: int = 1,
        metadata: Optional[Dict[str, Any]] = None
    ) -> TemporalNode:
        prov = MediaNodeProvenance(created_by=creator, confidence=confidence, revision=revision)
        safe_clip = clip_name.replace(".", "_")
        return TemporalNode(
            uri=f"node://clip/{safe_clip}/transcript/{int(start_seconds * 100)}?rev={revision}",
            provenance=prov,
            start_seconds=start_seconds,
            end_seconds=end_seconds,
            metadata={
                "clip_name": clip_name,
                "text": text,
                **(metadata or {})
            }
        )

import hashlib
import json

class ContextBudgeter:
    """
    Manages modality-aware context budgets (tokens, images, output limits)
    for model prompt generation, using a Retrieve -> Rank -> Compress pipeline.
    """
    def __init__(self, text_token_limit: int = 2000, max_images: int = 5) -> None:
        self.text_token_limit = text_token_limit
        self.max_images = max_images

    def compile_budgeted_context(self, nodes: List[MediaNode]) -> Dict[str, Any]:
        # 1. Rank nodes by confidence or relevance score
        ranked_nodes = sorted(
            nodes,
            key=lambda x: x.provenance.confidence if hasattr(x, "provenance") else 1.0,
            reverse=True
        )
        
        compiled_text = []
        text_tokens_used = 0
        images_included = []
        
        # 2. Add elements under budget limits
        for node in ranked_nodes:
            # Check for image/visual nodes
            if node.type == "spatial_node" and len(images_included) < self.max_images:
                img_path = node.metadata.get("frame_path")
                if img_path:
                    images_included.append(img_path)
            
            # Rough token estimate (4 characters = 1 token average)
            node_desc = f"{node.type} | {node.uri} | {json.dumps(node.metadata)}"
            node_tokens = len(node_desc) // 4
            
            if text_tokens_used + node_tokens <= self.text_token_limit:
                compiled_text.append(node_desc)
                text_tokens_used += node_tokens
                
        return {
            "text": "\n".join(compiled_text),
            "tokens_used": text_tokens_used,
            "images": images_included
        }

class MediaAnalysisCache:
    """
    Multi-level cache (L1, L2, L3) key builder and resolver.
    """
    def __init__(self, graph_repo: MediaGraphRepository) -> None:
        self.graph_repo = graph_repo

    def build_cache_key(
        self,
        media_hash: str,
        analysis_type: str,
        model_name: str,
        model_version: str,
        params: Dict[str, Any],
        analyzer_version: str = "1.0"
    ) -> str:
        # Include analyzer_version and params in invalidation hash
        params_str = json.dumps(params, sort_keys=True)
        combined = f"{media_hash}:{analysis_type}:{model_name}:{model_version}:{params_str}:{analyzer_version}"
        h = hashlib.sha256(combined.encode("utf-8")).hexdigest()[:24]
        return f"cache://{analysis_type}/{h}"

    def get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        node = self.graph_repo.get_node(cache_key)
        if node:
            return node.metadata.get("result")
        return None

    def save_cached_result(self, media_graph_uri: str, cache_key: str, tier: str, result: Any) -> None:
        prov = MediaNodeProvenance(created_by=f"cache_tier_{tier.lower()}", confidence=1.0)
        node = SemanticNode(
            uri=cache_key,
            provenance=prov,
            label="cache_item",
            score=1.0,
            metadata={"tier": tier, "result": result}
        )
        self.graph_repo.save_node(media_graph_uri, node)

