"""
Comprehensive service for managing the data hierarchy

Handles: DataDomain → Dataset → DataElement → Metadata → Quality Rules
"""

import logging
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.data_hierarchy import (
    DataDomain, Dataset, DataElement, DataElementMetadata, DataLineage,
    DataGovernance, QualityTarget, RuleEffectiveness, QualityCheckRun, QualityIssue,
    DatasetType, ClassificationLevel, GovernanceRole, IssueSeverity, IssueStatus
)
from app.models.data_quality_rule import DataQualityRule
from app.utils.audit_logger import log_audit_action

logger = logging.getLogger(__name__)


class DataHierarchyService:
    """Service for managing the complete data hierarchy"""

    # ===== DOMAIN MANAGEMENT =====

    @staticmethod
    async def create_domain(
        db: AsyncSession,
        name: str,
        description: str = None,
        business_owner_id: UUID = None,
        domain_steward_id: UUID = None,
        current_user_id: UUID = None,
    ) -> DataDomain:
        """Create a new data domain"""
        try:
            domain = DataDomain(
                name=name,
                description=description,
                business_owner_id=business_owner_id,
                domain_steward_id=domain_steward_id,
            )
            db.add(domain)
            await db.flush()

            if current_user_id:
                await log_audit_action(
                    db=db,
                    user_id=current_user_id,
                    action="CREATE",
                    entity_type="DataDomain",
                    entity_id=str(domain.id),
                    entity_name=domain.name,
                )

            await db.commit()
            return domain

        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating domain: {str(e)}")
            raise

    @staticmethod
    async def get_domain(db: AsyncSession, domain_id: UUID) -> DataDomain:
        """Get a domain by ID"""
        result = await db.execute(
            select(DataDomain).where(DataDomain.id == domain_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_domains(
        db: AsyncSession,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[DataDomain], int]:
        """List all domains with pagination"""
        query = select(DataDomain).order_by(desc(DataDomain.created_at))
        
        count_result = await db.execute(
            select(func.count(DataDomain.id))
        )
        total = count_result.scalar() or 0

        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(query)
        return result.scalars().all(), total

    # ===== DATASET MANAGEMENT =====

    @staticmethod
    async def create_dataset(
        db: AsyncSession,
        name: str,
        domain_id: UUID,
        dataset_type: DatasetType,
        description: str = None,
        business_definition: str = None,
        data_source_system: str = None,
        database_name: str = None,
        table_name: str = None,
        classification: ClassificationLevel = ClassificationLevel.INTERNAL,
        data_owner_id: UUID = None,
        data_steward_id: UUID = None,
        current_user_id: UUID = None,
    ) -> Dataset:
        """Create a new dataset within a domain"""
        try:
            dataset = Dataset(
                name=name,
                domain_id=domain_id,
                dataset_type=dataset_type,
                description=description,
                business_definition=business_definition,
                data_source_system=data_source_system,
                database_name=database_name,
                table_name=table_name,
                classification=classification,
                data_owner_id=data_owner_id,
                data_steward_id=data_steward_id,
            )
            db.add(dataset)
            await db.flush()

            if current_user_id:
                await log_audit_action(
                    db=db,
                    user_id=current_user_id,
                    action="CREATE",
                    entity_type="Dataset",
                    entity_id=str(dataset.id),
                    entity_name=dataset.name,
                )

            await db.commit()
            return dataset

        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating dataset: {str(e)}")
            raise

    @staticmethod
    async def get_dataset(db: AsyncSession, dataset_id: UUID) -> Dataset:
        """Get a dataset by ID"""
        result = await db.execute(
            select(Dataset).where(Dataset.id == dataset_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_datasets_in_domain(
        db: AsyncSession,
        domain_id: UUID,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[Dataset], int]:
        """List datasets in a domain"""
        query = select(Dataset).where(
            Dataset.domain_id == domain_id
        ).order_by(desc(Dataset.created_at))

        count_result = await db.execute(
            select(func.count(Dataset.id)).where(Dataset.domain_id == domain_id)
        )
        total = count_result.scalar() or 0

        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(query)
        return result.scalars().all(), total

    @staticmethod
    async def list_all_datasets(
        db: AsyncSession,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[Dataset], int]:
        """List datasets across all domains"""
        query = select(Dataset).order_by(desc(Dataset.created_at))

        count_result = await db.execute(select(func.count(Dataset.id)))
        total = count_result.scalar() or 0

        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(query)
        return result.scalars().all(), total

    # ===== DATA ELEMENT MANAGEMENT =====

    @staticmethod
    async def create_element(
        db: AsyncSession,
        name: str,
        dataset_id: UUID,
        data_type: str,
        description: str = None,
        business_term: str = None,
        business_definition: str = None,
        column_position: int = None,
        is_primary_key: bool = False,
        is_foreign_key: bool = False,
        nullable: bool = True,
        classification: ClassificationLevel = ClassificationLevel.INTERNAL,
        data_owner_id: UUID = None,
        current_user_id: UUID = None,
    ) -> DataElement:
        """Create a new data element within a dataset"""
        try:
            element = DataElement(
                name=name,
                dataset_id=dataset_id,
                data_type=data_type,
                description=description,
                business_term=business_term,
                business_definition=business_definition,
                column_position=column_position,
                is_primary_key=is_primary_key,
                is_foreign_key=is_foreign_key,
                nullable=nullable,
                classification=classification,
                data_owner_id=data_owner_id,
            )
            db.add(element)
            await db.flush()

            if current_user_id:
                await log_audit_action(
                    db=db,
                    user_id=current_user_id,
                    action="CREATE",
                    entity_type="DataElement",
                    entity_id=str(element.id),
                    entity_name=element.name,
                )

            await db.commit()
            return element

        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating element: {str(e)}")
            raise

    @staticmethod
    async def list_elements_in_dataset(
        db: AsyncSession,
        dataset_id: UUID,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[DataElement], int]:
        """List elements in a dataset"""
        query = select(DataElement).where(
            DataElement.dataset_id == dataset_id
        ).order_by(DataElement.column_position)

        count_result = await db.execute(
            select(func.count(DataElement.id)).where(DataElement.dataset_id == dataset_id)
        )
        total = count_result.scalar() or 0

        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(query)
        return result.scalars().all(), total

    # ===== METADATA MANAGEMENT =====

    @staticmethod
    async def update_element_metadata(
        db: AsyncSession,
        element_id: UUID,
        metadata_dict: dict,
    ) -> DataElementMetadata:
        """Update or create metadata for an element"""
        try:
            result = await db.execute(
                select(DataElementMetadata).where(DataElementMetadata.element_id == element_id)
            )
            metadata = result.scalar_one_or_none()

            if not metadata:
                metadata = DataElementMetadata(element_id=element_id, **metadata_dict)
                db.add(metadata)
            else:
                for key, value in metadata_dict.items():
                    setattr(metadata, key, value)
                metadata.updated_at = datetime.now(timezone.utc)

            await db.flush()
            await db.commit()
            return metadata

        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating metadata: {str(e)}")
            raise

    @staticmethod
    async def get_element_metadata(db: AsyncSession, element_id: UUID) -> DataElementMetadata:
        """Get metadata for an element"""
        result = await db.execute(
            select(DataElementMetadata).where(DataElementMetadata.element_id == element_id)
        )
        return result.scalar_one_or_none()

    # ===== GOVERNANCE MANAGEMENT =====

    @staticmethod
    async def assign_governance_role(
        db: AsyncSession,
        domain_id: UUID = None,
        dataset_id: UUID = None,
        element_id: UUID = None,
        role: GovernanceRole = None,
        user_id: UUID = None,
        department_id: UUID = None,
        responsibility_description: str = None,
        current_user_id: UUID = None,
    ) -> DataGovernance:
        """Assign a governance role to a user for a hierarchy level"""
        try:
            governance = DataGovernance(
                domain_id=domain_id,
                dataset_id=dataset_id,
                element_id=element_id,
                role=role,
                user_id=user_id,
                department_id=department_id,
                responsibility_description=responsibility_description,
            )
            db.add(governance)
            await db.flush()

            if current_user_id:
                await log_audit_action(
                    db=db,
                    user_id=current_user_id,
                    action="CREATE",
                    entity_type="DataGovernance",
                    entity_id=str(governance.id),
                    entity_name=f"{role.value} for {user_id}",
                )

            await db.commit()
            return governance

        except Exception as e:
            await db.rollback()
            logger.error(f"Error assigning governance: {str(e)}")
            raise

    @staticmethod
    async def get_governance_for_dataset(
        db: AsyncSession,
        dataset_id: UUID,
    ) -> list[DataGovernance]:
        """Get all governance assignments for a dataset"""
        result = await db.execute(
            select(DataGovernance).where(
                DataGovernance.dataset_id == dataset_id,
                DataGovernance.is_active == True
            )
        )
        return result.scalars().all()

    # ===== LINEAGE MANAGEMENT =====

    @staticmethod
    async def create_lineage(
        db: AsyncSession,
        source_dataset_id: UUID,
        target_dataset_id: UUID,
        relationship_type: str,
        description: str = None,
        current_user_id: UUID = None,
    ) -> DataLineage:
        """Create a lineage relationship between datasets"""
        try:
            lineage = DataLineage(
                source_dataset_id=source_dataset_id,
                target_dataset_id=target_dataset_id,
                relationship_type=relationship_type,
                description=description,
            )
            db.add(lineage)
            await db.flush()

            if current_user_id:
                await log_audit_action(
                    db=db,
                    user_id=current_user_id,
                    action="CREATE",
                    entity_type="DataLineage",
                    entity_id=str(lineage.id),
                    entity_name=f"{relationship_type} relationship",
                )

            await db.commit()
            return lineage

        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating lineage: {str(e)}")
            raise

    @staticmethod
    async def get_dataset_lineage(
        db: AsyncSession,
        dataset_id: UUID,
    ) -> tuple[list[DataLineage], list[DataLineage]]:
        """Get upstream and downstream lineage for a dataset"""
        upstream_result = await db.execute(
            select(DataLineage).where(DataLineage.target_dataset_id == dataset_id)
        )
        upstream = upstream_result.scalars().all()

        downstream_result = await db.execute(
            select(DataLineage).where(DataLineage.source_dataset_id == dataset_id)
        )
        downstream = downstream_result.scalars().all()

        return upstream, downstream

    # ===== QUALITY RULES =====

    @staticmethod
    async def assign_quality_rule_to_element(
        db: AsyncSession,
        rule_id: UUID,
        element_id: UUID,
        current_user_id: UUID = None,
    ) -> DataQualityRule:
        """Associate a quality rule with a data element"""
        try:
            rule = await DataHierarchyService.get_quality_rule(db, rule_id)
            if not rule:
                raise ValueError("Rule not found")

            rule.element_id = element_id
            rule.target_level = "element"
            rule.updated_at = datetime.now(timezone.utc)
            
            db.add(rule)
            await db.flush()

            if current_user_id:
                await log_audit_action(
                    db=db,
                    user_id=current_user_id,
                    action="UPDATE",
                    entity_type="DataQualityRule",
                    entity_id=str(rule.id),
                    entity_name=rule.name,
                )

            await db.commit()
            return rule

        except Exception as e:
            await db.rollback()
            logger.error(f"Error assigning rule: {str(e)}")
            raise

    @staticmethod
    async def get_quality_rule(db: AsyncSession, rule_id: UUID) -> DataQualityRule:
        """Get a quality rule by ID"""
        result = await db.execute(
            select(DataQualityRule).where(DataQualityRule.id == rule_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_rules_for_element(
        db: AsyncSession,
        element_id: UUID,
    ) -> list[DataQualityRule]:
        """Get all quality rules for a data element"""
        result = await db.execute(
            select(DataQualityRule).where(
                DataQualityRule.element_id == element_id,
                DataQualityRule.status == "active"
            )
        )
        return result.scalars().all()

    # ===== QUALITY ISSUES =====

    @staticmethod
    async def create_quality_issue(
        db: AsyncSession,
        rule_id: UUID,
        dataset_id: UUID,
        severity: IssueSeverity,
        description: str = None,
        detected_at: datetime = None,
        assigned_to_id: UUID = None,
        current_user_id: UUID = None,
    ) -> QualityIssue:
        """Create a quality issue"""
        try:
            if not detected_at:
                detected_at = datetime.now(timezone.utc)

            issue = QualityIssue(
                rule_id=rule_id,
                dataset_id=dataset_id,
                severity=severity,
                status=IssueStatus.OPEN,
                description=description,
                detected_at=detected_at,
                assigned_to_id=assigned_to_id,
            )
            db.add(issue)
            await db.flush()

            if current_user_id:
                await log_audit_action(
                    db=db,
                    user_id=current_user_id,
                    action="CREATE",
                    entity_type="QualityIssue",
                    entity_id=str(issue.id),
                    entity_name=f"{severity.value} issue",
                )

            await db.commit()
            return issue

        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating issue: {str(e)}")
            raise

    @staticmethod
    async def get_open_issues(
        db: AsyncSession,
        dataset_id: UUID = None,
        severity: IssueSeverity = None,
        limit: int = None,
    ) -> list[QualityIssue]:
        """Get open quality issues"""
        query = select(QualityIssue).options(selectinload(QualityIssue.dataset)).where(
            QualityIssue.status == IssueStatus.OPEN
        )

        if dataset_id:
            query = query.where(QualityIssue.dataset_id == dataset_id)

        if severity:
            query = query.where(QualityIssue.severity == severity)

        query = query.order_by(desc(QualityIssue.detected_at))
        if limit:
            query = query.limit(limit)
        result = await db.execute(query)
        return result.scalars().all()

    # ===== SEARCH & DISCOVERY =====

    @staticmethod
    async def search_hierarchy(
        db: AsyncSession,
        search_term: str,
        search_type: str = "all",  # all, domain, dataset, element
    ) -> dict:
        """Search across the data hierarchy"""
        results = {
            "domains": [],
            "datasets": [],
            "elements": [],
        }

        if search_type in ["all", "domain"]:
            domain_result = await db.execute(
                select(DataDomain).where(
                    DataDomain.name.ilike(f"%{search_term}%") |
                    DataDomain.description.ilike(f"%{search_term}%")
                )
            )
            results["domains"] = domain_result.scalars().all()

        if search_type in ["all", "dataset"]:
            dataset_result = await db.execute(
                select(Dataset).where(
                    Dataset.name.ilike(f"%{search_term}%") |
                    Dataset.description.ilike(f"%{search_term}%") |
                    Dataset.business_definition.ilike(f"%{search_term}%")
                )
            )
            results["datasets"] = dataset_result.scalars().all()

        if search_type in ["all", "element"]:
            element_result = await db.execute(
                select(DataElement).where(
                    DataElement.name.ilike(f"%{search_term}%") |
                    DataElement.description.ilike(f"%{search_term}%") |
                    DataElement.business_definition.ilike(f"%{search_term}%")
                )
            )
            results["elements"] = element_result.scalars().all()

        return results
