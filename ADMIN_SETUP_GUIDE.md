# DQ Command Center - Administrator Setup Guide

## Table of Contents
1. [Initial Setup](#initial-setup)
2. [Secure Admin Provisioning](#secure-admin-provisioning)
3. [First-Time Configuration](#first-time-configuration)
4. [User Management](#user-management)
5. [Data Governance Setup](#data-governance-setup)
6. [Security Best Practices](#security-best-practices)
7. [Troubleshooting](#troubleshooting)

## Initial Setup

### Prerequisites
- Docker and Docker Compose installed
- PostgreSQL 16+ (included in Docker setup)
- Python 3.11+ (for backend)
- Node.js 18+ (for frontend)

### Step 1: Environment Configuration

Create or update `.env` file in the project root:

```bash
# Database Configuration
POSTGRES_USER=dqadmin
POSTGRES_PASSWORD=[REDACTED-DEV-CREDENTIAL]  # Change in production!
POSTGRES_DB=dq_command_center
DATABASE_URL=postgresql+asyncpg://dqadmin:[REDACTED-DEV-CREDENTIAL]@postgres:5432/dq_command_center

# JWT Configuration
JWT_SECRET_KEY=your-secret-key-min-32-characters-do-not-expose!!
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Security
CORS_ORIGINS=http://localhost:5173,http://localhost:80,http://localhost
RATE_LIMIT_PER_MINUTE=20
LOCKOUT_THRESHOLD=5
LOCKOUT_DURATION_MINUTES=15

# Admin Initialization (First Time Setup Only)
INIT_ADMIN_EMAIL=admin@example.com
INIT_ADMIN_PASSWORD=[REDACTED-DEV-CREDENTIAL]
INIT_ADMIN_NAME=Administrator

# Application
APP_NAME=DQ Command Center
ENVIRONMENT=development
LOG_LEVEL=INFO

# Email (Optional - for production)
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=noreply@dqcommandcenter.com
SMTP_USE_TLS=true

# Frontend
VITE_API_BASE_URL=http://localhost:80/api
```

### Step 2: Start the Application

```bash
# Development with Docker
docker-compose up -d

# Monitor logs
docker-compose logs -f backend

# Wait for migrations and initialization
# Expected output:
# "System initialization complete"
# "Access the application at http://localhost"
```

### Step 3: Initial Access

1. Navigate to `http://localhost` in your browser
2. You will be redirected to login page
3. Use credentials set in `INIT_ADMIN_EMAIL` and `INIT_ADMIN_PASSWORD`
4. After successful login, **change the admin password immediately**

## Secure Admin Provisioning

### Security Considerations

⚠️ **IMPORTANT**: Never commit `.env` file to version control. Credentials should be:
- Generated securely
- Stored in secure vaults or configuration management systems
- Rotated regularly
- Never logged to console or exposed in container logs

### Recommended Setup for Production

1. **Use Environment Secrets Management**:
   ```bash
   # AWS Secrets Manager
   aws secretsmanager create-secret --name dq-admin-creds \
     --secret-string '{"email":"admin@company.com","password":"STRONG_PASSWORD"}'
   
   # Or use HashiCorp Vault
   vault kv put secret/dq-admin email="admin@company.com" password="STRONG_PASSWORD"
   ```

2. **Set Credentials During Deployment**:
   ```bash
   docker-compose --env-file <(vault kv get -format=env secret/dq-admin) up
   ```

3. **Remove Initialization Credentials After Setup**:
   ```bash
   # After successful admin creation, clear these:
   INIT_ADMIN_EMAIL=
   INIT_ADMIN_PASSWORD=
   INIT_ADMIN_NAME=
   ```

4. **Enable LDAP/SSO** (Recommended for Enterprise):
   - Admin can configure LDAP directory integration
   - Users authenticate against corporate directory
   - See [SSO Configuration Guide](./docs/SSO_SETUP.md)

## First-Time Configuration

### Step 1: Access Admin Dashboard

After logging in with admin account:
1. Click user icon (top right) → "Settings"
2. Navigate to "Administration" panel

### Step 2: Create Organizations/Departments

1. Go to Admin → Departments
2. Create departments matching your organizational structure:
   - Finance
   - Sales
   - Technology
   - Operations
   - etc.

### Step 3: Set Up Roles

1. Go to Admin → Roles
2. System roles already exist (Super Admin, Admin, Manager, Analyst, User)
3. Create custom roles if needed:
   - Data Quality Manager
   - Data Steward
   - Data Analyst
   - Auditor
   - etc.

### Step 4: Create Initial Users

1. Go to Admin → Users
2. Click "Add User"
3. Fill in user details:
   - Email
   - Full Name
   - Department
   - Role(s)
4. System will send welcome email (if SMTP configured)
5. User will set their own password on first login

## User Management

### Adding Users

```bash
# Via UI
1. Admin → Users → Add User
2. Provide email and select role
3. User receives activation email

# Via API (for automation)
POST /api/v1/users
{
  "email": "newuser@company.com",
  "full_name": "New User",
  "department": "Finance",
  "roles": ["Analyst"]
}
```

### Managing User Permissions

1. Go to Admin → Roles
2. Select role to modify
3. Check/uncheck permissions
4. Click "Save"

Available permissions by module:
- **Dashboard**: View access
- **Data Quality**: View and manage rules, issues
- **Data Governance**: View and manage ownership, stewardship
- **Datasets**: View, manage, upload, export
- **Analytics**: View reports and trends
- **Admin**: User management, audit logs, role management

### Revoking Access

1. Go to Admin → Users
2. Find user
3. Click "Deactivate" (soft delete - keeps history)
4. User will see "Account Inactive" message on next login

### Password Reset

Users can reset their own password:
1. Go to login page → "Forgot Password"
2. Enter email
3. Click link in email
4. Set new password

Admin can force password reset:
1. Admin → Users
2. Find user
3. Click "Reset Password"
4. User will be prompted to set new password on next login

## Data Governance Setup

### Define Data Domains

1. Go to Data Explorer → Data Domains
2. Click "Create Domain"
3. Provide:
   - Domain Name (e.g., "Customer Data", "Financial Records")
   - Description
   - Business Owner (user)
   - Domain Steward (user)

### Register Datasets

1. Go to Data Explorer → Datasets
2. Click "Register Dataset"
3. Provide:
   - Name
   - Domain
   - Type (Table/Collection/API/File/Stream/View)
   - Connection details (database, table, API endpoint, etc.)
   - Owner
   - Steward

### Define Data Elements

1. In Dataset details
2. Click "Define Elements"
3. Add each column/field:
   - Name
   - Data Type
   - Description
   - Business Term
   - Classification (Public/Internal/Restricted/Sensitive)
   - Owner
   - Steward

### Set Quality Targets

1. In Dataset details → Quality Targets
2. Click "Add Target"
3. Set SLA for each dimension:
   - Completeness: >= 95%
   - Accuracy: >= 98%
   - Uniqueness: >= 99%
   - Timeliness: within 2 hours
   - Validity: >= 99%
   - Consistency: >= 97%

### Create Quality Rules

1. Go to Data Quality → Quality Rules
2. Click "Create Rule"
3. Define rule:
   - Name
   - Type (Completeness/Format/Uniqueness/etc.)
   - Dataset/Element
   - Condition/Expression
   - Threshold
   - Action on failure

## Security Best Practices

### 1. Password Policy

- Enforce strong passwords (min 12 characters, mixed case, numbers, symbols)
- Require password change every 90 days
- Prevent reuse of last 5 passwords
- Lock account after 5 failed attempts (15 min lockout)

Admin → Settings → Security Policy

### 2. Authentication & Authorization

- ✅ Enable Multi-Factor Authentication (MFA) for admin users
- ✅ Use short-lived access tokens (15 minutes)
- ✅ Implement role-based access control (RBAC)
- ✅ Audit all administrative actions

### 3. API Security

- ✅ All API endpoints require authentication
- ✅ Rate limiting: 120 requests/minute (adjustable)
- ✅ CORS restricted to known domains
- ✅ Security headers enforced (X-Content-Type-Options, etc.)

### 4. Data Protection

- ✅ Encrypt sensitive data at rest (PostgreSQL encryption)
- ✅ Use TLS/SSL for data in transit (HTTPS)
- ✅ Classify data by sensitivity level
- ✅ Implement row-level security for sensitive datasets

### 5. Audit & Monitoring

- ✅ All API calls logged with user, timestamp, action
- ✅ Admin actions require audit trail
- ✅ Failed login attempts logged and monitored
- ✅ Access to sensitive data logged

View audit logs:
```bash
Admin → Audit Logs
Filter by:
- User
- Action
- Resource
- Date Range
```

### 6. Network Security

- ✅ Run behind reverse proxy (nginx included)
- ✅ Restrict backend access to frontend only
- ✅ Use VPC/private networks in cloud environments
- ✅ Regular security updates and patching

### 7. Secrets Management

```bash
# Development (never use in production!)
# Secrets stored in .env file

# Production (recommended)
# Use AWS Secrets Manager, HashiCorp Vault, or similar
# Never store secrets in code or configuration files
# Rotate secrets regularly

# Critical secrets that must be managed securely:
- JWT_SECRET_KEY
- Database passwords
- API keys
- Encryption keys
```

## Troubleshooting

### Initialization Issues

**Problem**: "System initialization failed"

```bash
# Check logs
docker-compose logs backend

# Common causes:
1. Database not ready - wait for healthcheck
   docker-compose logs postgres

2. Alembic migration failed
   docker-compose exec backend alembic current
   docker-compose exec backend alembic upgrade head

3. Invalid environment variables
   Verify .env file syntax
```

### Can't Login

**Problem**: "Invalid credentials" or "User not found"

```bash
# Verify admin user exists
docker-compose exec postgres psql -U dqadmin -d dq_command_center -c \
  "SELECT email, is_super_admin FROM users WHERE is_super_admin=true;"

# If admin doesn't exist, you need to reinitialize:
1. Remove data: docker-compose down -v
2. Update .env with admin credentials
3. Restart: docker-compose up
```

**Problem**: "Account locked after multiple failed attempts"

```bash
# Wait 15 minutes or ask admin to unlock via UI:
Admin → Users → [Username] → Unlock Account
```

### Database Issues

**Problem**: "Could not connect to database"

```bash
# Check PostgreSQL is healthy
docker-compose ps postgres

# Check connection string in .env
# Verify POSTGRES_PASSWORD in docker-compose matches .env

# Force restart database
docker-compose down
docker-compose up postgres -d
# Wait for healthcheck (observe logs)
docker-compose up
```

**Problem**: "Migration failed"

```bash
# Check what migrations exist
docker-compose exec backend alembic history

# Rollback and re-apply
docker-compose exec backend alembic downgrade -1
docker-compose exec backend alembic upgrade head

# Check for SQL errors
docker-compose logs backend | grep -i error
```

### API Issues

**Problem**: "Unauthorized" on protected endpoints

```bash
# Verify token is being sent
# Check Authorization header: "Authorization: Bearer <token>"

# Token expired?
# Use refresh token endpoint to get new token
POST /api/v1/auth/refresh
{ "refresh_token": "your_refresh_token" }

# Token invalid?
# Logout and login again to get fresh tokens
```

### Performance Issues

**Problem**: Dashboard slow to load

```bash
# Check database performance
docker-compose exec postgres psql -U dqadmin -d dq_command_center -c \
  "SELECT query, calls, mean_time FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"

# Add indexes if needed (work with DBA)
# Check for missing metrics cache
```

## Support & Next Steps

- For security issues, contact security@company.com
- For general support, see [README.md](./README.md)
- For API documentation, visit `http://localhost/docs` (Swagger UI)
- For detailed reference, see [Architecture Guide](./docs/ARCHITECTURE.md)

---

**Last Updated**: August 2024  
**Version**: 1.0.0  
**Status**: Production Ready
