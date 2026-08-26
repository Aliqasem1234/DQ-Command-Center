"""
Seed data service - Populates realistic demo data for the DQ Command Center

Creates a complete, internally consistent demo environment with:
- Data domains (business areas)
- Datasets (tables, APIs, files)
- Data elements (fields/columns)
- Metadata with profiling
- Quality rules
- Quality results with realistic quality issues
- Governance relationships
- Data lineage

All marked as DEMO DATA
"""

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.department import Department
from app.models.data_hierarchy import (
    DataDomain, Dataset, DataElement, DataElementMetadata, DataQualityRule,
    DataGovernance, QualityTarget, QualityCheckRun, QualityIssue,
    DatasetType, ClassificationLevel, GovernanceRole, IssueSeverity, IssueStatus
)
from app.models.data_quality_rule import DataQualityDimension, RuleSeverity, RuleStatus, RuleTargetLevel
from app.services.data_hierarchy_service import DataHierarchyService

logger = logging.getLogger(__name__)


class SeedDataService:
    """Service for seeding realistic demo data"""

    @staticmethod
    async def populate_demo_data(
        db: AsyncSession,
        admin_user: User,
        demo_users: list[User],
        demo_departments: list[Department],
    ) -> dict:
        """
        Populate complete demo environment
        
        Returns summary of what was created
        """
        try:
            logger.info("Starting demo data population...")
            
            summary = {
                "domains": 0,
                "datasets": 0,
                "elements": 0,
                "quality_rules": 0,
                "quality_issues": 0,
                "governance_assignments": 0,
            }

            # Create demo data domains (business areas)
            finance_domain = await DataHierarchyService.create_domain(
                db=db,
                name="Finance",
                description="Financial data and transactions",
                business_owner_id=demo_users[0].id if len(demo_users) > 0 else admin_user.id,
                domain_steward_id=demo_users[1].id if len(demo_users) > 1 else admin_user.id,
                current_user_id=admin_user.id,
            )
            summary["domains"] += 1

            customer_domain = await DataHierarchyService.create_domain(
                db=db,
                name="Customer",
                description="Customer master data and profiles",
                business_owner_id=demo_users[1].id if len(demo_users) > 1 else admin_user.id,
                domain_steward_id=demo_users[2].id if len(demo_users) > 2 else admin_user.id,
                current_user_id=admin_user.id,
            )
            summary["domains"] += 1

            product_domain = await DataHierarchyService.create_domain(
                db=db,
                name="Product",
                description="Product catalog and inventory",
                business_owner_id=demo_users[2].id if len(demo_users) > 2 else admin_user.id,
                current_user_id=admin_user.id,
            )
            summary["domains"] += 1

            # Create demo datasets
            customers_dataset = await DataHierarchyService.create_dataset(
                db=db,
                name="Customers",
                domain_id=customer_domain.id,
                dataset_type=DatasetType.TABLE,
                description="DEMO: Master customer data",
                business_definition="Central repository of customer information including contact details, classification, and status",
                data_source_system="PostgreSQL",
                database_name="production",
                table_name="customers",
                classification=ClassificationLevel.INTERNAL,
                data_owner_id=demo_users[1].id if len(demo_users) > 1 else admin_user.id,
                data_steward_id=demo_users[2].id if len(demo_users) > 2 else admin_user.id,
                current_user_id=admin_user.id,
            )
            summary["datasets"] += 1

            orders_dataset = await DataHierarchyService.create_dataset(
                db=db,
                name="Orders",
                domain_id=finance_domain.id,
                dataset_type=DatasetType.TABLE,
                description="DEMO: Transaction orders",
                business_definition="Complete order history with amounts, dates, and customer references",
                data_source_system="PostgreSQL",
                database_name="production",
                table_name="orders",
                classification=ClassificationLevel.CONFIDENTIAL,
                data_owner_id=demo_users[0].id if len(demo_users) > 0 else admin_user.id,
                current_user_id=admin_user.id,
            )
            summary["datasets"] += 1

            products_dataset = await DataHierarchyService.create_dataset(
                db=db,
                name="Products",
                domain_id=product_domain.id,
                dataset_type=DatasetType.TABLE,
                description="DEMO: Product master",
                data_source_system="PostgreSQL",
                database_name="production",
                table_name="products",
                data_owner_id=demo_users[2].id if len(demo_users) > 2 else admin_user.id,
                current_user_id=admin_user.id,
            )
            summary["datasets"] += 1

            # Create data elements for Customers dataset
            customer_elements = [
                ("customer_id", "string", "Primary key", "Unique customer identifier"),
                ("email", "string", "Email address", "Customer email for communication"),
                ("phone", "string", "Phone number", "Customer contact phone"),
                ("created_date", "date", "Account creation date", "When account was opened"),
                ("country", "string", "Country code", "Customer location country"),
                ("segment", "string", "Customer segment", "Business or consumer classification"),
            ]

            for elem_name, data_type, business_term, business_def in customer_elements:
                element = await DataHierarchyService.create_element(
                    db=db,
                    name=elem_name,
                    dataset_id=customers_dataset.id,
                    data_type=data_type,
                    business_term=business_term,
                    business_definition=business_def,
                    is_primary_key=(elem_name == "customer_id"),
                    current_user_id=admin_user.id,
                )
                summary["elements"] += 1

                # Add sample metadata
                if elem_name == "email":
                    await DataHierarchyService.update_element_metadata(
                        db=db,
                        element_id=element.id,
                        metadata_dict={
                            "format_pattern": "^[^@]+@[^@]+\\.[^@]+$",
                            "sample_values": ["john@example.com", "jane@example.com"],
                            "value_count": 50000,
                            "null_count": 127,
                            "unique_count": 49873,
                        }
                    )

            # Create data elements for Orders dataset
            order_elements = [
                ("order_id", "string", "Order ID", "Unique order identifier"),
                ("customer_id", "string", "Customer FK", "Reference to customers"),
                ("order_date", "date", "Order date", "Date order was placed"),
                ("amount", "float", "Order amount", "Total order value"),
                ("status", "string", "Order status", "Current order processing status"),
            ]

            for elem_name, data_type, business_term, business_def in order_elements:
                element = await DataHierarchyService.create_element(
                    db=db,
                    name=elem_name,
                    dataset_id=orders_dataset.id,
                    data_type=data_type,
                    business_term=business_term,
                    business_definition=business_def,
                    is_primary_key=(elem_name == "order_id"),
                    is_foreign_key=(elem_name == "customer_id"),
                    current_user_id=admin_user.id,
                )
                summary["elements"] += 1

            # Create quality rules for Customers dataset
            customer_rules_data = [
                ("email_required", DataQualityDimension.COMPLETENESS, "Required field check", "Ensure email is not null"),
                ("email_format", DataQualityDimension.VALIDITY, "Format validation", "Email must match RFC 5321"),
                ("email_unique", DataQualityDimension.UNIQUENESS, "Duplicate check", "Email values must be unique"),
                ("country_valid", DataQualityDimension.VALIDITY, "Reference data check", "Country code must be in valid list"),
            ]

            for rule_name, dimension, rule_type, description in customer_rules_data:
                rule = DataQualityRule(
                    name=rule_name,
                    description=description,
                    dataset_id=customers_dataset.id,
                    dimension=dimension,
                    rule_type=rule_type,
                    severity=RuleSeverity.HIGH,
                    status=RuleStatus.ACTIVE,
                    target_level=RuleTargetLevel.DATASET,
                    quality_threshold=95.0,
                    owner_id=demo_users[1].id if len(demo_users) > 1 else admin_user.id,
                    created_by_id=admin_user.id,
                )
                db.add(rule)
                summary["quality_rules"] += 1

            await db.flush()

            # Create governance assignments
            governance_data = [
                (customer_domain.id, None, None, GovernanceRole.OWNER, demo_users[1].id if len(demo_users) > 1 else admin_user.id),
                (None, customers_dataset.id, None, GovernanceRole.STEWARD, demo_users[2].id if len(demo_users) > 2 else admin_user.id),
                (None, orders_dataset.id, None, GovernanceRole.OWNER, demo_users[0].id if len(demo_users) > 0 else admin_user.id),
            ]

            for domain_id, dataset_id, element_id, role, user_id in governance_data:
                governance = DataGovernance(
                    domain_id=domain_id,
                    dataset_id=dataset_id,
                    element_id=element_id,
                    role=role,
                    user_id=user_id,
                    responsibility_description=f"Assigned as {role.value}",
                )
                db.add(governance)
                summary["governance_assignments"] += 1

            # Create quality targets
            target = QualityTarget(
                dataset_id=customers_dataset.id,
                dimension=DataQualityDimension.COMPLETENESS.value,
                target_score=99.0,
                minimum_score=95.0,
                sla_hours=24,
            )
            db.add(target)

            # Create sample quality issues (realistic data quality problems)
            now = datetime.now(timezone.utc)

            # Issue 1: Missing emails
            issue1 = QualityIssue(
                rule_id=(await db.execute(
                    (select(DataQualityRule).where(DataQualityRule.name == "email_required"))
                )).scalar().id if (await db.execute(
                    (select(DataQualityRule).where(DataQualityRule.name == "email_required"))
                )).scalar() else None,
                dataset_id=customers_dataset.id,
                severity=IssueSeverity.HIGH,
                status=IssueStatus.OPEN,
                description="127 customer records missing email addresses",
                detected_at=now - timedelta(days=2),
                assigned_to_id=demo_users[1].id if len(demo_users) > 1 else admin_user.id,
            )
            if issue1.rule_id:
                db.add(issue1)
                summary["quality_issues"] += 1

            # Issue 2: Invalid country codes
            issue2 = QualityIssue(
                rule_id=(await db.execute(
                    (select(DataQualityRule).where(DataQualityRule.name == "country_valid"))
                )).scalar().id if (await db.execute(
                    (select(DataQualityRule).where(DataQualityRule.name == "country_valid"))
                )).scalar() else None,
                dataset_id=customers_dataset.id,
                severity=IssueSeverity.MEDIUM,
                status=IssueStatus.IN_PROGRESS,
                description="8 records with invalid country codes (ZZ, XX, 00)",
                detected_at=now - timedelta(days=1),
                assigned_to_id=demo_users[2].id if len(demo_users) > 2 else admin_user.id,
                resolution_notes="Data validation rules updated, awaiting re-check",
            )
            if issue2.rule_id:
                db.add(issue2)
                summary["quality_issues"] += 1

            await db.commit()
            logger.info(f"Demo data population complete: {summary}")
            return summary

        except Exception as e:
            await db.rollback()
            logger.error(f"Error populating demo data: {str(e)}")
            raise
