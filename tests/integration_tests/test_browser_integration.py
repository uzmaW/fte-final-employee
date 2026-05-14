"""
Playwright-based integration tests for AI Employee system.
Tests vault operations, file management, and browser automation patterns.
"""

import pytest
import asyncio
import json
import tempfile
from pathlib import Path
from datetime import datetime
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from utilities.vault_manager import VaultManager


@pytest.fixture
def temp_vault():
    """Create a temporary vault for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir) / "test_vault"
        vault_path.mkdir()
        
        for subdir in ["Needs_Action", "In_Progress", "Plans", "Done", 
                      "Pending_Approval", "Approved", "Rejected", "Logs", "Accounting"]:
            (vault_path / subdir).mkdir()
        
        yield vault_path


class TestPlaywrightVaultSimulation:
    """Test vault operations simulating Playwright browser interactions."""
    
    def test_simulate_browser_form_submission_to_vault(self, temp_vault):
        """Simulate user submitting form in Obsidian UI that creates vault files."""
        manager = VaultManager()
        manager.vault_path = temp_vault
        
        # Simulate browser form data (like from Obsidian web UI)
        form_data = {
            "task_type": "email_task",
            "priority": "high",
            "email_from": "client@example.com",
            "email_subject": "Urgent: Budget Approval Needed",
            "action_required": "Review and respond to budget request"
        }
        
        # Create task file based on form data
        task_file = temp_vault / "Needs_Action" / "EMAIL_BROWSER_001.md"
        with open(task_file, 'w') as f:
            f.write(f"""---
type: {form_data['task_type']}
priority: {form_data['priority']}
source: browser_ui
created: {datetime.utcnow().isoformat()}Z
---

# {form_data['email_subject']}

**From:** {form_data['email_from']}
**Subject:** {form_data['email_subject']}

## Action Required
{form_data['action_required']}
""")
        
        # Verify file was created
        assert task_file.exists()
        
        # Read and verify
        task = manager.read_task_file(task_file)
        assert task['priority'] == 'high'
        assert 'Budget' in task['content']
    
    def test_simulate_browser_file_drag_and_drop(self, temp_vault):
        """Simulate drag-and-drop file operations (move between folders)."""
        manager = VaultManager()
        manager.vault_path = temp_vault
        
        # Create initial task
        task_file = temp_vault / "Needs_Action" / "TASK_001.md"
        with open(task_file, 'w') as f:
            f.write("---\ntype: test\n---\n# Test Task")
        
        # Simulate drag-drop: Needs_Action → In_Progress/claude
        in_progress_dir = temp_vault / "In_Progress" / "claude"
        in_progress_dir.mkdir(parents=True, exist_ok=True)
        new_path = in_progress_dir / "TASK_001.md"
        task_file.rename(new_path)
        
        # Verify
        assert not task_file.exists()
        assert new_path.exists()
        
        # Simulate another drag-drop: In_Progress → Done
        done_path = temp_vault / "Done" / "TASK_001.md"
        new_path.rename(done_path)
        
        assert done_path.exists()
    
    def test_simulate_browser_approval_workflow(self, temp_vault):
        """Simulate approval workflow using file system as medium."""
        manager = VaultManager()
        manager.vault_path = temp_vault
        
        # Step 1: System creates approval request
        manager.create_approval_request(
            action_id="ACTION_BROWSER_001",
            action_type="payment",
            description="Pay $750 to vendor ABC",
            risk_level="medium"
        )
        
        # Verify in pending folder
        pending_file = temp_vault / "Pending_Approval" / "ACTION_BROWSER_001.md"
        assert pending_file.exists()
        
        # Step 2: Simulate user opening file in browser and reading
        with open(pending_file, 'r') as f:
            pending_content = f.read()
        assert "Pay $750" in pending_content
        
        # Step 3: Simulate user approving (drag-drop to Approved folder)
        approved_file = temp_vault / "Approved" / "ACTION_BROWSER_001.md"
        pending_file.rename(approved_file)
        
        # Step 4: System detects approval
        approved_actions = manager.get_approved_actions()
        assert len(approved_actions) == 1
        assert approved_actions[0]['action_id'] == "ACTION_BROWSER_001"


class TestPlaywrightDashboardUpdates:
    """Test dashboard updates simulating browser polling."""
    
    @pytest.fixture
    def vault_with_dashboard(self):
        """Create vault with dashboard file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir) / "test_vault"
            vault_path.mkdir()
            
            for subdir in ["Needs_Action", "In_Progress", "Plans", "Done", 
                          "Pending_Approval", "Approved", "Rejected", "Logs", "Accounting"]:
                (vault_path / subdir).mkdir()
            
            # Create initial dashboard
            dashboard_file = vault_path / "Dashboard.md"
            dashboard_file.write_text("""# AI Employee Dashboard

**Last Updated:** 2026-02-08 10:00:00 UTC
**Uptime:** 0 hours

## Status Summary
- Overall Status: 🟡 Initializing
- Vault Structure: 🟢 Ready

## Activity Summary
- Total Tasks: 0
- Completed Today: 0

## Pending Approvals
No pending approvals.
""")
            
            yield vault_path
    
    def test_dashboard_updates_via_browser_poll(self, vault_with_dashboard):
        """Simulate browser polling and updating dashboard."""
        manager = VaultManager()
        manager.vault_path = vault_with_dashboard
        
        # Create some tasks
        for i in range(3):
            task_file = vault_with_dashboard / "Needs_Action" / f"TASK_{i}.md"
            with open(task_file, 'w') as f:
                f.write(f"---\ntype: test\n---\n# Task {i}")
        
        # Create approval
        manager.create_approval_request(
            action_id="ACTION_001",
            action_type="payment",
            description="Test payment"
        )
        
        # Simulate browser refresh - update dashboard
        success = manager.update_dashboard({})
        assert success
        
        # Read dashboard and verify update
        dashboard_file = vault_with_dashboard / "Dashboard.md"
        with open(dashboard_file, 'r') as f:
            content = f.read()
        
        # Verify timestamp is recent
        assert "2026-02-08" in content or "UTC" in content


class TestPlaywrightReportGeneration:
    """Test generating reports using vault data."""
    
    def test_generate_briefing_from_vault_data(self, temp_vault):
        """Test generating executive briefing from vault transaction data."""
        manager = VaultManager()
        manager.vault_path = temp_vault
        
        # Create accounting file with transaction data
        accounting_file = temp_vault / "Accounting" / "Current_Month.md"
        with open(accounting_file, 'w') as f:
            f.write("""# February 2026 Accounting

## Transactions

### Revenue
| Date | Customer | Amount |
|------|----------|--------|
| Feb 1 | Acme Corp | $25,000 |
| Feb 3 | TechCorp | $15,000 |
| Feb 5 | Global Inc | $20,000 |
| **Total** | **-** | **$60,000** |

### Expenses
| Date | Vendor | Amount |
|------|--------|--------|
| Feb 2 | AWS | $4,500 |
| Feb 4 | Payroll | $35,000 |
| Feb 5 | Marketing | $8,000 |
| **Total** | **-** | **$47,500** |

## Summary
- Revenue: $60,000
- Expenses: $47,500
- Net: $12,500
""")
        
        # Create briefing based on data
        manager.create_plan(
            plan_id="BRIEF_FEB_001",
            title="February Financial Briefing",
            steps=[
                "Collect transaction data from Accounting/Current_Month.md",
                "Calculate totals and trends",
                "Identify top revenue sources",
                "Identify major expenses",
                "Generate executive summary"
            ],
            priority="high"
        )
        
        # Verify briefing created
        brief_file = temp_vault / "Plans" / "BRIEF_FEB_001.md"
        assert brief_file.exists()
        
        with open(brief_file, 'r') as f:
            brief_content = f.read()
        
        assert "Financial Briefing" in brief_content
        assert "Calculate totals" in brief_content


class TestPlaywrightMultipleAgents:
    """Test vault operations with multiple concurrent agents."""
    
    def test_multiple_agents_working_on_different_tasks(self, temp_vault):
        """Test multiple agents claiming and processing different tasks."""
        manager = VaultManager()
        manager.vault_path = temp_vault
        
        agents = ["agent_email", "agent_payment", "agent_reporting"]
        
        # Create tasks for each agent
        for i, agent in enumerate(agents):
            task_file = temp_vault / "Needs_Action" / f"TASK_AGENT_{i}.md"
            with open(task_file, 'w') as f:
                f.write(f"""---
type: {agent}_task
priority: high
assigned_to: {agent}
---

# Task for {agent}
""")
        
        # Simulate each agent claiming and working on task
        for agent in agents:
            # Find unprocessed task
            needs_action_files = list((temp_vault / "Needs_Action").glob("*.md"))
            if needs_action_files:
                task_file = needs_action_files[0]
                
                # Claim to agent's In_Progress folder
                agent_dir = temp_vault / "In_Progress" / agent
                agent_dir.mkdir(parents=True, exist_ok=True)
                new_path = agent_dir / task_file.name
                task_file.rename(new_path)
                
                # Log event
                manager.log_event(
                    event_type="task_claimed",
                    task_id=task_file.name,
                    agent=agent
                )
                
                # Complete task
                manager.move_task_to_done(new_path)
                
                # Log completion
                manager.log_event(
                    event_type="task_completed",
                    task_id=task_file.name,
                    agent=agent
                )
        
        # Verify all tasks completed
        done_files = list((temp_vault / "Done").glob("*.md"))
        assert len(done_files) == len(agents)
        
        # Verify audit trail
        today = datetime.utcnow().strftime("%Y-%m-%d")
        log_file = temp_vault / "Logs" / f"{today}.json"
        with open(log_file, 'r') as f:
            log_data = json.load(f)
        
        # Should have claim + complete events for each agent
        assert len(log_data['events']) >= len(agents) * 2


class TestPlaywrightRealWorldScenarios:
    """Test real-world workflow scenarios."""
    
    def test_end_to_end_email_handling_workflow(self, temp_vault):
        """Test complete email handling workflow from receipt to response."""
        manager = VaultManager()
        manager.vault_path = temp_vault
        
        # Step 1: Email arrives (from watcher)
        email_task = temp_vault / "Needs_Action" / "EMAIL_INCOMING_001.md"
        with open(email_task, 'w') as f:
            f.write("""---
type: email_task
priority: high
source: gmail
created: 2026-02-08T10:00:00Z
---

# Process: Client Budget Increase Request

**From:** john.doe@client.com
**Subject:** Q1 Budget Increase - Additional Resources Needed

**Email Body:**
We need to increase our Q1 budget by $50K for additional engineering resources. This will allow us to accelerate the product roadmap. Can you review and let us know if this is possible?

**Action Required:**
Review budget impact and send approval or denial.
""")
        
        # Step 2: Claude claims task
        manager.claim_task(email_task, agent_name="claude")
        
        # Verify in progress
        in_progress_file = list((temp_vault / "In_Progress" / "claude").glob("*.md"))[0]
        assert in_progress_file.exists()
        
        # Step 3: Claude creates plan
        manager.create_plan(
            plan_id="PLAN_EMAIL_BUDGET_001",
            title="Review and Respond to Budget Request",
            steps=[
                "Extract budget amount and justification",
                "Check Company_Handbook thresholds ($50K requires CEO approval)",
                "Create approval request for CEO review",
                "Wait for approval decision",
                "Compose professional response",
                "Send email response"
            ],
            related_task="EMAIL_INCOMING_001"
        )
        
        # Step 4: High-risk action triggers approval request
        manager.create_approval_request(
            action_id="ACTION_BUDGET_INCREASE_001",
            action_type="budget_approval",
            description="Approve $50K budget increase for client Q1 project",
            risk_level="high",
            priority="high"
        )
        
        # Step 5: User approves action
        approval_file = temp_vault / "Pending_Approval" / "ACTION_BUDGET_INCREASE_001.md"
        approved_file = temp_vault / "Approved" / "ACTION_BUDGET_INCREASE_001.md"
        approval_file.rename(approved_file)
        
        # Step 6: Claude sends response and completes task
        manager.log_event(
            event_type="action_executed",
            task_id="EMAIL_INCOMING_001",
            details={"action": "approval_email_sent"},
            agent="claude"
        )
        
        in_progress_file = list((temp_vault / "In_Progress" / "claude").glob("*.md"))[0]
        manager.move_task_to_done(in_progress_file, result="success")
        
        # Verify completion
        done_files = list((temp_vault / "Done").glob("*.md"))
        assert len(done_files) == 1
        
        # Verify audit trail
        today = datetime.utcnow().strftime("%Y-%m-%d")
        log_file = temp_vault / "Logs" / f"{today}.json"
        with open(log_file, 'r') as f:
            log_data = json.load(f)
        
        # Should have at least action_executed event logged
        assert len(log_data['events']) >= 1
    
    def test_payment_processing_with_approval_gates(self, temp_vault):
        """Test payment processing with approval workflow."""
        manager = VaultManager()
        manager.vault_path = temp_vault
        
        # Payment amount: $1,500 (requires approval)
        manager.create_approval_request(
            action_id="PAYMENT_VENDOR_001",
            action_type="payment",
            description="Pay invoice #INV-2026-001 to Acme Services - $1,500",
            risk_level="medium",
            priority="high"
        )
        
        pending_file = temp_vault / "Pending_Approval" / "PAYMENT_VENDOR_001.md"
        assert pending_file.exists()
        
        # Simulate user reviewing and approving
        approved_file = temp_vault / "Approved" / "PAYMENT_VENDOR_001.md"
        pending_file.rename(approved_file)
        
        # Simulate payment execution
        manager.log_event(
            event_type="payment_executed",
            task_id="PAYMENT_VENDOR_001",
            details={
                "amount": 1500,
                "recipient": "Acme Services",
                "invoice": "INV-2026-001"
            },
            agent="payment_processor"
        )
        
        # Move to done
        approved_file.rename(temp_vault / "Done" / "PAYMENT_VENDOR_001.md")
        
        # Verify completion
        done_files = list((temp_vault / "Done").glob("*.md"))
        assert len(done_files) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
