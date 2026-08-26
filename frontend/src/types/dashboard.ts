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
