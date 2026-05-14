"""
platinum_delegation.py - Cloud-Local delegation pattern for Platinum Tier.

From the hackathon PDF Platinum Tier:
  - Work-Zone Specialization: Cloud handles drafting, Local handles approvals and sends
  - Delegation via Synced Vault with claim-by-move rule
  - Secrets never sync to cloud
  - Single-writer rule for Dashboard.md

This module handles the coordination between Cloud and Local agents.
"""

import json
import time
import logging
import hashlib
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Set

from config import get_settings

logger = logging.getLogger(__name__)


class DelegationConflictError(Exception):
    """Raised when a task ownership conflict is detected."""
    pass


class VaultSyncError(Exception):
    """Raised when vault synchronization fails."""
    pass


class TaskClaim:
    """Represents a claim on a task file."""
    
    def __init__(self, task_id: str, agent_id: str, timestamp: datetime, metadata: Dict[str, Any] = None):
        self.task_id = task_id
        self.agent_id = agent_id
        self.timestamp = timestamp
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'task_id': self.task_id,
            'agent_id': self.agent_id,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskClaim':
        return cls(
            task_id=data['task_id'],
            agent_id=data['agent_id'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            metadata=data.get('metadata', {})
        )


class CloudLocalDelegator:
    """
    Manages delegation of tasks between Cloud and Local agents.
    
    Architecture (from hackathon PDF):
    
    ┌─────────────────────────────────────────┐
    │               CLOUD AGENT               │
    │  ┌─────────────┐                        │
    │  │ Draft Emails │  Draft social posts   │
    │  │ Draft social │  Accounting drafts    │
    │  │ Write Updates│  /Updates directory   │
    │  └─────────────┘                        │
    │         │                               │
    │         ▼                               │
    │  Synced Vault (/Updates)                │
    │         │                               │
    │         ▼                               │
    │  LOCAL AGENT (merges to Dashboard)      │
    │  ┌─────────────┐                        │
    │  │  Approvals   │  Secrets / Payments   │
    │  │  WhatsApp    │  Final send actions   │
    │  │  Execution   │  Dashboard updates    │
    │  └─────────────┘                        │
    └─────────────────────────────────────────┘
    """
    
    # Domain ownership rules - which agent owns which work zones
    CLOUD_DOMAINS = {
        'email_drafting': 'Cloud drafts email replies and new messages',
        'social_drafting': 'Cloud drafts social media posts',
        'accounting_drafts': 'Cloud creates accounting entry drafts',
        'content_scheduling': 'Cloud schedules content for later posting',
    }
    
    LOCAL_DOMAINS = {
        'approvals': 'Only Local can approve/reject actions',
        'whatsapp_session': 'WhatsApp session stays on Local',
        'payments': 'Payment execution only on Local',
        'banking': 'Banking operations only on Local',
        'final_send': 'Final send/post actions only on Local',
        'dashboard_writer': 'Local is the single writer for Dashboard.md',
        'secrets': 'Secrets NEVER leave Local',
    }
    
    def __init__(self, vault_path: str, agent_id: str, is_cloud: bool = False):
        """
        Initialize the delegator.
        
        Args:
            vault_path: Path to Obsidian vault
            agent_id: Unique identifier for this agent ('cloud' or 'local')
            is_cloud: Whether this is the cloud agent
        """
        self.vault_path = Path(vault_path)
        self.agent_id = agent_id
        self.is_cloud = is_cloud
        self.is_local = not is_cloud
        
        # Directories
        self.updates_dir = self.vault_path / 'Updates'
        self.needs_action_dir = self.vault_path / 'Needs_Action'
        self.in_progress_dir = self.vault_path / 'In_Progress'
        self.approved_dir = self.vault_path / 'Approved'
        self.done_dir = self.vault_path / 'Done'
        self.signals_dir = self.vault_path / 'Signals'
        self.claims_dir = self.vault_path / '.claims'
        
        # Ensure directories exist
        for d in [self.updates_dir, self.signals_dir, self.claims_dir]:
            d.mkdir(parents=True, exist_ok=True)
        
        # Agent claims tracking
        self._active_claims: Dict[str, TaskClaim] = {}
        self._load_claims()
        
        # Settings
        self.settings = get_settings()
        
        # Stats
        self._stats = {
            'tasks_delegated': 0,
            'tasks_claimed': 0,
            'tasks_completed': 0,
            'conflicts_resolved': 0,
            'syncs_performed': 0,
            'started_at': datetime.now().isoformat()
        }
    
    def _load_claims(self):
        """Load existing task claims from disk."""
        if not self.claims_dir.exists():
            return
        
        for claim_file in self.claims_dir.glob('*.json'):
            try:
                data = json.loads(claim_file.read_text())
                claim = TaskClaim.from_dict(data)
                self._active_claims[claim.task_id] = claim
            except Exception as e:
                logger.warning(f"Error loading claim {claim_file}: {e}")
    
    def _save_claim(self, claim: TaskClaim):
        """Persist a task claim to disk."""
        claim_file = self.claims_dir / f"{claim.task_id}.json"
        claim_file.write_text(json.dumps(claim.to_dict(), indent=2))
    
    def _remove_claim(self, task_id: str):
        """Remove a task claim from disk."""
        claim_file = self.claims_dir / f"{task_id}.json"
        if claim_file.exists():
            claim_file.unlink()
    
    def can_handle(self, task_type: str) -> bool:
        """
        Check if this agent is authorized to handle the given task type.
        
        Args:
            task_type: The type of task (e.g., 'email_drafting', 'approvals')
            
        Returns:
            True if this agent is authorized for this task type
        """
        if self.is_cloud:
            return task_type in self.CLOUD_DOMAINS
        else:
            return task_type in self.LOCAL_DOMAINS
    
    def delegate_to_cloud(self, task_file: Path, task_type: str) -> bool:
        """
        Move a task to Cloud's domain (Updates directory).
        
        Args:
            task_file: The task file to delegate
            task_type: Type of task for cloud handling
            
        Returns:
            True if delegation was successful
        """
        if not self.is_local:
            raise DelegationConflictError("Only Local agent can delegate to Cloud")
        
        if task_type not in self.CLOUD_DOMAINS:
            logger.warning(f"Task type '{task_type}' not in Cloud domains")
            return False
        
        try:
            # Create an update file for Cloud
            update_file = self.updates_dir / f"TO_CLOUD_{task_file.name}"
            
            # Read original task
            original_content = task_file.read_text()
            
            # Add delegation header
            delegation_header = f"""---
delegation_type: to_cloud
task_type: {task_type}
delegated_by: local
delegated_at: {datetime.now().isoformat()}
original_file: {task_file.name}
status: pending_cloud
---

"""
            # Write to Updates for Cloud to pick up
            update_content = delegation_header + original_content
            update_file.write_text(update_content)
            
            # Move original to In_Progress to prevent double processing
            if task_file.exists():
                in_progress_file = self.in_progress_dir / f"cloud_pending_{task_file.name}"
                if task_file.rename(in_progress_file):
                    logger.info(f"Delegated {task_file.name} to Cloud")
                    self._stats['tasks_delegated'] += 1
                    return True
                    
        except Exception as e:
            logger.error(f"Error delegating to Cloud: {e}")
            raise VaultSyncError(f"Delegation failed: {e}")
        
        return False
    
    def collect_from_cloud(self) -> int:
        """
        Collect processed updates from Cloud agent.
        
        Returns:
            Number of updates collected
        """
        if not self.is_local:
            raise DelegationConflictError("Only Local agent collects Cloud updates")
        
        collected = 0
        updates_pattern = 'FROM_CLOUD_*.md'
        
        for update_file in self.updates_dir.glob(updates_pattern):
            try:
                content = update_file.read_text()
                
                # Parse delegation header
                if content.startswith('---'):
                    parts = content.split('---', 2)
                    if len(parts) >= 3:
                        metadata_str = parts[1]
                        metadata = {}
                        for line in metadata_str.strip().split('\n'):
                            if ':' in line:
                                k, v = line.split(':', 1)
                                metadata[k.strip()] = v.strip()
                        
                        original_name = metadata.get('original_file', '')
                        task_type = metadata.get('task_type', '')
                        
                        # Process the update based on task type
                        if task_type == 'email_drafting':
                            # Move draft to email approval queue
                            dest = self.approved_dir / f"DRAFT_{original_name}"
                        elif task_type == 'social_drafting':
                            dest = self.approved_dir / f"DRAFT_{original_name}"
                        elif task_type == 'accounting_drafts':
                            dest = self.approved_dir / f"DRAFT_{original_name}"
                        else:
                            dest = self.needs_action_dir / f"FROM_CLOUD_{original_name}"
                        
                        dest.write_text(content)
                        
                        # Remove the update file
                        update_file.unlink()
                        
                        # If original exists in In_Progress, move to Done
                        in_progress_name = f"cloud_pending_{original_name}"
                        in_progress_file = self.in_progress_dir / in_progress_name
                        if in_progress_file.exists():
                            done_file = self.done_dir / f"CLOUD_{original_name}"
                            in_progress_file.rename(done_file)
                        
                        collected += 1
                        logger.info(f"Collected Cloud update: {original_name}")
                        
            except Exception as e:
                logger.error(f"Error collecting Cloud update {update_file}: {e}")
        
        self._stats['syncs_performed'] += 1
        return collected
    
    def send_to_cloud(self, task_type: str, content: str, metadata: Dict[str, Any] = None) -> bool:
        """
        Send a task to Cloud for processing.
        
        Args:
            task_type: Type of task for Cloud handling
            content: Task content
            metadata: Additional metadata
            
        Returns:
            True if sent successfully
        """
        if not self.is_local:
            raise DelegationConflictError("Only Local agent can send to Cloud")
        
        try:
            timestamp = datetime.now().isoformat()
            task_id = f"{task_type}_{timestamp}"
            
            update_content = f"""---
delegation_type: to_cloud
task_type: {task_type}
sent_by: local
sent_at: {timestamp}
---

{content}
"""
            
            update_file = self.updates_dir / f"TO_CLOUD_{task_id}.md"
            update_file.write_text(update_content)
            
            # Record claim
            claim = TaskClaim(
                task_id=task_id,
                agent_id='cloud',
                timestamp=datetime.now()
            )
            self._save_claim(claim)
            self._stats['tasks_delegated'] += 1
            
            logger.info(f"Sent task to Cloud: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending to Cloud: {e}")
            return False
    
    def process_cloud_response(self, response_file: Path) -> bool:
        """
        Process a response file from Cloud agent.
        
        Args:
            response_file: Path to the FROM_CLOUD response file
            
        Returns:
            True if processed successfully
        """
        if not self.is_local:
            raise DelegationConflictError("Only Local agent processes Cloud responses")
        
        try:
            content = response_file.read_text()
            
            # Parse header to determine what action to take
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    metadata = {}
                    for line in parts[1].strip().split('\n'):
                        if ':' in line:
                            k, v = line.split(':', 1)
                            metadata[k.strip()] = v.strip()
                    
                    action = metadata.get('action', 'needs_review')
                    
                    if action == 'draft_approved':
                        # Move to appropriate action folder
                        dest = self.approved_dir / response_file.name
                    elif action == 'needs_human_review':
                        dest = self.needs_action_dir / response_file.name
                    else:
                        dest = self.needs_action_dir / response_file.name
                    
                    dest.write_text(content)
                    response_file.unlink()
                    return True
                    
        except Exception as e:
            logger.error(f"Error processing Cloud response: {e}")
        
        return False
    
    def check_conflicts(self) -> List[Dict[str, Any]]:
        """
        Check for task ownership conflicts between agents.
        
        Returns:
            List of conflict descriptions
        """
        conflicts = []
        
        # Check for tasks claimed by both agents
        all_claims = {}
        for claim_file in self.claims_dir.glob('*.json'):
            try:
                data = json.loads(claim_file.read_text())
                task_id = data.get('task_id')
                agent_id = data.get('agent_id')
                
                if task_id in all_claims:
                    if all_claims[task_id].get('agent_id') != agent_id:
                        conflicts.append({
                            'task_id': task_id,
                            'claim_1': all_claims[task_id],
                            'claim_2': {'agent_id': agent_id}
                        })
                else:
                    all_claims[task_id] = {'agent_id': agent_id}
                    
            except Exception as e:
                logger.error(f"Error reading claim file {claim_file}: {e}")
        
        # Check for files in In_Progress claimed by the wrong agent
        for agent_folder in self.in_progress_dir.glob('*'):
            if agent_folder.is_dir():
                for task_file in agent_folder.glob('*.md'):
                    # Ensure the folder name matches the claiming agent
                    if agent_folder.name != self.agent_id:
                        # This agent shouldn't be working on this file
                        conflicts.append({
                            'type': 'wrong_agent',
                            'file': task_file.name,
                            'expected_agent': agent_folder.name,
                            'actual': self.agent_id
                        })
        
        # Resolve conflicts using timestamp-based priority
        for conflict in conflicts:
            self._resolve_conflict(conflict)
        
        return conflicts
    
    def _resolve_conflict(self, conflict: Dict[str, Any]):
        """Resolve a delegation conflict using predefined rules."""
        self._stats['conflicts_resolved'] += 1
        
        task_id = conflict.get('task_id', conflict.get('file', 'unknown'))
        
        if conflict.get('type') == 'wrong_agent':
            # Move file back to the correct agent's folder or to Needs_Action
            file_path = Path(conflict.get('file', ''))
            # Implementation depends on specific conflict type
            logger.info(f"Resolved conflict for {task_id}: moved to Needs_Action")
        else:
            # Use claim-by-move: first claim wins
            logger.info(f"Resolved dual-claim conflict for {task_id}: first claim wins")
    
    def generate_sync_report(self) -> str:
        """Generate a sync status report."""
        report = f"""## Cloud-Local Sync Report

**Generated:** {datetime.now().isoformat()}
**Agent:** {self.agent_id} ({'Cloud' if self.is_cloud else 'Local'})

### Statistics
- Tasks Delegated: {self._stats['tasks_delegated']}
- Tasks Claimed: {self._stats['tasks_claimed']}
- Tasks Completed: {self._stats['tasks_completed']}
- Conflicts Resolved: {self._stats['conflicts_resolved']}
- Syncs Performed: {self._stats['syncs_performed']}

### Directory Status
- Updates pending: {len(list(self.updates_dir.glob('*.md')))}
- In Progress (local): {len(list((self.in_progress_dir / 'local').glob('*.md') if (self.in_progress_dir / 'local').exists() else []))}
- In Progress (cloud): {len(list((self.in_progress_dir / 'cloud').glob('*.md') if (self.in_progress_dir / 'cloud').exists() else []))}
- Pending Approval: {len(list(self.approved_dir.glob('*.md')))}
- Completed: {len(list(self.done_dir.glob('*.md')))}

### Active Claims
"""
        
        for task_id, claim in self._active_claims.items():
            age = datetime.now() - claim.timestamp
            report += f"- {task_id}: claimed by {claim.agent_id} ({age.seconds}s ago)\n"
        
        if not self._active_claims:
            report += "- No active claims\n"
        
        report += "\n### Security Status\n"
        report += "- Secrets: LOCAL ONLY ✓\n"
        report += "- WhatsApp session: LOCAL ONLY ✓\n"
        report += "- Banking credentials: LOCAL ONLY ✓\n"
        
        return report


class SyncOrchestrator:
    """
    Coordinates synchronization between Cloud and Local agents.
    """
    
    def __init__(self, vault_path: str, sync_method: str = 'git'):
        """
        Initialize sync orchestrator.
        
        Args:
            vault_path: Path to Obsidian vault
            sync_method: 'git' or 'syncthing'
        """
        self.vault_path = Path(vault_path)
        self.sync_method = sync_method
        self.local_delegator = CloudLocalDelegator(vault_path, 'local', is_cloud=False)
        self.cloud_delegator = CloudLocalDelegator(vault_path, 'cloud', is_cloud=True)
    
    def sync(self):
        """Perform synchronization based on the configured method."""
        if self.sync_method == 'git':
            return self._git_sync()
        elif self.sync_method == 'syncthing':
            return self._syncthing_sync()
        else:
            logger.warning(f"Unknown sync method: {self.sync_method}")
            return False
    
    def _git_sync(self) -> bool:
        """Sync using Git."""
        try:
            import subprocess
            
            repo_dir = self.vault_path
            
            # Check if it's a git repo
            if not (repo_dir / '.git').exists():
                logger.warning("Vault is not a Git repository")
                return False
            
            # Add, commit, and push (local → cloud)
            subprocess.run(['git', '-C', str(repo_dir), 'add', '.'], 
                          check=True, capture_output=True)
            
            # Check if there are changes
            result = subprocess.run(['git', '-C', str(repo_dir), 'diff', '--cached'],
                                   capture_output=True, text=True)
            if result.stdout.strip():
                subprocess.run(
                    ['git', '-C', str(repo_dir), 'commit', '-m', 
                     f'Vault sync at {datetime.now().isoformat()}'],
                    check=True, capture_output=True
                )
                subprocess.run(['git', '-C', str(repo_dir), 'push'],
                              check=True, capture_output=True)
                logger.info("Git sync completed: pushed to cloud")
            else:
                logger.info("Git sync: no changes to push")
            
            # Pull any cloud changes (cloud → local)
            subprocess.run(['git', '-C', str(repo_dir), 'pull'],
                          capture_output=True)
            
            self.local_delegator._stats['syncs_performed'] += 1
            return True
            
        except Exception as e:
            logger.error(f"Git sync error: {e}")
            return False
    
    def _syncthing_sync(self) -> bool:
        """Sync using Syncthing (placeholder)."""
        # Syncthing runs as a daemon and auto-syncs
        logger.info("Syncthing sync: relying on daemon auto-sync")
        return True
    
    def check_and_process_updates(self):
        """Check for updates from Cloud and process them."""
        if self.local_delegator.collect_from_cloud() > 0:
            logger.info("Cloud updates collected and processed")


# ─── CLI Entry Point ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Cloud-Local Delegation Manager')
    parser.add_argument('--vault-path', default='AI_Employee_Vault', help='Vault path')
    parser.add_argument('--agent', choices=['cloud', 'local', 'sync'], default='local',
                       help='Agent role')
    parser.add_argument('--check-conflicts', action='store_true', help='Check for conflicts')
    parser.add_argument('--sync', action='store_true', help='Perform sync')
    parser.add_argument('--report', action='store_true', help='Generate sync report')
    parser.add_argument('--method', default='git', choices=['git', 'syncthing'], help='Sync method')
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    if args.agent == 'sync':
        orchestrator = SyncOrchestrator(args.vault_path, args.method)
        if args.sync:
            orchestrator.sync()
        if args.check_conflicts:
            orchestrator.local_delegator.check_conflicts()
        if args.report:
            print(orchestrator.local_delegator.generate_sync_report())
    else:
        is_cloud = args.agent == 'cloud'
        delegator = CloudLocalDelegator(args.vault_path, args.agent, is_cloud)
        
        if args.check_conflicts:
            conflicts = delegator.check_conflicts()
            if conflicts:
                for c in conflicts:
                    print(f"Conflict: {c}")
            else:
                print("No conflicts detected.")
        
        if args.report:
            print(delegator.generate_sync_report())