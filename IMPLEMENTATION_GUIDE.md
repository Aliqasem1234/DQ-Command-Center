# Phase 4 Refactoring - Implementation & Integration Guide

## Overview

The architectural refactoring of the DQ Command Center is complete at the foundation level. This guide covers:

1. Integration of new components
2. Testing procedures
3. Migration strategy
4. Deployment checklist
5. Final production readiness verification

---

## 1. COMPONENT INTEGRATION

### 1.1 Database Migration

**Status**: Migration 006 created and ready

```bash
# In backend directory
alembic upgrade 006

# This will:
# - Create new tables: data_domains, datasets, data_elements, data_element_metadata
# - Create new tables: data_lineage, data_governance, quality_targets, quality_check_runs, quality_issues
# - Create new table: rule_effectiveness
# - Update data_quality_rules table to add dataset_id, element_id, target_level FKs
# - Drop old tables: data_assets, governance_policies, data_stewardships, metadata, metadata_tags
```

**Rollback** (if needed):
```bash
alembic downgrade 005
```

### 1.2 Update Main Application Router

**File**: `backend/app/api/v1/router.py`

**Add to router imports**:
```python
from app.api.v1.data_hierarchy_routes import router as hierarchy_router

# In APIRouter creation
api_router.include_router(hierarchy_router, tags=["data-hierarchy"])
```

### 1.3 Service Initialization

**File**: `backend/app/main.py`

**On startup** (after migrations):
```python
@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    # Seed demo data if environment is demo/development
    if os.getenv("ENV") != "production":
        async with AsyncSessionLocal() as db:
            admin_user = await get_or_create_admin(db)
            demo_users = await create_demo_users(db)
            demo_departments = await create_demo_departments(db)
            
            summary = await SeedDataService.populate_demo_data(
                db=db,
                admin_user=admin_user,
                demo_users=demo_users,
                demo_departments=demo_departments,
            )
            logger.info(f"Demo data loaded: {summary}")
```

### 1.4 Update Authentication & RBAC

**Existing Permissions** - Should add to seeding:
```python
# In auth setup/seeding
RBAC_PERMISSIONS = {
    # Existing
    "user:view", "user:manage",
    "department:view", "department:manage",
    
    # New - Data Hierarchy
    "domain:view", "domain:manage",
    "dataset:view", "dataset:manage", 
    "element:view", "element:manage",
    "metadata:view", "metadata:manage",
    
    # New - Quality
    "quality_rule:view", "quality_rule:manage",
    "quality_issue:view", "quality_issue:manage",
    "quality_target:view", "quality_target:manage",
    
    # New - Governance
    "governance:view", "governance:manage",
}
```

---

## 2. TESTING PROCEDURES

### 2.1 Unit Tests

**Create**: `backend/tests/test_data_hierarchy_service.py`

```python
# Test examples
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.services.data_hierarchy_service import DataHierarchyService

@pytest.mark.asyncio
async def test_create_domain(db: AsyncSession):
    domain = await DataHierarchyService.create_domain(
        db=db,
        name="Test Domain",
        description="Test"
    )
    assert domain.id is not None
    assert domain.name == "Test Domain"

@pytest.mark.asyncio
async def test_create_dataset_in_domain(db: AsyncSession, domain):
    dataset = await DataHierarchyService.create_dataset(
        db=db,
        name="Test Dataset",
        domain_id=domain.id,
        dataset_type="table"
    )
    assert dataset.domain_id == domain.id

# Similar tests for:
# - Element creation
# - Metadata updates
# - Governance assignments
# - Lineage creation
# - Search functionality
```

### 2.2 Integration Tests

**Create**: `backend/tests/test_data_hierarchy_integration.py`

```python
# Test complete workflows
@pytest.mark.asyncio
async def test_complete_hierarchy_workflow(db: AsyncSession):
    """Test creating complete domain -> dataset -> element hierarchy"""
    
    # 1. Create domain
    domain = await DataHierarchyService.create_domain(db, "Finance")
    
    # 2. Create dataset
    dataset = await DataHierarchyService.create_dataset(
        db, "Orders", domain.id, "table"
    )
    
    # 3. Create elements
    element1 = await DataHierarchyService.create_element(
        db, "order_id", dataset.id, "string", is_primary_key=True
    )
    element2 = await DataHierarchyService.create_element(
        db, "amount", dataset.id, "float"
    )
    
    # 4. Add metadata
    await DataHierarchyService.update_element_metadata(
        db, element1.id, {"value_count": 50000, "unique_count": 50000}
    )
    
    # 5. Assign governance
    await DataHierarchyService.assign_governance_role(
        db, dataset_id=dataset.id, role="owner", user_id=admin_user_id
    )
    
    # Verify relationships
    assert len(domain.datasets) == 1
    assert len(dataset.elements) == 2
    assert dataset.governance is not None
```

### 2.3 API Tests

**Create**: `backend/tests/test_data_hierarchy_api.py`

```python
# Test API endpoints
@pytest.mark.asyncio
async def test_create_domain_endpoint(client, admin_token):
    response = await client.post(
        "/api/v1/domains",
        json={"name": "Test Domain", "description": "Test"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Test Domain"

@pytest.mark.asyncio
async def test_get_domain_datasets(client, admin_token, domain_id):
    response = await client.get(
        f"/api/v1/domains/{domain_id}/datasets",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_search_hierarchy(client, admin_token):
    response = await client.get(
        "/api/v1/search?q=test&search_type=all",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert "domains" in response.json()
    assert "datasets" in response.json()
    assert "elements" in response.json()
```

### 2.4 Analytics Tests

**Create**: `backend/tests/test_quality_analytics_service.py`

```python
@pytest.mark.asyncio
async def test_health_score_calculation(db: AsyncSession, dataset_with_rules):
    """Test health score calculation with realistic data"""
    health = await QualityAnalyticsService.calculate_overall_health_score(
        db, dataset_id=dataset_with_rules.id, days=30
    )
    
    assert health["health_score"] >= 0 and health["health_score"] <= 100
    assert health["status"] in ["excellent", "good", "fair", "poor", "critical"]
    assert health["active_rules"] >= 0

@pytest.mark.asyncio
async def test_quality_by_dimension(db: AsyncSession):
    """Test dimension-based quality scores"""
    dims = await QualityAnalyticsService.quality_by_dimension(db)
    
    for dim_name in ["accuracy", "completeness", "consistency", "validity", "uniqueness", "timeliness"]:
        assert dim_name in dims
        assert "score" in dims[dim_name]
        assert "status" in dims[dim_name]

@pytest.mark.asyncio
async def test_quality_trends(db: AsyncSession):
    """Test trend calculation"""
    trends = await QualityAnalyticsService.quality_trends(db, days=30)
    
    assert trends["trend"] in ["improving", "stable", "degrading"]
    assert isinstance(trends["daily_data"], list)
```

### 2.5 Run Tests

```bash
cd backend

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_data_hierarchy_service.py -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Run only integration tests
pytest tests/test_data_hierarchy_integration.py -v
```

---

## 3. DATA MIGRATION STRATEGY

### For Existing Installations

If migrating from old schema to new:

```python
# Migration script: backend/alembic/versions/007_migrate_demo_data.py

async def migrate_data():
    """
    Migrate data from old schema to new schema if needed
    
    Old → New Mapping:
    - DataAsset (type="table") → Dataset
    - DataAsset (type="field") → DataElement
    - GovernancePolicy → DataGovernance
    - DataStewardship → DataGovernance
    - Metadata → DataElementMetadata
    """
    # Implementation would read from old tables, create new hierarchy
    pass
```

---

## 4. FRONTEND INTEGRATION

### 4.1 Navigation Redesign

**File**: `frontend/src/routes/index.tsx`

```typescript
export const router = createBrowserRouter([
  // ... auth routes ...
  {
    path: '/',
    element: <ProtectedRoute><MainLayout /></ProtectedRoute>,
    children: [
      // Core DQ functionality
      { path: 'dashboard', element: <DashboardPage /> },
      { path: 'data-quality', element: <DataQualityPage /> },
      { path: 'data-explorer', element: <DataExplorerPage /> },
      { path: 'data-domains', element: <DataDomainExplorer /> },
      { path: 'datasets', element: <DatasetBrowser /> },
      { path: 'datasets/:id', element: <DatasetDetails /> },
      { path: 'governance', element: <GovernanceMatrix /> },
      
      // Admin functionality
      { path: 'users', element: <UserListPage /> },
      { path: 'roles', element: <RoleListPage /> },
      { path: 'departments', element: <DepartmentListPage /> },
      { path: 'audit', element: <AuditLogPage /> },
    ],
  },
]);
```

### 4.2 New Pages to Create

1. **DataDomainExplorer** - Browse and manage domains
2. **DatasetBrowser** - Search and browse datasets
3. **DatasetDetails** - Complete dataset view with:
   - Metadata
   - Quality rules
   - Quality results
   - Issues
   - Governance
   - Lineage
4. **DataQualityDashboard** - Enhanced with real analytics
5. **GovernanceMatrix** - Ownership visualization

### 4.3 Component Updates

Update existing components:

```typescript
// DashboardPage - Use new analytics service
const [health, setHealth] = useState<HealthScoreResponse>();
const [trends, setTrends] = useState<QualityTrendsResponse>();

useEffect(() => {
  api.get('/api/v1/dashboard/health').then(setHealth);
  api.get('/api/v1/dashboard/trends').then(setTrends);
}, []);

// Show real metrics, not hardcoded values
<HealthCard score={health?.health_score} status={health?.status} />
<TrendChart data={trends?.daily_data} />
```

---

## 5. DEPLOYMENT CHECKLIST

### Pre-Deployment

- [ ] All tests passing (unit, integration, API)
- [ ] Code reviewed and approved
- [ ] Database migrations tested in staging
- [ ] Performance tests completed
- [ ] Security audit passed
- [ ] Documentation updated
- [ ] Rollback plan prepared

### Deployment Steps

1. **Backup Database**
   ```bash
   pg_dump -h production-db -U dbuser dq_command_center > backup-pre-phase4.sql
   ```

2. **Deploy Backend**
   ```bash
   # Pull latest code
   git pull origin main
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Run migrations
   cd backend && alembic upgrade head
   
   # Restart services
   systemctl restart dq-backend
   ```

3. **Deploy Frontend**
   ```bash
   cd frontend
   npm install
   npm run build
   # Deploy dist/ to web server
   ```

4. **Verify**
   ```bash
   # Check database
   psql -h production-db -U dbuser -d dq_command_center -c "SELECT COUNT(*) FROM data_domains;"
   
   # Test API
   curl -H "Authorization: Bearer <token>" https://api.dq-center/api/v1/domains
   
   # Check logs
   tail -f /var/log/dq-backend/app.log
   ```

### Post-Deployment

- [ ] Monitor error logs
- [ ] Verify all endpoints accessible
- [ ] Check dashboard displays real data
- [ ] Confirm demo data loaded
- [ ] Test user workflows
- [ ] Collect performance metrics

---

## 6. PRODUCTION READINESS VERIFICATION

### Database

- [x] Schema properly designed
- [x] Foreign keys with cascades configured
- [x] Indexes on query paths
- [x] Unique constraints enforced
- [ ] Backup strategy in place
- [ ] Monitoring/alerting configured

### Backend

- [x] Models compile and validate
- [x] Services implement CRUD
- [x] API routes organized hierarchically
- [x] Schemas validated with Pydantic
- [ ] All endpoints tested
- [ ] RBAC enforced everywhere
- [ ] Error handling comprehensive
- [ ] Logging complete

### Frontend

- [ ] Navigation restructured
- [ ] All pages created
- [ ] Real data used (not mocks)
- [ ] Performance optimized
- [ ] Responsive design
- [ ] Accessibility verified

### Security

- [x] Authentication (existing)
- [x] RBAC foundation (existing)
- [ ] RBAC enhanced for new entities
- [ ] Audit logging comprehensive
- [ ] Secrets management in place
- [ ] CORS configured
- [ ] Rate limiting active

### Operations

- [ ] Monitoring configured
- [ ] Alerting set up
- [ ] Logging centralized
- [ ] Backups automated
- [ ] Disaster recovery tested
- [ ] Runbooks documented

---

## 7. REMAINING WORK SUMMARY

### Critical (Must Complete)

1. **Frontend Pages** (2-3 hours)
   - Data Domain Explorer
   - Dataset Browser
   - Dataset Details view
   - Dashboard updates
   - Governance Matrix

2. **API Endpoint Completion** (1-2 hours)
   - Quality rules CRUD
   - Quality issues CRUD
   - Lineage management
   - Analytics endpoints
   - Metadata management

3. **Testing** (2-3 hours)
   - Unit tests for services
   - Integration tests for workflows
   - API endpoint tests
   - RBAC enforcement tests

### Important (Should Complete)

4. **Seed Data Integration** (1 hour)
   - Call SeedDataService on startup
   - Verify demo data loads
   - Test demo workflows

5. **Documentation** (1-2 hours)
   - Update API documentation
   - Create user guide
   - Update architecture docs
   - Create troubleshooting guide

### Nice to Have

6. **Performance Optimization** (1 hour)
   - Optimize queries with JOIN
   - Add caching where appropriate
   - Profile hot paths

7. **Advanced Features** (future)
   - Data lineage visualization
   - Impact analysis
   - Automated remediation suggestions
   - ML-based anomaly detection

---

## 8. TESTING SUMMARY

| Component | Test Type | Status | Coverage |
|-----------|-----------|--------|----------|
| Models | Unit | ⏳ Pending | - |
| Services | Unit | ⏳ Pending | - |
| Services | Integration | ⏳ Pending | - |
| API | Endpoint | ⏳ Pending | - |
| API | RBAC | ⏳ Pending | - |
| Database | Migration | ⏳ Pending | - |
| Analytics | Unit | ⏳ Pending | - |
| Frontend | Component | ⏳ Pending | - |
| E2E | Workflow | ⏳ Pending | - |

---

## 9. TROUBLESHOOTING

### Migration Issues

```bash
# Check migration status
alembic current

# See migration history
alembic history --verbose

# Downgrade if needed
alembic downgrade 005
```

### API Not Responding

```bash
# Check service status
systemctl status dq-backend

# Check logs
tail -100 /var/log/dq-backend/app.log | grep ERROR

# Test database connection
python3 -c "from app.database import AsyncSessionLocal; import asyncio; asyncio.run(AsyncSessionLocal())"
```

### Demo Data Missing

```bash
# Check if tables have data
psql -h localhost -d dq_command_center -c "SELECT COUNT(*) FROM data_domains;"

# Re-seed
# Kill app, delete database, restart app with ENV=development
```

---

## 10. KEY CONTACTS & RESOURCES

**Architecture Documentation**: `/REFACTORING_PLAN.md`
**Status Reports**: `/REFACTORING_STATUS.md`
**Migration Details**: `backend/alembic/versions/006_redesign_data_hierarchy.py`
**Service Code**: `backend/app/services/`
**API Routes**: `backend/app/api/v1/data_hierarchy_routes.py`

---

**Status**: Ready for integration and testing  
**Next Step**: Execute testing procedures and frontend integration  
**Estimated Timeline**: 7-10 hours to production readiness
