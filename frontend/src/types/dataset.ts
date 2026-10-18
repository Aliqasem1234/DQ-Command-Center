export interface DataDomain {
  id: string;
  name: string;
  description: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface Dataset {
  id: string;
  name: string;
  description: string | null;
  domain_id: string | null;
  dataset_type: string;
  classification: string;
  row_count: number | null;
  last_updated: string | null;
  status: string;
  data_owner_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface DataElement {
  id: string;
  name: string;
  data_type: string;
  dataset_id: string;
  column_position: number | null;
  is_primary_key: boolean;
  is_foreign_key: boolean;
  nullable: boolean;
  classification: string;
}

export interface DatasetVersion {
  id: string;
  dataset_id: string;
  version_number: number;
  original_filename: string | null;
  file_format: string;
  file_size_bytes: number | null;
  row_count: number | null;
  column_count: number | null;
  is_original: boolean;
  source_version_id: string | null;
  cleaning_operations: CleaningOperation[] | null;
  rows_changed: number | null;
  values_changed: number | null;
  status: 'uploaded' | 'profiling' | 'profiled' | 'scanning' | 'scanned' | 'cleaning' | 'error';
  quality_score: number | null;
  error_message: string | null;
  created_by_id: string | null;
  created_by_name: string | null;
  created_at: string;
}

export interface ColumnProfile {
  name: string;
  inferred_type: string;
  value_count: number;
  null_count: number;
  unique_count: number;
  duplicate_count: number;
  min_length: number | null;
  max_length: number | null;
  min_value: string | null;
  max_value: string | null;
  average_value: number | null;
  sample_values: string[];
}

export interface ProfileSummary {
  row_count: number;
  column_count: number;
  columns: ColumnProfile[];
}

export interface ScanResult {
  checks_run: number;
  issues_found: number;
  issues_resolved: number;
  quality_score: number;
}

export interface CleaningOperation {
  type:
    | 'trim_whitespace' | 'collapse_whitespace' | 'remove_control_characters' | 'standardize_case'
    | 'normalize_dates' | 'convert_type' | 'map_values' | 'remove_duplicate_rows' | 'fill_missing';
  columns?: string[] | 'all';
  column?: string;
  case?: 'lower' | 'upper' | 'title';
  target_format?: string;
  source_format?: string;
  day_first?: boolean;
  strategy?: 'drop_row' | 'fill_value' | 'fill_mean' | 'fill_median' | 'fill_mode';
  value?: string;
  target?: 'integer' | 'decimal' | 'boolean';
  on_invalid?: 'keep' | 'set_missing';
  decimal_separator?: '.' | ',';
  mapping?: Record<string, string>;
  case_sensitive?: boolean;
  keep?: 'first' | 'last';
}

export interface CleaningOperationReport {
  type: string;
  rows_removed: number;
  skipped: number;
  skipped_examples: { column: string; value: string; reason: string }[];
  note?: string;
}

export interface CleaningPreview {
  original_row_count: number;
  result_row_count: number;
  rows_changed: number;
  rows_modified: number;
  rows_removed: number;
  values_changed: number;
  changed_columns: Record<string, number>;
  exact_duplicates_before: number;
  exact_duplicates_after: number;
  potential_duplicates_after: number;
  operations_report: CleaningOperationReport[];
  removes_rows: boolean;
  quality_score_before: number | null;
  quality_score_after: number | null;
  sample_changes: { row: number; before: Record<string, unknown>; after: Record<string, unknown> | null }[];
}

export interface VersionQualitySummary {
  version_id: string;
  version_number: number;
  is_original: boolean;
  quality_score: number | null;
  row_count: number | null;
  created_at: string;
}

export interface QualityComparison {
  dataset_id: string;
  versions: VersionQualitySummary[];
}

export interface RowPreview {
  columns: string[];
  rows: Record<string, unknown>[];
  total: number;
  page: number;
  page_size: number;
}
