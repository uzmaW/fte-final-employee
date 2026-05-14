---
name: ralph-wiggum-loop
description: Implement task persistence and multi-step completion patterns. Tasks loop until done, with state tracking and error recovery.
allowed-tools: Read, Write, Glob
---

# Ralph Wiggum Loop Skill

Implement task persistence patterns where Claude keeps looping on a task until it's complete. Tasks track their progress, handle errors gracefully, and never get abandoned.

## Overview

This skill manages:
- Multi-step task completion
- Loop-based task processing
- State tracking and checkpoints
- Error recovery and retry logic
- Task completion verification
- Orphaned task detection and recovery

## The Loop Pattern

**Named after:** The Simpsons character who says "I'm in danger" - tasks that could be abandoned in danger of never completing.

### Basic Pattern

```
1. Read task file
   ↓
2. Extract current step
   ↓
3. Execute step
   ↓
4. Update task status
   ↓
5. Check if complete
   ├─ YES → Move to Done/
   └─ NO → Go to step 1 (LOOP)
```

### State Machine

```
PENDING (initial state)
├─ start_step: 0
├─ current_step: 0
└─ Loop → IN_PROGRESS

IN_PROGRESS (executing)
├─ current_step: 1, 2, 3...
├─ [Execute step]
├─ [Update status]
└─ Loop until steps_complete == total_steps

CHECKPOINT (milestone reached)
├─ completed_steps: [1,2,3]
├─ next_step: 4
└─ Ready to resume if interrupted

BLOCKED (waiting for dependency)
├─ blocked_by: external_task_id
├─ resume_when: condition_met
└─ Wait for unblock signal

COMPLETE (all steps done)
├─ completion_time: timestamp
├─ result: success/partial/failure
└─ Move to Done/
```

## Task File Format

### Multi-Step Task

```markdown
---
type: multi_step_task
task_id: TASK_2026_02_08_001
priority: high
status: in_progress
total_steps: 5
current_step: 3
created: 2026-02-08T10:00:00Z
started: 2026-02-08T10:05:00Z
---

# Complex Task: Quarterly Financial Close

## Steps

### Step 1: Collect Transactions ✅ COMPLETE
- Downloaded bank statements
- Exported accounting records
- Verified date ranges

**Completion Time:** 10:15 AM
**Status:** Success

---

### Step 2: Categorize & Validate ✅ COMPLETE
- Categorized 247 transactions
- Flagged 12 uncategorized items
- Verified account balances

**Completion Time:** 10:45 AM
**Status:** Success

---

### Step 3: Calculate Metrics 🔄 IN PROGRESS
- [ ] Calculate revenue metrics
- [ ] Calculate expense metrics
- [ ] Calculate margin metrics
- [ ] Verify calculations

**Started:** 11:00 AM
**Expected Completion:** 12:00 PM

---

### Step 4: Generate Reports (Pending)
- [ ] Create CEO briefing
- [ ] Create detailed reports
- [ ] Format for distribution

**Status:** Awaiting step 3 completion

---

### Step 5: Distribute & Archive (Pending)
- [ ] Send reports to team
- [ ] Archive in vault
- [ ] Update Dashboard

**Status:** Awaiting step 4 completion

---

## Progress

**Completed:** 2/5 steps (40%)
**In Progress:** Step 3
**Time Elapsed:** 1 hour
**Estimated Remaining:** 1 hour

## Instructions for Next Loop

1. Continue with Step 3: Calculate Metrics
2. Complete all checkboxes in Step 3
3. Update "Status" to "COMPLETE"
4. Move to Step 4 when Step 3 is done
5. Keep looping until all 5 steps complete

## Error Handling

If Step 3 fails:
- Log error details
- Update status: "ERROR"
- Suggest recovery action
- Wait for manual intervention or auto-retry
```

## Loop Implementation

### Claude's Loop Logic

```python
def process_task(task_file):
    """
    The Ralph Wiggum Loop - keep processing until complete.
    """
    while True:
        # 1. Read task
        task = read_task_file(task_file)
        
        # 2. Check if complete
        if is_complete(task):
            move_to_done(task_file)
            break
        
        # 3. Get current step
        current_step = task['current_step']
        step_details = task['steps'][current_step]
        
        # 4. Execute step
        try:
            result = execute_step(step_details)
            
            # 5. Update task
            task['steps'][current_step]['status'] = 'COMPLETE'
            task['steps'][current_step]['completion_time'] = now()
            task['current_step'] += 1
            
            # 6. Write back
            write_task_file(task_file, task)
            
            # 7. Log progress
            log_event('step_complete', current_step, result)
            
        except Exception as e:
            # Handle error
            task['status'] = 'ERROR'
            task['steps'][current_step]['error'] = str(e)
            write_task_file(task_file, task)
            break  # Exit loop, manual review needed
```

### When to Loop

**Loop When:**
- More steps remain
- Current step succeeded
- No blocking dependencies
- Error recovery still possible

**Stop When:**
- All steps complete
- Critical error encountered
- Manual intervention needed
- Timeout exceeded (48h)

## Checkpoint Pattern

### Save State at Milestones

```markdown
---
task_id: TASK_2026_02_08_001
current_step: 3
completed_steps: [1, 2]
next_checkpoint: 5
---

# Task With Checkpoints

## Completed Phase 1 (Steps 1-2)
✅ Collection complete
✅ Validation complete

## Current Phase 2 (Steps 3-4)
🔄 Processing step 3
⏳ Step 4 waiting

## Next Checkpoint: Step 5
When reached, can pause if needed

---

**Checkpoint Status:** Safe to pause here
**Resume:** From step 5
**Estimated Total Time:** 2 hours
**Time Remaining:** 1 hour
```

### Recovery from Checkpoint

If task is interrupted:
1. Read task file
2. Find last checkpoint
3. Skip completed steps
4. Resume from next step
5. Continue looping

## Error Recovery

### Retry Logic

```
Error occurs in Step 3
  ↓
Log error
  ↓
Increment retry_count
  ↓
Check if retry_count < max_retries
  ├─ YES: Wait 1 minute, Loop again
  └─ NO: Mark as ERROR, exit loop
```

### Error Escalation

```python
if error_type == "transient":
    # Network error, timeout, etc.
    retry_with_backoff()  # Loop continues
    
elif error_type == "resource":
    # Missing data, permission issue
    alert_user()
    block_task()  # Exit loop
    
elif error_type == "validation":
    # Data doesn't match expectations
    log_details()
    request_manual_review()  # Exit loop
```

## Task Completion Criteria

### Step Completion

A step is complete when:
- All checkboxes checked
- Status updated to "COMPLETE"
- Results logged
- No errors occurred

### Task Completion

Task is complete when:
- All steps marked COMPLETE
- No errors blocking
- Verification passed
- Moved to Done/ folder

### Verification Checklist

```markdown
## Completion Verification

- [ ] All steps completed
- [ ] No errors encountered
- [ ] Results match expectations
- [ ] Audit log created
- [ ] Dashboard updated
- [ ] Stakeholders notified
- [ ] Task moved to Done/
```

## Examples

### Example 1: Email Response Task

```markdown
---
type: multi_step_task
total_steps: 4
current_step: 1
status: in_progress
---

# Task: Respond to Client Email

## Step 1: Read Email 🔄
- [ ] Open email
- [ ] Extract key information
- [ ] Identify action items

## Step 2: Research (Pending)
- [ ] Gather relevant data
- [ ] Check status
- [ ] Prepare response

## Step 3: Draft Response (Pending)
- [ ] Write professional response
- [ ] Include all requested info
- [ ] Review for tone

## Step 4: Send & Log (Pending)
- [ ] Send email
- [ ] Log in audit trail
- [ ] Mark complete

---

Loop continues through each step until all 4 complete.
```

### Example 2: Financial Close Task

```markdown
---
type: multi_step_task
total_steps: 5
current_step: 2
status: in_progress
---

# Task: Monthly Financial Close

## Step 1: Collect Data ✅
- Transactions imported
- Bank reconciled
- Records verified

## Step 2: Categorize Transactions 🔄
- [ ] Auto-categorize all
- [ ] Manual review uncategorized
- [ ] Verify totals

## Step 3: Calculate Metrics (Pending)
## Step 4: Generate Reports (Pending)
## Step 5: Archive (Pending)

---

Loop continues until all 5 steps complete.
```

### Example 3: Data Migration Task

```markdown
---
type: multi_step_task
total_steps: 6
current_step: 3
status: in_progress
---

# Task: Migrate Customer Data

## Step 1: Export ✅
- Data extracted from old system
- Format validated
- Backup created

## Step 2: Transform ✅
- Data mapped to new schema
- Validation passed
- Ready for import

## Step 3: Load 🔄
- [ ] Import to new system
- [ ] Verify record count
- [ ] Check data integrity

## Step 4: Validate (Pending)
## Step 5: Notify Users (Pending)
## Step 6: Archive Old System (Pending)

---

If Step 3 fails: Backtrack, fix, retry.
If all steps complete: Move to Done/.
```

## Timeout Prevention

### Task Timeout Rules

```
Tasks older than 48 hours without progress
├─ Alert system
├─ Check for blockers
├─ Escalate to human if stuck
└─ Option to cancel or reset
```

### Stuck Task Detection

```python
def detect_stuck_task(task):
    """Find tasks that haven't progressed."""
    
    # Same step for too long
    if task['step_start_time'] < now() - 24*hours:
        alert("Task stuck on step", task['id'])
    
    # No updates for too long
    if task['last_update'] < now() - 6*hours:
        alert("Task has stalled", task['id'])
    
    # In error state for too long
    if task['status'] == 'ERROR' and task['error_time'] < now() - 2*hours:
        alert("Task blocked by error", task['id'])
```

## Best Practices

1. **Break Into Small Steps**
   - Each step should be < 5 minutes
   - Clear success criteria
   - Independent from others

2. **Log Progress**
   - Update status after each step
   - Record completion time
   - Document any issues

3. **Verify Completion**
   - Check all checkboxes
   - Validate results
   - Test success criteria

4. **Handle Errors Gracefully**
   - Catch errors specifically
   - Log detailed error info
   - Plan recovery steps

5. **Avoid Infinite Loops**
   - Set step limit (usually 5-10)
   - Timeout after 48 hours
   - Require manual review if stuck

## Integration Points

### With Vault
- Task files in In_Progress/
- Update on each loop
- Move to Done/ when complete
- Log events to audit trail

### With Approval Workflow
- Some steps require approvals
- Loop pauses at approval step
- Resume when approved
- Continue to next step

### With Dashboard
- Update progress percentage
- Show current step
- Alert if stuck
- Report completion

## See Also

- [Base Watcher Pattern](../../watchers/base_watcher.py)
- [Task Workflow](../../AI_Employee_Vault/Dashboard.md)
- [Approval Integration](.../approval-workflow/SKILL.md)
