# AI Employee (Digital FTE) - Bronze Tier MVP

An autonomous Digital Full-Time Equivalent (FTE) that manages personal and business affairs 24/7 using Claude Code, Obsidian vault, Python watchers, and MCP servers.

**Status:** 🟡 Bronze Tier (MVP) - Core infrastructure and testing framework complete

> **📋 Project Structure Updated (Feb 2026):** The project has been reorganized into a scalable, domain-based architecture. See [STRUCTURE.md](STRUCTURE.md) for the new directory layout and migration details. All 106 tests pass successfully with the new structure.

## What's Included (Bronze Tier)

### ✅ Completed
- **Skills Architecture** - Modular Agent Skills framework with YAML-based instructions
  - Vault Operations skill (foundation for all operations)
  - Templates for Plans, Approvals, and Briefings
  - Example workflows and patterns
  
- **Obsidian Vault Structure** - Local-first memory and control center
  - Task workflow folders: Needs_Action → In_Progress → Done
  - Approval gates: Pending_Approval → Approved/Rejected
  - Dashboard, Company_Handbook, Business_Goals
  - Audit logging system (JSON format)

- **Configuration System** - Environment-based settings
  - `.env` template with all required variables
  - Pydantic-based configuration validation
  - Support for all API credentials

- **Python Core Modules**
  - `vault_manager.py` - All vault operations (read, write, move, log)
  - `config.py` - Configuration management

- **Comprehensive Testing Suite** - 22 passing tests
  - Unit tests for vault operations
  - Browser integration tests (Playwright patterns)
  - Real-world workflow scenarios
  - Multi-agent concurrent processing
  - Error handling and edge cases

### 🟡 Next Steps (Silver+ Tiers)
- Gmail watcher (email polling)
- WhatsApp watcher (message handling)
- Filesystem watcher (approval execution)
- MCP servers (external actions)
- Orchestrator.py (master process)
- Watchdog.py (health monitoring)

---

## Quick Start

### 1. Prerequisites
- Python 3.10+
- Obsidian (for vault viewing/editing)
- Git

### 2. Installation

```bash
# Clone the repository
git clone <repo-url>
cd fte-employee

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install additional test dependencies
pip install pytest pytest-asyncio pydantic-settings
```

### 3. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your settings (for now, most can stay as defaults)
# For testing, you can leave them blank
```

### 4. Create Initial Vault

The vault directory structure is already created. You can:

```bash
# Open the vault in Obsidian
# File → Open vault folder → Select AI_Employee_Vault

# Or just verify it exists
ls -la AI_Employee_Vault/
```

### 5. Run Tests

```bash
# Run all tests
python3 -m pytest tests/ -v

# Run specific test module
python3 -m pytest tests/test_vault_operations.py -v

# Run with coverage
pip install pytest-cov
python3 -m pytest tests/ --cov=. --cov-report=html
```

---

## Project Structure

```
fte-employee/
├── .claude/
│   └── skills/
│       ├── vault-operations/          # Foundation skill
│       │   ├── SKILL.md               # Core instructions
│       │   ├── templates/
│       │   │   ├── plan-template.md
│       │   │   ├── approval-template.md
│       │   │   └── briefing-template.md
│       │   └── examples/
│       │       ├── plan-example.md
│       │       └── briefing-example.md
│       ├── gmail-processor/           # Coming in Silver Tier
│       ├── whatsapp-handler/          # Coming in Silver Tier
│       ├── financial-auditor/         # Coming in Gold Tier
│       ├── approval-workflow/         # Coming in Gold Tier
│       └── ralph-wiggum-loop/         # Coming in Platinum Tier
│
├── AI_Employee_Vault/                 # Local Obsidian vault (memory)
│   ├── Needs_Action/                  # Inbox of tasks
│   ├── In_Progress/                   # Tasks being worked on
│   ├── Plans/                         # Generated plans
│   ├── Done/                          # Completed tasks
│   ├── Pending_Approval/              # Awaiting human decision
│   ├── Approved/                      # User-approved actions
│   ├── Rejected/                      # Rejected actions (logged)
│   ├── Logs/                          # Audit trail (JSON)
│   ├── Accounting/                    # Financial records
│   ├── Dashboard.md                   # System status
│   ├── Company_Handbook.md            # Decision thresholds & rules
│   └── Business_Goals.md              # Quarterly objectives
│
├── tests/
│   ├── test_vault_operations.py       # Unit tests (8 tests)
│   ├── test_vault_browser.py          # Browser integration tests (6 tests)
│   ├── test_playwright_integration.py # Playwright patterns (8 tests)
│   ├── conftest.py                    # Pytest configuration
│   └── run_tests.sh                   # Test runner script
│
├── config.py                          # Configuration management
├── vault_manager.py                   # Vault operations API
├── requirements.txt                   # Python dependencies
├── .env.example                       # Environment template
└── README.md                          # This file
```

---

## How It Works (Bronze Tier)

### 1. Task Workflow

```
Create Task → Needs_Action/
     ↓
Claude Claims → In_Progress/claude/
     ↓
Create Plan → Plans/
     ↓
Check Risk Level
     ├─ Low Risk → Execute → Done/
     └─ High Risk → Pending_Approval/
     ↓
[If approval needed]
User Reviews → Approved/ or Rejected/
     ↓
Execute → Done/
     ↓
Log Event → Logs/YYYY-MM-DD.json
     ↓
Update Dashboard.md
```

### 2. Example: Process an Email Task

**Step 1: Create task** (from Gmail watcher, coming in Silver Tier)
```markdown
---
type: email_task
priority: high
source: gmail
created: 2026-02-08T10:30:00Z
---

# Respond to client email

From: client@example.com
Subject: Budget increase request

Action: Review and respond
```

**Step 2: Claude claims it**
```python
manager.claim_task(task_file, agent_name="claude")
# Moves file to In_Progress/claude/
```

**Step 3: Claude creates a plan**
```python
manager.create_plan(
    plan_id="PLAN_EMAIL_001",
    title="Respond to Client",
    steps=["Review request", "Check thresholds", "Draft response", "Send email"]
)
```

**Step 4: Check approval thresholds** (from Company_Handbook.md)
```markdown
## Decision Thresholds
- < $100: Auto-approved
- $100-5000: Human approval required
- > $5000: CEO approval required
```

**Step 5: Create approval request if needed**
```python
manager.create_approval_request(
    action_id="ACTION_BUDGET_001",
    action_type="budget_approval",
    description="Approve $50K budget increase",
    risk_level="high"
)
# Moves to Pending_Approval/
```

**Step 6: User approves** (drag-drop file to Approved/)
```
Pending_Approval/ACTION_BUDGET_001.md → Approved/ACTION_BUDGET_001.md
```

**Step 7: Claude executes and completes**
```python
manager.move_task_to_done(task_file, result="email_sent")
# Moves to Done/
```

**Step 8: Log event for audit trail**
```python
manager.log_event(
    event_type="task_completed",
    task_id="EMAIL_TASK_001",
    details={"result": "email_sent"},
    agent="claude"
)
# Creates/updates Logs/2026-02-08.json
```

---

## Vault Manager API

### Reading from Vault

```python
from vault_manager import VaultManager

manager = VaultManager()

# Get all pending tasks
tasks = manager.get_needs_action_tasks()
for task in tasks:
    print(f"{task['priority']}: {task['file_name']}")

# Read a single task file
task = manager.read_task_file(Path("AI_Employee_Vault/Needs_Action/EMAIL_001.md"))
print(task['metadata'])  # YAML frontmatter
print(task['content'])   # Content below frontmatter
```

### Writing to Vault

```python
# Create a plan
manager.create_plan(
    plan_id="PLAN_2026_02_08_001",
    title="Handle Customer Inquiry",
    steps=[
        "Read email",
        "Extract key information",
        "Formulate response",
        "Send email"
    ],
    priority="high",
    related_task="EMAIL_001"
)

# Create an approval request
manager.create_approval_request(
    action_id="ACTION_2026_02_08_001",
    action_type="payment",
    description="Pay $500 invoice to vendor",
    risk_level="medium",
    priority="high"
)

# Claim a task (move from Needs_Action to In_Progress)
manager.claim_task(task_file, agent_name="claude")

# Complete a task (move to Done)
manager.move_task_to_done(task_file, result="success")

# Log an event
manager.log_event(
    event_type="task_completed",
    task_id="EMAIL_001",
    details={"response": "sent"},
    agent="claude"
)

# Update dashboard
manager.update_dashboard({"status": "operational"})
```

---

## Company Handbook

The `AI_Employee_Vault/Company_Handbook.md` contains:

- **Financial Decision Thresholds** - Auto-approve, human review, CEO approval limits
- **Task Priority Rules** - Response time targets for critical, high, medium, low
- **Security & Access Control** - Credential management, vault access, error handling
- **Standard Operating Procedures** - Daily sync, hourly checks, weekly briefings
- **Escalation Procedures** - When to alert user, response time expectations
- **Health Checks** - Monitor system health, auto-recovery, maintenance tasks

---

## Business Goals

The `AI_Employee_Vault/Business_Goals.md` tracks:

- **Revenue Targets** - Monthly/quarterly revenue goals
- **Cost Optimization** - Budget reduction targets
- **Team Expansion** - Hiring plans and milestones
- **Product Development** - Feature release schedule
- **Customer Satisfaction** - NPS and support metrics
- **KPI Dashboard** - Revenue, operational, customer metrics

---

## Testing

### Run All Tests
```bash
python3 -m pytest tests/ -v
```

### Test Coverage by Module

| Module | Tests | Status |
|--------|-------|--------|
| Vault Operations (read/write) | 8 | ✅ PASS |
| Browser Integration | 6 | ✅ PASS |
| Playwright Scenarios | 8 | ✅ PASS |
| **Total** | **22** | **✅ PASS** |

### Test Categories

- **Unit Tests** - Individual functions and methods
- **Integration Tests** - Complete workflows (task → approval → completion)
- **Browser Simulation** - Playwright patterns for UI automation
- **Error Handling** - Invalid files, missing directories, corrupted data
- **Multi-Agent** - Multiple agents working concurrently

---

## Environment Variables

See `.env.example` for all available settings. Key ones:

```bash
# Vault
VAULT_PATH=AI_Employee_Vault
SKILLS_PATH=.claude/skills
LOG_LEVEL=INFO

# APIs (fill in when ready for Silver+ Tiers)
GMAIL_CLIENT_ID=...
TWILIO_ACCOUNT_SID=...
STRIPE_API_KEY=...

# Feature Flags
ENABLE_GMAIL_WATCHER=false
ENABLE_ORCHESTRATOR=false
```

---

## Next Steps

### Silver Tier (Email + Messaging)
- [ ] Implement Gmail watcher
- [ ] Implement WhatsApp watcher
- [ ] Create Gmail Processor skill
- [ ] Create WhatsApp Handler skill
- [ ] Test email/message workflows

### Gold Tier (Financial Intelligence)
- [ ] Implement Financial Auditor skill
- [ ] Create accounting transaction parser
- [ ] Generate Monday CEO briefings
- [ ] Create Financial Approval Workflow skill

### Platinum Tier (Full Autonomy)
- [ ] Implement Ralph Wiggum Loop skill
- [ ] Create MCP servers (email, payments, social)
- [ ] Build Orchestrator.py (master scheduler)
- [ ] Build Watchdog.py (process health monitor)
- [ ] Integrate with PM2 for process management
- [ ] 24/7 autonomous operation with human oversight

---

## Architecture Overview

```
┌─────────────────────────────────────────────┐
│        Claude Code (Brain)                  │
│   - Agent Skills                            │
│   - Reasoning & Decision Making             │
│   - Task Processing                         │
└────────────┬────────────────────────────────┘
             │
┌────────────▼────────────────────────────────┐
│   Vault Manager                             │
│   - Read/Write vault files                  │
│   - Manage task workflow                    │
│   - Log audit trail                         │
└────────────┬───────────┬────────────────────┘
             │           │
     ┌───────▼───┐   ┌────▼──────────┐
     │  Vault    │   │  Audit Logs   │
     │(Obsidian) │   │   (JSON)      │
     └───────────┘   └───────────────┘
```

### Data Flow

1. **Input Sources** → Tasks created in `/Needs_Action/`
   - Gmail Watcher (Silver Tier)
   - WhatsApp Watcher (Silver Tier)
   - Manual creation
   - API triggers

2. **Processing** → Claude processes tasks
   - Read task from vault
   - Create plan
   - Check approval thresholds
   - Execute or request approval

3. **Approval** → Human-in-the-loop
   - High-risk actions moved to `/Pending_Approval/`
   - User reviews and moves to `/Approved/` or `/Rejected/`
   - System detects approval and executes

4. **Completion** → Task moved to `/Done/`
   - Event logged to `/Logs/`
   - Dashboard updated
   - Metrics recorded

5. **Output** → External actions (Silver+ Tiers)
   - Send emails (MCP email server)
   - Process payments (MCP payment server)
   - Post to social (MCP social server)
   - Browser automation (MCP browser server)

---

## Security Considerations

✅ **Implemented**
- Credentials stored in `.env` (never in code)
- Vault files are local (no cloud sync)
- Audit logging of all actions
- Approval gates for risky decisions

🔒 **Best Practices**
- Never commit `.env` to version control
- Rotate API keys monthly
- Keep vault directory secure (chmod 700)
- Review audit logs regularly
- Test with non-production API keys first

---

## Support & Troubleshooting

### Tests Failing?
```bash
# Reinstall dependencies
pip install -r requirements.txt
pip install pytest pytest-asyncio pydantic-settings

# Run single test for debugging
python3 -m pytest tests/test_vault_operations.py::TestVaultReading::test_read_task_file_with_frontmatter -v -s
```

### Vault Issues?
```bash
# Verify vault structure
ls -la AI_Employee_Vault/
python3 -c "from vault_manager import VaultManager; m = VaultManager(); print('Vault OK')"
```

### Import Errors?
```bash
# Make sure you're in the right directory
pwd  # Should be repo root
python3 config.py  # Test config loading
```

---

## Development

### Add a New Skill
1. Create directory: `.claude/skills/new-skill/`
2. Add `SKILL.md` with instructions
3. Add templates in `templates/`
4. Add examples in `examples/`

### Add a New Watcher
1. Create `watchers/new_watcher.py`
2. Extend `BaseWatcher` class
3. Implement poll logic
4. Add tests in `tests/`

### Add a New MCP Server
1. Create `mcp_servers/new_server.py`
2. Implement server interface
3. Handle credentials securely
4. Add error handling

---

## Contributing

This is a personal project, but feel free to fork and customize!

## License

Proprietary - For personal use

---

## References

- [Anthropic Skills Guide](https://github.com/anthropics/skills)
- [Model Context Protocol (MCP)](https://modelcontextprotocol.io)
- [Obsidian](https://obsidian.md)
- [Playwright](https://playwright.dev)

---

**Version:** 1.0 (Bronze Tier MVP)  
**Last Updated:** 2026-02-08  
**Status:** Ready for development
