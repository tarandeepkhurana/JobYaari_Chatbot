from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, Column, Integer, Float, Text, TIMESTAMP, ARRAY, Index, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB, TSVECTOR
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func
import uuid


class Base(DeclarativeBase):
    pass


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        Index("idx_jobs_source", "source"),
        Index("idx_jobs_job_type", "job_type"),
        Index("idx_jobs_work_mode", "work_mode"),
        Index("idx_jobs_remote", "remote"),
        Index("idx_jobs_posted_at", "posted_at"),
        Index("idx_jobs_is_active", "is_active"),
        Index("idx_jobs_skills", "skills", postgresql_using="gin"),
        Index("idx_jobs_categories", "categories", postgresql_using="gin"),
        Index("idx_jobs_eligibility", "eligibility", postgresql_using="gin"),
        Index("idx_jobs_cities", "cities", postgresql_using="gin"),
        Index(
            "idx_jobs_embedding",
            "embedding",
            postgresql_using="ivfflat",
            postgresql_with={"lists": 100},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source               = Column(Text, nullable=False)
    source_job_id        = Column(Text, nullable=False)
    source_url           = Column(Text)
    application_url      = Column(Text)

    title                = Column(Text, nullable=False)
    description          = Column(Text)
    job_type             = Column(Text)
    work_mode            = Column(Text)
    remote               = Column(Boolean, default=False)

    org_name             = Column(Text)
    org_logo_url         = Column(Text)
    org_size             = Column(Text)

    cities               = Column(ARRAY(Text))
    state                = Column(Text)
    country              = Column(Text, default="India")

    salary_min           = Column(Integer)
    salary_max           = Column(Integer)
    salary_currency      = Column(Text, default="INR")
    salary_period        = Column(Text)
    salary_display       = Column(Text)
    is_paid              = Column(Boolean, default=True)

    stipend_min          = Column(Integer)
    stipend_max          = Column(Integer)
    stipend_display      = Column(Text)

    experience_min_years = Column(Float)
    experience_max_years = Column(Float)
    experience_label     = Column(Text)

    duration_display     = Column(Text)
    duration_days        = Column(Integer)

    skills               = Column(ARRAY(Text))
    categories           = Column(ARRAY(Text))
    eligibility          = Column(ARRAY(Text))
    benefits             = Column(ARRAY(Text))
    work_functions       = Column(ARRAY(Text))

    posted_at            = Column(TIMESTAMP(timezone=True))
    expires_at           = Column(TIMESTAMP(timezone=True))
    scraped_at           = Column(TIMESTAMP(timezone=True), server_default=func.now())
    last_updated_at      = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    dedupe_key           = Column(Text, unique=True)
    status               = Column(Text, default="active")
    is_active            = Column(Boolean, default=True)

    embedding_text       = Column(Text)
    embedding            = Column(Vector(1536))
    embedding_model = Column(Text, default="text-embedding-ada-002")

    raw_payload          = Column(JSONB)
    extra_metadata       = Column(JSONB)
    search_vector        = Column(TSVECTOR)
    

class User(Base):
    __tablename__ = "users"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        nullable=False,
        default=uuid.uuid4
    )

    email = Column(Text)

    phone = Column(Text)

    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now()
    )

    last_sign_in_at = Column(
        TIMESTAMP(timezone=True),
        nullable=True
    )

    raw_app_meta_data = Column(JSONB)

    raw_user_meta_data = Column(JSONB)

    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    # Relationship
    chats = relationship(
        "Chat",
        back_populates="user",
        cascade="all, delete-orphan"
    )


class Chat(Base):
    __tablename__ = "chats"

    __table_args__ = (
        Index("idx_chats_user_id", "user_id"),
        Index("idx_chats_created_at", "created_at"),
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Foreign key defined here
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True
    )

    title = Column(
        Text,
        nullable=False
    )

    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now()
    )

    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    conversation_summary = Column(
        Text,
        nullable=True
    )

    summary_updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=True
    )

    summary_message_count = Column(
        Integer,
        default=0
    )
    
    retrieved_jobs = Column(
        JSONB,
        nullable=True
    )

    last_retrieval_query = Column(
        Text,
        nullable=True
    )

    last_retrieval_filters = Column(
        JSONB,
        nullable=True
    )

    retrieval_updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=True
    )
    
    # Relationship
    user = relationship(
        "User",
        back_populates="chats"
    )


class Message(Base):
    __tablename__ = "messages"

    __table_args__ = (
        Index("idx_messages_chat_id", "chat_id"),
        Index("idx_messages_created_at", "created_at"),
        Index("idx_messages_message_type", "message_type"),
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    chat_id = Column(
        UUID(as_uuid=True),
        ForeignKey("chats.id", ondelete="CASCADE"),
        nullable=False
    )

    message_type = Column(
        Text,
        nullable=False
    )
    # "user" | "assistant" | "system"

    content = Column(
        Text,
        nullable=False
    )

    retrieved_jobs = Column(
        JSONB,
        nullable=True
    )

    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now()
    )

    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    # Optional ORM relationship
    chat = relationship(
        "Chat",
        backref="messages"
    )


class Resume(Base):
    __tablename__ = "resumes"

    __table_args__ = (
        Index("uq_resumes_user_id", "user_id", unique=True),
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True
    )

    resume_text = Column(Text)

    parsed_data = Column(JSONB)

    embedding = Column(Vector(1536))

    file_name = Column(Text)

    file_mime_type = Column(Text)

    file_size_bytes = Column(Integer)

    storage_bucket = Column(Text)

    storage_path = Column(Text)

    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now()
    )

    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    intents = relationship(
        "ResumeIntent",
        back_populates="resume",
        cascade="all, delete-orphan",
    )


class ResumeIntent(Base):
    __tablename__ = "resume_intents"

    __table_args__ = (
        UniqueConstraint(
            "resume_id",
            "position",
            name="uq_resume_intents_resume_position",
        ),
        Index("idx_resume_intents_resume_id", "resume_id"),
        Index("idx_resume_intents_user_id", "user_id"),
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    resume_id = Column(
        UUID(as_uuid=True),
        ForeignKey("resumes.id", ondelete="CASCADE"),
        nullable=False,
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    position = Column(
        Integer,
        nullable=False,
    )

    label = Column(
        Text,
        nullable=False,
    )

    query = Column(
        Text,
        nullable=False,
    )

    evidence = Column(JSONB)

    embedding = Column(Vector(1536))

    embedding_model = Column(
        Text,
        default="text-embedding-ada-002",
    )

    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
    )

    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    resume = relationship(
        "Resume",
        back_populates="intents",
    )
