export interface DashboardStats {
  total_users: number;
  active_users: number;
  roles_count: number;
  departments_count: number;
  audit_events_today: number;
}

export interface ChartDataPoint {
  date: string;
  count: number;
}

export interface RecentActivityItem {
  id: string;
  user_email: string | null;
  action: string;
  entity_type: string;
  created_at: string;
}

export interface DashboardResponse {
  stats: DashboardStats;
  registration_chart: ChartDataPoint[];
  login_chart: ChartDataPoint[];
  recent_activity: RecentActivityItem[];
}

export interface DimensionScore {
  dimension: string;
  score: number | null;
  status: string;
  rule_count: number;
}

export interface QualityTrendPoint {
  date: string;
  pass_rate: number;
  total_runs: number;
}

export interface DashboardHealthSummary {
  // null until at least one of the user's datasets has been scanned
  health_score: number | null;
  scanned_datasets?: number;
  status: string;
  dimensions: Record<string, DimensionScore>;
  open_issues: number;
  critical_issues: number;
  recent_trend: string;
  total_datasets: number;
  total_quality_rules: number;
  daily_trend: QualityTrendPoint[];
}

export interface QualityIssueSummary {
  id: string;
  description: string | null;
  severity: string;
  status: string;
  dataset_name: string | null;
  detected_at: string;
}
