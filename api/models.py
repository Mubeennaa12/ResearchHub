import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Text, Table
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

# Many-to-Many association table for Project Bookmarks
project_document_association = Table(
    "project_document",
    Base.metadata,
    Column("project_id", String(36), ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True),
    Column("document_id", String(36), ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True),
    Column("created_at", DateTime, default=datetime.utcnow)
)


class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    collections = relationship("Collection", back_populates="workspace", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="workspace", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="workspace", cascade="all, delete-orphan")
    facts = relationship("WorkspaceFact", back_populates="workspace", cascade="all, delete-orphan")
    notes = relationship("PersonalNote", back_populates="workspace", cascade="all, delete-orphan")


class WorkspaceFact(Base):
    __tablename__ = "workspace_facts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    fact_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    workspace = relationship("Workspace", back_populates="facts")


class Collection(Base):
    __tablename__ = "collections"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)  # e.g., Papers, GitHub, Datasets, Notes, Videos
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    workspace = relationship("Workspace", back_populates="collections")
    folders = relationship("Folder", back_populates="collection", cascade="all, delete-orphan")


class Folder(Base):
    __tablename__ = "folders"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    collection_id = Column(String(36), ForeignKey("collections.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    collection = relationship("Collection", back_populates="folders")
    documents = relationship("Document", back_populates="folder")


class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    folder_id = Column(String(36), ForeignKey("folders.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(255), nullable=False)
    file_path_or_url = Column(Text, nullable=False)
    source_type = Column(String(50), nullable=False)  # "pdf" | "github" | "youtube" | "web" | "paper" | "note"
    metadata_json = Column(JSON, default=dict)  # Stores properties like page count, git owner, transcript duration, etc.
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    workspace = relationship("Workspace", back_populates="documents")
    folder = relationship("Folder", back_populates="documents")
    projects = relationship("Project", secondary=project_document_association, back_populates="documents")
    notes = relationship("PersonalNote", back_populates="document", cascade="all, delete-orphan")


class Project(Base):
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    workspace = relationship("Workspace", back_populates="projects")
    documents = relationship("Document", secondary=project_document_association, back_populates="projects")
    chat_sessions = relationship("ChatSession", back_populates="project", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    notes = relationship("PersonalNote", back_populates="project", cascade="all, delete-orphan")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(50), nullable=False)  # "user" | "assistant" | "system"
    content = Column(Text, nullable=False)
    citations = Column(JSON, default=list)  # List of cited source documents and positions/pages
    eval_metrics = Column(JSON, default=dict)  # RAGAS metrics: latency, faithfulness, etc.
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    session = relationship("ChatSession", back_populates="messages")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    status = Column(String(50), default="todo")  # "todo" | "in_progress" | "done"
    due_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="tasks")


class PersonalNote(Base):
    __tablename__ = "personal_notes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)  # Markdown text
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    workspace = relationship("Workspace", back_populates="notes")
    project = relationship("Project", back_populates="notes")
    document = relationship("Document", back_populates="notes")
