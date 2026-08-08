import json
import sqlite3
import threading
import urllib.request
import urllib.error
import base64
import os
import shutil
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class Entity(BaseModel):
    """
    Graph node entity with addressable URI.
    """
    uri: str
    type: str
    metadata: Dict[str, Any] = {}
    version: int = 1

class Edge(BaseModel):
    """
    Directed relational edge between two entities.
    """
    source_uri: str
    target_uri: str
    relationship: str

class GraphRepository(ABC):
    """
    Abstract Graph Repository Interface for AgentForge graph objects.
    """
    @abstractmethod
    def save_entity(self, entity: Entity) -> None:
        pass

    @abstractmethod
    def get_entity(self, uri: str) -> Optional[Entity]:
        pass

    @abstractmethod
    def delete_entity(self, uri: str) -> None:
        pass

    @abstractmethod
    def relate_entities(self, source_uri: str, target_uri: str, relationship: str) -> None:
        pass

    @abstractmethod
    def unrelate_entities(self, source_uri: str, target_uri: str, relationship: str) -> None:
        pass

    @abstractmethod
    def get_related_entities(self, source_uri: str, relationship: str) -> List[Entity]:
        pass

class EventRepository(ABC):
    """
    Abstract Event Logging Repository Interface for system execution auditing.
    """
    @abstractmethod
    def log_event(self, event_type: str, correlation_id: str, payload: Dict[str, Any], version: str = "1.0") -> None:
        pass

    @abstractmethod
    def get_event_logs(self, correlation_id: str) -> List[Dict[str, Any]]:
        pass

class ArtifactMetadata(BaseModel):
    """
    Metadata schemas representing cached/tracked data files.
    """
    uri: str
    checksum: str
    mime_type: str
    size_bytes: int
    creator: str
    parent_artifact_uri: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ArtifactRepository(ABC):
    """
    Abstract metadata repository for tracking processed artifacts.
    """
    @abstractmethod
    def save_artifact_metadata(self, metadata: ArtifactMetadata) -> None:
        pass

    @abstractmethod
    def get_artifact_metadata(self, uri: str) -> Optional[ArtifactMetadata]:
        pass

class BlobRepository(ABC):
    """
    Abstract Binary Large Object storage repository.
    """
    @abstractmethod
    def save_blob(self, key: str, file_path: str) -> str:
        pass

    @abstractmethod
    def get_blob_path(self, key: str) -> Optional[str]:
        pass

class SettingsRepository(ABC):
    """
    Abstract key-value configurations repository.
    """
    @abstractmethod
    def set_setting(self, key: str, value: Any) -> None:
        pass

    @abstractmethod
    def get_setting(self, key: str) -> Optional[Any]:
        pass

class VectorRepository(ABC):
    """
    Abstract Interface for dense embeddings vector queries.
    """
    @abstractmethod
    def store_vector(self, uri: str, vector: List[float], metadata: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def search_similar(self, query_vector: List[float], limit: int = 5) -> List[Dict[str, Any]]:
        pass

class SQLiteGraphRepository(GraphRepository):
    """
    Thread-safe SQLite Adjacency List implementation of GraphRepository.
    """
    def __init__(self, db_path: str = ":memory:") -> None:
        self.db_path = db_path
        self._lock = threading.Lock()
        self._shared_conn = None
        if self.db_path == ":memory:":
            self._shared_conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._shared_conn.row_factory = sqlite3.Row
            self._shared_conn.execute("PRAGMA foreign_keys = ON;")
        self._initialize_db()

    def _get_connection(self) -> sqlite3.Connection:
        if self._shared_conn:
            return self._shared_conn
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _close_connection(self, conn: sqlite3.Connection) -> None:
        if conn is not self._shared_conn:
            conn.close()

    def _initialize_db(self) -> None:
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS entities (
                            uri TEXT PRIMARY KEY,
                            type TEXT NOT NULL,
                            metadata TEXT NOT NULL,
                            version INTEGER NOT NULL DEFAULT 1,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS edges (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            source_uri TEXT NOT NULL,
                            target_uri TEXT NOT NULL,
                            relationship TEXT NOT NULL,
                            FOREIGN KEY(source_uri) REFERENCES entities(uri) ON DELETE CASCADE,
                            FOREIGN KEY(target_uri) REFERENCES entities(uri) ON DELETE CASCADE,
                            UNIQUE(source_uri, target_uri, relationship)
                        );
                    """)
            finally:
                self._close_connection(conn)

    def save_entity(self, entity: Entity) -> None:
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    conn.execute(
                        """
                        INSERT INTO entities (uri, type, metadata, version)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(uri) DO UPDATE SET
                            type = excluded.type,
                            metadata = excluded.metadata,
                            version = excluded.version;
                        """,
                        (entity.uri, entity.type, json.dumps(entity.metadata), entity.version)
                    )
            finally:
                self._close_connection(conn)

    def get_entity(self, uri: str) -> Optional[Entity]:
        with self._lock:
            conn = self._get_connection()
            try:
                row = conn.execute("SELECT uri, type, metadata, version FROM entities WHERE uri = ?", (uri,)).fetchone()
                if row:
                    return Entity(
                        uri=row["uri"],
                        type=row["type"],
                        metadata=json.loads(row["metadata"]),
                        version=row["version"]
                    )
                return None
            finally:
                self._close_connection(conn)

    def delete_entity(self, uri: str) -> None:
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    conn.execute("DELETE FROM entities WHERE uri = ?", (uri,))
            finally:
                self._close_connection(conn)

    def relate_entities(self, source_uri: str, target_uri: str, relationship: str) -> None:
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    conn.execute(
                        """
                        INSERT INTO edges (source_uri, target_uri, relationship)
                        VALUES (?, ?, ?)
                        ON CONFLICT(source_uri, target_uri, relationship) DO NOTHING;
                        """,
                        (source_uri, target_uri, relationship)
                    )
            finally:
                self._close_connection(conn)

    def unrelate_entities(self, source_uri: str, target_uri: str, relationship: str) -> None:
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    conn.execute(
                        "DELETE FROM edges WHERE source_uri = ? AND target_uri = ? AND relationship = ?",
                        (source_uri, target_uri, relationship)
                    )
            finally:
                self._close_connection(conn)

    def get_related_entities(self, source_uri: str, relationship: str) -> List[Entity]:
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.execute(
                    """
                    SELECT e.uri, e.type, e.metadata, e.version
                    FROM entities e
                    JOIN edges ed ON e.uri = ed.target_uri
                    WHERE ed.source_uri = ? AND ed.relationship = ?
                    """,
                    (source_uri, relationship)
                )
                results = []
                for row in cursor.fetchall():
                    results.append(Entity(
                        uri=row["uri"],
                        type=row["type"],
                        metadata=json.loads(row["metadata"]),
                        version=row["version"]
                    ))
                return results
            finally:
                self._close_connection(conn)

class SQLiteEventRepository(EventRepository):
    """
    Thread-safe SQLite implementation of EventRepository.
    """
    def __init__(self, db_path: str = ":memory:") -> None:
        self.db_path = db_path
        self._lock = threading.Lock()
        self._shared_conn = None
        if self.db_path == ":memory:":
            self._shared_conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._shared_conn.row_factory = sqlite3.Row
        self._initialize_db()

    def _get_connection(self) -> sqlite3.Connection:
        if self._shared_conn:
            return self._shared_conn
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _close_connection(self, conn: sqlite3.Connection) -> None:
        if conn is not self._shared_conn:
            conn.close()

    def _initialize_db(self) -> None:
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS events_log (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            correlation_id TEXT NOT NULL,
                            version TEXT DEFAULT '1.0',
                            event_type TEXT NOT NULL,
                            payload TEXT NOT NULL,
                            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
            finally:
                self._close_connection(conn)

    def log_event(self, event_type: str, correlation_id: str, payload: Dict[str, Any], version: str = "1.0") -> None:
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    conn.execute(
                        """
                        INSERT INTO events_log (correlation_id, version, event_type, payload)
                        VALUES (?, ?, ?, ?)
                        """,
                        (correlation_id, version, event_type, json.dumps(payload))
                    )
            finally:
                self._close_connection(conn)

    def get_event_logs(self, correlation_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.execute(
                    """
                    SELECT correlation_id, version, event_type, payload, timestamp
                    FROM events_log
                    WHERE correlation_id = ?
                    ORDER BY timestamp ASC
                    """,
                    (correlation_id,)
                )
                results = []
                for row in cursor.fetchall():
                    results.append({
                        "correlation_id": row["correlation_id"],
                        "version": row["version"],
                        "event_type": row["event_type"],
                        "payload": json.loads(row["payload"]),
                        "timestamp": row["timestamp"]
                    })
                return results
            finally:
                self._close_connection(conn)

class SQLiteArtifactRepository(ArtifactRepository):
    """
    Thread-safe SQLite implementation of ArtifactRepository.
    """
    def __init__(self, db_path: str = ":memory:") -> None:
        self.db_path = db_path
        self._lock = threading.Lock()
        self._shared_conn = None
        if self.db_path == ":memory:":
            self._shared_conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._shared_conn.row_factory = sqlite3.Row
        self._initialize_db()

    def _get_connection(self) -> sqlite3.Connection:
        if self._shared_conn:
            return self._shared_conn
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _close_connection(self, conn: sqlite3.Connection) -> None:
        if conn is not self._shared_conn:
            conn.close()

    def _initialize_db(self) -> None:
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS artifacts_metadata (
                            uri TEXT PRIMARY KEY,
                            checksum TEXT NOT NULL,
                            mime_type TEXT NOT NULL,
                            size_bytes INTEGER NOT NULL,
                            creator TEXT NOT NULL,
                            parent_artifact_uri TEXT,
                            metadata TEXT NOT NULL
                        );
                    """)
            finally:
                self._close_connection(conn)

    def save_artifact_metadata(self, metadata: ArtifactMetadata) -> None:
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    conn.execute(
                        """
                        INSERT INTO artifacts_metadata (uri, checksum, mime_type, size_bytes, creator, parent_artifact_uri, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(uri) DO UPDATE SET
                            checksum = excluded.checksum,
                            mime_type = excluded.mime_type,
                            size_bytes = excluded.size_bytes,
                            creator = excluded.creator,
                            parent_artifact_uri = excluded.parent_artifact_uri,
                            metadata = excluded.metadata;
                        """,
                        (metadata.uri, metadata.checksum, metadata.mime_type, metadata.size_bytes, metadata.creator, metadata.parent_artifact_uri, json.dumps(metadata.metadata))
                    )
            finally:
                self._close_connection(conn)

    def get_artifact_metadata(self, uri: str) -> Optional[ArtifactMetadata]:
        with self._lock:
            conn = self._get_connection()
            try:
                row = conn.execute("SELECT uri, checksum, mime_type, size_bytes, creator, parent_artifact_uri, metadata FROM artifacts_metadata WHERE uri = ?", (uri,)).fetchone()
                if row:
                    return ArtifactMetadata(
                        uri=row["uri"],
                        checksum=row["checksum"],
                        mime_type=row["mime_type"],
                        size_bytes=row["size_bytes"],
                        creator=row["creator"],
                        parent_artifact_uri=row["parent_artifact_uri"],
                        metadata=json.loads(row["metadata"])
                    )
                return None
            finally:
                self._close_connection(conn)

class LocalFileSystemBlobRepository(BlobRepository):
    """
    Managed Directory Blob storage engine.
    """
    def __init__(self, storage_dir: str = "/tmp/agentforge_blobs") -> None:
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)

    def save_blob(self, key: str, file_path: str) -> str:
        dest_path = os.path.join(self.storage_dir, key)
        shutil.copy2(file_path, dest_path)
        return f"blob://{key}"

    def get_blob_path(self, key: str) -> Optional[str]:
        dest_path = os.path.join(self.storage_dir, key)
        if os.path.exists(dest_path):
            return dest_path
        return None

class SQLiteSettingsRepository(SettingsRepository):
    """
    Thread-safe SQLite key-value settings store.
    """
    def __init__(self, db_path: str = ":memory:") -> None:
        self.db_path = db_path
        self._lock = threading.Lock()
        self._shared_conn = None
        if self.db_path == ":memory:":
            self._shared_conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._shared_conn.row_factory = sqlite3.Row
        self._initialize_db()

    def _get_connection(self) -> sqlite3.Connection:
        if self._shared_conn:
            return self._shared_conn
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _close_connection(self, conn: sqlite3.Connection) -> None:
        if conn is not self._shared_conn:
            conn.close()

    def _initialize_db(self) -> None:
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS settings (
                            key TEXT PRIMARY KEY,
                            value TEXT NOT NULL
                        );
                    """)
            finally:
                self._close_connection(conn)

    def set_setting(self, key: str, value: Any) -> None:
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    conn.execute(
                        "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value;",
                        (key, json.dumps(value))
                    )
            finally:
                self._close_connection(conn)

    def get_setting(self, key: str) -> Optional[Any]:
        with self._lock:
            conn = self._get_connection()
            try:
                row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
                if row:
                    return json.loads(row["value"])
                return None
            finally:
                self._close_connection(conn)

class InMemoryVectorRepository(VectorRepository):
    """
    In-memory Mock Vector DB for embeddings queries.
    """
    def __init__(self) -> None:
        self._store = []

    def store_vector(self, uri: str, vector: List[float], metadata: Dict[str, Any]) -> None:
        self._store.append({"uri": uri, "vector": vector, "metadata": metadata})

    def search_similar(self, query_vector: List[float], limit: int = 5) -> List[Dict[str, Any]]:
        # Dummy Cosine similarity/identity match fallback
        return self._store[:limit]

class SurrealDBGraphRepository(GraphRepository):
    """
    Zero-dependency HTTP/JSON-RPC client for SurrealDB 2.0+ Graph Database execution.
    Converts relationships directly into native graph edges.
    """
    def __init__(
        self,
        url: str = "http://localhost:8000",
        username: str = "root",
        password: str = "root",
        namespace: str = "agentforge",
        database: str = "core"
    ) -> None:
        self.url = url.rstrip("/")
        self.username = username
        self.password = password
        self.namespace = namespace
        self.database = database
        self._auth_header = "Basic " + base64.b64encode(f"{username}:{password}".encode()).decode()

    def _query(self, sql: str, vars: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        url = f"{self.url}/sql"
        headers = {
            "Accept": "application/json",
            "Content-Type": "text/plain",
            "Authorization": self._auth_header,
            "NS": self.namespace,
            "DB": self.database
        }
        
        req = urllib.request.Request(url, data=sql.encode("utf-8"), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                res_body = response.read().decode("utf-8")
                res_data = json.loads(res_body)
                results = []
                for stmt_res in res_data:
                    if stmt_res.get("status") == "ERR":
                        raise ValueError(f"SurrealDB Error: {stmt_res.get('result')}")
                    results.append(stmt_res.get("result", []))
                return results
        except urllib.error.URLError as e:
            raise ConnectionError(f"Failed to connect to SurrealDB at {self.url}: {e}")

    def _escape_uri(self, uri: str) -> str:
        return f"entity:⟨{uri}⟩"

    def save_entity(self, entity: Entity) -> None:
        escaped_id = self._escape_uri(entity.uri)
        payload = {
            "uri": entity.uri,
            "type": entity.type,
            "metadata": entity.metadata,
            "version": entity.version
        }
        sql_with_content = f"UPDATE {escaped_id} CONTENT {json.dumps(payload)};"
        self._query(sql_with_content)

    def get_entity(self, uri: str) -> Optional[Entity]:
        escaped_id = self._escape_uri(uri)
        sql = f"SELECT * FROM {escaped_id};"
        try:
            res = self._query(sql)
            if res and res[0]:
                record = res[0][0]
                return Entity(
                    uri=record["uri"],
                    type=record["type"],
                    metadata=record.get("metadata", {}),
                    version=record.get("version", 1)
                )
        except Exception:
            return None
        return None

    def delete_entity(self, uri: str) -> None:
        escaped_id = self._escape_uri(uri)
        sql = f"DELETE {escaped_id};"
        self._query(sql)

    def relate_entities(self, source_uri: str, target_uri: str, relationship: str) -> None:
        src = self._escape_uri(source_uri)
        dst = self._escape_uri(target_uri)
        sql = f"RELATE {src}->{relationship}->{dst} UNIQUE;"
        self._query(sql)

    def unrelate_entities(self, source_uri: str, target_uri: str, relationship: str) -> None:
        src = self._escape_uri(source_uri)
        dst = self._escape_uri(target_uri)
        sql = f"DELETE {relationship} WHERE in = {src} AND out = {dst};"
        self._query(sql)

    def get_related_entities(self, source_uri: str, relationship: str) -> List[Entity]:
        src = self._escape_uri(source_uri)
        sql = f"SELECT * FROM (SELECT ->{relationship}->entity AS targets FROM {src}).targets;"
        try:
            res = self._query(sql)
            if res and res[0]:
                records = res[0]
                results = []
                for record in records:
                    if record and isinstance(record, dict) and "uri" in record:
                        results.append(Entity(
                            uri=record["uri"],
                            type=record["type"],
                            metadata=record.get("metadata", {}),
                            version=record.get("version", 1)
                        ))
                return results
        except Exception:
            return []
        return []
