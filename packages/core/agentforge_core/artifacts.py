import hashlib
import os
from typing import Dict, Any, Optional
from agentforge_core.di import get_container
from agentforge_core.storage import (
    ArtifactMetadata,
    ArtifactRepository,
    BlobRepository
)

class ArtifactManager:
    """
    Manager governing execution artifacts (files).
    Computes checksums, registers paths in BlobRepository, and records metadata traces.
    """
    def __init__(
        self,
        artifact_repo: Optional[ArtifactRepository] = None,
        blob_repo: Optional[BlobRepository] = None
    ) -> None:
        self._artifact_repo = artifact_repo
        self._blob_repo = blob_repo

    def _get_artifact_repo(self) -> ArtifactRepository:
        if self._artifact_repo:
            return self._artifact_repo
        return get_container().resolve(ArtifactRepository)

    def _get_blob_repo(self) -> BlobRepository:
        if self._blob_repo:
            return self._blob_repo
        return get_container().resolve(BlobRepository)

    def _compute_checksum(self, file_path: str) -> str:
        """
        Calculates SHA-256 hash of file content.
        """
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def register_file(
        self,
        file_path: str,
        mime_type: str,
        creator: str,
        parent_artifact_uri: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ArtifactMetadata:
        """
        Hashes local file content, copies it to blob store, logs metadata records,
        and returns the canonical ArtifactMetadata model.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found for artifact registration: {file_path}")

        checksum = self._compute_checksum(file_path)
        size_bytes = os.path.getsize(file_path)
        uri = f"artifact://{checksum}"

        # 1. Copy binary content into managed BlobRepository
        blob_repo = self._get_blob_repo()
        blob_repo.save_blob(checksum, file_path)

        # 2. Record artifact entry traces in metadata repository
        meta = ArtifactMetadata(
            uri=uri,
            checksum=checksum,
            mime_type=mime_type,
            size_bytes=size_bytes,
            creator=creator,
            parent_artifact_uri=parent_artifact_uri,
            metadata=metadata or {}
        )
        self._get_artifact_repo().save_artifact_metadata(meta)

        return meta

    def get_artifact(self, uri: str) -> Optional[ArtifactMetadata]:
        return self._get_artifact_repo().get_artifact_metadata(uri)

    def get_local_path(self, uri: str) -> Optional[str]:
        """
        Retrieves the absolute local filesystem path of the registered artifact blob.
        """
        if not uri.startswith("artifact://"):
            return None
        checksum = uri.split("artifact://")[1]
        return self._get_blob_repo().get_blob_path(checksum)
