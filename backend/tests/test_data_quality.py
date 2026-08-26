"""
Tests for Data Quality Rules functionality
"""
import pytest
from datetime import datetime, timezone
from uuid import uuid4
from app.models.data_quality_rule import (
    DataQualityRule,
    DataQualityResult,
    DataQualityDimension,
    RuleSeverity,
    RuleStatus,
)
from app.schemas.data_quality_rule import (
    DataQualityRuleCreate,
    DataQualityRuleUpdate,
    DataQualityResultCreate,
)
from app.services.data_quality_service import DataQualityService


@pytest.mark.asyncio
async def test_create_data_quality_rule(db_session, super_admin_user):
    """Test creating a data quality rule"""
    rule_data = DataQualityRuleCreate(
        name="Test Rule",
        description="A test data quality rule",
        dimension=DataQualityDimension.ACCURACY,
        rule_type="format_validation",
        severity=RuleSeverity.HIGH,
        status=RuleStatus.ACTIVE,
        data_source="test_dataset",
        target_field="test_field",
    )

    rule = await DataQualityService.create_rule(db_session, rule_data, super_admin_user.id)

    assert rule is not None
    assert rule.name == "Test Rule"
    assert rule.dimension == DataQualityDimension.ACCURACY
    assert rule.rule_type == "format_validation"
    assert rule.severity == RuleSeverity.HIGH
    assert rule.created_by_id == super_admin_user.id


@pytest.mark.asyncio
async def test_get_data_quality_rule(db_session, super_admin_user):
    """Test retrieving a data quality rule"""
    rule_data = DataQualityRuleCreate(
        name="Get Test Rule",
        dimension=DataQualityDimension.COMPLETENESS,
        rule_type="required_field",
    )

    created_rule = await DataQualityService.create_rule(db_session, rule_data, super_admin_user.id)

    retrieved_rule = await DataQualityService.get_rule(db_session, created_rule.id)

    assert retrieved_rule is not None
    assert retrieved_rule.id == created_rule.id
    assert retrieved_rule.name == "Get Test Rule"


@pytest.mark.asyncio
async def test_update_data_quality_rule(db_session, super_admin_user):
    """Test updating a data quality rule"""
    rule_data = DataQualityRuleCreate(
        name="Original Name",
        dimension=DataQualityDimension.VALIDITY,
        rule_type="value_check",
        severity=RuleSeverity.LOW,
    )

    rule = await DataQualityService.create_rule(db_session, rule_data, super_admin_user.id)

    update_data = DataQualityRuleUpdate(
        name="Updated Name",
        severity=RuleSeverity.CRITICAL,
    )

    updated_rule = await DataQualityService.update_rule(
        db_session, rule.id, update_data, super_admin_user.id
    )

    assert updated_rule is not None
    assert updated_rule.name == "Updated Name"
    assert updated_rule.severity == RuleSeverity.CRITICAL


@pytest.mark.asyncio
async def test_delete_data_quality_rule(db_session, super_admin_user):
    """Test deleting a data quality rule"""
    rule_data = DataQualityRuleCreate(
        name="Delete Test Rule",
        dimension=DataQualityDimension.CONSISTENCY,
        rule_type="consistency_check",
    )

    rule = await DataQualityService.create_rule(db_session, rule_data, super_admin_user.id)

    success = await DataQualityService.delete_rule(db_session, rule.id, super_admin_user.id)

    assert success is True

    # Verify it's actually deleted
    deleted_rule = await DataQualityService.get_rule(db_session, rule.id)
    assert deleted_rule is None


@pytest.mark.asyncio
async def test_list_data_quality_rules(db_session, super_admin_user):
    """Test listing data quality rules with pagination"""
    # Create multiple rules
    for i in range(15):
        rule_data = DataQualityRuleCreate(
            name=f"Rule {i}",
            dimension=DataQualityDimension.ACCURACY if i % 2 == 0 else DataQualityDimension.COMPLETENESS,
            rule_type="test_rule",
        )
        await DataQualityService.create_rule(db_session, rule_data, super_admin_user.id)

    # Test default pagination
    rules, total = await DataQualityService.list_rules(db_session, page=1, page_size=10)

    assert total >= 15
    assert len(rules) <= 10

    # Test filtering by dimension
    accuracy_rules, accuracy_total = await DataQualityService.list_rules(
        db_session,
        dimension="accuracy",
        page=1,
        page_size=100,
    )

    assert accuracy_total > 0
    assert all(rule.dimension == DataQualityDimension.ACCURACY for rule in accuracy_rules)


@pytest.mark.asyncio
async def test_record_data_quality_result(db_session, super_admin_user):
    """Test recording a data quality result"""
    rule_data = DataQualityRuleCreate(
        name="Rule for Results",
        dimension=DataQualityDimension.ACCURACY,
        rule_type="test_rule",
    )

    rule = await DataQualityService.create_rule(db_session, rule_data, super_admin_user.id)

    result_data = DataQualityResultCreate(
        rule_id=rule.id,
        execution_timestamp=datetime.now(timezone.utc),
        status="passed",
        records_checked=100,
        records_passed=95,
        records_failed=5,
        execution_duration_ms=1234,
    )

    result = await DataQualityService.record_result(db_session, result_data)

    assert result is not None
    assert result.rule_id == rule.id
    assert result.status == "passed"
    assert result.records_passed == 95


@pytest.mark.asyncio
async def test_get_rule_results(db_session, super_admin_user):
    """Test retrieving results for a specific rule"""
    rule_data = DataQualityRuleCreate(
        name="Rule for Multiple Results",
        dimension=DataQualityDimension.COMPLETENESS,
        rule_type="test_rule",
    )

    rule = await DataQualityService.create_rule(db_session, rule_data, super_admin_user.id)

    # Record multiple results
    for i in range(5):
        result_data = DataQualityResultCreate(
            rule_id=rule.id,
            execution_timestamp=datetime.now(timezone.utc),
            status="passed" if i % 2 == 0 else "failed",
            records_checked=100 + i,
            records_passed=90 + i,
            records_failed=10 - i,
        )
        await DataQualityService.record_result(db_session, result_data)

    results, total = await DataQualityService.get_rule_results(
        db_session, rule.id, page=1, page_size=10
    )

    assert total >= 5
    assert len(results) <= 10


@pytest.mark.asyncio
async def test_calculate_metrics(db_session, super_admin_user):
    """Test calculating data quality metrics"""
    # Create rules with different dimensions
    for dimension in DataQualityDimension:
        rule_data = DataQualityRuleCreate(
            name=f"Rule for {dimension.value}",
            dimension=dimension,
            rule_type="test_rule",
            status=RuleStatus.ACTIVE if dimension != DataQualityDimension.TIMELINESS else RuleStatus.DRAFT,
        )
        rule = await DataQualityService.create_rule(db_session, rule_data, super_admin_user.id)

        # Record a result
        result_data = DataQualityResultCreate(
            rule_id=rule.id,
            execution_timestamp=datetime.now(timezone.utc),
            status="passed",
            records_checked=100,
            records_passed=95,
            records_failed=5,
        )
        await DataQualityService.record_result(db_session, result_data)

    metrics = await DataQualityService.calculate_metrics(db_session)

    assert metrics.total_rules >= 6
    assert metrics.active_rules >= 5
    assert metrics.draft_rules >= 1
    assert metrics.total_results >= 6
    assert metrics.results_passed >= 6
    assert len(metrics.dimension_stats) == 6  # One for each dimension
    assert metrics.overall_pass_rate >= 0


# Task 3: Dimension Tests
def test_dimension_configurations():
    """Test dimension configurations are available"""
    from app.services.dimension_service import DimensionService
    from app.models.data_quality_rule import DataQualityDimension

    for dimension in DataQualityDimension:
        config = DimensionService.get_dimension_config(dimension)
        assert config is not None
        assert config.name is not None
        assert config.description is not None
        assert len(config.common_rule_types) > 0


# Task 4: Monitoring Tests
@pytest.mark.asyncio
async def test_monitoring_service(db_session, super_admin_user):
    """Test monitoring service calculations"""
    from app.services.monitoring_service import MonitoringService
    
    # Create test rule and results
    rule_data = DataQualityRuleCreate(
        name="Monitoring Test Rule",
        dimension=DataQualityDimension.ACCURACY,
        rule_type="test_rule",
    )
    rule = await DataQualityService.create_rule(db_session, rule_data, super_admin_user.id)
    
    # Create multiple results
    for i in range(5):
        result_data = DataQualityResultCreate(
            rule_id=rule.id,
            execution_timestamp=datetime.now(timezone.utc),
            status="passed" if i % 2 == 0 else "failed",
            records_checked=100,
            records_passed=90,
            records_failed=10,
        )
        await DataQualityService.record_result(db_session, result_data)
    
    # Test health score calculation
    health = await MonitoringService.get_health_score(db_session)
    assert health["health_score"] >= 0
    assert health["health_score"] <= 100


# Task 6: Governance Tests
@pytest.mark.asyncio
async def test_governance_create_asset(db_session, super_admin_user):
    """Test creating governance data asset"""
    from app.services.governance_service import GovernanceService
    from app.schemas.data_governance import DataAssetCreate
    from app.models.data_governance import ClassificationLevel
    
    asset_data = DataAssetCreate(
        name="Test Asset",
        asset_type="table",
        classification=ClassificationLevel.CONFIDENTIAL,
    )
    
    asset = await GovernanceService.create_data_asset(db_session, asset_data, super_admin_user.id)
    
    assert asset is not None
    assert asset.name == "Test Asset"
    assert asset.classification == ClassificationLevel.CONFIDENTIAL


# Task 7: Metadata Tests
@pytest.mark.asyncio
async def test_metadata_service(db_session):
    """Test metadata management"""
    from app.services.metadata_service import MetadataService
    from app.models.metadata import DataType
    from uuid import uuid4
    
    asset_id = uuid4()
    metadata_data = {
        "display_name": "Test Field",
        "description": "Test Description",
        "data_type": DataType.STRING,
    }
    
    # Note: This would need a real data asset, but testing the service structure
    stats = await MetadataService.get_metadata_statistics(db_session)
    assert "total_metadata" in stats
