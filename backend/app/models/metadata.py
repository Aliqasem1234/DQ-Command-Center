from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Enum, Float
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from app.database import Base
import uuid
from datetime import datetime
import enum


class DataType(str, enum.Enum):
    """Data types for metadata"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    TIMESTAMP = "timestamp"
    JSON = "json"
    BINARY = "binary"
    ARRAY = "array"
    OBJECT = "object"
    UNKNOWN = "unknown"


class Metadata(Base):
    """Detailed metadata for data assets"""
    __tablename__ = "metadata"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    data_asset_id = Column(UUID(as_uuid=True), ForeignKey("data_assets.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    
    # Basic metadata
    display_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    data_type = Column(Enum(DataType), nullable=False)
    
    # Field-level metadata
    nullable = Column(Boolean, default=True, nullable=False)
    default_value = Column(String(255), nullable=True)
    column_position = Column(Integer, nullable=True)
    is_primary_key = Column(Boolean, default=False, nullable=False)
    is_foreign_key = Column(Boolean, default=False, nullable=False)
    
    # Statistics and profiling
    value_count = Column(Integer, nullable=True)
    null_count = Column(Integer, nullable=True)
    unique_count = Column(Integer, nullable=True)
    duplicate_count = Column(Integer, nullable=True)
    min_value = Column(String(255), nullable=True)
    max_value = Column(String(255), nullable=True)
    average_length = Column(Float, nullable=True)
    
    # Quality metrics
    completeness_score = Column(Float, nullable=True)
    validity_score = Column(Float, nullable=True)
    uniqueness_score = Column(Float, nullable=True)
    
    # Business metadata
    business_term = Column(String(255), nullable=True)
    business_definition = Column(Text, nullable=True)
    steward_notes = Column(Text, nullable=True)
    example_values = Column(JSON, nullable=True)
    
    # Technical metadata
    format_validation = Column(String(255), nullable=True)
    allowed_values = Column(JSON, nullable=True)
    regex_pattern = Column(String(500), nullable=True)
    
    # Audit
    last_profiled = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(datetime.now().astimezone().tzinfo))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(datetime.now().astimezone().tzinfo))
    
    # Relationships
    data_asset = relationship("DataAsset")

    def __repr__(self):
        return f"<Metadata {self.display_name}>"


class MetadataTag(Base):
    """Tags for organizing and categorizing metadata"""
    __tablename__ = "metadata_tags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    metadata_id = Column(UUID(as_uuid=True), ForeignKey("metadata.id", ondelete="CASCADE"), nullable=False, index=True)
    tag = Column(String(100), nullable=False)
    category = Column(String(100), nullable=True, index=True)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(datetime.now().astimezone().tzinfo))
    
    metadata = relationship("Metadata")

    def __repr__(self):
        return f"<MetadataTag {self.tag}>"
