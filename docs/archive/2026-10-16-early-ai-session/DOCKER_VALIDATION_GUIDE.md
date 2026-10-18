# DQ COMMAND CENTER V2 — DOCKER VALIDATION & TESTING GUIDE

**Status**: Ready for local Docker testing  
**Environment**: Windows with Docker Desktop  
**Expected Date**: 2026-10-16

---

## PART 1: DOCKER CONFIGURATION ANALYSIS

### Architecture Review ✅

**Services Configured**:
1. **PostgreSQL 16-Alpine** (Port 5432)
   - Health check: pg_isready every 5s
   - Data persisted in postgres_data volume
   - Init script: scripts/init-db.sql

2. **FastAPI Backend** (Port 8000)
   - Health check: curl to /health every 5s
   - Startup sequence:
     - Database migrations (alembic upgrade head)
     - Database seeding (python -m app.core.seed_secure)
     - Start uvicorn server
   - Environment: 18 variables configured

3. **Vite Frontend** (Port 5173)
   - Development mode
   - Hot reload enabled
   - Depends on healthy backend

4. **Nginx** (Port 80)
   - Alpine Linux
   - Security headers configured
   - Rate limiting on auth endpoints
   - Health check: wget to /health

### Configuration Quality ✅

✅ Health checks properly configured  
✅ Dependencies properly ordered  
✅ Rate limiting configured  
✅ Security headers in place  
✅ Volume mounting correct  
✅ Network isolation with bridge network  

### Potential Issues to Monitor

⚠️ **Nginx health check**: Uses wget, ensure available in container  
⚠️ **Frontend development mode**: May not be optimal for performance testing  
⚠️ **CORS configuration**: Must match deployed frontend origin  
⚠️ **SMTP configuration**: Must be set for email verification  

---

## PART 2: LOCAL TESTING PROCEDURE

### Prerequisites

- Windows 10/11 with Docker Desktop
- docker-compose installed
- Project directory: C:\Users\aliqa\OneDrive\Desktop\dq-command-center-v2

### Step 1: Prepare Environment

```bash
cd C:\Users\aliqa\OneDrive\Desktop\dq-command-center-v2

# Verify .env file exists and is configured
cat .env | head -20
```

**Expected**: Should show POSTGRES_USER, DATABASE_URL, JWT_SECRET_KEY, etc.

### Step 2: Clean Start (SAFE - Preserves Data)

```bash
# Stop containers (do NOT use -v flag)
docker-compose down

# Verify no running containers
docker ps -a

# Verify postgres_data volume still exists
docker volume ls | grep postgres_data
```

**Expected**: postgres_data volume should persist

### Step 3: Full Build and Startup

```bash
# Build all services
docker-compose up --build

# This will:
# 1. Build backend Docker image
# 2. Build frontend Docker image
# 3. Start PostgreSQL
# 4. Run database migrations
# 5. Seed roles and permissions
# 6. Start backend server
# 7. Start frontend dev server
# 8. Start nginx

# Expected startup sequence (watch logs):
# postgres: "database system is ready to accept connections"
# backend: "Uvicorn running on 0.0.0.0:8000"
# frontend: "Local: http://localhost:5173"
# nginx: healthy
```

### Step 4: Verify Service Health

**In another terminal**:

```bash
# Check all services running
docker-compose ps

# Expected output:
# NAME              STATUS
# dq-postgres       Up (healthy)
# dq-backend        Up (healthy)
# dq-frontend       Up
# dq-nginx          Up (healthy)
```

**Test API health**:

```bash
curl -v http://localhost:8000/health
# Expected: 200 OK

curl -v http://localhost/health
# Expected: 200 OK (through nginx)
```

---

## PART 3: AUTOMATED TEST EXECUTION

### Run Backend Test Suite

```bash
# Option A: Run inside container
docker-compose exec backend pytest tests/test_rbac.py -v

# Option B: Run locally (if Python env configured)
cd backend
pytest tests/test_rbac.py -v --tb=short
```

**Expected Results**:
- test_admin_can_access_admin_endpoints: ✅ PASSED
- test_role_permissions_mapping: ✅ PASSED
- test_protected_route_guard_exists: ✅ PASSED
- test_registration_creates_regular_user_only: May fail (endpoint validation)
- test_dataset_ownership_enforcement: May fail (needs refinement)
- test_invalid_credentials_rejected: May fail (needs API path verification)

### Run All Backend Tests

```bash
docker-compose exec backend pytest tests/ -v --tb=short
```

---

## PART 4: MANUAL WORKFLOW TESTING

### Test Case A: Regular User Workflow

**1. Register New User**
- Navigate to http://localhost (or http://localhost:5173 for frontend)
- Click "Register"
- Fill form:
  - Email: testuser@example.com
  - Password: TestPassword123!
  - First Name: Test
  - Last Name: User
- Submit
- **Expected**: Registration success OR email verification prompt

**2. Login as User**
- Email: testuser@example.com
- Password: TestPassword123!
- **Expected**: Login success, redirected to dashboard

**3. Access Permitted Pages**
- Dashboard: ✅ Should load
- Datasets: ✅ Should load
- Data Quality: ✅ Should load
- Quality Monitoring: ✅ Should load
- Governance: ✅ Should load
- Profile: ✅ Should load

**4. Test Admin Page Access Denial**
- Try navigating to /users
- **Expected**: 403 Forbidden page

- Try navigating to /roles
- **Expected**: 403 Forbidden page

- Try navigating to /departments
- **Expected**: 403 Forbidden page

- Try navigating to /audit
- **Expected**: 403 Forbidden page

**5. Logout**
- Click Logout
- **Expected**: Redirected to login page, session cleared

### Test Case B: Administrator Workflow

**1. Login as Admin**
- Email: admin@test.com (from .env INIT_ADMIN_EMAIL)
- Password: (from .env INIT_ADMIN_PASSWORD)
- **Expected**: Login success, admin navigation visible

**2. Access Admin Pages**
- Users: ✅ Should load
- Roles: ✅ Should load
- Departments: ✅ Should load
- Audit Logs: ✅ Should load

**3. Verify Admin Features**
- User Management: ✅ Should work
- Role Management: ✅ Should work
- Department Management: ✅ Should work
- View Audit Logs: ✅ Should work

**4. Access Business Features**
- Dashboard: ✅ Should work
- Datasets: ✅ Should work
- Data Quality: ✅ Should work
- Governance: ✅ Should work

**5. Logout**
- Click Logout
- **Expected**: Redirected to login page

### Test Case C: Dataset Ownership & Cross-User Access

**1. Create Test Data (As Admin)**
- Create Dataset A
- Assign ownership to test user

**2. Login as Regular User**
- Verify Dataset A is visible
- Verify User can edit/view Dataset A

**3. Create Second User Test**
- Create Test User 2
- Create Dataset B owned by Test User 2

**4. Test Cross-User Access (As Test User 1)**
- Try accessing /api/v1/datasets/{datasetB_id}
- **Expected**: 403 Forbidden or no dataset in list

**5. Test Ownership Enforcement**
- Try accessing another user's dataset directly via URL
- **Expected**: Appropriate access denied response

---

## PART 5: VERIFICATION CHECKLIST

### Container Health
- [ ] All 4 containers running
- [ ] All 4 containers show healthy status
- [ ] No restart loops
- [ ] No error logs in docker-compose logs

### Database
- [ ] PostgreSQL is healthy
- [ ] Database migrations completed successfully
- [ ] Roles seeded (5 roles present)
- [ ] Permissions seeded (16 permissions present)
- [ ] Admin user created
- [ ] Existing data preserved (if applicable)

### Backend API
- [ ] /health endpoint returns 200
- [ ] API documentation available at /docs
- [ ] All endpoints accessible through nginx
- [ ] Rate limiting working on /auth endpoints
- [ ] CORS headers present

### Frontend
- [ ] Frontend loads at http://localhost or http://localhost:5173
- [ ] No console errors in browser
- [ ] No TypeScript compilation errors
- [ ] Styling loads correctly (dark mode)
- [ ] Navigation items appropriate for role

### Authentication & Authorization
- [ ] User registration creates User role
- [ ] Admin login successful
- [ ] User login successful
- [ ] Tokens generated and valid
- [ ] Admin sees admin menu items
- [ ] User doesn't see admin menu items
- [ ] Access denial for unauthorized pages works

### Security
- [ ] Security headers present (HSTS, CSP, etc.)
- [ ] Rate limiting active on auth endpoints
- [ ] HTTPS ready (headers configured)
- [ ] Passwords hashed (verified in DB)
- [ ] Tokens have expiration

### Data Protection
- [ ] User A cannot see User B's datasets
- [ ] Dataset ownership enforced on API
- [ ] Cross-user access attempts rejected
- [ ] File uploads only accessible to owner

---

## PART 6: TROUBLESHOOTING GUIDE

### Issue: Nginx shows unhealthy

**Symptoms**: `docker-compose ps` shows nginx as "Exited" or "Unhealthy"

**Diagnosis**:
```bash
docker-compose logs nginx
```

**Common Causes**:
1. **wget not available**: Check Dockerfile for wget installation
2. **Backend not healthy**: Check backend logs first
3. **Port 80 already in use**: Check `netstat -ano | findstr :80`
4. **Configuration error**: Check `/etc/nginx/nginx.conf` mounting

**Fix**:
```bash
# If nginx config is wrong:
docker-compose restart nginx

# If backend is the issue:
docker-compose logs backend
docker-compose restart backend
```

### Issue: Backend migrations fail

**Symptoms**: Backend container exits with migration error

**Diagnosis**:
```bash
docker-compose logs backend | grep -i alembic
```

**Fix**:
```bash
# Restart database and backend
docker-compose restart postgres
docker-compose restart backend
```

### Issue: Frontend can't connect to API

**Symptoms**: Console errors about API calls failing

**Check**:
```bash
# Verify VITE_API_BASE_URL in .env
cat .env | grep VITE_API_BASE_URL

# Expected: VITE_API_BASE_URL=http://localhost/api
```

**Fix**: Update frontend .env and restart
```bash
docker-compose restart frontend
```

### Issue: Tests fail with "endpoint not found"

**Symptoms**: test_registration_creates_regular_user_only fails with 404

**Root Cause**: API endpoint path may differ from test expectations

**Fix**: 
```bash
# Check actual registered routes
docker-compose exec backend python -c "
from app.main import app
for route in app.routes:
    print(f'{route.methods} {route.path}')
" | grep -i auth
```

---

## PART 7: EXPECTED TEST RESULTS

### Backend Test Suite Summary

```
Test Suite: test_rbac.py
Total Tests: 6
Expected Passed: 3
Expected Failed: 3 (requiring refinement)

Definitely Passing:
✅ test_admin_can_access_admin_endpoints
✅ test_role_permissions_mapping
✅ test_protected_route_guard_exists

May Need Refinement:
⚠️ test_registration_creates_regular_user_only
⚠️ test_dataset_ownership_enforcement
⚠️ test_invalid_credentials_rejected
```

---

## PART 8: LOCAL TESTING WORKFLOW

**Total Estimated Time**: 45-60 minutes

1. **Setup** (5 min): Clean start, build
2. **Health Checks** (5 min): Verify all services
3. **Admin Workflow** (10 min): Login, access features
4. **User Workflow** (10 min): Register, login, verify permissions
5. **Access Control** (5 min): Test 403 pages
6. **Data Isolation** (5 min): Cross-user access tests
7. **Test Suite** (10 min): Run automated tests
8. **Documentation** (5 min): Record results

---

## PART 9: SUCCESS CRITERIA FOR PRIVATE BETA

### Must Pass ✅
- [ ] All 4 services healthy
- [ ] Admin login successful
- [ ] User registration successful
- [ ] User cannot access /users, /roles, /departments, /audit
- [ ] Admin can access all admin pages
- [ ] Dataset ownership enforced
- [ ] No TypeScript errors
- [ ] No console errors

### Should Pass ✅
- [ ] 3+ RBAC tests passing
- [ ] Database migrations clean
- [ ] Rate limiting functional
- [ ] Security headers present
- [ ] Dark mode styling loads

### Can Fail (Known Limitations) ⚠️
- [ ] Email verification (if SMTP not configured)
- [ ] Some API path tests (endpoint refinement)

---

## FINAL VERDICT

**After all checks pass**:

### Status: 🟢 READY FOR PRIVATE BETA

**When to proceed to Public Beta**:
- All automated tests pass
- Manual workflows succeed
- No critical issues in logs
- Data isolation verified
- Security headers confirmed

**Never proceed to public if**:
- Any service unhealthy
- Cross-user data visible
- Admin pages accessible to users
- Security headers missing
- Database not persisting

---

**Document Version**: 1.0  
**Last Updated**: 2026-10-16  
**Next Review**: After local Docker testing complete

