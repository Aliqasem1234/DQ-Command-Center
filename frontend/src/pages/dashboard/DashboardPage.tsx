import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Box, Typography, Grid, Card, CardContent, List, ListItem, ListItemText, Chip,
} from '@mui/material';
import {
  People as PeopleIcon, AdminPanelSettings as RolesIcon,
  Business as DeptIcon, History as AuditIcon, PersonAdd as RegisterIcon,
  Login as LoginIcon,
} from '@mui/icons-material';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line } from 'recharts';
import { dashboardService } from '../../services/dashboardService';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import type { DashboardResponse } from '../../types';

export function DashboardPage() {
  const { t } = useTranslation();
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const result = await dashboardService.getStats();
        setData(result);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) return <LoadingSpinner />;

  const stats = data?.stats;
  const kpiCards = [
    { label: t('dashboard.activeUsers'), value: String(stats?.active_users ?? 0), icon: <PeopleIcon />, color: '#388e3c' },
    { label: t('nav.roles', 'Roles'), value: String(stats?.roles_count ?? 0), icon: <RolesIcon />, color: '#1976d2' },
    { label: t('nav.departments', 'Departments'), value: String(stats?.departments_count ?? 0), icon: <DeptIcon />, color: '#f57c00' },
    { label: t('dashboard.auditToday', 'Audit Events Today'), value: String(stats?.audit_events_today ?? 0), icon: <AuditIcon />, color: '#d32f2f' },
  ];

  return (
    <Box>
      <Typography variant="h4" fontWeight={600} gutterBottom>{t('dashboard.title')}</Typography>

      <Grid container spacing={3} sx={{ mt: 1 }}>
        {kpiCards.map((kpi) => (
          <Grid item xs={12} sm={6} md={3} key={kpi.label}>
            <Card>
              <CardContent sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Box sx={{ p: 1.5, borderRadius: 2, bgcolor: `${kpi.color}15`, color: kpi.color, display: 'flex' }}>{kpi.icon}</Box>
                <Box>
                  <Typography variant="h4" fontWeight={700}>{kpi.value}</Typography>
                  <Typography variant="body2" color="text.secondary">{kpi.label}</Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Grid container spacing={3} sx={{ mt: 2 }}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <RegisterIcon color="primary" /> {t('dashboard.registrations', 'Registrations')}
              </Typography>
              {data?.registration_chart && data.registration_chart.length > 0 ? (
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={data.registration_chart}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                    <YAxis allowDecimals={false} />
                    <Tooltip />
                    <Bar dataKey="count" fill="#1976d2" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <Typography variant="body2" color="text.secondary">{t('common.noData')}</Typography>
              )}
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <LoginIcon color="primary" /> {t('dashboard.logins', 'Logins')}
              </Typography>
              {data?.login_chart && data.login_chart.length > 0 ? (
                <ResponsiveContainer width="100%" height={250}>
                  <LineChart data={data.login_chart}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                    <YAxis allowDecimals={false} />
                    <Tooltip />
                    <Line type="monotone" dataKey="count" stroke="#388e3c" strokeWidth={2} dot={{ r: 3 }} />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <Typography variant="body2" color="text.secondary">{t('common.noData')}</Typography>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Box sx={{ mt: 3 }}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>{t('dashboard.recentActivity')}</Typography>
            {data?.recent_activity && data.recent_activity.length > 0 ? (
              <List dense>
                {data.recent_activity.slice(0, 10).map((item) => (
                  <ListItem key={item.id} divider>
                    <ListItemText
                      primary={<>{item.user_email || 'System'} <Chip label={item.action} size="small" variant="outlined" sx={{ ml: 1 }} /> <strong>{item.entity_type}</strong></>}
                      secondary={new Date(item.created_at).toLocaleString()}
                    />
                  </ListItem>
                ))}
              </List>
            ) : (
              <Typography variant="body2" color="text.secondary">{t('common.noData')}</Typography>
            )}
          </CardContent>
        </Card>
      </Box>
    </Box>
  );
}
