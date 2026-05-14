# AI Employee - Quick Start Guide

## 🚀 5-Minute Setup

### 1. Install & Configure
```bash
# Install dependencies
pip install -r requirements.txt
pip install pytest pytest-asyncio pydantic-settings

# Setup environment
cp .env.example .env
# (Optional: edit .env for your credentials)
```

### 2. Verify Installation
```bash
# Run tests
python3 -m pytest tests/ -v

# Expected: 22 passed in ~0.4s
```

### 3. Open Vault in Obsidian
```bash
# Open Obsidian
# File → Open vault folder
# Select: AI_Employee_Vault/
```

That's it! 🎉

---

## 📋 How It Works (Simple Example)

### Create a Task
```bash
# Create a markdown file in AI_Employee_Vault/Needs_Action/
# FILE: EMAIL_TASK_001.md
```

```markdown
---
type: email_task
priority: high
source: gmail
created: 2026-02-08T10:30:00Z
---

# Respond to Client Email

**From:** client@example.com
**Subject:** Budget Increase Request

Need to review and respond by end of business.
```

### Python: Process the Task
```python
from vault_manager import VaultManager

manager = VaultManager()

# Get pending tasks
tasks = manager.get_needs_action_tasks()
print(f"Found {len(tasks)} tasks")

# Claim a task
task_file = Path("AI_Employee_Vault/Needs_Action/EMAIL_TASK_001.md")
manager.claim_task(task_file, agent_name="claude")
# File moves to: In_Progress/claude/EMAIL_TASK_001.md

# Create a plan
manager.create_plan(
    plan_id="PLAN_EMAIL_001",
    title="Respond to Client",
    steps=[
        "Review request details",
        "Check Company_Handbook thresholds",
        "Create approval if needed",
        "Send response"
    ]
)

# Complete the task
task_file = Path("AI_Employee_Vault/In_Progress/claude/EMAIL_TASK_001.md")
manager.move_task_to_done(task_file, result="email_sent")
# File moves to: Done/EMAIL_TASK_001.md

# Log the event
manager.log_event(
    event_type="task_completed",
    task_id="EMAIL_TASK_001",
    details={"response": "approved_and_sent"},
    agent="claude"
)
```

---

## 🎯 Core Concepts

### Task Workflow
```
Create Task
    ↓
Needs_Action/ (Inbox)
    ↓
Claim → In_Progress/ (Working)
    ↓
Plan → Plans/ (Strategy)
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
Log Event → Logs/2026-02-08.json
```

### Vault Folders

| Folder | Purpose | When |
|--------|---------|------|
| `Needs_Action/` | Inbox of new tasks | Tasks arrive here |
| `In_Progress/` | Currently being worked | Claude claims tasks here |
| `Plans/` | Generated action plans | Claude creates strategies |
| `Done/` | Completed tasks | Tasks finish here |
| `Pending_Approval/` | Awaiting human decision | High-risk actions |
| `Approved/` | User approved actions | Ready for execution |
| `Rejected/` | Rejected by user | Logged and skipped |
| `Logs/` | Audit trail | All events recorded |
| `Accounting/` | Financial records | Transaction tracking |

### Decision Thresholds (from Company_Handbook.md)

```
Payment Amount     Decision Authority    Action
─────────────────────────────────────────────────
< $100            Auto-approved         Execute now
$100-$500         Human review          Wait for approval
$500-$5K          Human approval        Pending_Approval
$5K-$50K          CEO approval          Escalate
> $50K            Board approval        Escalate
```

---

## 🔧 Common Operations

### Read a Task
```python
from vault_manager import VaultManager
from pathlib import Path

manager = VaultManager()
task = manager.read_task_file(
    Path("AI_Employee_Vault/Needs_Action/EMAIL_001.md")
)

print(task['priority'])      # high
print(task['metadata'])      # YAML frontmatter
print(task['content'])       # Task content
```

### List All Pending Tasks
```python
tasks = manager.get_needs_action_tasks()
for task in tasks:
    print(f"[{task['priority']}] {task['file_name']}")
```

### Check Pending Approvals
```python
approvals = manager.check_pending_approvals()
for approval in approvals:
    print(f"Action: {approval['file_name']}")
```

### Update Dashboard
```python
manager.update_dashboard({})
# Updates the Dashboard.md timestamp
```

---

## 📊 Monitoring

### View Real-Time Status
Open `AI_Employee_Vault/Dashboard.md` in Obsidian to see:
- System status
- Active tasks
- Pending approvals
- Recent completions
- Component health

### View Audit Trail
```bash
# View today's events
cat AI_Employee_Vault/Logs/2026-02-08.json | python3 -m json.tool
```

### Check Task Count
```bash
# Pending tasks
ls AI_Employee_Vault/Needs_Action/ | wc -l

# In progress
ls AI_Employee_Vault/In_Progress/claude/ | wc -l

# Completed
ls AI_Employee_Vault/Done/ | wc -l
```

---

## ✅ Testing

### Run All Tests
```bash
python3 -m pytest tests/ -v
# 22 tests, all passing
```

### Run Specific Test
```bash
python3 -m pytest tests/test_vault_operations.py::TestVaultReading -v
```

### Run with Coverage
```bash
pip install pytest-cov
python3 -m pytest tests/ --cov=. --cov-report=html
# Open htmlcov/index.html
```

---

## 🔐 Security

### Credentials
```bash
# ✅ GOOD: Use .env file
export GMAIL_CLIENT_ID=...
export STRIPE_API_KEY=...

# ❌ BAD: Never hardcode credentials
api_key = "sk_live_1234567890"  # DON'T DO THIS
```

### Files
```bash
# Protect the vault
chmod 700 AI_Employee_Vault/

# Don't commit .env
echo ".env" >> .gitignore
```

### Audit
```bash
# Review all actions
cat AI_Employee_Vault/Logs/*.json | python3 -m json.tool
```

---

## 🚦 Next Steps

### 1. Explore the Vault
- Open `AI_Employee_Vault/` in Obsidian
- Read `Dashboard.md`
- Review `Company_Handbook.md`
- Check `Business_Goals.md`

### 2. Create Your First Task
- Create `AI_Employee_Vault/Needs_Action/TEST_001.md`
- Use the template format shown above
- Run the Python code to process it

### 3. Run Tests
- `python3 -m pytest tests/ -v`
- See all 22 tests pass
- Explore test code to understand patterns

### 4. Ready for Silver Tier?
See `README.md` section "Next Steps: Silver Tier"
- Gmail integration
- WhatsApp integration
- Automated watchers

---

## 📚 Resources

| Document | Purpose |
|----------|---------|
| `README.md` | Complete documentation |
| `.claude/skills/vault-operations/SKILL.md` | Vault operations guide |
| `AI_Employee_Vault/Company_Handbook.md` | Decision rules |
| `AI_Employee_Vault/Business_Goals.md` | Goals & metrics |
| `IMPLEMENTATION_SUMMARY.txt` | Project summary |

---

## 🐛 Troubleshooting

### Tests Failing?
```bash
# Reinstall dependencies
pip install -r requirements.txt --upgrade
pip install pytest pytest-asyncio pydantic-settings

# Run single test for debugging
python3 -m pytest tests/test_vault_operations.py::TestVaultReading::test_read_task_file_with_frontmatter -v -s
```

### Can't Import Modules?
```bash
# Make sure you're in project root
pwd  # Should end with /fte-employee

# Test import
python3 -c "from vault_manager import VaultManager; print('OK')"
```

### Vault Not Found?
```bash
# Create it
mkdir -p AI_Employee_Vault/{Needs_Action,In_Progress,Plans,Done,Pending_Approval,Approved,Rejected,Logs,Accounting}

# Verify
ls -la AI_Employee_Vault/
```

---

## 💡 Tips

1. **Use Obsidian's File Explorer** to drag-and-drop files between folders
2. **Watch Dashboard.md** for real-time system status
3. **Check Logs/** for audit trail of all actions
4. **Reference Company_Handbook.md** for decision thresholds
5. **Run tests frequently** to verify system health

---

## 🎓 Learning Path

**Beginner:**
1. Read this QUICKSTART.md
2. Run the tests
3. Explore vault structure in Obsidian
4. Create one test task and process it

**Intermediate:**
1. Study `README.md` for full API
2. Review test code to understand patterns
3. Read SKILL.md for vault operations
4. Create multiple tasks with different priorities

**Advanced:**
1. Plan Silver Tier implementation (Gmail watcher)
2. Review architecture in README.md
3. Study test patterns for your own tests
4. Customize Company_Handbook.md for your needs

---

## 🎉 You're Ready!

The AI Employee Bronze Tier MVP is complete and tested.

Start by running:
```bash
python3 -m pytest tests/ -v
```

Then open `AI_Employee_Vault/Dashboard.md` in Obsidian.

Questions? Check `README.md` or `IMPLEMENTATION_SUMMARY.txt`.

Happy automating! 🤖
