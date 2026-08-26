# DQ Command Center - Production Deployment Guide

## Pre-Deployment Checklist

### Security Hardening

- [ ] Generated strong JWT_SECRET_KEY (min 32 chars, cryptographically secure)
- [ ] Updated database credentials (not defaults)
- [ ] Configured CORS to specific production domain only
- [ ] Enabled HTTPS/TLS for all traffic
- [ ] Configured security headers (CSP, X-Frame-Options, etc.)
- [ ] Set up secure password policy
- [ ] Enabled audit logging
- [ ] Configured rate limiting appropriately
- [ ] Set up backup strategy
- [ ] Tested disaster recovery procedures

### Infrastructure

- [ ] Provisioned production database (managed service recommended)
- [ ] Set up load balancer (if multi-instance)
- [ ] Configured monitoring and alerting
- [ ] Set up log aggregation
- [ ] Configured secrets management (Vault/Secrets Manager)
- [ ] Set up CI/CD pipeline
- [ ] Configured auto-scaling (if applicable)
- [ ] Tested failover procedures

### Data & Compliance

- [ ] Data classification scheme defined
- [ ] Data retention policy established
- [ ] Compliance requirements documented (GDPR, CCPA, etc.)
- [ ] Privacy policy updated
- [ ] Encryption at rest configured
- [ ] Encryption in transit configured
- [ ] Data masking for sensitive fields implemented

### Operational

- [ ] Runbooks documented for common tasks
- [ ] On-call rotation established
- [ ] SLA targets defined
- [ ] Change management process in place
- [ ] Rollback procedures tested
- [ ] Training completed for operations team
- [ ] Documentation finalized

## Environment Configuration

### Production .env Template

```bash
# ===== DATABASE =====
POSTGRES_HOST=prod-db.internal.company.com
POSTGRES_PORT=5432
POSTGRES_USER=dq_prod_user
POSTGRES_PASSWORD=${DB_PASSWORD}  # From secrets vault
POSTGRES_DB=dq_command_center_prod
DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}

# ===== SECURITY =====
JWT_SECRET_KEY=${JWT_SECRET_KEY}  # From secrets vault - STRONG!
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# ===== CORS & HEADERS =====
CORS_ORIGINS=https://dq.company.com,https://admin.dq.company.com
# Add security headers:
# X-Content-Type-Options: nosniff
# X-Frame-Options: DENY
# X-XSS-Protection: 1; mode=block
# Strict-Transport-Security: max-age=31536000

# ===== RATE LIMITING =====
RATE_LIMIT_PER_MINUTE=100
LOCKOUT_THRESHOLD=5
LOCKOUT_DURATION_MINUTES=30

# ===== SMTP (Email Notifications) =====
SMTP_HOST=smtp.company.com
SMTP_PORT=587
SMTP_USER=noreply@company.com
SMTP_PASSWORD=${SMTP_PASSWORD}  # From secrets vault
SMTP_FROM_EMAIL=noreply@company.com
SMTP_USE_TLS=true

# ===== APPLICATION =====
APP_NAME=DQ Command Center
ENVIRONMENT=production
LOG_LEVEL=INFO
SECRET_KEY=${SECRET_KEY}  # From secrets vault

# ===== FRONTEND =====
VITE_API_BASE_URL=https://api.dq.company.com

# ===== DO NOT SET (Use manual admin creation) =====
# INIT_ADMIN_EMAIL=
# INIT_ADMIN_PASSWORD=
```

## Deployment Architecture

### Recommended Setup

```
┌─────────────────────────────────────────────────────────┐
│                    Internet / CDN                       │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│         AWS Application Load Balancer (HTTPS)           │
│        - SSL/TLS Termination                            │
│        - Health checks                                  │
│        - Request logging                                │
└──────────────────────┬──────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
   ┌────▼────┐  ┌────────┐  ┌────────┐
   │ Backend  │  │Frontend│  │Nginx   │
   │ (Node 1) │  │(Node 1)│  │(ALB)   │
   └─────┬────┘  └────────┘  └────────┘
        │
┌──────▼─────────────────────────────────────────────────┐
│              Managed RDS PostgreSQL                     │
│  - Multi-AZ with automated failover                     │
│  - Automated backups (35 day retention)                 │
│  - Encryption at rest (AWS KMS)                         │
│  - Enhanced monitoring                                  │
│  - Parameter group for optimization                     │
└──────────────────────────────────────────────────────────┘
```

### Container Deployment

#### Using ECS/Fargate (AWS)

```yaml
# ecs-task-definition.json
{
  "family": "dq-command-center-prod",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "containerDefinitions": [
    {
      "name": "backend",
      "image": "YOUR_REGISTRY/dq-backend:v1.0.0",
      "portMappings": [{
        "containerPort": 8000,
        "hostPort": 8000
      }],
      "environment": [
        { "name": "ENVIRONMENT", "value": "production" },
        { "name": "LOG_LEVEL", "value": "INFO" }
      ],
      "secrets": [
        {
          "name": "DATABASE_URL",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:dq-db-url"
        },
        {
          "name": "JWT_SECRET_KEY",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:dq-jwt-secret"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/dq-command-center",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    },
    {
      "name": "frontend",
      "image": "YOUR_REGISTRY/dq-frontend:v1.0.0",
      "portMappings": [{
        "containerPort": 5173,
        "hostPort": 5173
      }],
      "environment": [
        { "name": "VITE_API_BASE_URL", "value": "https://api.dq.company.com" }
      ]
    }
  ]
}
```

#### Using Kubernetes

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dq-backend
  namespace: dq-prod
spec:
  replicas: 3
  selector:
    matchLabels:
      app: dq-backend
  template:
    metadata:
      labels:
        app: dq-backend
    spec:
      containers:
      - name: backend
        image: registry.company.com/dq-backend:v1.0.0
        ports:
        - containerPort: 8000
        env:
        - name: ENVIRONMENT
          value: "production"
        envFrom:
        - secretRef:
            name: dq-secrets
        - configMapRef:
            name: dq-config
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        securityContext:
          runAsNonRoot: true
          runAsUser: 1000
          readOnlyRootFilesystem: true
          allowPrivilegeEscalation: false
```

## Database Setup

### PostgreSQL Configuration

```sql
-- Production connection settings
ALTER SYSTEM SET shared_buffers = '4GB';
ALTER SYSTEM SET effective_cache_size = '12GB';
ALTER SYSTEM SET maintenance_work_mem = '1GB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;
ALTER SYSTEM SET random_page_cost = 1.1;
ALTER SYSTEM SET effective_io_concurrency = 200;

-- Create read replica for analytics
-- On AWS RDS: Create read replica through console
-- Set to manual promotion in case of failover

-- Enable encryption
-- AWS RDS: Enable encryption at rest with KMS
-- Certificates: Use AWS Certificate Manager

-- Backup configuration
-- Automated backups: 35 days retention
-- Manual snapshots: Daily (keep 7 days)
-- Test restore procedure monthly

SELECT pg_reload_conf();
```

### Performance Tuning

```sql
-- Add indexes for common queries
CREATE INDEX idx_datasets_domain_id ON datasets(domain_id);
CREATE INDEX idx_data_elements_dataset_id ON data_elements(dataset_id);
CREATE INDEX idx_quality_issues_dataset_id ON quality_issues(dataset_id);
CREATE INDEX idx_quality_issues_status ON quality_issues(status);
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);

-- VACUUM and ANALYZE
VACUUM ANALYZE;

-- Monitor slow queries
CREATE EXTENSION pg_stat_statements;
```

## Monitoring & Alerts

### Key Metrics to Monitor

1. **Application Health**
   - API response time (p95, p99)
   - Error rate (4xx, 5xx)
   - Uptime/availability
   - Request throughput

2. **Database Performance**
   - Connection count
   - Query latency
   - Slow query log
   - Replication lag (if replicated)

3. **Infrastructure**
   - CPU utilization (< 70%)
   - Memory utilization (< 80%)
   - Disk usage (< 85%)
   - Network I/O

4. **Security**
   - Failed login attempts
   - Unauthorized API calls
   - Rate limit violations
   - Audit log volume

### CloudWatch Alarms (AWS)

```python
# Create alarms for critical metrics
alarms = {
    "api-error-rate-high": {
        "metric": "ErrorRate",
        "threshold": 5,  # 5% error rate
        "action": "send_email,create_ticket"
    },
    "database-connection-high": {
        "metric": "DatabaseConnections",
        "threshold": 80,  # % of max connections
        "action": "send_email,page_oncall"
    },
    "disk-usage-high": {
        "metric": "DiskUtilization",
        "threshold": 85,
        "action": "send_email,page_oncall"
    },
    "failed-logins-spike": {
        "metric": "FailedLogins",
        "threshold": 50,  # in 5 minutes
        "action": "send_email,create_incident"
    }
}
```

## Backup & Disaster Recovery

### Backup Strategy

```bash
# Daily automated backups (AWS RDS)
- Backup window: 02:00 UTC (off-peak)
- Retention: 35 days
- Multi-AZ backup

# Weekly snapshot backups
- Day: Sunday 03:00 UTC
- Manual retention: 7 weeks
- Stored in S3 for long-term archive

# Test restore monthly
- Restore to staging environment
- Verify data integrity
- Document time-to-restore

# Database encryption
- KMS key rotation: Annual
- Cross-region backup replication
```

### Disaster Recovery Procedures

**RTO (Recovery Time Objective)**: 1 hour  
**RPO (Recovery Point Objective)**: 15 minutes

```bash
# Scenario 1: Single Instance Failure
1. ALB detects unhealthy instance (2 min)
2. Auto-scaling launches replacement (5 min)
3. New instance joins ECS cluster (3 min)
4. Total RTO: ~10 minutes

# Scenario 2: Database Failure
1. RDS Multi-AZ automatic failover (2-5 min)
2. Application reconnects to new primary
3. No data loss (replicated in real-time)
4. Total RTO: ~5 minutes

# Scenario 3: Entire Region Down
1. Activate disaster recovery in secondary region (manual)
2. Restore database from latest backup (15 min)
3. Deploy application stack (10 min)
4. Update DNS to point to DR region (5 min)
5. Total RTO: ~30 minutes
```

## Scaling

### Horizontal Scaling

```bash
# Add more backend instances
docker-compose scale backend=5

# Or with Kubernetes
kubectl scale deployment dq-backend --replicas=5

# Load balancer distributes traffic automatically
# Monitor: Application Load Balancer metrics
```

### Database Scaling

```sql
-- Read replica for analytics queries
-- Primary: Write operations
-- Replica: Read-only analytics queries

-- Implement query routing:
-- Write queries -> primary database
-- Read queries  -> replica database

-- If replica falls behind:
-- 1. Check replication lag
-- 2. Increase wal_keep_size on primary
-- 3. Monitor network latency
```

## Rollback Procedures

### Application Rollback

```bash
# Version 1.0.1 deployed, issues found

# Option 1: Quick rollback (if in-place)
docker-compose -f docker-compose-prod.yml down
docker pull registry.company.com/dq-backend:v1.0.0
docker-compose -f docker-compose-prod.yml up -d

# Option 2: Blue-Green Deployment
# 1. Keep two identical stacks (blue=old, green=new)
# 2. If issues, switch ALB to blue (instant rollback)
# 3. Investigate green environment

# Option 3: Kubernetes rollback
kubectl rollout undo deployment/dq-backend
```

### Database Rollback

```sql
-- If schema migration causes issues:
-- 1. Stop applications
-- 2. Restore database from backup (point-in-time)
-- 3. Run previous migrations
-- 4. Restart applications

-- Test procedure BEFORE production:
-- 1. Create snapshot of production database
-- 2. Restore to staging
-- 3. Apply migration
-- 4. Test application
-- 5. Rollback to snapshot
-- 6. Verify rollback procedure works
```

## Security Maintenance

### Regular Security Tasks

**Weekly**
- Review failed login attempts
- Monitor for unusual API patterns
- Check disk usage and log rotation

**Monthly**
- Review audit logs for suspicious activities
- Test backup restoration
- Verify security patches availability
- Review access control lists

**Quarterly**
- Security audit of infrastructure
- Penetration testing
- Review and update security policies
- Disaster recovery drill

**Annually**
- SOC 2 audit (if required)
- GDPR/CCPA compliance review
- Rotate all long-lived credentials
- Update security documentation

## Go-Live Checklist

- [ ] All security measures implemented and tested
- [ ] Monitoring and alerting active
- [ ] Backup and restore procedures tested
- [ ] Runbooks and documentation complete
- [ ] Team trained on operational procedures
- [ ] Change management approval obtained
- [ ] Rollback procedures tested
- [ ] Performance testing completed
- [ ] Load testing completed (at least 2x expected peak)
- [ ] Security scanning completed (SAST, DAST)
- [ ] Compliance requirements verified
- [ ] DNS cutover plan documented
- [ ] Communications plan finalized
- [ ] Post-launch support plan established

## Support & Escalation

**Critical Issues** (System Down)
- Page on-call engineer immediately
- Create incident in status page
- Establish war room

**High Priority** (Degraded Performance)
- Notify on-call engineer
- Investigate root cause
- Implement fix or rollback

**Medium Priority** (Limited Functionality)
- Create ticket in issue tracking system
- Schedule for next maintenance window
- Communicate impact to users

**Low Priority** (Minor Issues)
- Create ticket for backlog
- No immediate action required

---

**Last Updated**: August 2024  
**Version**: 1.0.0  
**Status**: Production Ready for Deployment
