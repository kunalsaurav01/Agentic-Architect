"""
Cerina Protocol Foundry - Custom Checkpointer for LangGraph
Provides persistence and resumability for the multi-agent workflow.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Optional, Iterator, Tuple, List
from contextlib import contextmanager

from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
)

from backend.models.database import (
    SessionLocal,
    Checkpoint as CheckpointDB,
    get_db_session,
)


class CerinaCheckpointer(BaseCheckpointSaver):
    """
    Custom checkpointer that persists LangGraph state to the database.
    Enables full resumability and crash recovery.
    """

    def __init__(self):
        super().__init__()
        self.serde = None  # Use JSON serialization directly

    def _serialize(self, data: Any) -> str:
        """Serialize checkpoint data to JSON string."""
        return json.dumps(data, default=str)

    def _deserialize(self, data: str) -> Any:
        """Deserialize checkpoint data from JSON string."""
        return json.loads(data)

    def get_tuple(self, config: dict) -> Optional[CheckpointTuple]:
        """
        Get a checkpoint tuple by config.

        Args:
            config: Configuration dict with thread_id and optionally checkpoint_id

        Returns:
            CheckpointTuple if found, None otherwise
        """
        thread_id = config.get("configurable", {}).get("thread_id")
        checkpoint_id = config.get("configurable", {}).get("checkpoint_id")

        if not thread_id:
            return None

        with get_db_session() as db:
            if checkpoint_id:
                # Get specific checkpoint
                checkpoint = (
                    db.query(CheckpointDB)
                    .filter(
                        CheckpointDB.thread_id == thread_id,
                        CheckpointDB.checkpoint_id == checkpoint_id
                    )
                    .first()
                )
            else:
                # Get latest checkpoint
                checkpoint = (
                    db.query(CheckpointDB)
                    .filter(CheckpointDB.thread_id == thread_id)
                    .order_by(CheckpointDB.created_at.desc())
                    .first()
                )

            if not checkpoint:
                return None

            # Reconstruct the checkpoint tuple
            checkpoint_data = checkpoint.checkpoint_data
            if isinstance(checkpoint_data, str):
                checkpoint_data = self._deserialize(checkpoint_data)

            metadata = checkpoint.checkpoint_metadata or {}
            if isinstance(metadata, str):
                metadata = json.loads(metadata)

            return CheckpointTuple(
                config={
                    "configurable": {
                        "thread_id": thread_id,
                        "checkpoint_id": checkpoint.checkpoint_id,
                    }
                },
                checkpoint=checkpoint_data,
                metadata=CheckpointMetadata(**metadata) if metadata else CheckpointMetadata(),
                parent_config={
                    "configurable": {
                        "thread_id": thread_id,
                        "checkpoint_id": checkpoint.parent_checkpoint_id,
                    }
                } if checkpoint.parent_checkpoint_id else None,
            )

    def list(
        self,
        config: Optional[dict] = None,
        *,
        filter: Optional[dict] = None,
        before: Optional[dict] = None,
        limit: Optional[int] = None,
    ) -> Iterator[CheckpointTuple]:
        """
        List checkpoints for a thread.

        Args:
            config: Configuration with thread_id
            filter: Optional filter criteria
            before: Get checkpoints before this one
            limit: Maximum number to return

        Yields:
            CheckpointTuple objects
        """
        thread_id = config.get("configurable", {}).get("thread_id") if config else None

        with get_db_session() as db:
            query = db.query(CheckpointDB)

            if thread_id:
                query = query.filter(CheckpointDB.thread_id == thread_id)

            if before:
                before_id = before.get("configurable", {}).get("checkpoint_id")
                if before_id:
                    before_checkpoint = (
                        db.query(CheckpointDB)
                        .filter(
                            CheckpointDB.thread_id == thread_id,
                            CheckpointDB.checkpoint_id == before_id
                        )
                        .first()
                    )
                    if before_checkpoint:
                        query = query.filter(
                            CheckpointDB.created_at < before_checkpoint.created_at
                        )

            query = query.order_by(CheckpointDB.created_at.desc())

            if limit:
                query = query.limit(limit)

            for checkpoint in query.all():
                checkpoint_data = checkpoint.checkpoint_data
                if isinstance(checkpoint_data, str):
                    checkpoint_data = self._deserialize(checkpoint_data)

                metadata = checkpoint.checkpoint_metadata or {}
                if isinstance(metadata, str):
                    metadata = json.loads(metadata)

                yield CheckpointTuple(
                    config={
                        "configurable": {
                            "thread_id": checkpoint.thread_id,
                            "checkpoint_id": checkpoint.checkpoint_id,
                        }
                    },
                    checkpoint=checkpoint_data,
                    metadata=CheckpointMetadata(**metadata) if metadata else CheckpointMetadata(),
                    parent_config={
                        "configurable": {
                            "thread_id": checkpoint.thread_id,
                            "checkpoint_id": checkpoint.parent_checkpoint_id,
                        }
                    } if checkpoint.parent_checkpoint_id else None,
                )

    def put(
        self,
        config: dict,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: Optional[dict] = None,
    ) -> dict:
        """
        Save a checkpoint.

        Args:
            config: Configuration with thread_id
            checkpoint: The checkpoint data to save
            metadata: Checkpoint metadata
            new_versions: Optional new channel versions

        Returns:
            Updated config with new checkpoint_id
        """
        thread_id = config.get("configurable", {}).get("thread_id")
        parent_checkpoint_id = config.get("configurable", {}).get("checkpoint_id")

        if not thread_id:
            thread_id = str(uuid.uuid4())

        new_checkpoint_id = str(uuid.uuid4())

        # Serialize the checkpoint data
        serialized_checkpoint = checkpoint
        if not isinstance(checkpoint, (str, dict)):
            serialized_checkpoint = self._serialize(checkpoint)

        # Serialize metadata
        serialized_metadata = {}
        if metadata:
            serialized_metadata = {
                "source": metadata.source if hasattr(metadata, "source") else "update",
                "step": metadata.step if hasattr(metadata, "step") else 0,
                "writes": metadata.writes if hasattr(metadata, "writes") else None,
            }

        with get_db_session() as db:
            checkpoint_record = CheckpointDB(
                thread_id=thread_id,
                checkpoint_id=new_checkpoint_id,
                parent_checkpoint_id=parent_checkpoint_id,
                checkpoint_data=serialized_checkpoint,
                checkpoint_metadata=serialized_metadata,
            )
            db.add(checkpoint_record)
            db.commit()

        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_id": new_checkpoint_id,
            }
        }

    def put_writes(
        self,
        config: dict,
        writes: List[Tuple[str, Any]],
        task_id: str,
    ) -> None:
        """
        Save pending writes for a checkpoint.
        This is used for intermediate state during node execution.

        Args:
            config: Configuration with thread_id and checkpoint_id
            writes: List of (channel, value) tuples to write
            task_id: ID of the current task
        """
        # For simplicity, we handle writes in the main put() call
        # This method can be enhanced for more granular write tracking
        pass

    def delete_thread(self, thread_id: str) -> None:
        """
        Delete all checkpoints for a thread.

        Args:
            thread_id: Thread ID to delete
        """
        with get_db_session() as db:
            db.query(CheckpointDB).filter(
                CheckpointDB.thread_id == thread_id
            ).delete()
            db.commit()

    def get_latest_checkpoint_id(self, thread_id: str) -> Optional[str]:
        """
        Get the ID of the latest checkpoint for a thread.

        Args:
            thread_id: Thread ID to query

        Returns:
            Latest checkpoint ID or None
        """
        with get_db_session() as db:
            checkpoint = (
                db.query(CheckpointDB)
                .filter(CheckpointDB.thread_id == thread_id)
                .order_by(CheckpointDB.created_at.desc())
                .first()
            )
            return checkpoint.checkpoint_id if checkpoint else None

    def get_checkpoint_count(self, thread_id: str) -> int:
        """
        Get the number of checkpoints for a thread.

        Args:
            thread_id: Thread ID to query

        Returns:
            Number of checkpoints
        """
        with get_db_session() as db:
            return (
                db.query(CheckpointDB)
                .filter(CheckpointDB.thread_id == thread_id)
                .count()
            )
