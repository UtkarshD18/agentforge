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
