# AI Employee System - Project Structure

This document describes the reorganized project structure following best practices for scalable AI systems.

## Overview

The AI Employee system is now organized into clear, domain-specific directories that separate concerns and improve maintainability.

## Directory Structure

```
ai-employee-system/
├── agents/                          # Agent definitions & configurations
│   ├── local_agent.json             # Local AI agent configuration
│   ├── cloud_agent.json             # Cloud AI agent configuration
│   └── orchestrator_agent.json      # Central orchestrator configuration
│
├── skills/                          # All skill implementations (domain-organized)
│   ├── communication/               # Communication-related skills
│   │   ├── email_processor/         # Email/Gmail processing
│   │   ├── whatsapp_handler/        # WhatsApp messaging
│   │   └── social_media_poster/     # Social media posting (future)
│   ├── finance/                     # Financial skills
│   │   ├── transaction_analyzer/    # Transaction analysis & auditing
│   │   ├── invoice_generator/       # Invoice generation (future)
│   │   └── expense_categorizer/     # Expense categorization (future)
│   ├── project_management/          # Project management skills (future)
│   │   ├── task_planner/
│   │   ├── deadline_tracker/
│   │   └── progress_reporter/
│   └── system/                      # System/core skills
│       ├── approval_manager/        # Approval workflow management
│       ├── vault_operations/        # Obsidian vault operations
│       ├── orchestration_loop/      # Main orchestration loop
│       └── audit_logger/            # Audit logging (future)
│
├── config/                          # Configuration files
│   ├── agent_config.yaml            # Agent instances & global settings
│   ├── skills_registry.json         # Skills metadata and dependencies
│   └── mcp_config.json              # MCP servers configuration
│
├── orchestrator/                    # Main orchestration logic
│   ├── orchestrator.py              # Central orchestrator process
│   ├── base_watcher.py              # Base watcher abstraction
│   ├── filesystem_watcher.py        # File system monitoring
│   ├── gmail_watcher.py             # Gmail monitoring
│   ├── whatsapp_watcher.py          # WhatsApp monitoring
│   └── __init__.py                  # Package initialization
│
├── mcp_servers/                     # MCP servers for external integrations
│   ├── browser_server.py            # Browser automation (Playwright)
│   ├── email_server.py              # Email integration
│   ├── payment_server.py            # Payment processing (Stripe)
│   ├── social_server.py             # Social media integration
│   └── __init__.py
│
├── utilities/                       # Utility modules & helpers
│   ├── vault_manager.py             # Obsidian vault operations
│   ├── api_server.py                # FastAPI server
│   ├── financial_auditor.py         # Financial analysis utilities
│   ├── watchdog_monitor.py          # System monitoring
│   └── __init__.py
│
├── deployment/                      # Deployment automation & scripts
│   ├── deploy.sh                    # Deployment script
│   ├── deployment_automation.py     # Python deployment utilities
│   ├── ecosystem.config.js          # PM2 configuration
│   ├── setup_cron_backups.sh        # Backup automation
│   └── __init__.py
│
├── tests/                           # Test suites (organized by component)
│   ├── test_skills/                 # Skill unit tests
│   │   ├── test_vault_operations.py
│   │   ├── test_transaction_analyzer.py
│   │   └── test_watchers.py
│   ├── test_agents/                 # Agent tests
│   ├── integration_tests/           # Integration tests
│   │   ├── test_browser_integration.py
│   │   └── test_vault_browser.py
│   ├── conftest.py                  # Pytest configuration
│   └── run_tests.sh                 # Test runner
│
├── AI_Employee_Vault/               # Obsidian vault (task management)
│   ├── Dashboard.md
│   ├── Company_Handbook.md
│   ├── Business_Goals.md
│   ├── Needs_Action/                # Tasks requiring attention
│   ├── In_Progress/                 # Currently active tasks
│   ├── Plans/                       # Planned tasks
│   ├── Done/                        # Completed tasks
│   ├── Pending_Approval/            # Tasks awaiting approval
│   ├── Approved/                    # Approved tasks
│   ├── Rejected/                    # Rejected tasks
│   ├── Accounting/                  # Financial records
│   ├── Logs/                        # System logs
│   └── .obsidian/                   # Obsidian configuration
│
├── scripts/                         # Utility scripts
│   └── backup_vault.sh              # Vault backup
│
├── docs/                            # Documentation
│   ├── AI Employee.pdf
│   ├── ai_employee.txt
│   └── hackathon_guide.txt
│
├── config.py                        # Global configuration loader
├── requirements.txt                 # Python dependencies
├── README.md                        # Main documentation
├── .env.example                     # Environment template
└── .claude/                         # Claude workspace (legacy, for reference)
```

## Key Design Principles

### 1. **Domain-Based Organization**
Skills are organized by domain (communication, finance, project_management, system) rather than by type. This makes it easier to find and maintain related functionality.

### 2. **Modular Architecture**
- Each skill is self-contained with its own SKILL.md, examples, and templates
- MCP servers are independent and can be enabled/disabled via configuration
- Watchers are pluggable components that can monitor different sources

### 3. **Configuration-Driven**
- Agent configurations are defined in JSON files (agents/)
- Skills registry contains metadata and dependencies (config/skills_registry.json)
- MCP servers configuration is centralized (config/mcp_config.json)
- Global settings are in YAML format (config/agent_config.yaml)

### 4. **Clear Separation of Concerns**
- **Orchestrator**: Handles workflow coordination and agent management
- **Utilities**: Provides helper functions and common operations
- **Skills**: Contains domain-specific logic
- **MCP Servers**: Manages external integrations
- **Tests**: Organized by component type (skills, agents, integration)

## Import Patterns

All Python modules are set up to work from the project root. Example imports:

```python
from config import get_settings
from utilities.vault_manager import VaultManager
from orchestrator.orchestrator import Orchestrator
from orchestrator.base_watcher import BaseWatcher
from mcp_servers.browser_server import BrowserServer
from skills.communication.email_processor.SKILL import EmailProcessor
```

## Running the System

### Start the Orchestrator
```bash
python3 orchestrator/orchestrator.py
```

### Run Tests
```bash
pytest tests/ -v
# or use the provided script
bash tests/run_tests.sh
```

### Deploy
```bash
bash deployment/deploy.sh
```

### Start API Server
```bash
python3 utilities/api_server.py
```

## Adding New Skills

To add a new skill:

1. Create a directory under `skills/{domain}/{skill_name}`
2. Add `SKILL.md` with skill documentation
3. Add `examples/` and `templates/` directories
4. Register the skill in `config/skills_registry.json`
5. Create tests in `tests/test_skills/`

## Configuration Files

### agents/
- `local_agent.json`: Configuration for local agent execution
- `cloud_agent.json`: Configuration for cloud-based execution
- `orchestrator_agent.json`: Central orchestrator configuration

### config/
- `agent_config.yaml`: Global settings and agent initialization
- `skills_registry.json`: Skills metadata, dependencies, and status
- `mcp_config.json`: MCP server configurations

## Migration Notes

This restructuring:
- ✓ Maintains backward compatibility through proper imports
- ✓ Passes all existing tests (106 tests)
- ✓ Improves code organization and maintainability
- ✓ Supports future scaling and feature additions
- ✓ Follows industry best practices for modular systems

### Files Moved
- `orchestrator.py` → `orchestrator/orchestrator.py`
- `vault_manager.py` → `utilities/vault_manager.py`
- `watchdog_monitor.py` → `utilities/watchdog_monitor.py`
- `financial_auditor.py` → `utilities/financial_auditor.py`
- `server.py` → `utilities/api_server.py`
- `deploy.sh` → `deployment/deploy.sh`
- `ecosystem.config.js` → `deployment/ecosystem.config.js`
- `setup_cron_backups.sh` → `deployment/setup_cron_backups.sh`
- `.claude/skills/*` → `skills/{domain}/*` (reorganized by category)

### Files Created
- `agents/` directory with agent JSON definitions
- `config/` directory with YAML and JSON configurations
- `orchestrator/` directory consolidating orchestration logic
- `utilities/` directory for common utilities
- `deployment/` directory for deployment automation
- `skills/` with domain-based organization

## Next Steps

1. Update external references to use new import paths
2. Consider creating stub implementations for placeholder skills
3. Add more comprehensive integration tests
4. Document skill development guidelines
5. Set up CI/CD pipeline with new structure
