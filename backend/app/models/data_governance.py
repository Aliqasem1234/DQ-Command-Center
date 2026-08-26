from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Enum, Integer
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from app.database import Base
import uuid
from datetime import datetime
import enum


class ClassificationLevel(str, enum.Enum):
    """Data classification levels"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class GovernanceStatus(str, enum.Enum):
    """Governance status"""
    DRAFT = "draft"
    APPROVED = "approved"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


class DataAsset(Base):
    """Represents a data asset under governance"""
    __tablename__ = "data_assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    business_definition = Column(Text, nullable=True)
    
    # Asset details
    asset_type = Column(String(100), nullable=False, index=True)  # table, field, database, api, file, etc.
    data_source = Column(String(255), nullable=True)
    database_name = Column(String(255), nullable=True)
    table_or_collection = Column(String(255), nullable=True)
    
    # Governance
    classification = Column(Enum(ClassificationLevel), default=ClassificationLevel.INTERNAL, nullable=False)
    status = Column(Enum(GovernanceStatus), default=GovernanceStatus.DRAFT, nullable=False, index=True)
    data_owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    data_steward_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Metadata
    creation_date = Column(DateTime(timezone=True), nullable=True)
    last_modified_date = Column(DateTime(timezone=True), nullable=True)
    retention_days = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Audit
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(datetime.now().astimezone().tzinfo))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(datetime.now().astimezone().tzinfo))
    
    # Relationships
    data_owner = relationship("User", foreign_keys=[data_owner_id])
    data_steward = relationship("User", foreign_keys=[data_steward_id])
    policies = relationship("GovernancePolicy", back_populates="data_asset", cascade="all, delete-orphan")
    quality_rules = relationship("DataQualityRule", foreign_keys="DataQualityRule.data_source")

    def __repr__(self):
        return f"<DataAsset {self.name}>"


class GovernancePolicy(Base):
    """Represents a governance policy"""
    __tablename__ = "governance_policies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Policy association
    data_asset_id = Column(UUID(as_uuid=True), ForeignKey("data_assets.id", ondelete="CASCADE"), nullable=True, index=True)
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id", ondelete="CASCADE"), nullable=True)
    
    # Policy details
    policy_type = Column(String(100), nullable=False, index=True)  # retention, access, quality, privacy, etc.
    policy_definition = Column(JSON, nullable=True)
    
    # Status and dates
    status = Column(Enum(GovernanceStatus), default=GovernanceStatus.DRAFT, nullable=False)
    effective_date = Column(DateTime(timezone=True), nullable=True)
    expiration_date = Column(DateTime(timezone=True), nullable=True)
    
    # Audit
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(datetime.now().astimezone().tzinfo))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(datetime.now().astimezone().tzinfo))
    
    # Relationships
    data_asset = relationship("DataAsset", back_populates="policies")
    department = relationship("Department")
    created_by = relationship("User")

    def __repr__(self):
        return f"<GovernancePolicy {self.name}>"


class DataStewardship(Base):
    """Represents stewardship relationships and responsibilities"""
    __tablename__ = "data_stewardships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    data_asset_id = Column(UUID(as_uuid=True), ForeignKey("data_assets.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id", ondelete="CASCADE"), nullable=True)
    
    # Responsibilities
    responsibility_type = Column(String(100), nullable=False, index=True)  # owner, steward, custodian, etc.
    description = Column(Text, nullable=True)
    
    # Dates
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Audit
    assigned_date = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(datetime.now().astimezone().tzinfo))
    
    # Relationships
    data_asset = relationship("DataAsset")
    user = relationship("User")
    department = relationship("Department")

    def __repr__(self):
        return f"<DataStewardship {self.user_id} -> {self.data_asset_id}>"
