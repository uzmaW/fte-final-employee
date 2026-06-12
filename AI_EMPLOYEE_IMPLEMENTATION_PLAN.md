# AI Employee (Digital FTE) Implementation Plan

## Project Overview
Building an autonomous Digital FTE (Full-Time Equivalent) that manages personal and business affairs 24/7 using Claude Code, Obsidian, Python Watchers, and MCP servers. This is a local-first, human-in-the-loop system designed to act as a "Senior Consultant" making autonomous decisions while requiring approval for risky actions.

**Key Innovation:** Implement all AI functionality as reusable Agent Skills (modular instructions) rather than monolithic scripts.

---

## Architecture Stack Summary

| Component | Purpose | Technology |
|-----------|---------|-----------|
| **Brain** | Reasoning engine with dynamic skill loading | Claude Code + Agent Skills |
| **Memory/GUI** | Dashboard & control center | Obsidian (local markdown vault) |
| **Sensors** | Event detection & triggers | Python Watchers (Gmail, WhatsApp, Filesystem) |
| **Hands** | Execute external actions | MCP Servers (send emails, make payments, post social) |
| **Orchestration** | Master scheduling & process management | Orchestrator.py + Watchdog.py |

---

## Development Tiers

### Bronze Tier (MVP) - Week 1-2
Core functionality with manual approval requirements.
- ✅ Vault Operations skill
- ✅ Basic file-based workflow
- ✅ Obsidian vault structure
- ✅ Simple Python watcher (filesystem)

### Silver Tier - Week 2-3
Add email and messaging integration.
- ✅ Gmail Processor skill
- ✅ WhatsApp Handler skill
- ✅ Gmail watcher
- ✅ Basic approval workflow

### Gold Tier - Week 3-4
Add financial intelligence and autonomous decision-making.
- ✅ Financial Auditor skill
- ✅ Monday Morning CEO Briefing (transaction audit)
- ✅ Approval Workflow skill
- ✅ Company Handbook enforcement

### Platinum Tier - Week 4+
Advanced autonomous operation with process management.
- ✅ Ralph Wiggum Loop skill (task persistence)
- ✅ MCP servers for external actions
- ✅ Orchestrator.py (master process)
- ✅ Watchdog.py (health monitoring)
- ✅ Process manager integration (PM2)

---

## Detailed Implementation Roadmap

### Phase 1: Skills Architecture Setup (Task 1)

**Objective:** Create modular, reusable Claude Skills with proper directory structure.

**Directory Structure:**
```
.claude/skills/
├── vault-operations/
│   ├── SKILL.md                    # Core instructions
│   ├── templates/
│   │   ├── plan-template.md
│   │   ├── approval-template.md
│   │   └── briefing-template.md
│   └── examples/
│       ├── plan-example.md
│       └── briefing-example.md
├── gmail-processor/
│   ├── SKILL.md
│   ├── reference.md               # Gmail API details
│   └── examples/
│       └── email-processing-flow.md
├── whatsapp-handler/
│   ├── SKILL.md
│   └── examples/
│       └── message-response.md
├── financial-auditor/
│   ├── SKILL.md
│   ├── templates/
│   │   └── ceo-briefing.md
│   └── reference.md               # Accounting logic
├── approval-workflow/
│   ├── SKILL.md
│   └── examples/
│       └── approval-flow.md
└── ralph-wiggum-loop/
    ├── SKILL.md
    └── reference.md               # Task completion patterns
```

**SKILL.md Format (YAML Frontmatter):**
```yaml
---
name: vault-operations
description: Read from and write to the Obsidian vault with proper folder structure and markdown formatting
allowed-tools: Read, Write, Glob
---
# Vault Operations Skill
[Instructions and usage guidelines]
```

**Tasks:**
- Create `.claude/skills/` directory
- Create subdirectories for each skill
- Create templates directory with markdown templates

---

### Phase 2: Core Skills Implementation (Tasks 2-7)

#### Skill 2: Vault Operations (Foundation)
**File:** `.claude/skills/vault-operations/SKILL.md`

**Purpose:** Teach Claude how to interact with Obsidian vault as the single source of truth.

**Vault Directory Structure:**
- `/Needs_Action/` - Inbox of tasks from Watchers
- `/In_Progress/<agent>/` - Tasks being worked on
- `/Plans/` - Generated plans (PLAN_* prefix)
- `/Done/` - Completed tasks
- `/Pending_Approval/` - Actions requiring human approval
- `/Approved/` - User-approved files ready for execution
- `/Rejected/` - User-rejected actions (logged)
- `/Logs/` - Audit trail (YYYY-MM-DD.json format)
- `/Dashboard.md` - Real-time system status
- `/Company_Handbook.md` - Rules of engagement & thresholds
- `/Business_Goals.md` - Quarterly objectives & metrics
- `/Accounting/Current_Month.md` - Transaction ledger

**Key Operations:**
1. List all files in `/Needs_Action/` using Glob
2. Parse YAML frontmatter (type, priority, source, timestamp)
3. Check `/In_Progress/` to avoid duplicate processing
4. Move claimed tasks to `/In_Progress/<agent>/`
5. Create plans with checklists in `/Plans/`
6. Move completed tasks to `/Done/`
7. Log all actions to `/Logs/`

**Deliverables:**
- SKILL.md with complete vault interaction instructions
- plan-template.md (markdown with checklist format)
- approval-template.md (for approval requests)
- briefing-template.md (for CEO briefing format)
- Examples showing each operation type

---

#### Skill 3: Gmail Processor
**File:** `.claude/skills/gmail-processor/SKILL.md`

**Purpose:** Process incoming emails, categorize them, and create tasks.

**Key Functions:**
- Fetch unread emails via Gmail API
- Categorize by sender/subject/keywords
- Extract actionable items
- Create task files in `/Needs_Action/`
- Mark emails as processed

**Deliverables:**
- SKILL.md with Gmail API integration patterns
- reference.md with Gmail API documentation
- email-processing-flow.md example

---

#### Skill 4: WhatsApp Handler
**File:** `.claude/skills/whatsapp-handler/SKILL.md`

**Purpose:** Handle WhatsApp messages, respond intelligently, and create tasks.

**Key Functions:**
- Monitor WhatsApp messages
- Parse message content for actionable items
- Generate contextual responses
- Log conversations
- Create tasks from urgent messages

**Deliverables:**
- SKILL.md with WhatsApp integration patterns
- message-response.md example

---

#### Skill 5: Financial Auditor
**File:** `.claude/skills/financial-auditor/SKILL.md`

**Purpose:** Analyze transactions and generate CEO briefings.

**Key Functions:**
- Parse bank transaction feeds
- Categorize by expense type
- Identify anomalies and revenue trends
- Generate "Monday Morning CEO Briefing"
- Report cash position and bottlenecks

**Deliverables:**
- SKILL.md with financial analysis logic
- reference.md with accounting principles
- ceo-briefing.md template

---

#### Skill 6: Approval Workflow
**File:** `.claude/skills/approval-workflow/SKILL.md`

**Purpose:** Implement human-in-the-loop safety gates for risky actions.

**Key Functions:**
- Identify high-risk actions (payments > $100, new recipients, etc.)
- Move proposals to `/Pending_Approval/`
- Wait for user to move to `/Approved/` or `/Rejected/`
- Execute only approved actions
- Log decision rationale

**Deliverables:**
- SKILL.md with approval gates & thresholds
- approval-flow.md example showing decision tree

---

#### Skill 7: Ralph Wiggum Loop
**File:** `.claude/skills/ralph-wiggum-loop/SKILL.md`

**Purpose:** Implement task completion persistence - Claude keeps iterating until task is done.

**Key Pattern:**
1. Read task file
2. Execute step
3. Update task status
4. If incomplete → Loop back to step 2
5. If complete → Move to `/Done/`

**Deliverables:**
- SKILL.md with loop pattern & completion markers
- reference.md with examples of task persistence

---

### Phase 3: Python Watchers & Automation (Task 8)

**Objective:** Build event listeners that trigger Claude with tasks.

**Directory Structure:**
```
watchers/
├── __init__.py
├── gmail_watcher.py       # Poll Gmail inbox
├── whatsapp_watcher.py    # Monitor WhatsApp messages
├── filesystem_watcher.py  # Monitor vault folders
├── base_watcher.py        # Abstract watcher class
└── config.py              # Configuration & credentials
```

**Watchers to Build:**

1. **gmail_watcher.py**
   - Authenticate with Gmail API (OAuth)
   - Poll unread emails every 5 minutes
   - Create task files in `/Needs_Action/`
   - Mark as processed

2. **whatsapp_watcher.py**
   - Connect to WhatsApp (via Twilio or similar)
   - Monitor incoming messages
   - Create task files from urgent messages
   - Queue responses

3. **filesystem_watcher.py**
   - Monitor `/Approved/` folder for approved actions
   - Trigger MCP servers to execute actions
   - Move completed files to `/Done/`

**Deliverables:**
- Each watcher as standalone Python script
- Common base class for error handling & retry logic
- Config system with environment variables

---

### Phase 4: MCP Server Implementations (Task 9)

**Objective:** Create servers for external actions (send email, make payments, post social).

**Directory Structure:**
```
mcp_servers/
├── email_server.py        # Send emails via SMTP
├── payment_server.py      # Process payments (Stripe, etc.)
├── social_server.py       # Post to social media
├── calendar_server.py     # Update calendar
└── browser_server.py      # Playwright automation
```

**MCP Servers to Build:**

1. **email_server.py**
   - Send emails via Gmail/SMTP
   - Track sent messages
   - Handle errors gracefully

2. **payment_server.py**
   - Process payments (with approval gates)
   - Validate recipients
   - Create audit logs

3. **social_server.py**
   - Post to Twitter, LinkedIn, etc.
   - Queue posts for scheduling
   - Log engagement

4. **browser_server.py**
   - Use Playwright for web automation
   - Click buttons, fill forms
   - Take screenshots for verification

**Deliverables:**
- Each MCP server as standalone process
- Configuration for credentials
- Error handling & retry logic

---

### Phase 5: Orchestration Layer (Tasks 10-11)

**Objective:** Master process for scheduling, folder watching, and health monitoring.

#### Orchestrator.py (Task 10)
**Purpose:** Master process that coordinates all components.

**Functions:**
- Start/stop all watchers
- Schedule recurring tasks (CEO briefing every Monday)
- Monitor folder changes
- Manage process lifecycle
- Log system health

**Pseudocode:**
```python
class Orchestrator:
    def __init__(self):
        self.watchers = []
        self.mcp_servers = []
        self.schedule = {}
    
    def start_watchers(self):
        # Launch gmail_watcher, whatsapp_watcher, etc.
        pass
    
    def schedule_task(self, name, cron_expression, action):
        # Schedule recurring tasks
        pass
    
    def watch_folders(self):
        # Monitor vault folders for changes
        pass
    
    def health_check(self):
        # Verify all processes are running
        pass
```

**Deliverables:**
- orchestrator.py with process management
- Cron scheduling support
- Folder watching (watchdog library)

#### Watchdog.py (Task 11)
**Purpose:** Health monitor that auto-restarts failed processes.

**Functions:**
- Monitor all process PIDs
- Detect crashes
- Auto-restart failed processes
- Alert on repeated failures
- Log health metrics

**Pseudocode:**
```python
class Watchdog:
    def __init__(self):
        self.processes = {}
        self.restart_count = {}
    
    def monitor_loop(self):
        while True:
            for name, pid in self.processes.items():
                if not self.is_running(pid):
                    self.restart(name)
            time.sleep(30)
    
    def is_running(self, pid):
        # Check if process is alive
        pass
    
    def restart(self, process_name):
        # Auto-restart failed process
        pass
```

**Deliverables:**
- watchdog.py with health monitoring
- Auto-restart logic
- Alert system

---

### Phase 6: Obsidian Vault Setup (Task 12)

**Objective:** Create the complete vault structure and initialize dashboards.

**Directory Structure:**
```
AI_Employee_Vault/
├── Needs_Action/
├── In_Progress/
│   ├── claude/
│   ├── email-processor/
│   └── financial-auditor/
├── Plans/
├── Done/
├── Pending_Approval/
├── Approved/
├── Rejected/
├── Logs/
│   └── 2026-02-08.json
├── Accounting/
│   └── Current_Month.md
├── Dashboard.md           # Real-time system status
├── Company_Handbook.md    # Rules & thresholds
├── Business_Goals.md      # Quarterly objectives
└── .obsidian/            # Obsidian configuration
    └── plugins.json
```

**Deliverables:**
- Create all directories
- Dashboard.md with system status widgets
- Company_Handbook.md with decision rules
- Business_Goals.md with quarterly targets
- Example task files in each folder
- Obsidian configuration for markdown rendering

---

### Phase 7: Templates & Examples (Task 13)

**Objective:** Create reusable templates for common workflows.

**Templates:**

1. **Company_Handbook.md**
   ```
   # Company Handbook
   
   ## Decision Thresholds
   - Payments < $100: Auto-approved
   - Payments $100-$1000: Requires approval
   - Payments > $1000: CEO approval + audit
   - New recipients: Always requires approval
   
   ## Task Priority Rules
   - Critical: Respond within 1 hour
   - High: Respond within 4 hours
   - Medium: Respond within 1 day
   - Low: Respond within 1 week
   
   ## Error Handling
   - Transient API errors: Retry 3x with exponential backoff
   - Authentication errors: Alert and stop
   ```

2. **Business_Goals.md**
   ```
   # Business Goals Q1 2026
   
   ## Revenue Targets
   - Product Sales: $50,000
   - Services: $30,000
   
   ## Efficiency Targets
   - Email processing time: < 2 hours/day
   - Meeting scheduling: Autonomous
   - Invoice processing: 100% automated
   ```

3. **Task Template** (for `/Needs_Action/`)
   ```yaml
   ---
   type: email_task
   priority: high
   source: gmail
   created: 2026-02-08T10:30:00Z
   ---
   
   # Task Title
   
   From: sender@example.com
   Subject: Original subject
   
   Action required: [specific action]
   ```

**Deliverables:**
- Company_Handbook.md with decision thresholds
- Business_Goals.md with quarterly targets
- Task template for each watcher type
- Example completed tasks for reference

---

### Phase 8: Configuration & Credentials (Task 14)

**Objective:** Build secure configuration system.

**Files to Create:**

1. **.env.example**
   ```
   # Gmail API
   GMAIL_CLIENT_ID=xxx
   GMAIL_CLIENT_SECRET=xxx
   GMAIL_REFRESH_TOKEN=xxx
   
   # WhatsApp (Twilio)
   TWILIO_ACCOUNT_SID=xxx
   TWILIO_AUTH_TOKEN=xxx
   
   # Payment Processing
   STRIPE_API_KEY=xxx
   
   # System
   VAULT_PATH=/path/to/AI_Employee_Vault
   LOG_LEVEL=DEBUG
   ```

2. **config.py**
   - Load from `.env`
   - Validate required variables
   - Set defaults

3. **Security Best Practices**
   - Never commit `.env`
   - Use environment variables
   - Rotate credentials monthly
   - Audit logging every action

**Deliverables:**
- .env.example template
- config.py with validation
- Setup guide for each API credential
- Security checklist

---

### Phase 9: Documentation (Task 15)

**Objective:** Write comprehensive guides and troubleshooting.

**Documents:**

1. **SETUP.md** - Step-by-step installation guide
2. **ARCHITECTURE.md** - System design and data flow
3. **SKILLS_GUIDE.md** - How to create custom skills
4. **API_REFERENCE.md** - All available APIs and tools
5. **TROUBLESHOOTING.md** - Common issues and solutions
6. **SECURITY.md** - Privacy and credential management
7. **DEPLOYMENT.md** - Cloud vs local deployment options

**Deliverables:**
- All markdown documentation files
- Quick start guide
- API reference with examples
- Troubleshooting FAQ

---

### Phase 10: Testing & Examples (Task 16)

**Objective:** Create working examples and test scenarios.

**Test Scenarios:**

1. **Bronze Tier Test**
   - Create a task in `/Needs_Action/`
   - Claude processes it
   - Creates approval in `/Pending_Approval/`
   - User approves/rejects
   - Task moves to `/Done/` or `/Rejected/`

2. **Silver Tier Test**
   - Receive email in Gmail
   - gmail_watcher creates task file
   - Claude processes email
   - Creates response task

3. **Gold Tier Test**
   - Simulate bank transactions
   - Financial auditor processes
   - Generates CEO briefing
   - Reports delivered to `/Done/`

4. **Platinum Tier Test**
   - All watchers running
   - Orchestrator scheduling tasks
   - Watchdog auto-restarting failed processes
   - MCP servers executing actions

**Deliverables:**
- Example task files for each tier
- Test data (sample emails, transactions)
- Test scenarios with expected outputs
- Integration test scripts

---

## Technology Stack Details

### Required Libraries

**Python:**
```
anthropic>=1.0.0          # Claude API
google-auth-oauthlib      # Gmail OAuth
google-auth-httplib2      # Gmail API
google-api-python-client  # Gmail client
twilio                    # WhatsApp via Twilio
stripe                    # Payment processing
playwright                # Browser automation
watchdog                  # Folder monitoring
pydantic                  # Configuration validation
python-dotenv             # .env file loading
schedule                  # Task scheduling
requests                  # HTTP requests
```

**Node/Global:**
```
pm2                       # Process manager
```

---

## Success Metrics

- ✅ All 5 core skills deployed and documented
- ✅ Watchers successfully polling Gmail and filesystem
- ✅ Vault properly organized with task workflow
- ✅ Approval workflow functioning with human approval gates
- ✅ Financial auditor generating weekly CEO briefings
- ✅ Orchestrator.py managing all processes
- ✅ Watchdog.py auto-restarting failed processes
- ✅ 100% uptime for 24+ hours with PM2 process manager
- ✅ Zero security incidents (credentials never logged)
- ✅ Complete documentation and runbooks

---

## Timeline Estimate

- **Bronze Tier (MVP):** 5-7 days
- **Silver Tier:** 3-5 days
- **Gold Tier:** 4-6 days
- **Platinum Tier:** 5-7 days
- **Documentation & Polish:** 3-5 days

**Total: 3-4 weeks** for fully functional Digital FTE

---

## References

- Hackathon Guide: "Personal AI Employee Hackathon 0: Building Autonomous FTEs in 2026"
- Skills Architecture: https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md
- Claude Code Documentation: https://claude.ai
- MCP Specification: https://modelcontextprotocol.io

---

**Document Version:** 1.0  
**Last Updated:** 2026-02-08  
**Status:** Ready for Implementation
