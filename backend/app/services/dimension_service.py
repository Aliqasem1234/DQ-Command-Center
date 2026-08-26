"""
Data Quality Dimension Configuration and Metadata

Provides dimension-specific configurations, validation rules, and best practices
for each of the 6 standard data quality dimensions.
"""

from enum import Enum
from typing import Dict, List, Any
from dataclasses import dataclass

from app.models.data_quality_rule import DataQualityDimension


@dataclass
class DimensionConfig:
    """Configuration for a data quality dimension"""
    name: str
    description: str
    examples: List[str]
    common_rule_types: List[str]
    validation_tips: List[str]
    related_frameworks: List[str]


DIMENSION_CONFIGURATIONS: Dict[DataQualityDimension, DimensionConfig] = {
    DataQualityDimension.ACCURACY: DimensionConfig(
        name="Accuracy",
        description="Ensures data correctly represents the actual values from authoritative sources",
        examples=[
            "Customer email addresses match validated sources",
            "Product prices match official price lists",
            "Sales amounts match source transactions",
            "Geographic coordinates are within acceptable tolerance",
        ],
        common_rule_types=[
            "source_match",
            "reference_data_check",
            "calculation_verification",
            "format_validation",
        ],
        validation_tips=[
            "Define authoritative data sources clearly",
            "Set acceptable tolerance levels for numeric values",
            "Document validation procedures for each rule",
            "Schedule regular audits against source systems",
        ],
        related_frameworks=[
            "ISO 8601 (Date/Time)",
            "IEEE 754 (Floating Point)",
            "RFC 5321 (Email)",
        ],
    ),
    DataQualityDimension.COMPLETENESS: DimensionConfig(
        name="Completeness",
        description="Measures the presence of required data values and absence of gaps",
        examples=[
            "All customer records have an email address",
            "Required order fields are populated",
            "No NULL values in critical columns",
            "All transactions have a corresponding date",
        ],
        common_rule_types=[
            "required_field",
            "null_check",
            "not_empty",
            "minimum_cardinality",
        ],
        validation_tips=[
            "Identify truly required vs optional fields",
            "Consider business logic that may override requirements",
            "Track missing data patterns over time",
            "Distinguish between NULL and empty string",
        ],
        related_frameworks=[
            "Data Completeness Standards",
            "MDM (Master Data Management)",
            "Business Rules Engine",
        ],
    ),
    DataQualityDimension.CONSISTENCY: DimensionConfig(
        name="Consistency",
        description="Ensures data is consistent across systems, formats, and over time",
        examples=[
            "Customer name spelled consistently across systems",
            "Address format matches standard",
            "Date formats consistent (YYYY-MM-DD)",
            "Status values from approved list",
        ],
        common_rule_types=[
            "format_consistency",
            "cross_system_match",
            "enum_validation",
            "case_sensitivity_check",
        ],
        validation_tips=[
            "Establish data standardization rules",
            "Document approved values and formats",
            "Implement data governance for master data",
            "Regular cross-system reconciliation",
        ],
        related_frameworks=[
            "ISO/IEC 11179 (Metadata Registry)",
            "Data Standardization Guidelines",
            "Entity Resolution",
        ],
    ),
    DataQualityDimension.VALIDITY: DimensionConfig(
        name="Validity",
        description="Ensures data conforms to required format, type, and range specifications",
        examples=[
            "Email addresses are valid email format",
            "Phone numbers have correct number of digits",
            "Dates fall within valid range",
            "Numeric values within acceptable range",
        ],
        common_rule_types=[
            "format_validation",
            "type_check",
            "range_check",
            "pattern_matching",
        ],
        validation_tips=[
            "Define valid ranges and formats explicitly",
            "Use regex patterns for complex validations",
            "Consider business logic exceptions",
            "Test boundary conditions",
        ],
        related_frameworks=[
            "JSON Schema",
            "XML Schema",
            "Regular Expressions (PCRE)",
        ],
    ),
    DataQualityDimension.UNIQUENESS: DimensionConfig(
        name="Uniqueness",
        description="Ensures there are no unintended duplicates in data",
        examples=[
            "Each customer has unique ID",
            "Email addresses are not duplicated",
            "Product SKUs are unique",
            "Transaction IDs never repeat",
        ],
        common_rule_types=[
            "duplicate_detection",
            "primary_key_check",
            "unique_constraint",
            "deduplication",
        ],
        validation_tips=[
            "Define what constitutes a duplicate",
            "Consider intentional duplicates (history records)",
            "Use fuzzy matching for potential duplicates",
            "Document deduplication procedures",
        ],
        related_frameworks=[
            "Entity Resolution",
            "Record Linkage",
            "Fuzzy Matching",
        ],
    ),
    DataQualityDimension.TIMELINESS: DimensionConfig(
        name="Timeliness",
        description="Measures how current and up-to-date data is, and how quickly it's available",
        examples=[
            "Customer updates reflected within 24 hours",
            "Transaction data available within 1 hour",
            "Real-time price updates for inventory",
            "Compliance data current within 30 days",
        ],
        common_rule_types=[
            "staleness_check",
            "latency_measurement",
            "refresh_frequency_check",
            "sla_compliance",
        ],
        validation_tips=[
            "Define acceptable data age by use case",
            "Establish SLAs for data refresh",
            "Monitor data pipeline latency",
            "Alert on data staleness",
        ],
        related_frameworks=[
            "Service Level Agreements (SLA)",
            "Data Pipeline Monitoring",
            "Event-driven Architecture",
        ],
    ),
}


class DimensionService:
    """Service for managing data quality dimension configurations"""

    @staticmethod
    def get_dimension_config(dimension: DataQualityDimension) -> DimensionConfig:
        """Get configuration for a specific dimension"""
        return DIMENSION_CONFIGURATIONS[dimension]

    @staticmethod
    def get_all_dimensions() -> Dict[str, DimensionConfig]:
        """Get all dimension configurations"""
        return {
            dim.value: config for dim, config in DIMENSION_CONFIGURATIONS.items()
        }

    @staticmethod
    def get_dimension_rule_types(dimension: DataQualityDimension) -> List[str]:
        """Get recommended rule types for a dimension"""
        config = DIMENSION_CONFIGURATIONS[dimension]
        return config.common_rule_types

    @staticmethod
    def get_dimension_validation_tips(dimension: DataQualityDimension) -> List[str]:
        """Get validation tips for a dimension"""
        config = DIMENSION_CONFIGURATIONS[dimension]
        return config.validation_tips

    @staticmethod
    def get_related_frameworks(dimension: DataQualityDimension) -> List[str]:
        """Get related standards and frameworks for a dimension"""
        config = DIMENSION_CONFIGURATIONS[dimension]
        return config.related_frameworks
