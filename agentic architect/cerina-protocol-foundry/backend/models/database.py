"""
Cerina Protocol Foundry - Database Models and Setup
Supports both SQLite (development) and PostgreSQL (production)
"""

import os
import uuid
from datetime import datetime
from typing import Optional, Generator
from contextlib import contextmanager

from sqlalchemy import (
    create_engine,
    Column,
    String,
    Text,
    Float,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
    Index,
    event,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.pool import StaticPool


# Configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./cerina_foundry.db"
)

# Determine if we're using SQLite or PostgreSQL
IS_SQLITE = DATABASE_URL.startswith("sqlite")

# Create engine with appropriate settings
if IS_SQLITE:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=os.getenv("SQL_DEBUG", "false").lower() == "true"
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        echo=os.getenv("SQL_DEBUG", "false").lower() == "true"
    )

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def generate_uuid() -> str:
    """Generate a UUID string."""
    return str(uuid.uuid4())


class Protocol(Base):
    """Main protocol table - stores CBT protocols."""
    __tablename__ = "protocols"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    thread_id = Column(String(36), nullable=False, index=True)
    user_intent = Column(Text, nullable=False)
    additional_context = Column(Text, nullable=True)
    final_protocol = Column(Text, nullable=True)
    current_draft = Column(Text, nullable=True)
    status = Column(String(50), default="drafting", index=True)
    safety_score = Column(Float, default=10.0)
    clinical_score = Column(Float, default=0.0)
    empathy_scores = Column(JSON, nullable=True)
    iteration_count = Column(Integer, default=0)
    max_iterations = Column(Integer, default=5)
    agent_notes = Column(JSON, nullable=True)

    # Human review fields
    approved_by = Column(String(255), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    human_feedback = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    versions = relationship("ProtocolVersion", back_populates="protocol", cascade="all, delete-orphan")
    safety_flags = relationship("SafetyFlagDB", back_populates="protocol", cascade="all, delete-orphan")
    feedback = relationship("AgentFeedback", back_populates="protocol", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="protocol", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Protocol(id={self.id}, status={self.status})>"


class ProtocolVersion(Base):
    """Versioned drafts of protocols."""
    __tablename__ = "protocol_versions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    protocol_id = Column(String(36), ForeignKey("protocols.id", ondelete="CASCADE"), nullable=False)
    version_number = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    agent_source = Column(String(100), nullable=False)
    changes_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    protocol = relationship("Protocol", back_populates="versions")

    # Index for efficient version queries
    __table_args__ = (
        Index("idx_protocol_version", "protocol_id", "version_number"),
    )

    def __repr__(self):
        return f"<ProtocolVersion(protocol_id={self.protocol_id}, v={self.version_number})>"


class SafetyFlagDB(Base):
    """Safety flags raised during protocol review."""
    __tablename__ = "safety_flags"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    protocol_id = Column(String(36), ForeignKey("protocols.id", ondelete="CASCADE"), nullable=False)
    flag_type = Column(String(100), nullable=False)
    severity = Column(String(20), nullable=False)
    details = Column(Text, nullable=False)
    location = Column(Text, nullable=True)
    resolved = Column(Boolean, default=False)
    resolution_notes = Column(Text, nullable=True)
    flagged_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    # Relationship
    protocol = relationship("Protocol", back_populates="safety_flags")

    # Index for unresolved flags
    __table_args__ = (
        Index("idx_unresolved_flags", "protocol_id", "resolved"),
    )

    def __repr__(self):
        return f"<SafetyFlag(type={self.flag_type}, severity={self.severity})>"


class AgentFeedback(Base):
    """Feedback from various agents."""
    __tablename__ = "agent_feedback"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    protocol_id = Column(String(36), ForeignKey("protocols.id", ondelete="CASCADE"), nullable=False)
    agent_name = Column(String(100), nullable=False)
    feedback_type = Column(String(50), nullable=True)  # critique, suggestion, etc.
    category = Column(String(100), nullable=True)
    feedback = Column(Text, nullable=False)
    score = Column(Float, nullable=True)
    iteration = Column(Integer, nullable=False)
    suggestions = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    protocol = relationship("Protocol", back_populates="feedback")

    # Index for agent queries
    __table_args__ = (
        Index("idx_agent_feedback", "protocol_id", "agent_name", "iteration"),
    )

    def __repr__(self):
        return f"<AgentFeedback(agent={self.agent_name}, score={self.score})>"


class Checkpoint(Base):
    """LangGraph checkpoints for state persistence and resumability."""
    __tablename__ = "checkpoints"

    thread_id = Column(String(36), primary_key=True)
    checkpoint_id = Column(String(36), primary_key=True)
    parent_checkpoint_id = Column(String(36), nullable=True)
    checkpoint_data = Column(JSON, nullable=False)
    checkpoint_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Index for parent lookups
    __table_args__ = (
        Index("idx_checkpoint_parent", "thread_id", "parent_checkpoint_id"),
        Index("idx_checkpoint_created", "thread_id", "created_at"),
    )

    def __repr__(self):
        return f"<Checkpoint(thread={self.thread_id}, id={self.checkpoint_id})>"


class AuditLog(Base):
    """Complete audit trail of all system actions."""
    __tablename__ = "audit_log"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    protocol_id = Column(String(36), ForeignKey("protocols.id", ondelete="SET NULL"), nullable=True)
    thread_id = Column(String(36), nullable=True, index=True)
    action = Column(String(100), nullable=False)
    actor = Column(String(255), nullable=False)  # "system", "agent:name", "human:user_id"
    details = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationship
    protocol = relationship("Protocol", back_populates="audit_logs")

    def __repr__(self):
        return f"<AuditLog(action={self.action}, actor={self.actor})>"


class DebateHistory(Base):
    """History of agent debates and discussions."""
    __tablename__ = "debate_history"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    protocol_id = Column(String(36), ForeignKey("protocols.id", ondelete="CASCADE"), nullable=False)
    from_agent = Column(String(100), nullable=False)
    to_agent = Column(String(100), nullable=True)  # None = broadcast
    message = Column(Text, nullable=False)
    message_type = Column(String(50), nullable=False)  # critique, suggestion, etc.
    iteration = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_debate_protocol", "protocol_id", "iteration"),
    )

    def __repr__(self):
        return f"<DebateHistory(from={self.from_agent}, type={self.message_type})>"


# Database initialization and session management

def init_db():
    """Initialize the database, creating all tables."""
    Base.metadata.create_all(bind=engine)


def drop_db():
    """Drop all tables - use with caution!"""
    Base.metadata.drop_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for FastAPI to get database sessions.
    Yields a session and ensures cleanup.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager for getting database sessions outside of FastAPI.
    Use this in agents and background tasks.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# SQLite-specific: Enable foreign keys
if IS_SQLITE:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


# Repository functions for common operations

class ProtocolRepository:
    """Repository for Protocol CRUD operations."""

    @staticmethod
    def create(db: Session, user_intent: str, thread_id: str, **kwargs) -> Protocol:
        """Create a new protocol."""
        protocol = Protocol(
            thread_id=thread_id,
            user_intent=user_intent,
            **kwargs
        )
        db.add(protocol)
        db.commit()
        db.refresh(protocol)
        return protocol

    @staticmethod
    def get_by_id(db: Session, protocol_id: str) -> Optional[Protocol]:
        """Get protocol by ID."""
        return db.query(Protocol).filter(Protocol.id == protocol_id).first()

    @staticmethod
    def get_by_thread_id(db: Session, thread_id: str) -> Optional[Protocol]:
        """Get protocol by thread ID."""
        return db.query(Protocol).filter(Protocol.thread_id == thread_id).first()

    @staticmethod
    def get_all(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None
    ) -> list[Protocol]:
        """Get all protocols with optional filtering."""
        query = db.query(Protocol)
        if status:
            query = query.filter(Protocol.status == status)
        return query.order_by(Protocol.created_at.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def update(db: Session, protocol_id: str, **kwargs) -> Optional[Protocol]:
        """Update a protocol."""
        protocol = db.query(Protocol).filter(Protocol.id == protocol_id).first()
        if protocol:
            for key, value in kwargs.items():
                setattr(protocol, key, value)
            protocol.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(protocol)
        return protocol

    @staticmethod
    def delete(db: Session, protocol_id: str) -> bool:
        """Delete a protocol."""
        protocol = db.query(Protocol).filter(Protocol.id == protocol_id).first()
        if protocol:
            db.delete(protocol)
            db.commit()
            return True
        return False


class CheckpointRepository:
    """Repository for checkpoint operations."""

    @staticmethod
    def save(
        db: Session,
        thread_id: str,
        checkpoint_id: str,
        checkpoint_data: dict,
        parent_checkpoint_id: Optional[str] = None,
        checkpoint_metadata: Optional[dict] = None
    ) -> Checkpoint:
        """Save a checkpoint."""
        checkpoint = Checkpoint(
            thread_id=thread_id,
            checkpoint_id=checkpoint_id,
            parent_checkpoint_id=parent_checkpoint_id,
            checkpoint_data=checkpoint_data,
            checkpoint_metadata=checkpoint_metadata
        )
        db.add(checkpoint)
        db.commit()
        db.refresh(checkpoint)
        return checkpoint

    @staticmethod
    def get_latest(db: Session, thread_id: str) -> Optional[Checkpoint]:
        """Get the latest checkpoint for a thread."""
        return (
            db.query(Checkpoint)
            .filter(Checkpoint.thread_id == thread_id)
            .order_by(Checkpoint.created_at.desc())
            .first()
        )

    @staticmethod
    def get_by_id(db: Session, thread_id: str, checkpoint_id: str) -> Optional[Checkpoint]:
        """Get a specific checkpoint."""
        return (
            db.query(Checkpoint)
            .filter(
                Checkpoint.thread_id == thread_id,
                Checkpoint.checkpoint_id == checkpoint_id
            )
            .first()
        )

    @staticmethod
    def get_history(db: Session, thread_id: str) -> list[Checkpoint]:
        """Get all checkpoints for a thread in order."""
        return (
            db.query(Checkpoint)
            .filter(Checkpoint.thread_id == thread_id)
            .order_by(Checkpoint.created_at.asc())
            .all()
        )


class AuditLogRepository:
    """Repository for audit log operations."""

    @staticmethod
    def log(
        db: Session,
        action: str,
        actor: str,
        protocol_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        details: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditLog:
        """Create an audit log entry."""
        log_entry = AuditLog(
            action=action,
            actor=actor,
            protocol_id=protocol_id,
            thread_id=thread_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        return log_entry

    @staticmethod
    def get_for_protocol(db: Session, protocol_id: str) -> list[AuditLog]:
        """Get all audit logs for a protocol."""
        return (
            db.query(AuditLog)
            .filter(AuditLog.protocol_id == protocol_id)
            .order_by(AuditLog.created_at.desc())
            .all()
        )
