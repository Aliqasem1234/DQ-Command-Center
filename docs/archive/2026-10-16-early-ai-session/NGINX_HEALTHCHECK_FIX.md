# NGINX HEALTHCHECK FIX — DQ COMMAND CENTER V2

**Issue**: dq-nginx service showing as unhealthy  
**Fix Applied**: 2026-10-16  
**Status**: Ready for testing

---

## ROOT CAUSE ANALYSIS

### Problem Identified
1. **IPv6 Connection Issue**: Nginx healthcheck used `wget http://localhost/health`
   - In Docker containers, `localhost` resolves to IPv6 (`[::1]`)
   - Network connectivity to IPv6 in Docker was failing

2. **HTTP Method Issue**: Healthcheck used `wget --spider`
   - `--spider` flag makes wget send HEAD request (not GET)
   - `/health` endpoint only accepts GET requests
   - Result: HTTP 405 Method Not Allowed

### Evidence
```
Error: "wget: can't connect to remote host: Connection refused"
Reason: [::1]:80 connection attempts failed
Fallback: Manual requests to http://127.0.0.1/health work fine
```

---

## THE FIX

### What Changed
**Before**:
```yaml
test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost/health"]
```

**After**:
```yaml
test: ["CMD", "wget", "-q", "--tries=1", "http://127.0.0.1/health", "-O", "-"]
```

### Why This Works
1. **127.0.0.1**: Explicitly uses IPv4 (not IPv6)
2. **Removed --spider**: Now makes real GET request (not HEAD)
3. **-O -**: Outputs response to stdout (tells wget to download, confirming successful GET)
4. **-q**: Quiet mode (no verbose output)

### File Modified
- `docker-compose.yml` (Nginx service healthcheck section)

---

## TESTING INSTRUCTIONS

### Step 1: Stop Running Containers (Safe - No Data Loss)

```powershell
cd C:\Users\aliqa\OneDrive\Desktop\dq-command-center-v2

# Stop containers (preserves all data)
docker-compose down

# Verify postgres volume still exists (data preserved)
docker volume ls | Select-String postgres_data
```

**Expected**: postgres_data volume should still exist

### Step 2: Rebuild and Start Services

```powershell
# Rebuild with new healthcheck configuration
docker-compose up --build

# Watch logs for:
# 1. postgres: "database system is ready"
# 2. backend: "Uvicorn running"
# 3. frontend: "Local: http://localhost"
# 4. nginx: "healthy"
```

### Step 3: Verify All Services Are Healthy

```powershell
# In another terminal, check status
docker-compose ps

# Expected output:
# NAME              STATUS
# dq-postgres       Up (healthy)
# dq-backend        Up (healthy)
# dq-frontend       Up
# dq-nginx          Up (healthy)  ← This should now be healthy!
```

### Step 4: Test Health Endpoints

```powershell
# Test backend health directly
curl -i http://localhost:8000/health
# Expected: HTTP 200 OK with JSON response

# Test nginx health (through proxy)
curl -i http://localhost/health
# Expected: HTTP 200 OK with JSON response

# Test nginx healthcheck command specifically
docker-compose exec nginx wget -q --tries=1 http://127.0.0.1/health -O -
# Expected: JSON output + exit code 0
```

### Step 5: Test Application Functionality

```powershell
# Open browser
# Navigate to http://localhost

# Test Admin Login
# Email: admin@test.com
# Password: (from .env)
# Should: Login successfully, see all features

# Test User Registration
# Create account: testuser@example.com
# Password: TestPassword123!
# Should: Register successfully, redirect to login or verify screen
```

### Step 6: Verify Data Persistence

```powershell
# Check database is still intact
docker-compose exec postgres psql -U postgres -d dq_command_center -c "SELECT COUNT(*) FROM users;"
# Expected: Should show existing user count

# Verify no data was lost
docker-compose exec backend python -c "
from app.models.user import User
from sqlalchemy import select
# Data should be intact
"
```

---

## SUCCESS CRITERIA ✅

All of the following must be true:

- [ ] `docker-compose ps` shows all 4 services
- [ ] All services show "Up" or "Up (healthy)" status
- [ ] **dq-nginx shows "Up (healthy)"** ← Main verification
- [ ] `curl http://localhost/health` returns 200 OK
- [ ] `curl http://localhost:8000/health` returns 200 OK
- [ ] Browser login works (admin account)
- [ ] User registration works
- [ ] No errors in docker-compose logs
- [ ] Database data is intact (existing users still present)

---

## IF HEALTHCHECK STILL FAILS

### Diagnostic Steps

```powershell
# Check nginx logs
docker-compose logs nginx

# Check if wget can connect to the endpoint
docker-compose exec nginx wget -v http://127.0.0.1/health

# Check if backend is responding
docker-compose exec nginx curl -v http://backend:8000/health

# Check Nginx configuration syntax
docker-compose exec nginx nginx -t
```

### Common Issues and Fixes

**Issue**: "Address family for hostname not supported"
- **Cause**: IPv6 still being attempted
- **Fix**: Verify 127.0.0.1 (not localhost) is in docker-compose.yml

**Issue**: Connection timeout
- **Cause**: Backend service not healthy when Nginx starts
- **Fix**: Normal; increase start_period in healthcheck if needed

**Issue**: "405 Method Not Allowed"
- **Cause**: Old configuration still in use
- **Fix**: Verify docker-compose.yml has `"-O", "-"` (removed --spider)
- **Action**: Delete image and rebuild: `docker-compose build --no-cache nginx`

---

## WHAT CHANGED

### Files Modified
1. **docker-compose.yml**
   - Line 1**: Nginx healthcheck command
   - Old: HEAD request via `--spider`
   - New: GET request via real download

### Files NOT Modified
- ✅ nginx/nginx.conf (no changes needed)
- ✅ backend code (no changes needed)
- ✅ frontend code (no changes needed)
- ✅ .env (no changes needed)
- ✅ Database (no changes needed)

### Data Safety
- ✅ PostgreSQL volume preserved
- ✅ Existing users intact
- ✅ Existing roles intact
- ✅ Existing permissions intact
- ✅ Backend configuration unchanged
- ✅ No destructive operations performed

---

## VERIFICATION CHECKLIST

### Pre-Test
- [ ] Read this document
- [ ] Stop running containers (`docker-compose down`)
- [ ] Verify postgres_data volume exists

### During Test
- [ ] Run `docker-compose up --build`
- [ ] Watch startup logs
- [ ] Verify all services start without errors

### Post-Test
- [ ] Run `docker-compose ps` and verify nginx is healthy
- [ ] Test curl commands to health endpoints
- [ ] Test browser login
- [ ] Verify database still has data
- [ ] Check application functionality works

---

## EXPECTED BEHAVIOR AFTER FIX

### Nginx Health Status
**Before**: Unhealthy (repeated failures)
**After**: Healthy (passes healthcheck every 5 seconds)

### Docker Logs
```
dq-nginx | [notice] [pid 1#0] signal 1 (SIGHUP) received, running "nginx -s reload"
dq-nginx | [notice] [pid 1#0] signal 29 (SIGIO) received
dq-nginx | [notice] 10/16/2026 16:00:00 #7 *1 "GET /health HTTP/1.1" 200 ...
```

### Health Endpoint Response
```json
HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": "healthy",
  "app": "DQ Command Center V2",
  "version": "1.0.0"
}
```

---

## SUMMARY

**Issue**: Nginx healthcheck using IPv6 and HEAD request, both failing
**Fix**: Use IPv4 and GET request explicitly
**Impact**: Minimal - only healthcheck command changed
**Risk**: None - no code or data affected
**Verification**: Docker `ps` command will show healthy status

After completing the tests above, **all Docker services should show healthy status** and the application should function normally.

---

**Fix Applied**: 2026-10-16 by Claude Haiku 4.5  
**Session**: https://claude.ai/code/session_01AqNEVUB9hUinGQ5GXfnDqH

