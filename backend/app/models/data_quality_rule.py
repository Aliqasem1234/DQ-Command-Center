from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Enum, Integer, Float, Index
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from app.database import Base
import uuid
from datetime import datetime
import enum


class DataQualityDimension(str, enum.Enum):
    """Standard data quality dimensions"""
    ACCURACY = "accuracy"
    COMPLETENESS = "completeness"
    CONSISTENCY = "consistency"
    VALIDITY = "validity"
    UNIQUENESS = "uniqueness"
    TIMELINESS = "timeliness"


class RuleSeverity(str, enum.Enum):
    """Rule severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RuleStatus(str, enum.Enum):
    """Rule execution status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DRAFT = "draft"
    ARCHIVED = "archived"


class RuleTargetLevel(str, enum.Enum):
    """Level at which a rule applies"""
    DATASET = "dataset"
    ELEMENT = "element"


class DataQualityRule(Base):
    __tablename__ = "data_quality_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Hierarchy - rules target dataset or element
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=True)
    element_id = Column(UUID(as_uuid=True), ForeignKey("data_elements.id", ondelete="CASCADE"), nullable=True)
    target_level = Column(Enum(RuleTargetLevel, native_enum=False), nullable=True)  # dataset or element
    
    # Rule definition
    dimension = Column(Enum(DataQualityDimension, native_enum=False), nullable=False, index=True)
    rule_type = Column(String(100), nullable=False)  # e.g., "required_field", "duplicate_check", "format_validation"
    severity = Column(Enum(RuleSeverity, native_enum=False), default=RuleSeverity.MEDIUM, nullable=False)
    status = Column(Enum(RuleStatus, native_enum=False), default=RuleStatus.DRAFT, nullable=False, index=True)
    
    # Rule configuration
    rule_definition = Column(JSON, nullable=True)  # Store rule parameters as JSON
    
    # Quality thresholds
    quality_threshold = Column(Float, nullable=True)  # e.g., 95.0 for 95% pass rate
    sla_hours = Column(Integer, nullable=True)  # SLA response time
    
    # Ownership & audit
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Metadata
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(datetime.now().astimezone().tzinfo))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(datetime.now().astimezone().tzinfo))
    
    # Relationships
    dataset = relationship("Dataset", back_populates="quality_rules")
    element = relationship("DataElement", back_populates="quality_rules")
    owner = relationship("User", foreign_keys=[owner_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    results = relationship("DataQualityResult", back_populates="rule", cascade="all, delete-orphan")
    effectiveness = relationship("RuleEffectiveness", back_populates="rule", uselist=False, cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_rule_dataset_element", "dataset_id", "element_id"),
    )

    def __repr__(self):
        return f"<DataQualityRule {self.name}>"


class DataQualityResult(Base):
    __tablename__ = "data_quality_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id = Column(UUID(as_uuid=True), ForeignKey("data_quality_rules.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Execution details
    execution_timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    status = Column(String(50), nullable=False, index=True)  # "passed", "failed", "error"
    
    # Metrics
    records_checked = Column(Integer, nullable=True)
    records_passed = Column(Integer, nullable=True)
    records_failed = Column(Integer, nullable=True)
    execution_duration_ms = Column(Integer, nullable=True)
    
    # Error handling
    error_details = Column(Text, nullable=True)
    error_stack = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(datetime.now().astimezone().tzinfo))
    
    # Relationships
    rule = relationship("DataQualityRule", back_populates="results")

    def __repr__(self):
        return f"<DataQualityResult {self.rule_id} - {self.status}>"
