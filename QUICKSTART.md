# DQ Command Center - Quick Start Guide

Get the Data Quality Command Center up and running in 5 minutes.

## Prerequisites

- Docker & Docker Compose installed
- Git (to clone the repository)
- 2GB+ free disk space

## Step 1: Clone & Setup (1 minute)

```bash
# Navigate to project directory
cd dq-command-center-v2

# Copy environment file (uses defaults for dev)
cp .env.example .env

# Review default settings in .env (optional)
cat .env
```

## Step 2: Start Services (2 minutes)

```bash
# Start all services (database, backend, frontend, nginx)
docker-compose up -d

# Watch initialization
docker-compose logs -f backend

# Wait for message: "System initialization complete"
# (Should take ~30 seconds)
```

## Step 3: Verify Services (1 minute)

```bash
# Check all services are running
docker-compose ps

# Should show:
# - dq-postgres (healthy)
# - dq-backend (running)
# - dq-frontend (running)  
# - dq-nginx (running)
```

## Step 4: Access Application (1 minute)

### Frontend
Open your browser: **http://localhost**

### Swagger API Docs
Open your browser: **http://localhost:8000/docs**

## Default Login Credentials

The system creates a super admin on startup with these default credentials:

```
Email:    admin@dqcommandcenter.com
Password: [REDACTED-DEV-CREDENTIAL]
```

⚠️ **IMPORTANT**: Change these credentials immediately after first login!

## Post-Startup Tasks

### Change Admin Password
1. Login with default credentials
2. Click user icon (top right) → Settings
3. Click "Change Password"
4. Enter new secure password
5. Save

### Create Test Users
1. Go to Admin → Users
2. Click "Add User"
3. Enter:
   - Email: analyst@company.local
   - Full Name: Test Analyst
   - Department: Analytics
   - Role: Analyst
4. Click "Create"

### Create Sample Domains
1. Go to Data Explorer → Data Domains
2. Click "Create Domain"
3. Enter:
   - Name: Customer Data
   - Description: Customer and account information
4. Click "Create"

## Common Operations

### View Dashboard
1. Click "Dashboard" (left sidebar)
2. See quality metrics and trends

### Create Dataset
1. Go to Data Explorer
2. Click "New Dataset"
3. Fill in details:
   - Name: Customers
   - Domain: Customer Data
   - Type: Table
4. Click "Create"

### View API Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Troubleshooting

### Services won't start
```bash
# Check logs
docker-compose logs postgres
docker-compose logs backend

# Force restart
docker-compose down
docker-compose up -d
```

### Can't login
```bash
# Reset database and reinitialize
docker-compose down -v
docker-compose up -d
# Wait 30 seconds for initialization
```

### Can't access http://localhost
```bash
# Check nginx logs
docker-compose logs nginx

# Verify frontend is running
docker-compose logs frontend

# Try direct backend access
curl http://localhost:8000/health
```

### Port already in use
```bash
# See what's using the port
lsof -i :80  # Frontend
lsof -i :8000  # Backend
lsof -i :5432  # Database

# Kill the process or use different port
docker-compose -f docker-compose.yml -p dq2 up -d
```

## Stopping Services

```bash
# Stop all services (data persists)
docker-compose down

# Stop and delete all data (fresh start)
docker-compose down -v

# View logs after stopping
docker-compose logs backend
```

## Next Steps

### For Administrators
→ Read [ADMIN_SETUP_GUIDE.md](./ADMIN_SETUP_GUIDE.md)
- User management
- Data governance setup
- Quality rules configuration
- Security settings

### For Production Deployment
→ Read [PRODUCTION_DEPLOYMENT.md](./PRODUCTION_DEPLOYMENT.md)
- Security hardening
- Database optimization
- Monitoring setup
- Backup strategy

### For Development
→ Read [docs/IMPLEMENTATION_GUIDE.md](./docs/IMPLEMENTATION_GUIDE.md)
- Architecture details
- Adding new features
- API integration

### For Testing
→ Read [TESTING_GUIDE.md](./TESTING_GUIDE.md)
- Running tests
- Writing tests
- Coverage targets

## Key URLs

| Service | URL |
|---------|-----|
| **Frontend** | http://localhost |
| **Swagger API** | http://localhost:8000/docs |
| **ReDoc API** | http://localhost:8000/redoc |
| **OpenAPI Spec** | http://localhost:8000/openapi.json |
| **Database** | localhost:5432 (internal only) |

## What's Included

### Frontend
- ✅ Modern login/registration
- ✅ Real-time quality dashboard
- ✅ Data explorer for browsing
- ✅ Quality rules management
- ✅ Admin controls
- ✅ Responsive mobile design

### Backend
- ✅ FastAPI application
- ✅ PostgreSQL database
- ✅ JWT authentication
- ✅ Role-based access control
- ✅ Comprehensive audit logging
- ✅ Data quality analytics

### Infrastructure
- ✅ Docker containerization
- ✅ Nginx reverse proxy
- ✅ Automated migrations
- ✅ Health checks
- ✅ Volume management

## Environment Variables

Key variables you can customize:

```bash
# Database (change in production!)
POSTGRES_USER=dqadmin
POSTGRES_PASSWORD=[REDACTED-DEV-CREDENTIAL]
POSTGRES_DB=dq_command_center

# Security
JWT_SECRET_KEY=dev-secret-key-...
CORS_ORIGINS=http://localhost:5173,http://localhost:80

# Application
APP_NAME=DQ Command Center
ENVIRONMENT=development
LOG_LEVEL=DEBUG
```

Full options: See `.env` file

## Architecture Overview

```
Browser (http://localhost)
       ↓
Nginx (Reverse Proxy, Rate Limit, SSL)
       ↓
FastAPI Backend (http://localhost:8000)
       ↓
PostgreSQL Database (port 5432)
```

## Performance Expectations

| Operation | Time |
|-----------|------|
| Container startup | 30-60 seconds |
| Database ready | 10 seconds |
| First login | < 1 second |
| Dashboard load | < 2 seconds |
| API response (avg) | < 100ms |

## Getting Help

1. **Documentation**: Read ADMIN_SETUP_GUIDE.md
2. **Troubleshooting**: See ADMIN_SETUP_GUIDE.md troubleshooting section
3. **API Help**: Visit http://localhost:8000/docs
4. **Logs**: `docker-compose logs [service]`

---

**Ready to go!** 🚀

Start with: `docker-compose up -d`

Then access: http://localhost

Questions? Check the [ADMIN_SETUP_GUIDE.md](./ADMIN_SETUP_GUIDE.md)
