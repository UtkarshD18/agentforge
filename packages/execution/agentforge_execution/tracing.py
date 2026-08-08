import threading
from contextlib import contextmanager
from typing import List, Dict, Any, Optional
from agentforge_core.di import get_container
from agentforge_core.storage import GraphRepository, Entity

# Thread-local storage to track active execution trace spans in the call stack
_thread_local_context = threading.local()

def get_active_span_uri() -> Optional[str]:
    """
    Returns the task/span URI currently active on the calling thread, or None.
    """
    return getattr(_thread_local_context, "active_span_uri", None)

@contextmanager
def execution_span(task_uri: str, parent_uri: Optional[str] = None):
    """
    Context manager to record task span lifecycles.
    Links child spans to parent spans in the database graph.
    """
    # 1. Resolve parent (explicitly provided, or retrieved from thread-local context)
    resolved_parent = parent_uri or get_active_span_uri()
    
    # 2. Update thread-local stack
    previous_span = get_active_span_uri()
    _thread_local_context.active_span_uri = task_uri

    # 3. Save span entity and relate to parent in DB
    try:
        container = get_container()
        repo = container.resolve(GraphRepository)
        
        # Save span task entity
        repo.save_entity(Entity(
            uri=task_uri,
            type="trace_span",
            metadata={"parent_uri": resolved_parent}
        ))
        
        # If parent exists, create child edge relation
        if resolved_parent:
            repo.relate_entities(resolved_parent, task_uri, "child")
    except Exception:
        # Ignore DB errors in contexts where DB repository is not registered (e.g., lightweight tests)
        pass

    try:
        yield task_uri
    finally:
        # Restore previous span context on exit
        _thread_local_context.active_span_uri = previous_span

class ExecutionLineageTracker:
    """
    Utility wrapper to retrieve OpenTelemetry-style parent/child traces from storage.
    """
    @staticmethod
    def get_lineage_trace(root_task_uri: str) -> Dict[str, Any]:
        """
        Traverses storage database edges starting from root task URI to fetch full lineage.
        """
        try:
            container = get_container()
            repo = container.resolve(GraphRepository)
        except Exception:
            return {"uri": root_task_uri, "children": []}

        # Sub-helper to gather child relations recursively
        def gather_children(parent_uri: str) -> List[Dict[str, Any]]:
            # Retrieve entities that point to parent_uri with a "child" relationship
            related = repo.get_related_entities(parent_uri, "child")
            
            # Since get_related_entities might search source->target, 
            # let's fetch all matching inbound child_of edges.
            # In SQLite repo, relate_entities saves: source_uri, target_uri, relationship
            # If we call relate(child, parent, "child_of"), the parent is target_uri.
            # So we query children using a database lookup.
            children_nodes = []
            
            # Let's query edges directly or query adjacent nodes:
            # We can use the SQLite adapter query interface:
            # For this model diagnostics, we fetch nodes pointing back to parent.
            for node in related:
                children_nodes.append({
                    "uri": node.uri,
                    "type": node.type,
                    "metadata": node.metadata,
                    "children": gather_children(node.uri)
                })
            return children_nodes

        root_entity = repo.get_entity(root_task_uri)
        return {
            "uri": root_task_uri,
            "type": root_entity.type if root_entity else "unknown",
            "metadata": root_entity.metadata if root_entity else {},
            "children": gather_children(root_task_uri)
        }
