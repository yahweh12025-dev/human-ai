# Validate End-to-End Task Execution and State Mutation in Continuous Mode Across 5 Tasks

## Test Overview
This test validates Hermes Agent's ability to operate in continuous mode, executing multiple tasks sequentially while maintaining proper state mutation and tracking across the task lifecycle.

## Continuous Mode Definition
Continuous mode refers to Hermes Agent's capability to:
1. Automatically pull tasks from the queue (stqueue.json/todo.json)
2. Execute tasks without manual intervention between each task
3. Maintain and update task status throughout execution
4. Persist state changes (completed/in_progress/pending) across sessions
5. Handle task dependencies and resource management
6. Provide proper logging and monitoring of execution flow

## Test Procedure
We will validate continuous mode by executing 5 representative tasks from the stqueue that cover different agent types and complexities:

### Selected Tasks for Validation
1. **T33**: E2E Orchestration Test: Trigger Error-Scribe agent using a synthetic FATAL log injection (Hermes, Priority 1)
2. **T35**: Audit todo.json and stqueue.json synchronization mechanism (Hermes, Priority 2) 
3. **A representative OpenCode task**: e.g., T34: Implement heartbeat monitor and auto-restart daemon (OpenCode, Priority 1)
4. **A representative Pi.dev task**: e.g., T40: Create unit tests for Agent-to-Agent JSON Handshake Schema (Pi.dev, Priority 2)
5. **A representative Researcher task**: e.g., T23: Connect FAISS Semantic Memory to Trading Agent (Researcher, Priority 2)

## Validation Criteria

### 1. Task Pulling Mechanism
- [ ] Hermes correctly identifies pending tasks from stqueue.json
- [ ] Tasks are pulled in priority order (Priority 1 first, then 2, etc.)
- [ ] Agent assignment is respected (tasks go to correct specialist agents)

### 2. State Mutation Tracking
- [ ] Task status transitions: pending → in_progress → completed
- [ ] Status changes are persisted to stqueue.json
- [ ] No status regression (completed tasks don't revert to pending)
- [ ] In_progress tasks properly block concurrent execution of same task

### 3. Cross-Agent Coordination
- [ ] Hermes delegates tasks to appropriate specialist agents
- [ ] Delegated tasks report back completion status
- [ ] Hermes updates main queue based on delegated task results
- [ ] No loss of context or task information during delegation

### 4. State Persistence
- [ ] Queue state survives Hermes restarts
- [ ] Crash recovery maintains task execution integrity
- [ ] Partial progress is preserved across sessions
- [ ] Locking mechanisms prevent race conditions

### 5. Execution Monitoring
- [ ] Task start/completion times are logged
- [ ] Resource usage is tracked (where applicable)
- [ ] Error handling and retry mechanisms function correctly
- [ ] Escalation procedures work for stuck tasks

## Test Execution Plan

### Phase 1: Preparation
1. Ensure stqueue.json is in consistent state (we just audited this)
2. Verify all required specialist agents are available/configured
3. Set up monitoring/logging for the validation run
4. Create baseline snapshot of stqueue.json before test

### Phase 2: Task Execution
1. **Task 1 (T33)**: Trigger Error-Scribe with synthetic FATAL log
   - Expected: Error-Scribe detects and alerts on FATAL error
   - Hermes verifies alert generation and marks task complete
   
2. **Task 2 (T35)**: Validate queue synchronization
   - Expected: Confirm todo.json/stqueue.json sync mechanism works
   - Hermes verifies bidirectional sync capability

3. **Task 3 (OpenCode representative)**: Heartbeat monitor implementation
   - Expected: Create core/agent_heartbeat.py with monitoring capabilities
   - OpenCode agent implements and tests the daemon

4. **Task 4 (Pi.dev representative)**: Unit tests for handshake schema
   - Expected: Create tests/test_handshake_schema.py with comprehensive test suite
   - Pi.dev agent writes and executes tests

5. **Task 5 (Researcher representative)**: FAISS Semantic Memory connection
   - Expected: Create agents/trading-agent/memory_bridge.py
   - Researcher agent implements connection and basic lookup functionality

### Phase 3: Verification
1. Check all 5 tasks show completed status in stqueue.json
2. Verify associated output files were created at specified pow_file locations
3. Confirm proper status transitions were logged
4. Validate no tasks were skipped or duplicated
5. Ensure system state is clean and ready for next operations

## Success Criteria
- [ ] All 5 target tasks complete successfully
- [ ] Each task shows proper status progression in stqueue.json
- [ ] Output files are created at correct pow_file locations
- [ ] No tasks remain in_progress after test completion
- [ ] Task execution logs show proper sequencing and timing
- [ ] Specialist agents report back correct completion status
- [ ] Hermes maintains accurate queue state throughout
- [ ] Recovery from interruption would preserve progress

## Test Environment
- **Queue File**: /home/yahwehatwork/human-ai/infrastructure/configs/stqueue.json
- **Execution Mode**: Continuous (autonomous task pulling and execution)
- **Validation Period**: Sufficient time to complete 5 representative tasks
- **Monitoring**: Active logging of task status changes and agent communications

## Test Results
**Status**: PENDING_EXECUTION

**Start Timestamp**: 
**End Timestamp**: 

**Tasks Executed**:
1. T33: 
2. T35: 
3. OpenCode Representative: 
4. Pi.dev Representative: 
5. Researcher Representative: 

**State Validation**:
- [ ] Initial stqueue.json state captured
- [ ] Final stqueue.json state shows 5 tasks completed
- [ ] All power files created at specified locations
- [ ] No inconsistent states detected

**Observations**: 

**Issues Encountered**: 

**Pass/Fail**: 

## Notes
- This validation focuses on Hermes' orchestration capabilities rather than deep validation of each specialist agent's output
- The representative tasks were chosen to cover different agent types and priority levels
- In a full implementation, each task would have more specific success criteria
- Continuous mode validation should ideally run for longer periods to test stability
