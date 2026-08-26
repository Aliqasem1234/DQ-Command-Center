"""Redesign data hierarchy - establish proper domain/dataset/element structure

Revision ID: 006
Revises: 005
Create Date: 2026-08-26 00:00:00.000000

This migration implements the professional DQ Command Center data hierarchy:
DataDomain → Dataset → DataElement → Metadata → Quality Rules → Results → Governance
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create DataDomain table (business area/domain)
    op.create_table(
        "data_domains",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("business_owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("domain_steward_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="active", index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 2. Create Dataset table (tables, collections, APIs, etc.)
    op.create_table(
        "datasets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False, index=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("business_definition", sa.Text, nullable=True),
        sa.Column("domain_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("data_domains.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("dataset_type", sa.String(100), nullable=False, index=True),  # table, collection, api, file, etc.
        sa.Column("data_source_system", sa.String(255), nullable=True),
        sa.Column("database_name", sa.String(255), nullable=True),
        sa.Column("table_name", sa.String(255), nullable=True),
        sa.Column("classification", sa.String(50), nullable=False, server_default="internal"),
        sa.Column("data_owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("data_steward_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("row_count", sa.Integer, nullable=True),
        sa.Column("last_updated", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="active", index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_unique_constraint("uq_dataset_domain_name", "datasets", ["domain_id", "name"])

    # 3. Create DataElement table (fields/columns within a dataset)
    op.create_table(
        "data_elements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False, index=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("business_term", sa.String(255), nullable=True),
        sa.Column("business_definition", sa.Text, nullable=True),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("data_type", sa.String(100), nullable=False),  # string, integer, float, date, etc.
        sa.Column("column_position", sa.Integer, nullable=True),
        sa.Column("is_primary_key", sa.Boolean(), default=False, nullable=False),
        sa.Column("is_foreign_key", sa.Boolean(), default=False, nullable=False),
        sa.Column("nullable", sa.Boolean(), default=True, nullable=False),
        sa.Column("classification", sa.String(50), nullable=False, server_default="internal"),
        sa.Column("data_owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_unique_constraint("uq_element_dataset_name", "data_elements", ["dataset_id", "name"])
    op.create_index("ix_element_dataset_position", "data_elements", ["dataset_id", "column_position"])

    # 4. Create DataElementMetadata (detailed profiling and business metadata)
    op.create_table(
        "data_element_metadata",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("element_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("data_elements.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("sample_values", postgresql.JSON, nullable=True),
        sa.Column("format_pattern", sa.String(255), nullable=True),
        sa.Column("allowed_values", postgresql.JSON, nullable=True),
        sa.Column("min_length", sa.Integer, nullable=True),
        sa.Column("max_length", sa.Integer, nullable=True),
        sa.Column("value_count", sa.Integer, nullable=True),
        sa.Column("null_count", sa.Integer, nullable=True),
        sa.Column("unique_count", sa.Integer, nullable=True),
        sa.Column("duplicate_count", sa.Integer, nullable=True),
        sa.Column("min_value", sa.String(255), nullable=True),
        sa.Column("max_value", sa.String(255), nullable=True),
        sa.Column("average_value", sa.Float, nullable=True),
        sa.Column("last_profiled", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 5. Redesign DataQualityRule to have proper foreign keys
    # First, drop old constraints if they exist, add new ones
    op.add_column("data_quality_rules", sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("data_quality_rules", sa.Column("element_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("data_quality_rules", sa.Column("target_level", sa.String(50), nullable=True))  # dataset or element
    op.add_column("data_quality_rules", sa.Column("quality_threshold", sa.Float, nullable=True))  # % acceptable
    op.add_column("data_quality_rules", sa.Column("sla_hours", sa.Integer, nullable=True))  # SLA response time
    
    op.create_foreign_key("fk_rule_dataset", "data_quality_rules", "datasets", ["dataset_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key("fk_rule_element", "data_quality_rules", "data_elements", ["element_id"], ["id"], ondelete="CASCADE")
    op.create_index("ix_rule_dataset_element", "data_quality_rules", ["dataset_id", "element_id"])

    # 6. Create RuleEffectiveness tracking
    op.create_table(
        "rule_effectiveness",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("rule_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("data_quality_rules.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("last_30_days_pass_rate", sa.Float, nullable=True),
        sa.Column("last_30_days_fail_rate", sa.Float, nullable=True),
        sa.Column("trend", sa.String(50), nullable=True),  # improving, stable, degrading
        sa.Column("last_calculated", sa.DateTime(timezone=True), nullable=True),
    )

    # 7. Create QualityTarget (SLA/goals)
    op.create_table(
        "quality_targets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("datasets.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("element_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("data_elements.id", ondelete="CASCADE"), nullable=True),
        sa.Column("dimension", sa.String(100), nullable=False, index=True),  # accuracy, completeness, etc.
        sa.Column("target_score", sa.Float, nullable=False),  # e.g., 95.0
        sa.Column("minimum_score", sa.Float, nullable=False),  # e.g., 90.0
        sa.Column("sla_hours", sa.Integer, nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 8. Create governance relationship table (replaces confusion of ownership fields)
    op.create_table(
        "data_governance",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("domain_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("data_domains.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("datasets.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("element_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("data_elements.id", ondelete="CASCADE"), nullable=True),
        sa.Column("role", sa.String(50), nullable=False),  # owner, steward, curator, etc.
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("departments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("responsibility_description", sa.Text, nullable=True),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
        sa.Column("assigned_date", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_governance_role", "data_governance", ["role", "is_active"])

    # 9. Drop old redundant governance tables (they're replaced by unified model above)
    # But only if they exist
    op.execute("DROP TABLE IF EXISTS data_stewardships CASCADE")
    op.execute("DROP TABLE IF EXISTS governance_policies CASCADE")
    op.execute("DROP TABLE IF EXISTS data_assets CASCADE")
    op.execute("DROP TABLE IF EXISTS metadata_tags CASCADE")
    op.execute("DROP TABLE IF EXISTS metadata CASCADE")

    # 10. Create data lineage table (relationships between datasets)
    op.create_table(
        "data_lineage",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("source_dataset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("target_dataset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("relationship_type", sa.String(100), nullable=False),  # feed, join, transform, etc.
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 11. Create DataQualityCheck for recording quality checks (replaces old results table partially)
    # Keep results but add status tracking per check run
    op.create_table(
        "quality_check_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("check_timestamp", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("total_rules_executed", sa.Integer, nullable=True),
        sa.Column("rules_passed", sa.Integer, nullable=True),
        sa.Column("rules_failed", sa.Integer, nullable=True),
        sa.Column("overall_pass_rate", sa.Float, nullable=True),
        sa.Column("status", sa.String(50), nullable=False),  # success, partial, failed
        sa.Column("error_summary", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 12. Create quality issues table (for tracking ongoing issues)
    op.create_table(
        "quality_issues",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("rule_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("data_quality_rules.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("severity", sa.String(50), nullable=False, index=True),  # low, medium, high, critical
        sa.Column("status", sa.String(50), nullable=False, default="open", index=True),  # open, in_progress, resolved
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("assigned_to_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("quality_issues")
    op.drop_table("quality_check_runs")
    op.drop_table("data_lineage")
    op.drop_table("data_governance")
    op.drop_table("quality_targets")
    op.drop_table("rule_effectiveness")
    
    # Remove columns from data_quality_rules
    op.drop_constraint("fk_rule_element", "data_quality_rules", type_="foreignkey")
    op.drop_constraint("fk_rule_dataset", "data_quality_rules", type_="foreignkey")
    op.drop_column("data_quality_rules", "sla_hours")
    op.drop_column("data_quality_rules", "quality_threshold")
    op.drop_column("data_quality_rules", "target_level")
    op.drop_column("data_quality_rules", "element_id")
    op.drop_column("data_quality_rules", "dataset_id")
    
    op.drop_table("data_element_metadata")
    op.drop_table("data_elements")
    op.drop_table("datasets")
    op.drop_table("data_domains")
