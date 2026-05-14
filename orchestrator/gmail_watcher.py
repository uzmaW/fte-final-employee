"""
Gmail watcher - polls Gmail inbox and creates task files.
Requires Gmail API OAuth setup and refresh token in .env.
"""

import logging
import base64
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import re

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestrator.base_watcher import BaseWatcher

logger = logging.getLogger(__name__)


class GmailWatcher(BaseWatcher):
    """Watch Gmail inbox and create tasks for unread emails."""
    
    def __init__(self):
        """Initialize Gmail watcher."""
        # Initialize settings first
        from config import get_settings
        from utilities.vault_manager import VaultManager
        settings = get_settings()
        
        super().__init__(
            name="gmail",
            poll_interval=settings.gmail_poll_interval
        )
        self.gmail_service = None
        self.authenticate()
    
    def authenticate(self):
        """Authenticate with Gmail API using OAuth."""
        try:
            # Check if credentials are configured
            if not all([
                self.settings.gmail_client_id,
                self.settings.gmail_client_secret,
                self.settings.gmail_refresh_token
            ]):
                logger.warning("Gmail credentials not configured in .env")
                self.gmail_service = None
                return
            
            # In production, use google.auth library
            # For now, mark as ready
            logger.info("Gmail authentication configured")
            self.gmail_service = "configured"  # Placeholder
            
        except Exception as e:
            logger.error(f"Gmail authentication failed: {e}")
            self.gmail_service = None
    
    def poll(self) -> List[Dict[str, Any]]:
        """
        Poll Gmail for unread emails.
        
        Returns:
            List of email dictionaries to process
        """
        if not self.gmail_service:
            logger.warning("Gmail service not configured")
            return []
        
        try:
            logger.debug("Polling Gmail inbox")
            
            # In production, this would call:
            # results = self.gmail_service.users().messages().list(
            #     userId='me',
            #     q='is:unread',
            #     maxResults=10
            # ).execute()
            
            # For now, return empty list (demo mode)
            return []
            
        except Exception as e:
            logger.error(f"Error polling Gmail: {e}", exc_info=True)
            return []
    
    def get_email_details(self, message_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch full email details from Gmail API.
        
        Args:
            message_id: Gmail message ID
            
        Returns:
            Email dictionary with headers and body
        """
        try:
            # In production:
            # message = self.gmail_service.users().messages().get(
            #     userId='me',
            #     id=message_id,
            #     format='full'
            # ).execute()
            
            # Parse headers and body
            # return self._parse_email(message)
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching email {message_id}: {e}")
            return None
    
    def mark_as_read(self, message_id: str) -> bool:
        """
        Mark email as read in Gmail.
        
        Args:
            message_id: Gmail message ID
            
        Returns:
            True if successful
        """
        try:
            # In production:
            # self.gmail_service.users().messages().modify(
            #     userId='me',
            #     id=message_id,
            #     body={'removeLabelIds': ['UNREAD']}
            # ).execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Error marking email as read: {e}")
            return False
    
    def categorize_priority(self, email: Dict[str, Any]) -> str:
        """
        Determine email priority based on sender, subject, and content.
        
        Args:
            email: Email dictionary with from, subject, body
            
        Returns:
            Priority level: critical, high, medium, low
        """
        subject = email.get('subject', '').lower()
        body = email.get('body', '').lower()
        sender = email.get('from', '').lower()
        
        # Critical indicators
        critical_keywords = ['urgent', 'asap', 'emergency', 'critical', 'down', 'outage']
        if any(kw in subject or kw in body for kw in critical_keywords):
            return 'critical'
        
        # High priority indicators
        high_keywords = ['important', 'action needed', 'approval', 'review', 'decision', 'issue']
        if any(kw in subject or kw in body for kw in high_keywords):
            return 'high'
        
        # Check if from known important contacts (would be in config)
        important_senders = ['ceo', 'founder', 'lead', 'manager']
        if any(sender_kw in sender for sender_kw in important_senders):
            return 'high'
        
        # Default to medium for business emails, low for newsletters
        if 'newsletter' in subject or 'digest' in subject:
            return 'low'
        
        return 'medium'
    
    def extract_actions(self, email: Dict[str, Any]) -> List[str]:
        """
        Extract actionable items from email content.
        
        Args:
            email: Email dictionary
            
        Returns:
            List of action items
        """
        body = email.get('body', '')
        actions = []
        
        # Look for common action patterns
        patterns = [
            r'please\s+([^.!?]+)',
            r'can you\s+([^?]+)',
            r'need\s+you\s+to\s+([^.]+)',
            r'action items?[:\s]+([^.]+)',
            r'\[todo\]\s+([^.]+)',
            r'- \[\s*\]\s+([^.]+)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, body, re.IGNORECASE)
            actions.extend(matches)
        
        return [action.strip() for action in actions if action.strip()]
    
    def process_item(self, email: Dict[str, Any]) -> Optional[str]:
        """
        Process a single email and create a task file.
        
        Args:
            email: Email dictionary from Gmail API
            
        Returns:
            Path to created task file
        """
        try:
            message_id = email.get('id')
            
            # Get full email details
            email_details = self.get_email_details(message_id)
            if not email_details:
                logger.warning(f"Could not fetch email {message_id}")
                return None
            
            # Extract key information
            sender = email_details.get('from', 'Unknown')
            subject = email_details.get('subject', 'No subject')
            body = email_details.get('body', '')
            timestamp = email_details.get('date', '')
            has_attachments = email_details.get('has_attachments', False)
            
            # Categorize priority
            priority = self.categorize_priority(email_details)
            
            # Extract action items
            actions = self.extract_actions(email_details)
            
            # Generate task ID
            task_id = f"EMAIL_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_001"
            
            # Build task content
            actions_text = ""
            if actions:
                actions_text = "\n## Extracted Actions\n"
                for i, action in enumerate(actions, 1):
                    actions_text += f"- [ ] {action}\n"
            
            content = f"""**From:** {sender}  
**Subject:** {subject}  
**Date:** {timestamp}  
**Priority:** {priority}  

## Email Content

{body}
{actions_text}

## Quick Response

Reply to: {sender}

---

Email ID: {message_id}"""
            
            # Build metadata
            metadata = {
                'email_id': message_id,
                'from': sender,
                'subject': subject,
                'has_attachment': has_attachments,
            }
            
            # Create task file
            task_file = self.create_task_file(
                task_id=task_id,
                task_type='email_task',
                title=f"Email: {subject}",
                priority=priority,
                content=content,
                metadata=metadata
            )
            
            if task_file:
                # Mark as read in Gmail
                self.mark_as_read(message_id)
            
            return task_file
            
        except Exception as e:
            logger.error(f"Error processing email: {e}", exc_info=True)
            return None


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    
    watcher = GmailWatcher()
    
    if len(sys.argv) > 1 and sys.argv[1] == 'loop':
        # Run continuous loop
        watcher.run_loop()
    else:
        # Run once
        count = watcher.run_once()
        print(f"Processed {count} emails")
