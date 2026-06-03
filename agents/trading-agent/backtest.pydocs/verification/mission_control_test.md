# Verify Mission Control Integration: Create a verification report in the docs folder

## Test Overview
This test verifies the integration between Hermes Agent and the Mission Control system by creating a verification report that documents the current state, connectivity, and functionality of the Mission Control integration.

## Mission Control System Overview
Based on the logs and configuration observed, Mission Control appears to be a Next.js-based web interface that provides:
- Agent status monitoring
- Queue management 
- System statistics
- Activity tracking
- Notification center

## Verification Objectives
1. Confirm Mission Control service is running and accessible
2. Verify agent registration and status reporting
3. Check queue integration and task visibility
4. Validate system statistics and monitoring capabilities
5. Test notification system functionality
6. Document any issues or gaps in integration

## Verification Procedure

### 1. Service Availability Check
- [ ] Verify Mission Control server is running on expected port (10000)
- [ ] Confirm web interface loads correctly
- [ ] Check for any obvious error messages in UI

### 2. Agent Registration Verification
- [ ] Check /api/agents endpoint returns agent list
- [ ] Verify Hermes agent is registered and visible
- [ ] Check agent status fields (online/offline, last seen, etc.)
- [ ] Validate agent metadata (capabilities, version, etc.)

### 3. Queue Integration Check
- [ ] Verify /api/queue endpoint returns current stqueue data
- [ ] Check that pending tasks are visible in queue view
- [ ] Confirm completed tasks are properly tracked
- [ ] Validate task prioritization display

### 4. System Statistics Validation
- [ ] Check /api/system/stats returns meaningful metrics
- [ ] Verify agent-specific statistics are tracked
- [ ] Monitor resource usage reporting (if implemented)
- [ ] Check activity logging functionality

### 5. Notification System Test
- [ ] Verify /api/notifications endpoint functions
- [ ] Check for proper notification formatting
- [ ] Validate notification persistence and retrieval
- [ ] Test any real-time notification capabilities

### 6. Activity Tracking Verification
- [ ] Confirm /api/activities shows recent agent actions
- [ ] Verify activity filtering and sorting works
- [ ] Check activity detail views
- [ ] Validate activity-to-agent attribution

## Expected Outcomes
- Mission Control loads without errors in browser
- All API endpoints return valid JSON responses
- Hermes agent appears in agent list with correct status
- Task queue data is accurately reflected
- System metrics show reasonable values
- Notifications and activities are properly logged

## Current State Assessment (from log analysis)

### Working Components:
- ✓ Next.js server starting successfully on port 10000
- ✓ Most API endpoints responding (activities, notifications, system stats)
- ✓ Basic routing and proxy configuration functional

### Issues Identified:
- ✗ Permission denied accessing `/root/.openclaw/openclaw.json` 
- ✗ Queue API failing to find stqueue.json at multiple attempted paths
- ✗ Multiple 500 errors for queue and agent endpoints due to file access/permission issues

### Path Investigation:
The Mission Control is attempting to access stqueue.json at:
1. `/home/yahwehatwork/infrastructure/configs/stqueue.json` ❌ (wrong base path)
2. `/home/yahwehatwork/human-ai/infrastructure/human-ai/infrastructure/configs/stqueue.json` ❌ (duplicated path)
3. `/home/yahwehatwork/human-ai/human-ai/infrastructure/configs/stqueue.json` ❌ (duplicated path)

Correct path should be: `/home/yahwehatwork/human-ai/infrastructure/configs/stqueue.json` ✓

## Recommended Fixes
1. **Fix OpenClaw permission**: Ensure `/root/.openclaw/openclaw.json` is accessible or adjust path via OPENCLAW_DIR env var
2. **Fix queue path configuration**: Update Mission Control to use correct relative path to stqueue.json
3. **Verify agent registration**: Ensure Hermes agent is properly registered in OpenClaw config
4. **Test endpoints post-fix**: Validate all API endpoints return 200 with expected data

## Test Execution Steps

### Step 1: Environment Verification
```bash
# Check if Mission Control is running
curl -s http://localhost:10000 | grep -i nextjs

# Check OpenClaw config accessibility  
ls -la /root/.openclaw/openclaw.json 2>/dev/null || echo "OpenClaw config not accessible"

# Check stqueue.json location
ls -la /home/yahwehatwork/human-ai/infrastructure/configs/stqueue.json
```

### Step 2: API Endpoint Testing
```bash
# Test system stats (should work)
curl -s http://localhost:10000/api/system/stats | jq '.'

# Test notifications (should work)  
curl -s http://localhost:10000/api/notifications | jq '.'

# Test activities (should work)
curl -s http://localhost:10000/api/activities?limit=5 | jq '.'

# Test agents endpoint (may fail due to OpenClaw issue)
curl -s http://localhost:10000/api/agents | jq '.'

# Test queue endpoint (may fail due to path issue)
curl -s http://localhost:10000/api/queue | jq '.'
```

### Step 3: Fix Implementation
1. **Address OpenClaw permission**: 
   - Check if OpenClaw directory needs to be created or permissions fixed
   - Verify OPENCLAW_DIR environment variable is set correctly

2. **Correct queue path**:
   - Identify where the path configuration is defined in Mission Control source
   - Update to use correct relative path: `../../../../human-ai/infrastructure/configs/stqueue.json`
   - Or better, use environment variable for base path

### Step 4: Validation After Fixes
- Re-run API tests to confirm 200 responses
- Verify agent list includes Hermes
- Confirm queue data matches stqueue.json contents
- Check that system reflects recent task activity

## Success Criteria
- [ ] Mission Control loads successfully in browser
- [ ] /api/agents returns 200 with agent list including Hermes
- [ ] /api/queue returns 200 with correct stqueue data
- [ ] No 500 errors in core API endpoints
- [ ] Agent status shows appropriate values (online/offline, last seen)
- [ ] Queue shows pending and completed tasks correctly
- [ ] System statistics display meaningful data
- [ ] Notification and activity endpoints function properly

## Test Results
**Status**: PENDING_EXECUTION

**Execution Timestamp**: 

**Tests Performed**:
- Service availability: 
- Agent registration: 
- Queue integration: 
- System statistics: 
- Notification system: 
- Activity tracking: 

**Issues Found**: 
- OpenClaw permission error: /root/.openclaw/openclaw.json access denied
- Queue path resolution: multiple incorrect path attempts
- API endpoint failures due to above issues

**Fixes Applied**: 

**Validation Results**: 

**Pass/Fail**: 

## Conclusion
The Mission Control integration shows promise with core Next.js framework functioning, but suffers from configuration path issues preventing proper agent and queue integration. Fixing the file path and permission issues should enable full integration verification.

## Related Documents
- Error-Scribe E2E Test: ./error_scribe_e2e.md (T33)
- Queue Synchronization Audit: ./queue_sync_audit.md (T35) 
- Continuous Mode Validation: ./continuous_mode_e2e.md (T39)
