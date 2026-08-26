"""
Professional DQ Command Center Data Hierarchy Models

Establishes clear structure:
DataDomain → Dataset → DataElement → Metadata → Quality Rules → Results → Governance
"""

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Enum, Integer, Float, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from app.database import Base
import uuid
from datetime import datetime
import enum


# Enums
class DatasetType(str, enum.Enum):
    """Types of datasets"""
    TABLE = "table"
    COLLECTION = "collection"
    API = "api"
    FILE = "file"
    STREAM = "stream"
    VIEW = "view"


class ClassificationLevel(str, enum.Enum):
    """Data classification levels"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class GovernanceRole(str, enum.Enum):
    """Governance roles"""
    OWNER = "owner"
    STEWARD = "steward"
    CURATOR = "curator"
    ANALYST = "analyst"


class TrendDirection(str, enum.Enum):
    """Quality trend direction"""
    IMPROVING = "improving"
    STABLE = "stable"
    DEGRADING = "degrading"


class IssueSeverity(str, enum.Enum):
    """Quality issue severity"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IssueStatus(str, enum.Enum):
    """Quality issue status"""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"


class TargetStatus(str, enum.Enum):
    """Quality target status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class GovernancePolicyStatus(str, enum.Enum):
    """Governance policy lifecycle status"""
    DRAFT = "draft"
    APPROVED = "approved"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


class DatasetVersionStatus(str, enum.Enum):
    """Lifecycle status of a single uploaded/derived file version"""
    UPLOADED = "uploaded"
    PROFILING = "profiling"
    PROFILED = "profiled"
    SCANNING = "scanning"
    SCANNED = "scanned"
    CLEANING = "cleaning"
    ERROR = "error"


# Core Hierarchy Models

class DataDomain(Base):
    """Business domain - grouping related datasets"""
    __tablename__ = "data_domains"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    
    # Ownership
    business_owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    domain_steward_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Status
    status = Column(String(50), nullable=False, default="active", index=True)
    
    # Audit
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(datetime.now().astimezone().tzinfo))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(datetime.now().astimezone().tzinfo))
    
    # Relationships
    business_owner = relationship("User", foreign_keys=[business_owner_id])
    domain_steward = relationship("User", foreign_keys=[domain_steward_id])
    datasets = relationship("Dataset", back_populates="domain", cascade="all, delete-orphan")
    governance = relationship("DataGovernance", back_populates="domain", cascade="all, delete-orphan")
    policies = relationship("GovernancePolicy", back_populates="domain", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<DataDomain {self.name}>"


class Dataset(Base):
    """Table, collection, API, or other data source"""
    __tablename__ = "datasets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    business_definition = Column(Text, nullable=True)
    
    # Hierarchy
    domain_id = Column(UUID(as_uuid=True), ForeignKey("data_domains.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Type and location
    dataset_type = Column(Enum(DatasetType, native_enum=False), nullable=False, index=True)
    data_source_system = Column(String(255), nullable=True)  # e.g., "PostgreSQL", "S3", "Salesforce"
    database_name = Column(String(255), nullable=True)
    table_name = Column(String(255), nullable=True)
    
    # Classification
    classification = Column(Enum(ClassificationLevel, native_enum=False), default=ClassificationLevel.INTERNAL)
    
    # Ownership
    data_owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    data_steward_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Metadata
    row_count = Column(Integer, nullable=True)
    last_updated = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), nullable=False, default="active", index=True)
    
    # Audit
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(datetime.now().astimezone().tzinfo))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(datetime.now().astimezone().tzinfo))
    
    # Relationships
    domain = relationship("DataDomain", back_populates="datasets")
    data_owner = relationship("User", foreign_keys=[data_owner_id])
    data_steward = relationship("User", foreign_keys=[data_steward_id])
    elements = relationship("DataElement", back_populates="dataset", cascade="all, delete-orphan")
    quality_rules = relationship("DataQualityRule", back_populates="dataset", cascade="all, delete-orphan")
    quality_check_runs = relationship("QualityCheckRun", back_populates="dataset", cascade="all, delete-orphan")
    quality_issues = relationship("QualityIssue", back_populates="dataset", cascade="all, delete-orphan")
    lineage_sources = relationship("DataLineage", foreign_keys="DataLineage.source_dataset_id", back_populates="source_dataset")
    lineage_targets = relationship("DataLineage", foreign_keys="DataLineage.target_dataset_id", back_populates="target_dataset")
    governance = relationship("DataGovernance", back_populates="dataset", cascade="all, delete-orphan")
    policies = relationship("GovernancePolicy", back_populates="dataset", cascade="all, delete-orphan")
    quality_targets = relationship("QualityTarget", back_populates="dataset")
    versions = relationship(
        "DatasetVersion", back_populates="dataset", cascade="all, delete-orphan",
        foreign_keys="DatasetVersion.dataset_id",
    )

    __table_args__ = (
        UniqueConstraint("domain_id", "name", name="uq_dataset_domain_name"),
    )

    def __repr__(self):
        return f"<Dataset {self.name}>"


class DatasetVersion(Base):
    """One uploaded or derived (cleaned) file for a dataset.

    Versions form a chain: the original upload has source_version_id=None
    and is_original=True; every cleaned version points at the version it
    was produced from. The original file is never mutated - cleaning
    always writes a new version and a new file.
    """
    __tablename__ = "dataset_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)

    # File storage
    file_path = Column(String(500), nullable=False)  # relative to UPLOAD_DIR
    original_filename = Column(String(255), nullable=True)
    file_format = Column(String(20), nullable=False)  # csv, xlsx
    file_size_bytes = Column(Integer, nullable=True)

    # Shape
    row_count = Column(Integer, nullable=True)
    column_count = Column(Integer, nullable=True)

    # Lineage within the dataset's own version chain
    is_original = Column(Boolean, nullable=False, default=False)
    source_version_id = Column(UUID(as_uuid=True), ForeignKey("dataset_versions.id", ondelete="SET NULL"), nullable=True)
    cleaning_operations = Column(JSON, nullable=True)  # list of operations applied to produce this version
    rows_changed = Column(Integer, nullable=True)
    values_changed = Column(Integer, nullable=True)

    # Status + latest known quality score for this version
    status = Column(Enum(DatasetVersionStatus, native_enum=False), nullable=False, default=DatasetVersionStatus.UPLOADED, index=True)
    quality_score = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)

    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(datetime.now().astimezone().tzinfo))

    # Relationships
    dataset = relationship("Dataset", back_populates="versions", foreign_keys=[dataset_id])
    source_version = relationship("DatasetVersion", remote_side=[id], foreign_keys=[source_version_id])
    created_by = relationship("User")

    __table_args__ = (
        UniqueConstraint("dataset_id", "version_number", name="uq_dataset_version_number"),
    )

    def __repr__(self):
        return f"<DatasetVersion {self.dataset_id} v{self.version_number}>"


class DataElement(Base):
    """Field or column within a dataset"""
    __tablename__ = "data_elements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    business_term = Column(String(255), nullable=True)
    business_definition = Column(Text, nullable=True)
    
    # Hierarchy
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Type information
    data_type = Column(String(100), nullable=False)  # string, integer, float, date, datetime, etc.
    column_position = Column(Integer, nullable=True)
    
    # Constraints
    is_primary_key = Column(Boolean, default=False, nullable=False)
    is_foreign_key = Column(Boolean, default=False, nullable=False)
    nullable = Column(Boolean, default=True, nullable=False)
    
    # Classification
    classification = Column(Enum(ClassificationLevel, native_enum=False), default=ClassificationLevel.INTERNAL)
    
    # Ownership
    data_owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Audit
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(datetime.now().astimezone().tzinfo))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(datetime.now().astimezone().tzinfo))
    
    # Relationships
    dataset = relationship("Dataset", back_populates="elements")
    data_owner = relationship("User", foreign_keys=[data_owner_id])
    element_metadata = relationship("DataElementMetadata", back_populates="element", uselist=False, cascade="all, delete-orphan")
    quality_rules = relationship("DataQualityRule", back_populates="element")
    governance = relationship("DataGovernance", back_populates="element", cascade="all, delete-orphan")
    quality_targets = relationship("QualityTarget", back_populates="element")
    
    __table_args__ = (
        UniqueConstraint("dataset_id", "name", name="uq_element_dataset_name"),
        Index("ix_element_dataset_position", "dataset_id", "column_position"),
    )

    def __repr__(self):
        return f"<DataElement {self.name}>"


class DataElementMetadata(Base):
    """Detailed profiling and business metadata for an element"""
    __tablename__ = "data_element_metadata"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    element_id = Column(UUID(as_uuid=True), ForeignKey("data_elements.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    # Business metadata
    sample_values = Column(JSON, nullable=True)
    format_pattern = Column(String(255), nullable=True)
    allowed_values = Column(JSON, nullable=True)
    
    # Profiling statistics
    min_length = Column(Integer, nullable=True)
    max_length = Column(Integer, nullable=True)
    value_count = Column(Integer, nullable=True)
    null_count = Column(Integer, nullable=True)
    unique_count = Column(Integer, nullable=True)
    duplicate_count = Column(Integer, nullable=True)
    min_value = Column(String(255), nullable=True)
    max_value = Column(String(255), nullable=True)
    average_value = Column(Float, nullable=True)
    
    # Profiling history
    last_profiled = Column(DateTime(timezone=True), nullable=True)
    
    # Audit
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(datetime.now().astimezone().tzinfo))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(datetime.now().astimezone().tzinfo))
    
    # Relationships
    element = relationship("DataElement", back_populates="element_metadata")

    def __repr__(self):
        return f"<DataElementMetadata {self.element_id}>"


class DataLineage(Base):
    """Relationships and dependencies between datasets"""
    __tablename__ = "data_lineage"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    target_dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Relationship details
    relationship_type = Column(String(100), nullable=False)  # feed, join, transform, aggregate, etc.
    description = Column(Text, nullable=True)
    
    # Audit
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(datetime.now().astimezone().tzinfo))
    
    # Relationships
    source_dataset = relationship("Dataset", foreign_keys=[source_dataset_id], back_populates="lineage_sources")
    target_dataset = relationship("Dataset", foreign_keys=[target_dataset_id], back_populates="lineage_targets")

    def __repr__(self):
        return f"<DataLineage {self.source_dataset_id} → {self.target_dataset_id}>"


class DataGovernance(Base):
    """Unified governance relationships (replaces scattered ownership fields)"""
    __tablename__ = "data_governance"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Hierarchical assignment (one of domain/dataset/element)
    domain_id = Column(UUID(as_uuid=True), ForeignKey("data_domains.id", ondelete="CASCADE"), nullable=True, index=True)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=True, index=True)
    element_id = Column(UUID(as_uuid=True), ForeignKey("data_elements.id", ondelete="CASCADE"), nullable=True)
    
    # Role and assignment
    role = Column(Enum(GovernanceRole, native_enum=False), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    
    # Details
    responsibility_description = Column(Text, nullable=True)
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Audit
    assigned_date = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(datetime.now().astimezone().tzinfo))
    
    # Relationships
    domain = relationship("DataDomain", back_populates="governance")
    dataset = relationship("Dataset", back_populates="governance")
    element = relationship("DataElement", back_populates="governance")
    user = relationship("User")
    department = relationship("Department")
    
    __table_args__ = (
        Index("ix_governance_role", "role", "is_active"),
    )

    def __repr__(self):
        return f"<DataGovernance {self.user_id} - {self.role}>"


class GovernancePolicy(Base):
    """Governance policy (retention, access, quality, privacy, etc.) scoped to a domain or dataset"""
    __tablename__ = "governance_policies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Scope (one of domain/dataset)
    domain_id = Column(UUID(as_uuid=True), ForeignKey("data_domains.id", ondelete="CASCADE"), nullable=True, index=True)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=True, index=True)

    # Policy details
    policy_type = Column(String(100), nullable=False, index=True)  # retention, access, quality, privacy, etc.
    policy_definition = Column(JSON, nullable=True)

    # Status and dates
    status = Column(Enum(GovernancePolicyStatus, native_enum=False), default=GovernancePolicyStatus.DRAFT, nullable=False, index=True)
    effective_date = Column(DateTime(timezone=True), nullable=True)
    expiration_date = Column(DateTime(timezone=True), nullable=True)

    # Audit
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(datetime.now().astimezone().tzinfo))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(datetime.now().astimezone().tzinfo))

    # Relationships
    domain = relationship("DataDomain", back_populates="policies")
    dataset = relationship("Dataset", back_populates="policies")
    created_by = relationship("User")

    def __repr__(self):
        return f"<GovernancePolicy {self.name}>"


class QualityTarget(Base):
    """Quality goals and SLAs for datasets/elements"""
    __tablename__ = "quality_targets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Target association (dataset or element)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=True, index=True)
    element_id = Column(UUID(as_uuid=True), ForeignKey("data_elements.id", ondelete="CASCADE"), nullable=True)
    
    # Target details
    dimension = Column(String(100), nullable=False, index=True)  # accuracy, completeness, etc.
    target_score = Column(Float, nullable=False)  # e.g., 95.0 (%)
    minimum_score = Column(Float, nullable=False)  # e.g., 90.0 (%)
    sla_hours = Column(Integer, nullable=True)  # Response time SLA
    
    # Status
    status = Column(Enum(TargetStatus, native_enum=False), default=TargetStatus.ACTIVE)
    
    # Audit
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(datetime.now().astimezone().tzinfo))
    
    # Relationships
    dataset = relationship("Dataset", back_populates="quality_targets")
    element = relationship("DataElement", back_populates="quality_targets")

    def __repr__(self):
        return f"<QualityTarget {self.dimension} for {self.dataset_id}>"


class RuleEffectiveness(Base):
    """Tracks effectiveness and trends of quality rules"""
    __tablename__ = "rule_effectiveness"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id = Column(UUID(as_uuid=True), ForeignKey("data_quality_rules.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    # Metrics
    last_30_days_pass_rate = Column(Float, nullable=True)
    last_30_days_fail_rate = Column(Float, nullable=True)
    trend = Column(Enum(TrendDirection, native_enum=False), nullable=True)
    
    # Audit
    last_calculated = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    rule = relationship("DataQualityRule", back_populates="effectiveness")

    def __repr__(self):
        return f"<RuleEffectiveness {self.rule_id}>"


class QualityCheckRun(Base):
    """Record of a complete quality check run for a dataset"""
    __tablename__ = "quality_check_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Execution details
    check_timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # Results summary
    total_rules_executed = Column(Integer, nullable=True)
    rules_passed = Column(Integer, nullable=True)
    rules_failed = Column(Integer, nullable=True)
    overall_pass_rate = Column(Float, nullable=True)
    
    # Status
    status = Column(String(50), nullable=False)  # success, partial, failed
    error_summary = Column(Text, nullable=True)
    
    # Audit
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(datetime.now().astimezone().tzinfo))
    
    # Relationships
    dataset = relationship("Dataset", back_populates="quality_check_runs")

    def __repr__(self):
        return f"<QualityCheckRun {self.dataset_id} - {self.check_timestamp}>"


class QualityIssue(Base):
    """Tracking of ongoing data quality issues"""
    __tablename__ = "quality_issues"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id = Column(UUID(as_uuid=True), ForeignKey("data_quality_rules.id", ondelete="CASCADE"), nullable=False, index=True)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    
    # Issue details
    severity = Column(Enum(IssueSeverity, native_enum=False), nullable=False, index=True)
    status = Column(Enum(IssueStatus, native_enum=False), default=IssueStatus.OPEN, index=True)
    description = Column(Text, nullable=True)
    
    # Tracking
    detected_at = Column(DateTime(timezone=True), nullable=False)
    assigned_to_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    
    # Audit
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(datetime.now().astimezone().tzinfo))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(datetime.now().astimezone().tzinfo))
    
    # Relationships
    rule = relationship("DataQualityRule")
    dataset = relationship("Dataset", back_populates="quality_issues")
    assigned_to = relationship("User")

    def __repr__(self):
        return f"<QualityIssue {self.id} - {self.status}>"
