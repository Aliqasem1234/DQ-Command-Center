"""
Automatic data quality discovery.

Given a profiled DatasetVersion, this actually reads the real file and
checks it for concrete, well-known problems (nulls, duplicates, invalid
emails/dates/numbers, inconsistent casing) - it does not invent findings.
Every check that finds a problem gets a real DataQualityRule (so it shows
up next to user-authored rules) and a real DataQualityResult, and an open
QualityIssue is created/updated for it. Re-running the scan reconciles:
issues for checks that no longer find a problem are auto-resolved rather
than left stale.
"""
import logging
from datetime import datetime, timezone
from uuid import UUID

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.data_hierarchy import (
    Dataset, DataElement, DatasetVersion, QualityIssue, QualityCheckRun,
    IssueSeverity, IssueStatus, DatasetVersionStatus,
)
from app.models.data_quality_rule import (
    DataQualityRule, DataQualityResult, DataQualityDimension, RuleSeverity, RuleStatus, RuleTargetLevel,
)
from app.services.dataframe_io import read_dataframe
from app.services.profiling_service import EMAIL_RE, infer_column_type

logger = logging.getLogger(__name__)

AUTO_GENERATED_MARKER = "auto_discovered"


def _severity_for_ratio(bad_ratio: float) -> IssueSeverity:
    if bad_ratio >= 0.5:
        return IssueSeverity.CRITICAL
    if bad_ratio >= 0.2:
        return IssueSeverity.HIGH
    if bad_ratio >= 0.05:
        return IssueSeverity.MEDIUM
    return IssueSeverity.LOW


def _rule_severity_for_ratio(bad_ratio: float) -> RuleSeverity:
    if bad_ratio >= 0.5:
        return RuleSeverity.CRITICAL
    if bad_ratio >= 0.2:
        return RuleSeverity.HIGH
    if bad_ratio >= 0.05:
        return RuleSeverity.MEDIUM
    return RuleSeverity.LOW


def _detect_checks(df: pd.DataFrame, elements_by_name: dict[str, DataElement]) -> list[dict]:
    """Run every automatic check against the real dataframe. Returns a list
    of dicts describing each check that found a problem, plus a summary of
    every check that was evaluated (so passing checks can auto-resolve
    stale issues too)."""
    findings = []
    total_rows = len(df)

    # Dataset-level: exact duplicate rows
    if total_rows > 0:
        dup_mask = df.duplicated(keep="first")
        dup_count = int(dup_mask.sum())
        findings.append({
            "check_key": "duplicate_rows",
            "dimension": DataQualityDimension.UNIQUENESS,
            "element_name": None,
            "rule_type": "duplicate_row_check",
            "name": "Duplicate rows",
            "total": total_rows,
            "bad_count": dup_count,
            "description": f"{dup_count} of {total_rows} rows are exact duplicates of an earlier row.",
            "examples": df[dup_mask].head(3).to_dict("records") if dup_count else [],
            # Row labels affected; every cell of these rows counts as bad.
            "bad_rows": list(df.index[dup_mask]),
        })

    for column_name in df.columns:
        element = elements_by_name.get(column_name)
        series = df[column_name]
        non_null = series.dropna().astype(str).str.strip()
        non_null = non_null[non_null != ""]
        total = len(series)
        null_count = total - len(non_null)

        # Completeness
        if null_count > 0:
            findings.append({
                "check_key": f"completeness:{column_name}",
                "dimension": DataQualityDimension.COMPLETENESS,
                "element_name": column_name,
                "rule_type": "required_field",
                "name": f"Missing values in '{column_name}'",
                "total": total,
                "bad_count": null_count,
                "description": f"{null_count} of {total} values in '{column_name}' are missing.",
                "examples": [],
                "bad_rows": list(series.index[~series.index.isin(non_null.index)]),
            })

        if len(non_null) == 0:
            continue

        inferred_type = infer_column_type(series)

        # Validity: email
        if inferred_type == "email":
            invalid = non_null[~non_null.str.match(EMAIL_RE)]
            if len(invalid) > 0:
                findings.append({
                    "check_key": f"validity_email:{column_name}",
                    "dimension": DataQualityDimension.VALIDITY,
                    "element_name": column_name,
                    "rule_type": "email_format",
                    "name": f"Invalid email format in '{column_name}'",
                    "total": len(non_null),
                    "bad_count": len(invalid),
                    "description": f"{len(invalid)} of {len(non_null)} values in '{column_name}' are not valid email addresses.",
                    "examples": invalid.head(5).tolist(),
                    "bad_rows": list(invalid.index),
                })

        # Validity: datetime
        elif inferred_type == "datetime":
            parsed = pd.to_datetime(non_null, errors="coerce", format="mixed")
            invalid = non_null[parsed.isna()]
            if len(invalid) > 0:
                findings.append({
                    "check_key": f"validity_date:{column_name}",
                    "dimension": DataQualityDimension.VALIDITY,
                    "element_name": column_name,
                    "rule_type": "date_format",
                    "name": f"Invalid date format in '{column_name}'",
                    "total": len(non_null),
                    "bad_count": len(invalid),
                    "description": f"{len(invalid)} of {len(non_null)} values in '{column_name}' could not be parsed as dates.",
                    "examples": invalid.head(5).tolist(),
                    "bad_rows": list(invalid.index),
                })

        # Validity: numeric
        elif inferred_type in ("integer", "float"):
            numeric = pd.to_numeric(non_null, errors="coerce")
            invalid = non_null[numeric.isna()]
            if len(invalid) > 0:
                findings.append({
                    "check_key": f"validity_numeric:{column_name}",
                    "dimension": DataQualityDimension.VALIDITY,
                    "element_name": column_name,
                    "rule_type": "numeric_format",
                    "name": f"Invalid numeric value in '{column_name}'",
                    "total": len(non_null),
                    "bad_count": len(invalid),
                    "description": f"{len(invalid)} of {len(non_null)} values in '{column_name}' are not valid numbers.",
                    "examples": invalid.head(5).tolist(),
                    "bad_rows": list(invalid.index),
                })

        # Uniqueness: looks like an identifier column
        looks_like_id = "id" in column_name.lower() or (element.is_primary_key if element else False)
        if looks_like_id:
            dup_values = non_null[non_null.duplicated(keep=False)]
            if len(dup_values) > 0:
                findings.append({
                    "check_key": f"uniqueness:{column_name}",
                    "dimension": DataQualityDimension.UNIQUENESS,
                    "element_name": column_name,
                    "rule_type": "uniqueness_check",
                    "name": f"Duplicate values in '{column_name}'",
                    "total": len(non_null),
                    "bad_count": len(dup_values.unique()),
                    "description": f"{len(dup_values.unique())} distinct values in '{column_name}' appear more than once, though the column looks like an identifier.",
                    "examples": dup_values.unique()[:5].tolist(),
                    # Every row holding a repeated identifier is affected.
                    "bad_rows": list(dup_values.index),
                })

        # Consistency: same value in different casing/whitespace
        if inferred_type == "string":
            normalized = non_null.str.lower().str.strip()
            groups = non_null.groupby(normalized).unique()
            inconsistent_groups = [g for g in groups if len(g) > 1]
            inconsistent_keys = [key for key, g in groups.items() if len(g) > 1]
            if inconsistent_groups:
                affected = sum(len(g) for g in inconsistent_groups)
                findings.append({
                    "check_key": f"consistency:{column_name}",
                    "dimension": DataQualityDimension.CONSISTENCY,
                    "element_name": column_name,
                    "rule_type": "value_consistency",
                    "name": f"Inconsistent formatting in '{column_name}'",
                    "total": len(non_null),
                    "bad_count": affected,
                    "description": f"'{column_name}' has {len(inconsistent_groups)} sets of values that likely represent the same thing with different casing/spacing.",
                    "examples": [g.tolist() for g in inconsistent_groups[:5]],
                    "bad_rows": list(non_null.index[normalized.isin(inconsistent_keys)]),
                })

    return findings


def compute_quality_score(df: pd.DataFrame, findings: list[dict]) -> float:
    """Share of cells not affected by any failing check, as a percentage.

    Each finding names the rows it affects: a column check marks that
    column's cell in those rows, a row-level check (exact duplicate rows)
    marks every cell of the row. A cell flagged by several checks is counted
    once. (Previously the per-check counts were summed, mixing units - one
    duplicate row counted as a single cell - and double-counting overlaps.)
    """
    if not len(df) or not len(df.columns):
        return 100.0
    bad = pd.DataFrame(False, index=df.index, columns=df.columns)
    for finding in findings:
        rows = finding.get("bad_rows", [])
        if not rows:
            continue
        if finding["element_name"] is None:
            bad.loc[rows, :] = True
        elif finding["element_name"] in bad.columns:
            bad.loc[rows, finding["element_name"]] = True
    bad_cells = int(bad.values.sum())
    return 100.0 - bad_cells / bad.size * 100


async def scan_dataset_version(db: AsyncSession, version: DatasetVersion, current_user_id: UUID) -> dict:
    """Run automatic quality discovery against the version's real file and
    reconcile DataQualityRule/DataQualityResult/QualityIssue rows."""
    version.status = DatasetVersionStatus.SCANNING
    await db.flush()

    try:
        df = read_dataframe(version.file_path, version.file_format)
    except Exception as e:
        version.status = DatasetVersionStatus.ERROR
        version.error_message = f"Failed to read file for scan: {e}"
        await db.commit()
        raise

    dataset_result = await db.execute(select(Dataset).where(Dataset.id == version.dataset_id))
    dataset = dataset_result.scalar_one()

    elements_result = await db.execute(select(DataElement).where(DataElement.dataset_id == dataset.id))
    elements_by_name = {el.name: el for el in elements_result.scalars().all()}

    findings = _detect_checks(df, elements_by_name)
    findings_by_key = {f["check_key"]: f for f in findings if f["bad_count"] > 0}

    existing_rules_result = await db.execute(
        select(DataQualityRule)
        .options(selectinload(DataQualityRule.effectiveness))
        .where(DataQualityRule.dataset_id == dataset.id)
    )
    existing_rules = existing_rules_result.scalars().all()
    auto_rules_by_key = {
        r.rule_definition.get("check_key"): r
        for r in existing_rules
        if r.rule_definition and r.rule_definition.get("source") == AUTO_GENERATED_MARKER
    }

    now = datetime.now(timezone.utc)
    total_rules_executed = 0
    rules_passed = 0
    rules_failed = 0

    for check_key, finding in findings_by_key.items():
        total_rules_executed += 1
        bad_ratio = finding["bad_count"] / finding["total"] if finding["total"] else 0
        element = elements_by_name.get(finding["element_name"]) if finding["element_name"] else None

        rule = auto_rules_by_key.get(check_key)
        if rule is None:
            rule = DataQualityRule(
                name=finding["name"],
                description=finding["description"],
                dataset_id=dataset.id,
                element_id=element.id if element else None,
                target_level=RuleTargetLevel.ELEMENT if element else RuleTargetLevel.DATASET,
                dimension=finding["dimension"],
                rule_type=finding["rule_type"],
                severity=_rule_severity_for_ratio(bad_ratio),
                status=RuleStatus.ACTIVE,
                rule_definition={"source": AUTO_GENERATED_MARKER, "check_key": check_key},
                owner_id=current_user_id,
                created_by_id=current_user_id,
                created_at=now,
                updated_at=now,
            )
            db.add(rule)
            await db.flush()
        else:
            rule.description = finding["description"]
            rule.severity = _rule_severity_for_ratio(bad_ratio)
            rule.status = RuleStatus.ACTIVE
            rule.updated_at = now

        pass_count = finding["total"] - finding["bad_count"]
        pass_rate = (pass_count / finding["total"] * 100) if finding["total"] else 0
        rules_failed += 1

        db.add(DataQualityResult(
            rule_id=rule.id,
            execution_timestamp=now,
            status="failed",
            records_checked=finding["total"],
            records_passed=pass_count,
            records_failed=finding["bad_count"],
            error_details=None,
            created_at=now,
        ))

        issue_result = await db.execute(
            select(QualityIssue).where(
                QualityIssue.rule_id == rule.id,
                QualityIssue.status != IssueStatus.RESOLVED,
            )
        )
        issue = issue_result.scalar_one_or_none()
        severity = _severity_for_ratio(bad_ratio)
        description = (
            f"{finding['description']} "
            + (f"Examples: {finding['examples']}" if finding["examples"] else "")
        ).strip()

        if issue is None:
            db.add(QualityIssue(
                rule_id=rule.id,
                dataset_id=dataset.id,
                severity=severity,
                status=IssueStatus.OPEN,
                description=description,
                detected_at=now,
                created_at=now,
                updated_at=now,
            ))
        else:
            issue.severity = severity
            issue.description = description
            issue.updated_at = now

    # Auto-resolve issues for previously-detected checks that no longer find a problem
    for check_key, rule in auto_rules_by_key.items():
        if check_key in findings_by_key:
            continue
        rule.status = RuleStatus.INACTIVE
        rule.updated_at = now
        stale_issue_result = await db.execute(
            select(QualityIssue).where(
                QualityIssue.rule_id == rule.id,
                QualityIssue.status != IssueStatus.RESOLVED,
            )
        )
        stale_issue = stale_issue_result.scalar_one_or_none()
        if stale_issue:
            stale_issue.status = IssueStatus.RESOLVED
            stale_issue.resolved_at = now
            stale_issue.resolution_notes = "Automatically resolved - issue no longer detected on rescan."
            stale_issue.updated_at = now
        rules_passed += 1
        total_rules_executed += 1

    overall_pass_rate = (rules_passed / total_rules_executed * 100) if total_rules_executed else 100.0

    quality_score = compute_quality_score(df, list(findings_by_key.values()))

    db.add(QualityCheckRun(
        dataset_id=dataset.id,
        check_timestamp=now,
        total_rules_executed=total_rules_executed,
        rules_passed=rules_passed,
        rules_failed=rules_failed,
        overall_pass_rate=overall_pass_rate,
        quality_score=round(quality_score, 1),
        status="success",
        created_at=now,
    ))

    version.quality_score = round(quality_score, 1)
    version.status = DatasetVersionStatus.SCANNED
    await db.commit()

    return {
        "checks_run": total_rules_executed,
        "issues_found": len(findings_by_key),
        "issues_resolved": sum(1 for k in auto_rules_by_key if k not in findings_by_key),
        "quality_score": version.quality_score,
    }
