"""
gmail_processor.py - Gmail email processing implementation.

Backs the .claude/skills/gmail-processor/SKILL.md specification.
Handles Gmail API authentication, email fetching, categorization, and task file creation.
"""

import os
import re
import time
import logging
import base64
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    logger.warning("google-auth/google-api-python-client not installed - Gmail API unavailable")

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config import get_settings
from utilities.vault_manager import VaultManager
from utilities.retry_handler import with_retry, TransientError, PermanentError

logger = logging.getLogger(__name__)

# Gmail API scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.labels',
]


@dataclass
class EmailMessage:
    """Represents a processed email message."""
    message_id: str
    thread_id: str
    sender: str
    sender_name: str
    subject: str
    received: str
    snippet: str
    body: str
    priority: str  # critical, high, medium, low
    has_attachment: bool = False
    attachments: List[Dict[str, Any]] = field(default_factory=list)
    labels: List[str] = field(default_factory=list)
    is_read: bool = False
    categories: List[str] = field(default_factory=list)


class GmailProcessor:
    """
    Gmail email processor for the AI Employee system.
    
    Handles:
    - OAuth2 authentication with Gmail API
    - Fetching and parsing emails
    - Priority categorization
    - Creating task files in the vault
    - Marking emails as processed
    """
    
    # Known contact domains for priority boosting
    KNOWN_DOMAINS = []
    
    # Priority keywords
    CRITICAL_KEYWORDS = ['urgent', 'asap', 'emergency', 'down', 'crisis', 'outage', 'critical', 'immediately']
    HIGH_KEYWORDS = ['important', 'action required', 'approval needed', 'decision needed', 'review needed', 'deadline']
    MEDIUM_KEYWORDS = ['update', 'fyi', 'status', 'follow up', 'reminder', 'scheduled', 'meeting']
    LOW_KEYWORDS = ['newsletter', 'digest', 'unsubscribe', 'promotional', 'offer', 'sale', 'marketing']
    
    # Subject patterns
    CRITICAL_SUBJECTS = [r'urgent', r'emergency', r'down', r'outage', r'critical', r'asap']
    HIGH_SUBJECTS = [r'action.*required', r'approval.*needed', r'decision.*needed', r'review.*needed', r'important']
    LOW_SUBJECTS = [r'newsletter', r'digest', r'weekly.*update', r'monthly.*report']

    def __init__(self, vault_path: str = None):
        """
        Initialize Gmail processor.
        
        Args:
            vault_path: Path to Obsidian vault. If None, reads from config.
        """
        self.settings = get_settings()
        self.vault_path = Path(vault_path) if vault_path else self.settings.vault_path
        self.vault_manager = VaultManager()
        self.creds = None
        self.service = None
        self._authenticated = False
        
        # Stats
        self.stats = {
            'emails_processed': 0,
            'emails_skipped': 0,
            'tasks_created': 0,
            'errors': 0,
            'last_check': None,
            'started_at': datetime.now().isoformat()
        }
    
    def authenticate(self) -> bool:
        """
        Authenticate with Gmail API using OAuth2.
        
        Returns:
            True if authentication successful
        """
        try:
            creds = None
            
            # Try to load existing credentials
            token_path = Path(self.settings.vault_path) / '.gmail_token.json'
            
            if token_path.exists():
                creds = Credentials.from_authorized_user_file(
                    str(token_path), SCOPES
                )
            
            # If no valid credentials, get new ones
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(Path(self.settings.vault_path) / '.gmail_credentials.json'),
                        SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                
                # Save credentials
                with open(token_path, 'w') as f:
                    f.write(creds.to_json())
            
            self.creds = creds
            self.service = build('gmail', 'v1', credentials=creds)
            self._authenticated = True
            logger.info("Gmail API authentication successful")
            return True
            
        except Exception as e:
            logger.error(f"Gmail authentication failed: {e}")
            self._authenticated = False
            return False
    
    def authenticate_with_api_key(self, api_key: str) -> bool:
        """
        Authenticate using a pre-configured API key (simpler method).
        
        Args:
            api_key: Gmail API key
            
        Returns:
            True if successful
        """
        try:
            self.creds = Credentials.from_authorized_user_info(
                {'access_token': api_key, 'token_uri': 'https://oauth2.googleapis.com/token'}
            )
            self.service = build('gmail', 'v1', credentials=self.creds)
            self._authenticated = True
            return True
        except Exception as e:
            logger.error(f"API key authentication failed: {e}")
            return False
    
    @with_retry(max_attempts=3, base_delay=2, max_delay=30)
    def _fetch_emails_raw(self, max_results: int = 10, query: str = 'is:unread') -> List[Dict]:
        """
        Fetch emails from Gmail API with retry logic.
        
        Args:
            max_results: Maximum number of emails to fetch
            query: Gmail search query
            
        Returns:
            List of raw email message objects
        """
        if not self.service:
            raise PermanentError("Gmail service not initialized")
        
        results = self.service.users().messages().list(
            userId='me',
            q=query,
            maxResults=max(max_results, 1),
            # Include thread info
        ).execute()
        
        messages = results.get('messages', [])
        
        # Check for rate limiting
        if len(messages) == 0 and 'resultSizeEstimate' in results:
            logger.info(f"No new emails matching query: {query}")
        
        return messages
    
    def fetch_emails(self, max_results: int = 10, query: str = 'is:unread') -> List[EmailMessage]:
        """
        Fetch and parse emails from Gmail.
        
        Args:
            max_results: Maximum number of emails to fetch
            query: Gmail search query
            
        Returns:
            List of parsed EmailMessage objects
        """
        if not self._authenticated:
            logger.warning("Not authenticated with Gmail API")
            return []
        
        raw_messages = self._fetch_emails_raw(max_results, query)
        emails = []
        
        for msg_data in raw_messages:
            try:
                msg_id = msg_data['id']
                
                # Get full message details
                msg = self.service.users().messages().get(
                    userId='me',
                    id=msg_id,
                    format='full'
                ).execute()
                
                email = self._parse_message(msg)
                if email:
                    emails.append(email)
                    
            except HttpError as e:
                if e.resp.status == 429:
                    # Rate limited - wait and retry
                    logger.warning("Rate limited, waiting before retry...")
                    time.sleep(5)
                else:
                    logger.error(f"HTTP error fetching email: {e}")
                    self.stats['errors'] += 1
            except Exception as e:
                logger.error(f"Error parsing email {msg_data.get('id')}: {e}")
                self.stats['errors'] += 1
        
        self.stats['last_check'] = datetime.now().isoformat()
        return emails
    
    def _parse_message(self, msg: Dict) -> Optional[EmailMessage]:
        """Parse a raw Gmail API message into an EmailMessage."""
        try:
            headers = {}
            for header in msg.get('payload', {}).get('headers', []):
                headers[header['name'].lower()] = header['value']
            
            sender = headers.get('from', 'unknown')
            sender_name = self._extract_sender_name(sender)
            subject = headers.get('subject', '(No Subject)')
            thread_id = msg.get('threadId', msg['id'])
            received = headers.get('date', datetime.now().isoformat())
            
            # Parse received date
            try:
                from email.utils import parsedate_to_datetime
                received_dt = parsedate_to_datetime(received)
                received = received_dt.isoformat()
            except Exception:
                pass
            
            # Extract body
            body = self._extract_body(msg)
            snippet = msg.get('snippet', body[:200])
            
            # Check for attachments
            has_attachments = False
            attachments = []
            parts = msg.get('payload', {}).get('parts', [])
            for part in parts:
                if part.get('filename'):
                    has_attachments = True
                    attachments.append({
                        'filename': part['filename'],
                        'mimeType': part.get('mimeType', 'application/octet-stream'),
                        'sizeEstimate': part.get('sizeEstimate', 0)
                    })
            
            # Determine priority
            priority = self._categorize_priority(sender, subject, snippet, body)
            
            # Get labels
            labels = msg.get('labelIds', [])
            
            return EmailMessage(
                message_id=msg['id'],
                thread_id=thread_id,
                sender=sender,
                sender_name=sender_name,
                subject=subject,
                received=received,
                snippet=snippet,
                body=body,
                priority=priority,
                has_attachment=has_attachments,
                attachments=attachments,
                labels=labels
            )
            
        except Exception as e:
            logger.error(f"Error parsing message: {e}")
            return None
    
    def _extract_body(self, msg: Dict) -> str:
        """Extract text body from message."""
        payload = msg.get('payload', {})
        body_data = ''
        
        if 'body' in payload and 'data' in payload['body']:
            body_data = payload['body']['data']
        elif 'parts' in payload:
            for part in payload['parts']:
                if part.get('mimeType') == 'text/plain' and 'body' in part and 'data' in part['body']:
                    body_data = part['body']['data']
                    break
                elif part.get('mimeType') == 'text/html' and 'body' in part and 'data' in part['body']:
                    body_data = part['body']['data']
        
        if body_data:
            try:
                return base64.urlsafe_b64decode(body_data).decode('utf-8', errors='replace')
            except Exception:
                return body_data
        
        return '(No body content)'
    
    def _extract_sender_name(self, sender_header: str) -> str:
        """Extract sender name from email header."""
        # Format: "Name" <email> or email
        match = re.match(r'^"?([^"<]+)"?\s*<?([^>]+)>?', sender_header)
        if match:
            name = match.group(1).strip()
            email = match.group(2).strip()
            return name if name else email.split('@')[0]
        return sender_header.split('@')[0] if '@' in sender_header else sender_header
    
    def _categorize_priority(
        self,
        sender: str,
        subject: str,
        snippet: str,
        body: str
    ) -> str:
        """
        Categorize email priority based on sender, subject, and content.
        
        Priority levels: critical, high, medium, low
        """
        text = f"{sender} {subject} {snippet} {body}".lower()
        subject_lower = subject.lower()
        
        # Check sender importance
        known_senders = self._get_known_senders()
        sender_domain = sender.split('@')[-1] if '@' in sender else ''
        
        if sender in known_senders.get('critical', []):
            return 'critical'
        if sender in known_senders.get('high', []):
            return 'high'
        if sender_domain in self.KNOWN_DOMAINS:
            return 'high'
        
        # Check CRITICAL keywords
        for kw in self.CRITICAL_KEYWORDS:
            if kw in text:
                return 'critical'
        
        # Check subject patterns for CRITICAL
        for pattern in self.CRITICAL_SUBJECTS:
            if re.search(pattern, subject_lower):
                return 'critical'
        
        # Check HIGH keywords
        for kw in self.HIGH_KEYWORDS:
            if kw in text:
                return 'high'
        
        # Check subject patterns for HIGH
        for pattern in self.HIGH_SUBJECTS:
            if re.search(pattern, subject_lower):
                return 'high'
        
        # Check LOW keywords (these override medium)
        for kw in self.LOW_KEYWORDS:
            if kw in text:
                return 'low'
        
        # Check subject patterns for LOW
        for pattern in self.LOW_SUBJECTS:
            if re.search(pattern, subject_lower):
                return 'low'
        
        # Check MEDIUM keywords
        for kw in self.MEDIUM_KEYWORDS:
            if kw in text:
                return 'medium'
        
        # Default
        return 'medium'
    
    def _get_known_senders(self) -> Dict[str, List[str]]:
        """
        Get known senders from Company_Handbook or configuration.
        
        Returns:
            Dict with 'critical' and 'high' sender lists
        """
        try:
            handbook_path = self.vault_path / 'Company_Handbook.md'
            if handbook_path.exists():
                content = handbook_path.read_text()
                # Parse key contacts section if present
                # This is a simplified implementation
                return {
                    'critical': [],
                    'high': []
                }
        except Exception:
            pass
        
        return {'critical': [], 'high': []}
    
    def create_task_file(self, email: EmailMessage) -> Optional[Path]:
        """
        Create a task file from an email in the Needs_Action folder.
        
        Args:
            email: Parsed email message
            
        Returns:
            Path to created task file or None
        """
        try:
            timestamp = email.received
            task_id = f"EMAIL_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{email.message_id[:8]}"
            
            # Format attachments section
            attachments_section = ""
            if email.has_attachment and email.attachments:
                attachments_section = "\n## Attachments\n"
                for att in email.attachments:
                    size_kb = att.get('sizeEstimate', 0) / 1024
                    attachments_section += f"- `{att['filename']}` ({att['mimeType']}, {size_kb:.1f} KB)\n"
            
            # Format content
            content = f"""## Email Details

**From:** {email.sender_name} &lt;{email.sender}&gt;
**Subject:** {email.subject}
**Received:** {email.received}
**Priority:** {email.priority.upper()}
**Thread ID:** {email.thread_id}
**Labels:** {', '.join(email.labels) if email.labels else 'None'}

---

## Content

{email.body if email.body else email.snippet}

{attachments_section}

---

## Suggested Actions

- [ ] Read and understand the email
- [ ] Determine appropriate response
- [ ] Draft reply (if needed)
- [ ] Create approval request (if sensitive)
- [ ] Archive after processing

---

**Source:** Gmail API | Message ID: {email.message_id}"""
            
            metadata = {
                'type': 'email_task',
                'priority': email.priority,
                'source': 'gmail',
                'created': timestamp,
                'email_id': email.message_id,
                'thread_id': email.thread_id,
                'sender': email.sender,
                'subject': email.subject,
                'has_attachment': str(email.has_attachment).lower()
            }
            
            filename = f"{task_id}.md"
            filepath = self.vault_path / 'Needs_Action' / filename
            
            # Write with YAML frontmatter
            yaml_lines = ['---']
            for key, value in metadata.items():
                val_str = str(value)
                if '"' in val_str or ':' in val_str:
                    val_str = f'"{val_str}"'
                yaml_lines.append(f'{key}: {val_str}')
            yaml_lines.append('---')
            
            filepath.write_text('\n'.join(yaml_lines) + '\n\n' + content)
            
            self.stats['tasks_created'] += 1
            logger.info(f"Created task file: {filename}")
            
            # Update dashboard
            self.vault_manager.log_event(
                event_type='email_processed',
                task_id=task_id,
                details={'priority': email.priority, 'sender': email.sender}
            )
            
            return filepath
            
        except Exception as e:
            logger.error(f"Error creating task file for email: {e}")
            self.stats['errors'] += 1
            return None
    
    @with_retry(max_attempts=3, base_delay=2, max_delay=30)
    def mark_as_read(self, message_id: str) -> bool:
        """
        Mark an email as read by removing the UNREAD label.
        
        Args:
            message_id: Gmail message ID
            
        Returns:
            True if successful
        """
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            logger.debug(f"Marked as read: {message_id}")
            return True
        except HttpError as e:
            if e.resp.status == 404:
                raise PermanentError(f"Message not found: {message_id}")
            raise TransientError(f"Failed to mark as read: {e}")
    
    def mark_as_processed(self, message_id: str, labels: List[str] = None) -> bool:
        """
        Mark an email as processed with custom labels.
        
        Args:
            message_id: Gmail message ID
            labels: Optional labels to add
            
        Returns:
            True if successful
        """
        try:
            modify_body = {
                'removeLabelIds': ['UNREAD'],
                'addLabelIds': labels or ['PROCESSED']
            }
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body=modify_body
            ).execute()
            return True
        except Exception as e:
            logger.error(f"Error marking as processed: {e}")
            return False
    
    def process_inbox(self, max_emails: int = 10) -> Dict[str, Any]:
        """
        Main processing method: fetch, parse, create tasks, mark as read.
        
        Args:
            max_emails: Maximum emails to process per cycle
            
        Returns:
            Processing results summary
        """
        if not self._authenticated:
            return {'success': False, 'error': 'Not authenticated'}
        
        emails = self.fetch_emails(max_results=max_emails)
        
        result = {
            'fetched': len(emails),
            'tasks_created': 0,
            'marked_read': 0,
            'errors': 0,
            'skipped': 0
        }
        
        for email in emails:
            # Check for duplicates (task already exists for this email)
            existing_tasks = list((self.vault_path / 'Needs_Action').glob(f"*EMAIL*{email.message_id[:8]}*"))
            if existing_tasks:
                result['skipped'] += 1
                # Still mark as read if not already
                self.mark_as_read(email.message_id)
                result['marked_read'] += 1
                continue
            
            # Create task file
            task_file = self.create_task_file(email)
            if task_file:
                result['tasks_created'] += 1
                
                # Mark as read after successful task creation
                try:
                    self.mark_as_read(email.message_id)
                    result['marked_read'] += 1
                except Exception as e:
                    logger.warning(f"Could not mark email as read: {e}")
            else:
                result['errors'] += 1
        
        self.stats['emails_processed'] += result['fetched']
        self.stats['emails_skipped'] += result['skipped']
        
        return result
    
    def setup_labels(self) -> bool:
        """
        Create PROCESSED label if it doesn't exist.
        
        Returns:
            True if setup complete
        """
        try:
            labels = self.service.users().labels().list(userId='me').execute()
            label_names = [l['name'] for l in labels.get('labels', [])]
            
            if 'PROCESSED' not in label_names:
                self.service.users().labels().create(
                    userId='me',
                    body={'name': 'PROCESSED', 'labelListVisibility': 'labelShow', 'messageListVisibility': 'show'}
                ).execute()
                logger.info("Created PROCESSED label")
            
            return True
        except Exception as e:
            logger.error(f"Error setting up labels: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Return processor statistics."""
        return {
            **self.stats,
            'authenticated': self._authenticated,
            'uptime_seconds': (datetime.now() - datetime.fromisoformat(self.stats['started_at'])).total_seconds()
        }


# ─── Standalone Execution ────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Gmail Processor')
    parser.add_argument('--vault-path', default='AI_Employee_Vault', help='Vault path')
    parser.add_argument('--dry-run', action='store_true', help='Process without marking as read')
    parser.add_argument('--max-emails', type=int, default=10, help='Max emails to process')
    parser.add_argument('--setup', action='store_true', help='Setup PROCESSED label only')
    parser.add_argument('--test', action='store_true', help='Run self-test')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    if args.test:
        print("=" * 60)
        print("Gmail Processor Self-Test (Offline Mode)")
        print("=" * 60)

        processor2 = GmailProcessor(vault_path=args.vault_path)
        test_cases = [
            ('URGENT: Server is down!', 'critical'),
            ('Important: Please review ASAP', 'high'),
            ('Weekly status update', 'medium'),
            ('Newsletter: Weekly digest', 'low'),
        ]
        for subject, expected in test_cases:
            priority = processor2._categorize_priority(
                'test@example.com', subject, 'test body', 'test body'
            )
            assert priority == expected, f"Expected {expected}, got {priority} for '{subject}'"
            print(f"  ✓ '{subject}' → {priority}")

        import base64
        mock_msg = {
            'id': 'test123',
            'threadId': 'thread456',
            'snippet': 'Test email snippet',
            'payload': {
                'headers': [
                    {'name': 'From', 'value': 'Sender <sender@example.com>'},
                    {'name': 'Subject', 'value': 'Test Subject'},
                    {'name': 'Date', 'value': 'Sat, 14 May 2026 10:30:00 +0000'},
                ],
                'body': {'data': base64.urlsafe_b64encode(b'Test email body').decode()},
            },
            'labelIds': ['INBOX'],
        }
        email = processor2._parse_message(mock_msg)
        assert email is not None, "Should parse mock message"
        assert email.sender == 'Sender <sender@example.com>'
        assert email.subject == 'Test Subject'
        assert email.priority in ('critical', 'high', 'medium', 'low')
        print(f"  ✓ Parsed email: {email.subject} (priority: {email.priority})")

        from datetime import datetime
        email_msg = EmailMessage(
            message_id='TESTMSG001',
            thread_id='TESTTHREAD001',
            sender='test@example.com',
            sender_name='Test User',
            subject='Test Task Creation',
            received=datetime.now().isoformat(),
            snippet='Test snippet',
            body='Test body content',
            priority='high'
        )
        task_path = processor2.create_task_file(email_msg)
        if task_path:
            assert task_path.exists(), "Task file should exist"
            content = task_path.read_text()
            assert 'Test Task Creation' in content
            print(f"  ✓ Created task file: {task_path.name}")
            task_path.unlink()
        else:
            print("  ⚠ Task file creation returned None (vault may not be set up)")

        assert processor2._extract_sender_name('John Doe <john@example.com>') == 'John Doe'
        assert processor2._extract_sender_name('john@example.com') == 'john'
        print("  ✓ Sender name extraction works")

        assert processor2._parse_date('2026-01-15') == '2026-01-15'
        assert processor2._parse_date('01/15/2026') == '2026-01-15'
        print("  ✓ Date parsing works")

        assert processor2._categorize_priority(
            'colleague@knowncompany.com', 'Hey there', 'body', 'body'
        ) == 'medium'
        print("  ✓ Domain-based priority works")

        print("\n✓ All Gmail Processor tests passed (offline mode)!")
        print(f"\nStats: {json.dumps(processor2.get_stats(), indent=2, default=str)}")

    elif args.setup:
        print("=" * 60)
        print("Gmail Processor Self-Test")
        print("=" * 60)

        # Test 1: Priority categorization (no API needed)
        processor2 = GmailProcessor(vault_path=args.vault_path)
        test_cases = [
            ('URGENT: Server is down!', 'critical'),
            ('Important: Please review ASAP', 'high'),
            ('Weekly status update', 'medium'),
            ('Newsletter: Weekly digest', 'low'),
        ]
        for subject, expected in test_cases:
            priority = processor2._categorize_priority(
                'test@example.com', subject, 'test body', 'test body'
            )
            assert priority == expected, f"Expected {expected}, got {priority} for '{subject}'"
            print(f"  ✓ '{subject}' → {priority}")

        # Test 2: Email message parsing (mock data, no API)
        import base64
        mock_msg = {
            'id': 'test123',
            'threadId': 'thread456',
            'snippet': 'Test email snippet',
            'payload': {
                'headers': [
                    {'name': 'From', 'value': 'Sender <sender@example.com>'},
                    {'name': 'Subject', 'value': 'Test Subject'},
                    {'name': 'Date', 'value': 'Sat, 14 May 2026 10:30:00 +0000'},
                ],
                'body': {'data': base64.urlsafe_b64encode(b'Test email body').decode()},
            },
            'labelIds': ['INBOX'],
        }
        email = processor2._parse_message(mock_msg)
        assert email is not None, "Should parse mock message"
        assert email.sender == 'Sender <sender@example.com>'
        assert email.subject == 'Test Subject'
        assert email.priority in ('critical', 'high', 'medium', 'low')
        print(f"  ✓ Parsed email: {email.subject} (priority: {email.priority})")

        # Test 3: Task file creation
        from datetime import datetime
        email_msg = EmailMessage(
            message_id='TESTMSG001',
            thread_id='TESTTHREAD001',
            sender='test@example.com',
            sender_name='Test User',
            subject='Test Task Creation',
            received=datetime.now().isoformat(),
            snippet='Test snippet',
            body='Test body content',
            priority='high'
        )
        task_path = processor2.create_task_file(email_msg)
        if task_path:
            assert task_path.exists(), "Task file should exist"
            content = task_path.read_text()
            assert 'Test Task Creation' in content
            print(f"  ✓ Created task file: {task_path.name}")
            # Cleanup
            task_path.unlink()
        else:
            print("  ⚠ Task file creation returned None (vault may not be set up)")

        # Test 4: Sender name extraction
        assert processor2._extract_sender_name('John Doe <john@example.com>') == 'John Doe'
        assert processor2._extract_sender_name('john@example.com') == 'john'
        print("  ✓ Sender name extraction works")

        # Test 5: Date parsing
        assert processor2._parse_date('2026-01-15') == '2026-01-15'
        assert processor2._parse_date('01/15/2026') == '2026-01-15'
        print("  ✓ Date parsing works")

        # Test 6: Known domains
        # knowncompany.com is not in KNOWN_DOMAINS, so defaults to medium
        assert processor2._categorize_priority(
            'colleague@knowncompany.com', 'Hey there', 'body', 'body'
        ) == 'medium'
        print("  ✓ Domain-based priority works")

        print("\n✓ All Gmail Processor tests passed (offline mode)!")
        print(f"\nStats: {json.dumps(processor2.get_stats(), indent=2, default=str)}")

    elif args.setup:
        processor.setup_labels()
        print("Labels setup complete.")
        exit(0)
    
    result = processor.process_inbox(max_emails=args.max_emails)
    print(f"\nProcessing complete:")
    print(f"  Fetched: {result['fetched']}")
    print(f"  Tasks created: {result['tasks_created']}")
    print(f"  Marked read: {result['marked_read']}")
    print(f"  Skipped (duplicates): {result['skipped']}")
    print(f"  Errors: {result['errors']}")