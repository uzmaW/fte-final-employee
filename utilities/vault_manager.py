"""
Vault Manager - Handles all interactions with the Obsidian vault.
Provides methods to read, write, and manage task files.
"""

import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_settings

logger = logging.getLogger(__name__)

class VaultManager:
    """Manages all vault operations."""
    
    def __init__(self):
        self.settings = get_settings()
        self.vault_path = self.settings.vault_path
        self.ensure_vault_ready()
    
    def ensure_vault_ready(self):
        """Ensure vault is properly initialized."""
        required_dirs = [
            "Needs_Action", "In_Progress", "Plans", "Done",
            "Pending_Approval", "Approved", "Rejected", "Logs", "Accounting"
        ]
        
        for dir_name in required_dirs:
            dir_path = self.vault_path / dir_name
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def get_needs_action_tasks(self) -> List[Dict[str, Any]]:
        """Get all tasks in Needs_Action folder."""
        tasks_dir = self.vault_path / "Needs_Action"
        tasks = []
        
        for task_file in tasks_dir.glob("*.md"):
            try:
                task = self.read_task_file(task_file)
                tasks.append(task)
            except Exception as e:
                logger.error(f"Error reading task {task_file}: {e}")
        
        return tasks
    
    def read_task_file(self, file_path: Path) -> Dict[str, Any]:
        """Read a task file and extract metadata and content."""
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Split frontmatter from content
        parts = content.split('---')
        if len(parts) >= 3:
            metadata_str = parts[1]
            task_content = '---'.join(parts[2:])
            
            try:
                metadata = yaml.safe_load(metadata_str)
                if metadata is None:
                    metadata = {}
            except Exception as e:
                logger.error(f"Error parsing YAML frontmatter: {e}")
                metadata = {}
        else:
            metadata = {}
            task_content = content
        
        # Ensure metadata is a dict
        if not isinstance(metadata, dict):
            metadata = {}
        
        return {
            'file_path': str(file_path),
            'file_name': file_path.name,
            'metadata': metadata,
            'content': task_content.strip(),
            'priority': metadata.get('priority', 'medium'),
            'type': metadata.get('type', 'unknown'),
            'source': metadata.get('source', 'manual'),
            'action_id': metadata.get('action_id', ''),
        }
    
    def claim_task(self, task_file: Path, agent_name: str = "claude") -> bool:
        """Move task from Needs_Action to In_Progress."""
        try:
            agent_dir = self.vault_path / "In_Progress" / agent_name
            agent_dir.mkdir(parents=True, exist_ok=True)
            
            new_path = agent_dir / task_file.name
            task_file.rename(new_path)
            
            logger.info(f"Claimed task: {task_file.name}")
            return True
        except Exception as e:
            logger.error(f"Error claiming task: {e}")
            return False
    
    def create_plan(self, plan_id: str, title: str, steps: List[str], 
                   priority: str = "medium", related_task: str = "") -> bool:
        """Create a new plan file in Plans directory."""
        try:
            timestamp = datetime.utcnow().isoformat() + "Z"
            
            content = f"""---
plan_id: {plan_id}
type: task_plan
priority: {priority}
created: {timestamp}
related_task: {related_task}
status: active
---

# {title}

## Steps
"""
            for i, step in enumerate(steps, 1):
                content += f"- [ ] Step {i}: {step}\n"
            
            content += "\n## Status\n- Starting...\n"
            
            plan_file = self.vault_path / "Plans" / f"{plan_id}.md"
            with open(plan_file, 'w') as f:
                f.write(content)
            
            logger.info(f"Created plan: {plan_id}")
            return True
        except Exception as e:
            logger.error(f"Error creating plan: {e}")
            return False
    
    def create_approval_request(self, action_id: str, action_type: str,
                               description: str, risk_level: str = "medium",
                               priority: str = "high") -> bool:
        """Create an approval request in Pending_Approval."""
        try:
            timestamp = datetime.utcnow().isoformat() + "Z"
            
            content = f"""---
type: {action_type}_approval
priority: {priority}
created: {timestamp}
action_id: {action_id}
risk_level: {risk_level}
status: pending
---

# Approval Request: {action_type}

## Description
{description}

## Risk Level
{risk_level}

## Action Required
Please review and decide:
1. Move to `/Approved/` to authorize
2. Move to `/Rejected/` to deny

---
Generated: {timestamp}
"""
            
            approval_file = self.vault_path / "Pending_Approval" / f"{action_id}.md"
            with open(approval_file, 'w') as f:
                f.write(content)
            
            logger.info(f"Created approval request: {action_id}")
            return True
        except Exception as e:
            logger.error(f"Error creating approval request: {e}")
            return False
    
    def move_task_to_done(self, task_file: Path, result: str = "success") -> bool:
        """Move completed task to Done folder."""
        try:
            done_file = self.vault_path / "Done" / task_file.name
            task_file.rename(done_file)
            
            # Append completion metadata
            with open(done_file, 'a') as f:
                f.write(f"\n\n---\n**Completed:** {datetime.utcnow().isoformat()}Z\n**Result:** {result}\n")
            
            logger.info(f"Task completed: {task_file.name}")
            return True
        except Exception as e:
            logger.error(f"Error moving task to done: {e}")
            return False
    
    def log_event(self, event_type: str, task_id: str = "", details: Dict = None, 
                 agent: str = "system") -> bool:
        """Log an event to the daily log file."""
        try:
            today = datetime.utcnow().strftime("%Y-%m-%d")
            log_file = self.vault_path / "Logs" / f"{today}.json"
            
            event = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "event_type": event_type,
                "agent": agent,
                "task_id": task_id,
                "details": details or {}
            }
            
            # Read existing log or create new one
            if log_file.exists():
                with open(log_file, 'r') as f:
                    log_data = json.load(f)
            else:
                log_data = {
                    "date": today,
                    "timezone": "UTC",
                    "events": []
                }
            
            log_data["events"].append(event)
            
            # Write back
            with open(log_file, 'w') as f:
                json.dump(log_data, f, indent=2)
            
            logger.debug(f"Logged event: {event_type}")
            return True
        except Exception as e:
            logger.error(f"Error logging event: {e}")
            return False
    
    def update_dashboard(self, status_updates: Dict[str, str]) -> bool:
        """Update the Dashboard.md file with status."""
        try:
            dashboard_file = self.vault_path / "Dashboard.md"
            
            if not dashboard_file.exists():
                logger.warning("Dashboard.md not found")
                return False
            
            with open(dashboard_file, 'r') as f:
                content = f.read()
            
            # Update last updated time
            import re
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
            content = re.sub(
                r'\*\*Last Updated:\*\* .+',
                f"**Last Updated:** {timestamp}",
                content
            )
            
            with open(dashboard_file, 'w') as f:
                f.write(content)
            
            logger.debug("Updated dashboard")
            return True
        except Exception as e:
            logger.error(f"Error updating dashboard: {e}")
            return False
    
    def get_approved_actions(self) -> List[Dict[str, Any]]:
        """Get all approved actions waiting for execution."""
        approved_dir = self.vault_path / "Approved"
        actions = []
        
        for action_file in approved_dir.glob("*.md"):
            try:
                action = self.read_task_file(action_file)
                actions.append(action)
            except Exception as e:
                logger.error(f"Error reading approved action {action_file}: {e}")
        
        return actions
    
    def check_pending_approvals(self) -> List[Dict[str, Any]]:
        """Get all pending approvals."""
        pending_dir = self.vault_path / "Pending_Approval"
        approvals = []
        
        for approval_file in pending_dir.glob("*.md"):
            try:
                approval = self.read_task_file(approval_file)
                approvals.append(approval)
            except Exception as e:
                logger.error(f"Error reading approval {approval_file}: {e}")
        
        return approvals


def get_vault_manager() -> VaultManager:
    """Get vault manager singleton."""
    if not hasattr(get_vault_manager, '_instance'):
        get_vault_manager._instance = VaultManager()
    return get_vault_manager._instance


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    manager = VaultManager()
    
    # Test basic operations
    print("Testing vault manager...")
    print(f"Vault path: {manager.vault_path}")
    print(f"Vault ready: {manager.vault_path.exists()}")
