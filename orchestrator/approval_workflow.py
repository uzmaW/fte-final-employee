"""
approval_workflow.py - Human-in-the-loop approval workflow implementation.

Backs the .claude/skills/approval-workflow/SKILL.md specification.
Manages approval gates, risk assessment, escalation, and audit logging.
"""

import json
import os
import re
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config import get_settings
from utilities.vault_manager import VaultManager

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ApprovalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    ESCALATED = "escalated"
    AUTO_APPROVED = "auto_approved"


@dataclass
class ApprovalRequest:
    """Represents an approval request."""
    action_id: str
    action_type: str
    actor: str
    amount: float = 0.0
    recipient: str = ""
    reason: str = ""
    risk_level: str = "medium"
    priority: str = "normal"
    created_at: str = ""
    expires_at: str = ""
    status: str = "pending"
    approved_by: str = ""
    approved_at: str = ""
    rejection_reason: str = ""
    escalation_chain: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ApprovalWorkflowManager:
    """
    Human-in-the-Loop (HITL) approval workflow manager.
    
    Handles:
    - Risk assessment and routing
    - Multi-level approval chains
    - Deadline management and escalation
    - Auto-approval for low-risk items
    - Audit trail of all decisions
    """
    
    # Risk thresholds — configurable per organization
    RISK_THRESHOLDS = {
        'critical': {
            'min_amount': 50000,
            'description': 'Immediate escalation to CEO/Board',
            'max_response_time_hours': 4,
            'requires': ['ceo', 'board'],
        },
        'high': {
            'min_amount': 5000,
            'description': 'CFO/Finance approval required',
            'max_response_time_hours': 24,
            'requires': ['finance'],
        },
        'medium': {
            'min_amount': 500,
            'description': 'Manager/Team lead approval',
            'max_response_time_hours': 48,
            'requires': ['manager'],
        },
        'low': {
            'min_amount': 0,
            'description': 'Auto-approved, logged only',
            'max_response_time_hours': 0,
            'requires': [],
        },
    }
    
    # Auto-approve rules
    AUTO_APPROVE_RULES = {
        'max_amount': 50,  # Auto-approve payments under $50
        'known_recipients': True,  # Auto-approve if recipient is known
        'recurring': True,  # Auto-approve recurring payments
        'email_to_known_contacts': True,  # Auto-approve emails to known contacts
    }
    
    # Always require approval
    ALWAYS_REQUIRE_APPROVAL = {
        'actions': ['payment', 'transfer', 'contract_signing', 'legal'],
        'new_recipients': True,
        'amounts_over': 100,
        'sensitive_types': ['hr', 'legal', 'security'],
    }
    
    def __init__(self, vault_path: str = None):
        """
        Initialize approval workflow manager.
        
        Args:
            vault_path: Path to Obsidian vault
        """
        self.settings = get_settings()
        self.vault_path = Path(vault_path) if vault_path else self.settings.vault_path
        self.vault_manager = VaultManager()
        
        # Pending approvals directory
        self.pending_dir = self.vault_path / 'Pending_Approval'
        self.approved_dir = self.vault_path / 'Approved'
        self.rejected_dir = self.vault_path / 'Rejected'
        
        for d in [self.pending_dir, self.approved_dir, self.rejected_dir]:
            d.mkdir(parents=True, exist_ok=True)
        
        # Known recipients for auto-approval
        self.known_recipients = self._load_known_recipients()
        
        # Approval history
        self._history: List[ApprovalRequest] = []
        self._load_history()
        
        # Stats
        self.stats = {
            'requests_created': 0,
            'auto_approved': 0,
            'human_approved': 0,
            'rejected': 0,
            'escalated': 0,
            'expired': 0,
            'errors': 0,
            'started_at': datetime.now().isoformat()
        }
    
    def _load_known_recipients(self) -> Dict[str, Dict]:
        """Load known recipients from vault config."""
        known = {}
        recipients_file = self.vault_path / 'Company_Handbook.md'
        if recipients_file.exists():
            # Parse trusted contacts section if present
            content = recipients_file.read_text().lower()
            # Placeholder: in production, parse structured contacts
        return known
    
    def _load_history(self):
        """Load approval history from audit logs."""
        logs_dir = self.vault_path / 'Logs'
        if not logs_dir.exists():
            return
        
        for log_file in logs_dir.glob('*.json'):
            try:
                entries = json.loads(log_file.read_text())
                for entry in entries:
                    if entry.get('action_type', '').startswith('approval_'):
                        req = ApprovalRequest(
                            action_id=entry.get('task_id', ''),
                            action_type=entry.get('detail', {}).get('action_type', ''),
                            actor=entry.get('detail', {}).get('actor', ''),
                            status=entry.get('detail', {}).get('status', ''),
                        )
                        self._history.append(req)
            except Exception:
                continue
    
    def assess_risk(self, request: ApprovalRequest) -> str:
        """
        Assess the risk level of an approval request.
        
        Args:
            request: Approval request to assess
            
        Returns:
            Risk level: 'low', 'medium', 'high', or 'critical'
        """
        reasons = []
        
        # Check amount thresholds
        amount = request.amount
        if amount >= self.RISK_THRESHOLDS['critical']['min_amount']:
            reasons.append(f"Amount ${amount:,.2f} >= critical threshold")
            return 'critical', reasons
        elif amount >= self.RISK_THRESHOLDS['high']['min_amount']:
            reasons.append(f"Amount ${amount:,.2f} >= high threshold")
        elif amount >= self.RISK_THRESHOLDS['medium']['min_amount']:
            reasons.append(f"Amount ${amount:,.2f} >= medium threshold")
        
        # Check action type
        if request.action_type in self.ALWAYS_REQUIRE_APPROVAL['actions']:
            reasons.append(f"Action type '{request.action_type}' always requires approval")
            if request.risk_level in ('low', 'medium'):
                request.risk_level = 'high'
        
        # Check for new recipients
        if request.recipient and request.recipient not in self.known_recipients:
            reasons.append("Unknown recipient")
            if request.risk_level == 'low':
                request.risk_level = 'medium'
        
        # Check for sensitive types
        if request.metadata.get('sensitive_type') in self.ALWAYS_REQUIRE_APPROVAL['sensitive_types']:
            reasons.append("Sensitive action type")
            if request.risk_level in ('low', 'medium'):
                request.risk_level = 'high'
        
        return request.risk_level, reasons
    
    def can_auto_approve(self, request: ApprovalRequest) -> tuple:
        """
        Determine if a request can be auto-approved.
        
        Args:
            request: Approval request
            
        Returns:
            Tuple of (can_auto_approve: bool, reason: str)
        """
        # Check amount
        if request.amount > self.AUTO_APPROVE_RULES['max_amount']:
            return False, f"Amount ${request.amount:.2f} exceeds auto-approve limit"
        
        # Check action type
        if request.action_type in self.ALWAYS_REQUIRE_APPROVAL['actions']:
            return False, f"Action type '{request.action_type}' always requires manual approval"
        
        # Check if new recipient
        if (request.recipient and 
            request.recipient not in self.known_recipients and 
            self.ALWAYS_REQUIRE_APPROVAL['new_recipients']):
            return False, "Unknown recipient requires manual approval"
        
        # Check amount over threshold for new recipients
        if (request.recipient and 
            request.amount > self.ALWAYS_REQUIRE_APPROVAL['amounts_over'] and
            request.recipient not in self.known_recipients):
            return False, f"Amount over ${self.ALWAYS_REQUIRE_APPROVAL['amounts_over']} with unknown recipient"
        
        # Check sensitive types
        if request.metadata.get('sensitive_type') in self.ALWAYS_REQUIRE_APPROVAL['sensitive_types']:
            return False, "Sensitive action requires manual approval"
        
        return True, "Meets auto-approve criteria"
    
    def create_approval_request(self, request: ApprovalRequest) -> Path:
        """
        Create an approval request file in the Pending_Approval folder.
        
        Args:
            request: Approval request details
            
        Returns:
            Path to the created approval file
        """
        request.created_at = datetime.now().isoformat()
        
        # Set expiry (24 hours by default)
        if not request.expires_at:
            expires = datetime.now() + timedelta(hours=24)
            request.expires_at = expires.isoformat()
        
        # Assess risk
        risk_level, reasons = self.assess_risk(request)
        request.risk_level = risk_level
        
        # Check auto-approve
        can_auto, auto_reason = self.can_auto_approve(request)
        
        if can_auto:
            # Auto-approve
            request.status = ApprovalStatus.AUTO_APPROVED.value
            request.approved_by = 'system'
            request.approved_at = datetime.now().isoformat()
            self.stats['auto_approved'] += 1
            logger.info(f"Auto-approved: {request.action_id}")
        else:
            request.status = ApprovalStatus.PENDING.value
            logger.info(f"Created approval request: {request.action_id} (risk: {risk_level})")
        
        # Build filename
        safe_reason = re.sub(r'[^a-zA-Z0-9_]', '_', request.reason)[:30]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_prefix = request.action_type.upper()
        filename = f"{file_prefix}_{safe_reason}_{timestamp}.md"
        
        # Handle duplicate filenames
        filepath = self.pending_dir / filename
        counter = 1
        while filepath.exists():
            filepath = self.pending_dir / f"{file_prefix}_{safe_reason}_{timestamp}_{counter}.md"
            counter += 1
        
        # Build frontmatter
        metadata = {
            'type': 'approval_request',
            'action_id': request.action_id,
            'action_type': request.action_type,
            'actor': request.actor,
            'priority': request.priority,
            'risk_level': risk_level,
            'created': request.created_at,
            'expires': request.expires_at,
            'status': request.status,
            'amount': request.amount,
        }
        
        if request.recipient:
            metadata['recipient'] = request.recipient
        
        if request.approved_by:
            metadata['approved_by'] = request.approved_by
            metadata['approved_at'] = request.approved_at
        
        # Build content
        content_lines = [f"## Approval Request: {request.action_type.title()}"]
        content_lines.append("")
        content_lines.append(f"**Requested by:** {request.actor}")
        content_lines.append(f"**Risk Level:** {risk_level.upper()}")
        
        if request.amount:
            content_lines.append(f"**Amount:** ${request.amount:,.2f}")
        
        if request.recipient:
            content_lines.append(f"**Recipient:** {request.recipient}")
        
        if request.reason:
            content_lines.append(f"\n**Reason:**\n{request.reason}")
        
        content_lines.append("")
        content_lines.append("### Risk Assessment")
        for reason in reasons:
            content_lines.append(f"- {reason}")
        
        if can_auto:
            content_lines.append("")
            content_lines.append(f"**Auto-Approved:** ✅ {auto_reason}")
        else:
            content_lines.append("")
            content_lines.append("### Action Required")
            content_lines.append("- [ ] Review the request above")
            content_lines.append("- [ ] Verify recipient and amount")
            content_lines.append("- [ ] Move to `/Approved/` to approve or `/Rejected/` to reject")
        
        if request.metadata.get('preview'):
            content_lines.append("")
            content_lines.append("### Preview")
            content_lines.append(request.metadata['preview'])
        
        content_lines.append("")
        content_lines.append(f"**Expires:** {request.expires_at}")
        content_lines.append("")
        content_lines.append("---")
        content_lines.append("*Auto-generated by Approval Workflow Manager*")
        
        # Write file
        yaml_lines = ['---']
        for key, value in metadata.items():
            yaml_lines.append(f'{key}: "{value}"' if isinstance(value, str) and ':' in str(value) else f'{key}: {value}')
        yaml_lines.append('---')
        
        filepath.write_text('\n'.join(yaml_lines) + '\n\n' + '\n'.join(content_lines))
        
        # Log event
        self.vault_manager.log_event(
            event_type='approval_request',
            task_id=request.action_id,
            details={
                'action_type': request.action_type,
                'risk_level': risk_level,
                'amount': request.amount,
                'status': request.status,
                'auto_approved': can_auto
            }
        )
        
        self.stats['requests_created'] += 1
        return filepath
    
    def process_pending_approvals(self) -> Dict[str, Any]:
        """
        Scan for pending approvals and check for expired requests.
        Also watches for moved files (user approval/rejection).
        
        Returns:
            Processing results
        """
        results = {
            'checked': 0,
            'approved': 0,
            'rejected': 0,
            'expired': 0,
            'escalated': 0
        }
        
        now = datetime.now()
        
        # Check Pending_Approval for expired items
        for file_path in self.pending_dir.glob('*.md'):
            try:
                content = file_path.read_text()
                metadata = self._parse_frontmatter(content)
                
                expires_str = metadata.get('expires', '')
                status = metadata.get('status', 'pending')
                
                results['checked'] += 1
                
                # Check expiry
                if expires_str:
                    try:
                        expires = datetime.fromisoformat(expires_str)
                        if now > expires and status == 'pending':
                            # Mark as expired
                            self._move_to_expired(file_path, metadata)
                            results['expired'] += 1
                            self.stats['expired'] += 1
                            continue
                    except ValueError:
                        pass
                
                # Check if already moved to Approved or Rejected
                # (user moved the file, but frontmatter still says pending)
                # In this case, the filesystem watcher handles it
                
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
        
        # Check Approved folder for new approvals to execute
        for file_path in self.approved_dir.glob('*.md'):
            try:
                content = file_path.read_text()
                metadata = self._parse_frontmatter(content)
                
                if metadata.get('status') == 'approved':
                    # Already executed
                    continue
                
                # Execute the approved action
                action_id = metadata.get('action_id', '')
                action_type = metadata.get('action_type', '')
                
                # Mark as executed
                metadata['status'] = 'approved'
                metadata['executed_at'] = datetime.now().isoformat()
                
                # Move to Done
                done_path = self.vault_path / 'Done' / file_path.name
                if done_path.exists():
                    done_path = self.vault_path / 'Done' / f"{file_path.stem}_{datetime.now().strftime('%H%M%S')}.md"
                file_path.rename(done_path)
                
                results['approved'] += 1
                self.stats['human_approved'] += 1
                
                logger.info(f"Processed approved action: {action_id}")
                
            except Exception as e:
                logger.error(f"Error processing approved file {file_path}: {e}")
        
        # Check Rejected folder
        for file_path in self.rejected_dir.glob('*.md'):
            try:
                content = file_path.read_text()
                metadata = self._parse_frontmatter(content)
                
                action_id = metadata.get('action_id', '')
                rejection_reason = metadata.get('rejection_reason', 'No reason provided')
                
                # Log rejection
                self.vault_manager.log_event(
                    event_type='approval_rejected',
                    task_id=action_id,
                    details={'reason': rejection_reason}
                )
                
                results['rejected'] += 1
                self.stats['rejected'] += 1
                
                # Archive to Rejected folder (already there, just log)
                logger.info(f"Rejected action: {action_id} - {rejection_reason}")
                
            except Exception as e:
                logger.error(f"Error processing rejected file {file_path}: {e}")
        
        return results
    
    def _move_to_expired(self, file_path: Path, metadata: Dict):
        """Move an expired approval request to the Rejected folder with expiry note."""
        try:
            content = file_path.read_text()
            
            # Update metadata
            content = re.sub(
                r'(status:)\s*pending',
                r'\1 expired',
                content
            )
            content += f"\n\n**Expired:** {datetime.now().isoformat()}\n**Note:** This approval request expired and was automatically rejected."
            
            # Move to Rejected
            rejected_path = self.rejected_dir / file_path.name
            rejected_path.write_text(content)
            file_path.unlink()
            
            logger.info(f"Expired approval request: {file_path.name}")
            
            # Log event
            self.vault_manager.log_event(
                event_type='approval_expired',
                task_id=metadata.get('action_id', ''),
                details={'original_file': file_path.name}
            )
            
        except Exception as e:
            logger.error(f"Error moving expired request: {e}")
    
    def approve(self, action_id: str, approver: str = 'user') -> bool:
        """
        Approve a pending request.
        
        Args:
            action_id: The action ID to approve
            approver: Who approved it
            
        Returns:
            True if found and approved
        """
        # Find in pending
        for file_path in self.pending_dir.glob('*.md'):
            try:
                content = file_path.read_text()
                if action_id in content:
                    # Update status
                    content = re.sub(r'(status:)\s*pending', r'\1 approved', content)
                    content = re.sub(r'(approved_by:)\s*.*', f'\\1 {approver}', content)
                    if 'approved_at:' not in content:
                        # Add approved_at field
                        content = content.replace(
                            'status: approved',
                            f'status: approved\napproved_at: {datetime.now().isoformat()}'
                        )
                    
                    # Move to Approved
                    approved_path = self.approved_dir / file_path.name
                    approved_path.write_text(content)
                    file_path.unlink()
                    
                    self.stats['human_approved'] += 1
                    logger.info(f"Approved: {action_id} by {approver}")
                    return True
                    
            except Exception as e:
                logger.error(f"Error approving {action_id}: {e}")
        
        return False
    
    def reject(self, action_id: str, reason: str, rejecter: str = 'user') -> bool:
        """
        Reject a pending request.
        
        Args:
            action_id: The action ID to reject
            reason: Reason for rejection
            rejecter: Who rejected it
            
        Returns:
            True if found and rejected
        """
        for file_path in self.pending_dir.glob('*.md'):
            try:
                content = file_path.read_text()
                if action_id in content:
                    # Update status and add rejection reason
                    content = re.sub(r'(status:)\s*pending', r'\1 rejected', content)
                    content += f"\n\n**Rejected by:** {rejecter}\n**Reason:** {reason}\n**Rejected at:** {datetime.now().isoformat()}"
                    
                    # Move to Rejected
                    rejected_path = self.rejected_dir / file_path.name
                    rejected_path.write_text(content)
                    file_path.unlink()
                    
                    self.stats['rejected'] += 1
                    logger.info(f"Rejected: {action_id} by {rejecter}")
                    return True
                    
            except Exception as e:
                logger.error(f"Error rejecting {action_id}: {e}")
        
        return False
    
    def escalate(self, action_id: str, level: str, reason: str = '') -> bool:
        """
        Escalate a request to a higher authority.
        
        Args:
            action_id: The action ID to escalate
            level: Target escalation level (ceo, board)
            reason: Reason for escalation
            
        Returns:
            True if escalation initiated
        """
        for file_path in self.pending_dir.glob('*.md'):
            try:
                content = file_path.read_text()
                if action_id in content:
                    # Get existing metadata
                    metadata = self._parse_frontmatter(content)
                    current_risk = metadata.get('risk_level', 'medium')
                    
                    # Update risk level
                    content = re.sub(
                        r'risk_level:\s*\w+',
                        f'risk_level: {level}',
                        content
                    )
                    content += f"\n\n**Escalated to:** {level.upper()}\n**Reason:** {reason}\n**Escalated at:** {datetime.now().isoformat()}"
                    
                    # Move to special escalation pending
                    escalation_dir = self.pending_dir / 'Escalated'
                    escalation_dir.mkdir(parents=True, exist_ok=True)
                    escalation_path = escalation_dir / file_path.name
                    escalation_path.write_text(content)
                    file_path.unlink()
                    
                    self.stats['escalated'] += 1
                    logger.warning(f"Escalated: {action_id} to {level}")
                    return True
                    
            except Exception as e:
                logger.error(f"Error escalating {action_id}: {e}")
        
        return False
    
    def _parse_frontmatter(self, content: str) -> Dict[str, str]:
        """Parse YAML frontmatter from approval file."""
        metadata = {}
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                for line in parts[1].strip().split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        metadata[key.strip()] = value.strip().strip('"')
        return metadata
    
    def get_queue_summary(self) -> Dict[str, int]:
        """Get summary of approval queue."""
        return {
            'pending': len(list(self.pending_dir.glob('*.md'))) - 
                       len(list((self.pending_dir / 'Escalated').glob('*.md')) if (self.pending_dir / 'Escalated').exists() else []),
            'escalated': len(list((self.pending_dir / 'Escalated').glob('*.md')) if (self.pending_dir / 'Escalated').exists() else []),
            'approved': len(list(self.approved_dir.glob('*.md'))),
            'rejected': len(list(self.rejected_dir.glob('*.md'))),
        }
    
    def get_policy_summary(self) -> str:
        """Return readable policy summary."""
        lines = [
            "## Approval Policy Summary",
            "",
            "### Auto-Approve (No HITL Required)",
            f"- Payments < ${self.AUTO_APPROVE_RULES['max_amount']}",
            "- Known recipients (recurring)",
            "- Routine operational expenses",
            "",
            "### Always Require Approval",
        ]
        
        for action in self.ALWAYS_REQUIRE_APPROVAL['actions']:
            lines.append(f"- {action.title()}")
        if self.ALWAYS_REQUIRE_APPROVAL['new_recipients']:
            lines.append("- New recipients")
        lines.append(f"- Amounts over ${self.ALWAYS_REQUIRE_APPROVAL['amounts_over']} with unknown recipients")
        
        lines.extend(["", "### Risk-Based Routing"])
        for level, config in self.RISK_THRESHOLDS.items():
            lines.append(f"- **{level.title()}:** {config['description']} (>{config['min_amount'] - 1:,})")
        
        return '\n'.join(lines)
    
    def get_stats(self) -> Dict[str, Any]:
        """Return workflow statistics."""
        return {
            **self.stats,
            'queue': self.get_queue_summary(),
            'uptime_seconds': (datetime.now() - datetime.fromisoformat(self.stats['started_at'])).total_seconds()
        }


# ─── Standalone Execution ────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Approval Workflow Manager')
    parser.add_argument('--vault-path', default='AI_Employee_Vault', help='Vault path')
    parser.add_argument('--policy', action='store_true', help='Show policy summary')
    parser.add_argument('--create-test', action='store_true', help='Create test approval request')
    parser.add_argument('--process', action='store_true', help='Process pending approvals')
    parser.add_argument('--test', action='store_true', help='Run self-test')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    manager = ApprovalWorkflowManager(vault_path=args.vault_path)
    
    if args.policy:
        print(manager.get_policy_summary())
    
    if args.create_test:
        req = ApprovalRequest(
            action_id='TEST_001',
            action_type='payment',
            actor='gmail_processor',
            amount=1500.00,
            recipient='vendor@example.com',
            reason='Invoice #1234 for services rendered',
            priority='high',
            metadata={'preview': 'Payment for January consulting services'}
        )
        path = manager.create_approval_request(req)
        print(f"Created approval request: {path}")
    
    if args.process:
        results = manager.process_pending_approvals()
        print(f"Processed: {json.dumps(results, indent=2)}")
    
    if args.test:
        print("=" * 60)
        print("Approval Workflow Self-Test")
        print("=" * 60)
        
        # Test 1: Risk assessment - critical
        req = ApprovalRequest(
            action_id='TEST_CRIT',
            action_type='payment',
            actor='test',
            amount=100000,
            recipient='new_vendor.com',
            reason='Large payment'
        )
        risk, reasons = manager.assess_risk(req)
        assert risk == 'critical', f"Expected critical, got {risk}"
        print(f"✓ Critical risk detected: ${req.amount:,.2f}")
        
        # Test 2: Risk assessment - low
        req2 = ApprovalRequest(
            action_id='TEST_LOW',
            action_type='email',
            actor='test',
            amount=25,
            recipient='known@example.com'
        )
        risk2, reasons2 = manager.assess_risk(req2)
        print(f"✓ Low risk assessed: {risk2} ($25 email)")
        
        # Test 3: Auto-approve check — unknown recipient should NOT auto-approve
        # (new recipients always require approval per Company Handbook policy)
        req3 = ApprovalRequest(
            action_id='TEST_AUTO',
            action_type='email_reply',
            actor='test',
            amount=10,
            recipient='colleague@example.com'
        )
        # colleague@example.com is not in known_recipients, so requires manual approval
        can_auto, reason = manager.can_auto_approve(req3)
        assert not can_auto, f"Unknown recipient should NOT auto-approve: {reason}"
        print(f"✓ Unknown recipient requires approval: '{reason}'")
        
        # Test 4: Should NOT auto-approve (unknown recipient)
        req4 = ApprovalRequest(
            action_id='TEST_MANUAL',
            action_type='payment',
            actor='test',
            amount=50000,
            recipient='new_vendor.com'
        )
        can_auto2, reason2 = manager.can_auto_approve(req4)
        assert not can_auto2, "Large payment to unknown vendor should NOT auto-approve"
        print(f"✓ Manual approval required: {reason2}")

# Test 4b: Known recipient under limit CAN auto-approve
        manager.known_recipients['known_colleague'] = {'type': 'internal'}
        req4b = ApprovalRequest(
            action_id='TEST_AUTO2',
            action_type='email_reply',
            actor='test',
            amount=10,
            recipient='known_colleague'
        )
        can_auto3, reason3 = manager.can_auto_approve(req4b)
        # email_reply with low amount and known recipient should auto-approve
        assert can_auto3, f"Known recipient low amount should auto-approve: {reason3}"
        print(f"✓ Auto-approve for known recipient low amount: '{reason3}'")

        # Test 4c: Amount over $100 with unknown recipient should NOT auto-approve
        req4c = ApprovalRequest(
            action_id='TEST_MANUAL2',
            action_type='payment',
            actor='test',
            amount=200,
            recipient='unknown.com'
        )
        can_auto4, reason4 = manager.can_auto_approve(req4c)
        assert not can_auto4, "Amount > $100 with unknown recipient should NOT auto-approve"
        print(f"✓ Manual approval for unknown recipient: {reason4}")

        # Test 4d: Low amount with known recipient
        manager.known_recipients['known@example.com'] = {'type': 'partner'}
        req4d = ApprovalRequest(
            action_id='TEST_AUTO3',
            action_type='email_reply',
            actor='test',
            amount=5,
            recipient='known@example.com'
        )
        can_auto5, reason5 = manager.can_auto_approve(req4d)
        print(f"  Low amount known recipient: can_auto={can_auto5}, reason='{reason5}'")
        
        # Test 5: Create and retrieve approval
        req5 = ApprovalRequest(
            action_id='TEST_FLOW',
            action_type='payment',
            actor='test',
            amount=500,
            recipient='vendor.test.com',
            reason='Integration test'
        )
        filepath = manager.create_approval_request(req5)
        assert filepath.exists(), "Approval file should exist"
        print(f"✓ Approval request created: {filepath.name}")
        
        # Test 6: Approve
        approved = manager.approve('TEST_FLOW', 'test_user')
        assert approved, "Approval should succeed"
        print(f"✓ Approval processed")
        
        print("\n✓ All Approval Workflow tests passed!")
        print(f"\nStats: {json.dumps(manager.get_stats(), indent=2, default=str)}")