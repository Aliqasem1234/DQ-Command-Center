# DQ Command Center - Testing Guide

## Testing Strategy

### Test Coverage Targets
- Unit Tests: 80%+ coverage
- Integration Tests: Key workflows
- API Tests: All endpoints
- E2E Tests: Critical user journeys
- Security Tests: OWASP compliance
- Performance Tests: Load and stress testing

## Unit Tests

### Backend Unit Tests

```bash
# Run all backend tests
cd backend
pytest tests/ -v --cov=app

# Run specific test file
pytest tests/test_auth_service.py -v

# Run with coverage report
pytest tests/ --cov=app --cov-report=html
```

### Test Files Structure

```
backend/tests/
├── __init__.py
├── conftest.py                 # Pytest fixtures
├── test_auth_service.py        # Authentication tests
├── test_data_hierarchy.py      # Data hierarchy CRUD
├── test_data_quality_rules.py  # Quality rules tests
├── test_governance.py          # Governance tests
├── test_analytics.py           # Analytics calculations
├── test_permissions.py         # RBAC tests
├── test_audit_logging.py       # Audit trail tests
└── test_security.py            # Security tests
```

### Example Unit Tests

```python
# tests/test_data_hierarchy.py
import pytest
from app.services.data_hierarchy_service import DataHierarchyService
from app.models.data_hierarchy import DataDomain, Dataset

@pytest.fixture
async def db_session():
    """Fixture for test database session"""
    async with async_session_factory() as session:
        yield session

@pytest.mark.asyncio
async def test_create_domain(db_session):
    """Test creating a data domain"""
    service = DataHierarchyService(db_session)
    
    domain = await service.create_domain(
        name="Test Domain",
        description="Test Description",
        business_owner_id=1,
        domain_steward_id=1
    )
    
    assert domain.name == "Test Domain"
    assert domain.id is not None

@pytest.mark.asyncio
async def test_dataset_unique_constraint(db_session):
    """Test that dataset names are unique within a domain"""
    service = DataHierarchyService(db_session)
    domain = await service.create_domain("Domain", "Desc", 1, 1)
    
    await service.create_dataset(
        name="Dataset1",
        domain_id=domain.id,
        dataset_type="table"
    )
    
    with pytest.raises(IntegrityError):
        await service.create_dataset(
            name="Dataset1",
            domain_id=domain.id,
            dataset_type="table"
        )
```

### Frontend Unit Tests

```bash
# Run all frontend tests
cd frontend
npm test

# Run specific test file
npm test -- DataExplorerModern.test.tsx

# Watch mode (re-run on file changes)
npm test -- --watch

# Coverage report
npm test -- --coverage
```

## Integration Tests

### API Integration Tests

```bash
# Run integration tests with live database
cd backend
pytest tests/integration/ -v --db-url="postgresql://..."

# With Docker database
docker-compose -f docker-compose.test.yml up -d
pytest tests/integration/ -v
```

### Test Workflow Examples

```python
# tests/integration/test_workflow_create_dataset.py
@pytest.mark.asyncio
async def test_complete_dataset_workflow():
    """Test full workflow: Create domain → dataset → elements → rules"""
    
    # 1. Create domain
    domain_response = await client.post("/api/v1/domains", json={
        "name": "Test Domain",
        "description": "Testing"
    }, headers=auth_headers)
    assert domain_response.status_code == 201
    domain_id = domain_response.json()["id"]
    
    # 2. Create dataset
    dataset_response = await client.post("/api/v1/datasets", json={
        "name": "Test Dataset",
        "domain_id": domain_id,
        "dataset_type": "table"
    }, headers=auth_headers)
    assert dataset_response.status_code == 201
    dataset_id = dataset_response.json()["id"]
    
    # 3. Create elements
    element_response = await client.post(f"/api/v1/elements", json={
        "name": "email",
        "dataset_id": dataset_id,
        "data_type": "string"
    }, headers=auth_headers)
    assert element_response.status_code == 201
    
    # 4. Create quality rule
    rule_response = await client.post("/api/v1/quality-rules", json={
        "name": "Email Format Validation",
        "element_id": element_id,
        "rule_type": "format",
        "condition": "email_format"
    }, headers=auth_headers)
    assert rule_response.status_code == 201
    
    # 5. Verify relationship
    dataset = await client.get(f"/api/v1/datasets/{dataset_id}")
    assert len(dataset.json()["elements"]) == 1
```

## API Tests

### Endpoint Testing

```bash
# Using Postman/Newman
npm install -g newman
newman run postman_collection.json \
  --environment postman_environment.json \
  --reporters cli,json
```

### Health Check Endpoints

```bash
# Test health endpoints
curl http://localhost:8000/health

# Expected response (200 OK):
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2024-08-26T10:30:00Z"
}
```

### API Test Categories

1. **Authentication Tests**
   - Valid login
   - Invalid credentials
   - Token expiration
   - Refresh token flow
   - Logout

2. **Data Hierarchy Tests**
   - CRUD operations for domains, datasets, elements
   - Unique constraints
   - Relationship validation
   - Permission checks

3. **Quality Rules Tests**
   - Rule creation
   - Rule execution
   - Result recording
   - Issue creation

4. **Governance Tests**
   - Role assignment
   - Permission enforcement
   - Ownership changes
   - Audit logging

5. **Error Handling Tests**
   - 400 Bad Request
   - 401 Unauthorized
   - 403 Forbidden
   - 404 Not Found
   - 500 Server Error
   - Rate limiting (429)

## E2E Tests

### User Journey Tests

```python
# tests/e2e/test_quality_analyst_workflow.py
@pytest.mark.asyncio
async def test_analyst_creates_and_monitors_quality_rule():
    """Test complete analyst workflow"""
    
    # 1. Login as analyst
    login_response = await client.post("/api/v1/auth/login", json={
        "email": "analyst@company.com",
        "password": "AnalystPass123!"
    })
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Browse datasets
    datasets = await client.get("/api/v1/datasets", headers=headers)
    assert len(datasets.json()) > 0
    
    # 3. Select dataset and view elements
    dataset_id = datasets.json()[0]["id"]
    elements = await client.get(f"/api/v1/datasets/{dataset_id}/elements")
    
    # 4. Create quality rule
    rule = await client.post("/api/v1/quality-rules", 
        json={
            "name": "Completeness Check",
            "element_id": elements.json()[0]["id"],
            "rule_type": "completeness"
        },
        headers=headers
    )
    assert rule.status_code == 201
    
    # 5. Monitor rule results
    results = await client.get(
        f"/api/v1/quality-rules/{rule.json()['id']}/results",
        headers=headers
    )
    assert results.status_code == 200
    
    # 6. Create issue if problems detected
    if results.json()["pass_rate"] < 0.95:
        issue = await client.post("/api/v1/quality-issues",
            json={
                "rule_id": rule.json()["id"],
                "severity": "high",
                "description": "Low completeness score"
            },
            headers=headers
        )
        assert issue.status_code == 201
```

## Security Tests

### OWASP Testing

```bash
# OWASP Top 10 Testing Checklist
- [ ] Injection attacks (SQL injection, NoSQL injection)
- [ ] Broken authentication
- [ ] Sensitive data exposure
- [ ] XML external entities (XXE)
- [ ] Broken access control
- [ ] Security misconfiguration
- [ ] XSS (Cross-site scripting)
- [ ] Insecure deserialization
- [ ] Using components with known vulnerabilities
- [ ] Insufficient logging and monitoring
```

### Security Test Examples

```python
# tests/security/test_injection_prevention.py
def test_sql_injection_protection():
    """Verify SQL injection protection"""
    response = client.post("/api/v1/auth/login", json={
        "email": "'; DROP TABLE users; --",
        "password": "anything"
    })
    # Should return 401, not crash
    assert response.status_code == 401
    
    # Verify database still intact
    users = client.get("/api/v1/users", headers=admin_headers)
    assert users.status_code == 200

def test_xss_prevention():
    """Verify XSS protection in responses"""
    response = client.post("/api/v1/datasets", json={
        "name": "<script>alert('xss')</script>",
        "domain_id": 1
    }, headers=auth_headers)
    
    # Check that script tags are escaped in response
    data = response.json()
    assert "&lt;script&gt;" in data["name"] or "<script>" not in data["name"]

def test_rbac_enforcement():
    """Verify role-based access control"""
    # Get token for analyst (limited permissions)
    analyst_token = login_as_analyst()
    
    # Try to delete user (should fail)
    response = client.delete(
        "/api/v1/users/some-user-id",
        headers={"Authorization": f"Bearer {analyst_token}"}
    )
    assert response.status_code == 403

def test_rate_limiting():
    """Verify rate limiting"""
    for i in range(25):  # Exceed limit of 20 per minute
        response = client.get("/api/v1/datasets")
        if i < 20:
            assert response.status_code in [200, 401]  # Normal response
        else:
            assert response.status_code == 429  # Rate limited
```

## Performance Tests

### Load Testing

```bash
# Using k6
npm install -g k6

# Run load test
k6 run tests/performance/load_test.js

# Run with specific duration and users
k6 run --vus 100 --duration 30s tests/performance/load_test.js
```

### Performance Test Script

```javascript
// tests/performance/load_test.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
  vus: 50,           // Virtual users
  duration: '30s',   // Test duration
  thresholds: {
    http_req_duration: ['p(95)<500'],  // 95% of requests < 500ms
    http_req_failed: ['rate<0.1'],     // Error rate < 10%
  }
};

export default function () {
  // Login
  let loginResponse = http.post(
    'http://localhost:8000/api/v1/auth/login',
    JSON.stringify({
      email: 'analyst@company.com',
      password: '[REDACTED-DEV-CREDENTIAL]'
    })
  );
  
  let token = loginResponse.json('access_token');
  let headers = { 'Authorization': `Bearer ${token}` };
  
  // Get datasets (common operation)
  let response = http.get(
    'http://localhost:8000/api/v1/datasets',
    { headers: headers }
  );
  
  check(response, {
    'status is 200': (r) => r.status === 200,
    'response time < 500ms': (r) => r.timings.duration < 500,
  });
  
  sleep(1);
}
```

## Database Tests

### Data Integrity Tests

```sql
-- Verify foreign key constraints
SELECT constraint_name, table_name, column_name
FROM information_schema.key_column_usage
WHERE table_schema = 'public'
ORDER BY table_name;

-- Verify indexes are in place
SELECT indexname FROM pg_indexes WHERE schemaname = 'public';

-- Check for orphaned records
SELECT * FROM datasets WHERE domain_id NOT IN (SELECT id FROM data_domains);
```

## Test Execution Pipeline

### Local Testing

```bash
# Run all tests
make test

# Backend only
make test-backend

# Frontend only
make test-frontend

# Integration tests
make test-integration

# E2E tests
make test-e2e

# Security tests
make test-security

# Performance tests
make test-performance
```

### CI/CD Pipeline

```yaml
# .github/workflows/test.yml
name: Test Suite
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:16
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Backend Tests
        run: |
          cd backend
          pip install -r requirements.txt
          pytest tests/ --cov=app --junitxml=test-results.xml
      
      - name: Frontend Tests
        run: |
          cd frontend
          npm ci
          npm test -- --coverage
      
      - name: Integration Tests
        run: |
          cd backend
          pytest tests/integration/ -v
      
      - name: Upload Coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./backend/coverage.xml,./frontend/coverage/coverage-final.json
```

## Test Metrics

### Coverage Goals

```
Backend:
- Statements: 80%
- Branches: 75%
- Functions: 80%
- Lines: 80%

Frontend:
- Statements: 70%
- Branches: 65%
- Functions: 70%
- Lines: 70%
```

### Performance Benchmarks

```
API Response Times (p95):
- Login: < 200ms
- Get Datasets: < 300ms
- Create Quality Rule: < 500ms
- Get Dashboard Metrics: < 1000ms

Database Queries:
- Average: < 50ms
- 99th percentile: < 500ms
```

## Continuous Testing

### Pre-commit Hooks

```bash
# .husky/pre-commit
#!/bin/sh
. "$(dirname "$0")/_/husky.sh"

# Run linter and tests before commit
npm run lint
npm run test -- --bail
```

### Automated Testing Schedule

```bash
# Nightly: Full regression suite
0 2 * * * cd /app && pytest tests/ --junitxml=results.xml

# Weekly: Performance tests
0 3 * * 0 cd /app && k6 run tests/performance/load_test.js

# Monthly: Security audit
0 4 1 * * cd /app && bandit -r app/ && safety check
```

---

**Last Updated**: August 2024  
**Version**: 1.0.0  
**Status**: Complete Testing Framework
