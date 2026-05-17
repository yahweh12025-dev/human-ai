# Audit todo.json and stqueue.json Synchronization Mechanism

## Audit Overview
This audit examines the synchronization mechanism between todo.json (Hermes' internal task queue) and stqueue.json (the shared multi-agent task queue) to prevent task duplication and ensure consistency across agents.

## Current State Analysis
- **stqueue.json**: Contains 51 tasks (26 completed, 25 pending)
- **todo.json**: Not found in standard locations - this indicates a potential synchronization gap

## Synchronization Mechanism Requirements
1. **Bidirectional Sync**: Changes in either queue should propagate to the other
2. **Conflict Resolution**: Handle cases where same task exists in both queues with different statuses
3. **Task Mapping**: Ensure T-ID consistency between queues
4. **Atomic Updates**: Prevent race conditions during concurrent updates
5. **Backup/Rollback**: Ability to recover from sync failures

## Current Implementation Gaps Identified
1. **Missing todo.json**: Hermes' internal todo queue appears to be missing or not configured
2. **No Sync Process Visible**: No apparent automated synchronization mechanism between queues
3. **Manual Maintenance Risk**: Dependence on manual updates increases duplication risk
4. **Lack of Validation**: No automated validation of queue consistency

## Recommended Synchronization Approach
1. **Canonical Source**: Designate one queue as source of truth (likely stqueue.json for multi-agent compatibility)
2. **Sync Service**: Implement lightweight sync service that runs periodically
3. **Mapping Layer**: Create task ID mapping to handle any format differences
4. **Conflict Policy**: Define clear rules (e.g., stqueue wins, or manual resolution required)
5. **Monitoring**: Add validation checks and alerting for sync discrepancies

## Test Procedures
1. **Existence Check**: Verify both queue files exist in expected locations
2. **Format Validation**: Validate JSON structure of both files
3. **Task ID Consistency**: Ensure T-IDs map correctly between queues
4. **Status Synchronization**: Confirm status updates propagate correctly
5. **Duplicate Prevention**: Verify same task doesn't appear with different IDs
6. **Sync Latency**: Measure time for changes to propagate between queues

## Success Criteria
- [ ] Both todo.json and stqueue.json exist and are valid JSON
- [ ] Task T-IDs are consistent between queues (where applicable)
- [ ] No duplicate tasks exist across queues
- [ ] Status changes in one queue propagate to the other within expected timeframe
- [ ] Sync mechanism handles concurrent updates without data loss
- [ ] Audit trail available for sync operations

## Implementation Plan
1. **Phase 1**: Locate or create todo.json in Hermes' expected configuration
2. **Phase 2**: Implement basic sync script that reads/writes both queues
3. **Phase 3**: Add conflict detection and resolution logic
4. **Phase 4**: Integrate with Hermes' task execution lifecycle
5. **Phase 5**: Add monitoring and alerting for sync failures

## Verification Documents Location
- This document: ./human-ai/docs/verification/queue_sync_audit.md
- Related: ./human-ai/docs/verification/error_scribe_e2e.md (T33)
- Related: ./human-ai/docs/verification/continuous_mode_e2e.md (T39)

## Audit Completed By: Hermes Agent
**Audit Date**: 
**Findings**: Significant synchronization gap identified - todo.json missing
**Risk Level**: MEDIUM to HIGH (potential for task duplication and inconsistent state)
**Recommendation**: Implement synchronization mechanism before scaling autonomous operations
