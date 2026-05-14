---
name: vault-operations
description: Read from and write to the Obsidian vault with proper folder structure and markdown formatting. Use when processing inbox items, creating plans, generating reports, or updating dashboards.
allowed-tools: Read, Write, Glob
---

# Vault Operations Skill

Your personal Obsidian vault is the memory and control center for the AI Employee. Always interact with files using this consistent structure.

## Vault Directory Structure

The vault uses a task workflow pattern to manage all operations:

- `/Needs_Action/` - Inbox of tasks from Watchers (TODO items)
- `/In_Progress/<agent>/` - Tasks currently being worked on (claim by moving here)
- `/Plans/` - Generated plans with checklists (prefixed PLAN_*)
- `/Done/` - Completed tasks (moved after execution)
- `/Pending_Approval/` - Actions requiring human approval (prefixed with action type)
- `/Approved/` - User-approved files ready for execution
- `/Rejected/` - User-rejected actions (log and skip)
- `/Logs/` - Audit trail in YYYY-MM-DD.json format
- `/Accounting/` - Financial records and transaction ledger
- `Dashboard.md` - Real-time summary of system status
- `Company_Handbook.md` - Rules of engagement and thresholds
- `Business_Goals.md` - Quarterly objectives and metrics

## Reading from Vault

### When Processing Needs_Action Items:

1. **List all files**: Use Glob to scan `/Needs_Action/*.md`
2. **Parse metadata**: Extract YAML frontmatter (type, priority, source, created timestamp)
3. **Extract content**: Read the main content below the metadata
4. **Deduplicate**: Check `/In_Progress/` to avoid duplicate processing
5. **Claim task**: Move the file to `/In_Progress/<your-agent-name>/`

### Example Metadata Format:

```yaml
---
type: email_task|payment_request|approval_needed|report_request
priority: critical|high|medium|low
source: gmail|whatsapp|manual|filesystem
created: 2026-02-08T10:30:00Z
due: 2026-02-09T17:00:00Z
---
```

## Writing to Vault

### Creating Task Files (in `/Needs_Action/`)

Structure for new tasks from watchers:

```markdown
---
type: email_task
priority: high
source: gmail
created: 2026-02-08T10:30:00Z
---

# Task Title

**From:** sender@example.com  
**Subject:** Original email subject  
**Timestamp:** 2026-02-08T10:30:00Z

## Summary
Brief description of what action is needed.

## Context
Relevant details from the source.

## Action Required
- [ ] Specific action 1
- [ ] Specific action 2
```

### Creating Plans (in `/Plans/`)

Use this format for generated plans:

```markdown
---
plan_id: PLAN_2026_02_08_001
type: task_plan|approval_plan|briefing_plan
priority: high
created: 2026-02-08T10:30:00Z
related_task: TASK_NAME
status: active
---

# Plan Title

## Objective
What we're trying to accomplish.

## Steps
- [ ] Step 1 - Detailed description
- [ ] Step 2 - Detailed description
- [ ] Step 3 - Detailed description

## Success Criteria
- Criterion 1
- Criterion 2
- Criterion 3

## Timeline
- 10:30 AM - Start
- 11:00 AM - Checkpoint
- 12:00 PM - Complete
```

### Creating Approval Requests (in `/Pending_Approval/`)

Format for actions requiring human approval:

```markdown
---
type: payment_approval|action_approval|policy_override
priority: high
created: 2026-02-08T10:30:00Z
action_id: ACTION_2026_02_08_001
risk_level: low|medium|high|critical
---

# Approval Request: [Action Type]

## What
Detailed description of the proposed action.

## Why
Reasoning behind this action.

## Risk Assessment
- Risk Level: [low|medium|high|critical]
- Potential Impact: What could go wrong
- Mitigation: How we'll prevent issues

## Approval Required
Please move this file to `/Approved/` to authorize execution.

## Timeline
Must be decided by: [DATE/TIME]
```

### Updating Dashboard (Dashboard.md)

The Dashboard should be updated frequently with system status:

```markdown
# AI Employee System Dashboard

## Status Summary
- **Overall Status**: 🟢 Operational | 🟡 Degraded | 🔴 Error
- **Last Updated**: 2026-02-08 14:30 UTC
- **Uptime**: 24 days, 5 hours

## Active Tasks
| Task | Status | Priority | Source |
|------|--------|----------|--------|
| EMAIL_001 | In Progress | High | Gmail |
| PAYMENT_002 | Pending Approval | Critical | Manual |

## Pending Approvals
- [ ] PAYMENT_002 - $500 transfer to vendor (2h waiting)

## Recent Completions
- ✅ EMAIL_001 - Response sent
- ✅ REPORT_001 - CEO briefing generated

## System Health
- Gmail Watcher: ✅ Last checked 2m ago
- Filesystem Watcher: ✅ Monitoring
- Orchestrator: ✅ Running
- Vault Size: 245 files, 3.2 MB

## Next Scheduled Tasks
- 09:00 AM - Daily digest
- 05:00 PM - Email summary
- 08:00 AM (Tomorrow) - CEO briefing
```

### Creating Audit Logs (in `/Logs/`)

Logs should be in JSON format with one file per day:

```json
{
  "date": "2026-02-08",
  "timezone": "UTC",
  "events": [
    {
      "timestamp": "2026-02-08T10:30:00Z",
      "event_type": "task_claimed",
      "agent": "claude",
      "task_id": "EMAIL_001",
      "details": "Claimed email task from Gmail watcher"
    },
    {
      "timestamp": "2026-02-08T10:45:00Z",
      "event_type": "approval_requested",
      "agent": "claude",
      "action_id": "PAYMENT_002",
      "amount": 500,
      "recipient": "vendor@example.com",
      "reason": "Invoice payment"
    },
    {
      "timestamp": "2026-02-08T11:00:00Z",
      "event_type": "approval_granted",
      "agent": "user",
      "action_id": "PAYMENT_002"
    },
    {
      "timestamp": "2026-02-08T11:05:00Z",
      "event_type": "task_completed",
      "agent": "claude",
      "task_id": "EMAIL_001",
      "result": "success"
    }
  ]
}
```

## Task Workflow Pattern

The standard workflow for any task:

```
1. Task Created in /Needs_Action/
   ↓
2. Claude Reads & Claims (moves to /In_Progress/claude/)
   ↓
3. Analyze & Plan (creates file in /Plans/)
   ↓
4. Check Risk Level
   ├─ Low Risk → Execute → Move to /Done/
   └─ High Risk → Request Approval (move to /Pending_Approval/)
   ↓
5a. If Approved: Execute → Move to /Done/
5b. If Rejected: Log rejection → Move to /Rejected/
   ↓
6. Update Dashboard.md
   ↓
7. Log event to /Logs/YYYY-MM-DD.json
```

## Common Operations

### List Files in a Directory
```python
# Using glob pattern
files = glob("/Needs_Action/*.md")
```

### Read a File with Metadata
```python
content = read_file("/Needs_Action/EMAIL_001.md")
# Parse frontmatter
metadata = extract_yaml_frontmatter(content)
task_content = content.split('---')[2]
```

### Move File (Claiming a Task)
```python
move_file("/Needs_Action/EMAIL_001.md", "/In_Progress/claude/EMAIL_001.md")
```

### Append to Audit Log
```python
today = datetime.now().strftime("%Y-%m-%d")
log_file = f"/Logs/{today}.json"
event = {
    "timestamp": datetime.now().isoformat() + "Z",
    "event_type": "task_completed",
    "task_id": "EMAIL_001"
}
# Append to log JSON
```

### Update Dashboard Status
```python
dashboard_content = read_file("/Dashboard.md")
# Update status section
# Write back to /Dashboard.md
```

## Decision Rules (from Company_Handbook.md)

Always check `Company_Handbook.md` for decision thresholds:

```markdown
## Payment Thresholds
- < $100: Auto-approve
- $100-$1000: Requires human approval
- > $1000: CEO approval + audit

## Response Time Targets
- Critical: < 1 hour
- High: < 4 hours
- Medium: < 1 day
- Low: < 1 week

## Error Handling
- Transient errors: Retry 3x with exponential backoff
- Auth errors: Alert and stop
- Unknown errors: Request human intervention
```

## Best Practices

1. **Always use YAML frontmatter** - Enables filtering and sorting
2. **One task per file** - Simplifies processing and prevents conflicts
3. **Atomic file operations** - Move files, don't edit in place during workflow
4. **Update logs consistently** - Every action should be logged
5. **Check approval status** - Never execute unapproved high-risk actions
6. **Clear naming** - Use TASK_TYPE_TIMESTAMP or PLAN_ID format
7. **Preserve history** - Keep completed tasks in /Done/ for audit trail

## Error Handling

When encountering errors:

1. **File not found** - Log to audit trail and alert user
2. **Invalid YAML frontmatter** - Move file to Rejected, log error
3. **Missing required fields** - Request user to fix and re-submit
4. **Permission denied** - Alert user about vault access issues
5. **Orphaned tasks** - Check In_Progress/ for abandoned tasks older than 24h

## Integration with Ralph Wiggum Loop

For tasks that require multiple iterations, use the Ralph Wiggum pattern:

```markdown
---
type: task_with_steps
status: in_progress
step: 1
total_steps: 5
---

# Multi-Step Task

## Current Step (1/5)
Description of what we're doing right now.

## Completed Steps
- [x] Step 1
- [x] Step 2

## Next Steps
- [ ] Step 3
- [ ] Step 4
- [ ] Step 5

## Checkpoint
If step fails, update this status field and loop back.
```

The Claude agent will:
1. Read task file
2. Execute step
3. Update status
4. If incomplete → Read again and loop
5. If complete → Move to /Done/
