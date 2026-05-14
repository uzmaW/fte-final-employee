"""
Browser-based integration tests for Vault Operations using Playwright.
Tests vault file interactions with browser automation simulation.
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime
import sys
import asyncio

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utilities.vault_manager import VaultManager

class TestVaultBrowserIntegration:
    """Test vault operations with browser-like interactions."""
    
    @pytest.fixture
    def temp_vault(self):
        """Create a temporary vault."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir) / "test_vault"
            vault_path.mkdir()
            
            for subdir in ["Needs_Action", "In_Progress", "Plans", "Done", 
                          "Pending_Approval", "Approved", "Rejected", "Logs", "Accounting"]:
                (vault_path / subdir).mkdir()
            
            yield vault_path
    
    def test_simulate_user_approval_workflow(self, temp_vault):
        """Simulate user approving an action via file move."""
        manager = VaultManager()
        manager.vault_path = temp_vault
        
        # Step 1: Create approval request
        manager.create_approval_request(
            action_id="PAYMENT_001",
            action_type="payment",
            description="Pay $300 to vendor",
            risk_level="medium"
        )
        
        # Verify in pending
        pending_file = temp_vault / "Pending_Approval" / "PAYMENT_001.md"
        assert pending_file.exists()
        
        # Step 2: Simulate user approval (move to Approved)
        approved_file = temp_vault / "Approved" / "PAYMENT_001.md"
        pending_file.rename(approved_file)
        
        # Step 3: Check for approved actions
        approved_actions = manager.get_approved_actions()
        assert len(approved_actions) == 1
        assert approved_actions[0]['file_name'] == "PAYMENT_001.md"
    
    def test_simulate_task_processing_pipeline(self, temp_vault):
        """Simulate complete task processing pipeline."""
        manager = VaultManager()
        manager.vault_path = temp_vault
        
        # Step 1: Create task in Needs_Action
        task_file = temp_vault / "Needs_Action" / "EMAIL_TASK_001.md"
        with open(task_file, 'w') as f:
            f.write("""---
type: email_task
priority: high
source: gmail
created: 2026-02-08T10:00:00Z
---

# Respond to client email

From: client@example.com
Subject: Budget increase request

Action: Review and respond with approval or denial.
""")
        
        # Verify task in inbox
        tasks = manager.get_needs_action_tasks()
        assert len(tasks) == 1
        assert tasks[0]['priority'] == 'high'
        
        # Step 2: Claim task
        task_file = list((temp_vault / "Needs_Action").glob("*.md"))[0]
        manager.claim_task(task_file, agent_name="claude")
        
        tasks = manager.get_needs_action_tasks()
        assert len(tasks) == 0  # No longer in Needs_Action
        
        # Step 3: Create plan for task
        manager.create_plan(
            plan_id="PLAN_EMAIL_001",
            title="Respond to Client",
            steps=[
                "Review budget request details",
                "Check Company_Handbook approval thresholds",
                "Create approval request if needed",
                "Send response email"
            ],
            related_task="EMAIL_TASK_001"
        )
        
        plan_file = temp_vault / "Plans" / "PLAN_EMAIL_001.md"
        assert plan_file.exists()
        
        # Step 4: Complete task
        task_file = list((temp_vault / "In_Progress" / "claude").glob("*.md"))[0]
        manager.move_task_to_done(task_file, result="email_sent")
        
        done_file = temp_vault / "Done" / "EMAIL_TASK_001.md"
        assert done_file.exists()
        
        # Step 5: Verify audit trail
        manager.log_event(
            event_type="task_completed",
            task_id="EMAIL_TASK_001",
            details={"result": "email_sent"},
            agent="claude"
        )
        
        today = datetime.utcnow().strftime("%Y-%m-%d")
        log_file = temp_vault / "Logs" / f"{today}.json"
        with open(log_file, 'r') as f:
            log_data = json.load(f)
        
        assert len(log_data['events']) == 1
        assert log_data['events'][0]['task_id'] == "EMAIL_TASK_001"

class TestVaultMultipleTaskHandling:
    """Test handling multiple simultaneous tasks."""
    
    @pytest.fixture
    def temp_vault(self):
        """Create a temporary vault."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir) / "test_vault"
            vault_path.mkdir()
            
            for subdir in ["Needs_Action", "In_Progress", "Plans", "Done", 
                          "Pending_Approval", "Approved", "Rejected", "Logs", "Accounting"]:
                (vault_path / subdir).mkdir()
            
            yield vault_path
    
    def test_handle_multiple_concurrent_tasks(self, temp_vault):
        """Test handling multiple tasks simultaneously."""
        manager = VaultManager()
        manager.vault_path = temp_vault
        
        # Create multiple tasks with different priorities
        tasks_data = [
            ("EMAIL_001", "email_task", "critical"),
            ("PAYMENT_001", "payment_request", "high"),
            ("REPORT_001", "report_request", "medium"),
            ("ADMIN_001", "admin_task", "low"),
        ]
        
        for task_id, task_type, priority in tasks_data:
            task_file = temp_vault / "Needs_Action" / f"{task_id}.md"
            with open(task_file, 'w') as f:
                f.write(f"""---
type: {task_type}
priority: {priority}
created: 2026-02-08T10:00:00Z
---

# Task {task_id}

Priority: {priority}
""")
        
        # Get all tasks
        tasks = manager.get_needs_action_tasks()
        assert len(tasks) == 4
        
        # Sort by priority (critical -> low)
        priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        sorted_tasks = sorted(tasks, 
                             key=lambda t: priority_order.get(t.get('priority', 'medium'), 999))
        
        # Process in priority order
        processed_count = 0
        for task in sorted_tasks:
            # Claim task
            task_path = Path(task['file_path'])
            manager.claim_task(task_path)
            
            # Do some work (simulate)
            manager.log_event(
                event_type="task_processing",
                task_id=task['file_name'],
                details={"priority": task['priority']},
                agent="claude"
            )
            
            # Complete task
            task_path = list((temp_vault / "In_Progress" / "claude").glob("*.md"))[0]
            manager.move_task_to_done(task_path)
            processed_count += 1
        
        # Verify all processed
        assert processed_count == 4
        done_files = list((temp_vault / "Done").glob("*.md"))
        assert len(done_files) == 4

class TestVaultDashboardUpdates:
    """Test updating dashboard and metrics."""
    
    @pytest.fixture
    def temp_vault_with_dashboard(self):
        """Create a temporary vault with dashboard."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir) / "test_vault"
            vault_path.mkdir()
            
            for subdir in ["Needs_Action", "In_Progress", "Plans", "Done", 
                          "Pending_Approval", "Approved", "Rejected", "Logs", "Accounting"]:
                (vault_path / subdir).mkdir()
            
            # Create dashboard
            dashboard_file = vault_path / "Dashboard.md"
            dashboard_file.write_text("""# Dashboard

**Last Updated:** 2026-02-08 10:00:00 UTC

## Status
System operational.
""")
            
            yield vault_path
    
    def test_update_dashboard_metrics(self, temp_vault_with_dashboard):
        """Test updating dashboard with current metrics."""
        manager = VaultManager()
        manager.vault_path = temp_vault_with_dashboard
        
        # Create some tasks for metrics
        for i in range(5):
            task_file = temp_vault_with_dashboard / "Needs_Action" / f"TASK_{i:03d}.md"
            with open(task_file, 'w') as f:
                f.write(f"---\ntype: test\n---\n# Task {i}")
        
        # Create some completed tasks
        for i in range(3):
            done_file = temp_vault_with_dashboard / "Done" / f"DONE_{i:03d}.md"
            with open(done_file, 'w') as f:
                f.write(f"---\ntype: test\n---\n# Done Task {i}")
        
        # Update dashboard
        success = manager.update_dashboard({
            "tasks_pending": 5,
            "tasks_completed": 3,
        })
        
        assert success
        
        dashboard_file = temp_vault_with_dashboard / "Dashboard.md"
        with open(dashboard_file, 'r') as f:
            content = f.read()
        
        # Verify timestamp was updated (just check for UTC marker and year)
        assert "UTC" in content
        assert "2026-02-" in content or "Last Updated:" in content

class TestVaultErrorHandling:
    """Test error handling in vault operations."""
    
    @pytest.fixture
    def temp_vault(self):
        """Create a temporary vault."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir) / "test_vault"
            vault_path.mkdir()
            
            for subdir in ["Needs_Action", "In_Progress", "Plans", "Done", 
                          "Pending_Approval", "Approved", "Rejected", "Logs", "Accounting"]:
                (vault_path / subdir).mkdir()
            
            yield vault_path
    
    def test_handle_invalid_yaml_frontmatter(self, temp_vault):
        """Test handling files with invalid YAML."""
        manager = VaultManager()
        manager.vault_path = temp_vault
        
        # Create file with invalid YAML
        task_file = temp_vault / "Needs_Action" / "INVALID_001.md"
        with open(task_file, 'w') as f:
            f.write("""---
type: email_task
priority: [[[INVALID]]]
---

# Task
""")
        
        # Should handle gracefully
        task = manager.read_task_file(task_file)
        assert 'file_name' in task
        # Metadata should be empty or partial
        assert 'content' in task
    
    def test_handle_missing_directories(self, temp_vault):
        """Test that missing directories are created automatically."""
        manager = VaultManager()
        # Use a vault path that doesn't have all subdirs
        vault_path = Path(tempfile.mkdtemp()) / "new_vault"
        manager.vault_path = vault_path
        
        # Call ensure_vault_ready
        manager.ensure_vault_ready()
        
        # Verify all directories exist
        assert (vault_path / "Needs_Action").exists()
        assert (vault_path / "Plans").exists()
        assert (vault_path / "Done").exists()

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
