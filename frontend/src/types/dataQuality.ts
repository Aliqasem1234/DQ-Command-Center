export enum DataQualityDimension {
  ACCURACY = 'accuracy',
  COMPLETENESS = 'completeness',
  CONSISTENCY = 'consistency',
  VALIDITY = 'validity',
  UNIQUENESS = 'uniqueness',
  TIMELINESS = 'timeliness',
}

export enum RuleSeverity {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  CRITICAL = 'critical',
}

export enum RuleStatus {
  ACTIVE = 'active',
  INACTIVE = 'inactive',
  DRAFT = 'draft',
  ARCHIVED = 'archived',
}

export interface DataQualityRule {
  id: string;
  name: string;
  description?: string;
  data_source?: string;
  target_field?: string;
  dimension: DataQualityDimension;
  rule_type: string;
  severity: RuleSeverity;
  status: RuleStatus;
  rule_definition?: Record<string, any>;
  owner_id?: string;
  owner_name?: string;
  created_by_id?: string;
  created_by_name?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CreateDataQualityRuleRequest {
  name: string;
  description?: string;
  data_source?: string;
  target_field?: string;
  dimension: DataQualityDimension;
  rule_type: string;
  severity?: RuleSeverity;
  status?: RuleStatus;
  rule_definition?: Record<string, any>;
  owner_id?: string;
  is_active?: boolean;
}

export interface UpdateDataQualityRuleRequest {
  name?: string;
  description?: string;
  data_source?: string;
  target_field?: string;
  dimension?: DataQualityDimension;
  rule_type?: string;
  severity?: RuleSeverity;
  status?: RuleStatus;
  rule_definition?: Record<string, any>;
  owner_id?: string;
  is_active?: boolean;
}

export interface DataQualityRuleListResponse {
  items: DataQualityRule[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface DataQualityResult {
  id: string;
  rule_id: string;
  execution_timestamp: string;
  status: string;
  records_checked?: number;
  records_passed?: number;
  records_failed?: number;
  execution_duration_ms?: number;
  error_details?: string;
  pass_rate?: number;
  created_at: string;
}

export interface DataQualityResultListResponse {
  items: DataQualityResult[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface DimensionStats {
  dimension: DataQualityDimension;
  total_rules: number;
  active_rules: number;
  passed_results: number;
  failed_results: number;
  last_execution?: string;
}

export interface DataQualityMetrics {
  total_rules: number;
  active_rules: number;
  draft_rules: number;
  total_results: number;
  results_passed: number;
  results_failed: number;
  results_with_errors: number;
  overall_pass_rate: number;
  dimension_stats: DimensionStats[];
  last_updated: string;
}
