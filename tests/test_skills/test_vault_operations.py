"""
Unit tests for Vault Operations.
Tests reading, writing, and managing task files in the vault.
"""

import pytest
import json
import yaml
from pathlib import Path
from datetime import datetime
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utilities.vault_manager import VaultManager
from config import Settings

@pytest.fixture
def temp_vault(tmp_path):
    """Create a temporary vault for testing."""
    vault_path = tmp_path / "test_vault"
    vault_path.mkdir()
    
    # Create subdirectories
    for subdir in ["Needs_Action", "In_Progress", "Plans", "Done", 
                   "Pending_Approval", "Approved", "Rejected", "Logs", "Accounting"]:
        (vault_path / subdir).mkdir()
    
    return vault_path

@pytest.fixture
def vault_manager(temp_vault, monkeypatch):
    """Create a vault manager with temporary vault."""
    # Mock the settings to use temp vault
    monkeypatch.setenv("VAULT_PATH", str(temp_vault))
    manager = VaultManager()
    manager.vault_path = temp_vault
    return manager

class TestVaultReading:
    """Test reading from vault."""
    
    def test_read_task_file_with_frontmatter(self, temp_vault):
        """Test reading a task file with YAML frontmatter."""
        task_content = """---
type: email_task
priority: high
source: gmail
created: 2026-02-08T10:30:00Z
---

# Task Title

**From:** sender@example.com
**Subject:** Important task

## Action Required
- [ ] Do something
"""
        
        task_file = temp_vault / "Needs_Action" / "EMAIL_001.md"
        with open(task_file, 'w') as f:
            f.write(task_content)
        
        manager = VaultManager()
        manager.vault_path = temp_vault
        task = manager.read_task_file(task_file)
        
        assert task['metadata']['type'] == 'email_task'
        assert task['metadata']['priority'] == 'high'
        assert task['priority'] == 'high'
        assert 'Task Title' in task['content']
    
    def test_get_needs_action_tasks(self, temp_vault):
        """Test retrieving all tasks from Needs_Action."""
        # Create test tasks
        for i in range(3):
            task_file = temp_vault / "Needs_Action" / f"TASK_{i:03d}.md"
            with open(task_file, 'w') as f:
                f.write(f"""---
type: test_task
priority: medium
created: 2026-02-08T10:30:00Z
---

# Test Task {i}
""")
        
        manager = VaultManager()
        manager.vault_path = temp_vault
        tasks = manager.get_needs_action_tasks()
        
        assert len(tasks) == 3
        assert all('metadata' in t for t in tasks)
    
    def test_read_task_without_frontmatter(self, temp_vault):
        """Test reading a task file without YAML frontmatter."""
        task_content = "# Plain Task\n\nNo frontmatter here."
        
        task_file = temp_vault / "Needs_Action" / "PLAIN_001.md"
        with open(task_file, 'w') as f:
            f.write(task_content)
        
        manager = VaultManager()
        manager.vault_path = temp_vault
        task = manager.read_task_file(task_file)
        
        assert task['metadata'] == {}
        assert 'Plain Task' in task['content']

class TestVaultWriting:
    """Test writing to vault."""
    
    def test_create_plan(self, temp_vault):
        """Test creating a plan file."""
        manager = VaultManager()
        manager.vault_path = temp_vault
        
        steps = [
            "Analyze the situation",
            "Create action plan",
            "Execute plan",
            "Verify results"
        ]
        
        success = manager.create_plan(
            plan_id="PLAN_TEST_001",
            title="Test Plan",
            steps=steps,
            priority="high",
            related_task="TASK_001"
        )
        
        assert success
        plan_file = temp_vault / "Plans" / "PLAN_TEST_001.md"
        assert plan_file.exists()
        
        with open(plan_file, 'r') as f:
            content = f.read()
        
        assert "Test Plan" in content
        assert "Step 1: Analyze the situation" in content
        assert "Step 4: Verify results" in content
    
    def test_create_approval_request(self, temp_vault):
        """Test creating an approval request."""
        manager = VaultManager()
        manager.vault_path = temp_vault
        
        success = manager.create_approval_request(
            action_id="ACTION_001",
            action_type="payment",
            description="Transfer $500 to vendor",
            risk_level="medium",
            priority="high"
        )
        
        assert success
        approval_file = temp_vault / "Pending_Approval" / "ACTION_001.md"
        assert approval_file.exists()
        
        with open(approval_file, 'r') as f:
            content = f.read()
        
        assert "payment_approval" in content
        assert "Transfer $500" in content

class TestVaultWorkflow:
    """Test complete task workflow."""
    
    def test_claim_and_complete_task(self, temp_vault):
        """Test claiming a task and moving it to done."""
        manager = VaultManager()
        manager.vault_path = temp_vault
        
        # Create initial task
        task_file = temp_vault / "Needs_Action" / "EMAIL_001.md"
        with open(task_file, 'w') as f:
            f.write("---\ntype: email_task\npriority: high\n---\n# Email Task")
        
        assert task_file.exists()
        
        # Claim task
        success = manager.claim_task(task_file, agent_name="claude")
        assert success
        
        claimed_path = temp_vault / "In_Progress" / "claude" / "EMAIL_001.md"
        assert claimed_path.exists()
        assert not task_file.exists()
        
        # Move to done
        success = manager.move_task_to_done(claimed_path)
        assert success
        
        done_path = temp_vault / "Done" / "EMAIL_001.md"
        assert done_path.exists()
        
        with open(done_path, 'r') as f:
            content = f.read()
        assert "Completed:" in content
    
    def test_log_event(self, temp_vault):
        """Test logging events to audit trail."""
        manager = VaultManager()
        manager.vault_path = temp_vault
        
        # Log an event
        success = manager.log_event(
            event_type="task_claimed",
            task_id="EMAIL_001",
            details={"reason": "urgent"},
            agent="claude"
        )
        
        assert success
        
        today = datetime.utcnow().strftime("%Y-%m-%d")
        log_file = temp_vault / "Logs" / f"{today}.json"
        assert log_file.exists()
        
        with open(log_file, 'r') as f:
            log_data = json.load(f)
        
        assert log_data['date'] == today
        assert len(log_data['events']) > 0
        assert log_data['events'][0]['event_type'] == 'task_claimed'
        assert log_data['events'][0]['task_id'] == 'EMAIL_001'

class TestVaultPriorities:
    """Test priority-based task filtering."""
    
    def test_sort_by_priority(self, temp_vault):
        """Test sorting tasks by priority."""
        manager = VaultManager()
        manager.vault_path = temp_vault
        
        priorities = ['low', 'medium', 'high', 'critical']
        
        for priority in priorities:
            task_file = temp_vault / "Needs_Action" / f"{priority.upper()}_001.md"
            with open(task_file, 'w') as f:
                f.write(f"---\npriority: {priority}\n---\n# {priority.title()} Task")
        
        tasks = manager.get_needs_action_tasks()
        assert len(tasks) == 4
        
        # Sort by priority (critical -> low)
        priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        sorted_tasks = sorted(tasks, 
                             key=lambda t: priority_order.get(t.get('priority', 'medium'), 999))
        
        assert sorted_tasks[0]['priority'] == 'critical'
        assert sorted_tasks[-1]['priority'] == 'low'

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
