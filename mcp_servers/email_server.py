"""
Email MCP Server - Send emails via SMTP.
Handles email composition, sending, and tracking.
"""

import logging
import smtplib
from email.mime.text import MIMEText
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional, List
from datetime import datetime

from config import get_settings
from utilities.vault_manager import VaultManager

logger = logging.getLogger(__name__)


class EmailServer:
    """Send emails and manage email operations."""
    
    def __init__(self):
        """Initialize email server."""
        self.settings = get_settings()
        self.vault_manager = VaultManager()
        
        # Email configuration (would come from .env)
        self.smtp_host = "smtp.gmail.com"
        self.smtp_port = 587
        self.sender_email = None  # Would be set from config
        self.sender_password = None  # Would be set from config
    
    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        html: bool = False,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        attachments: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Send an email.
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body
            html: Whether body is HTML
            cc: CC recipients
            bcc: BCC recipients
            attachments: File paths to attach
            
        Returns:
            Result dict with status and message ID
        """
        try:
            if not self.sender_email:
                raise ValueError("Email not configured (check .env)")
            
            # Create message
            message = MIMEMultipart('alternative')
            message['Subject'] = subject
            message['From'] = self.sender_email
            message['To'] = to
            
            if cc:
                message['Cc'] = ', '.join(cc)
            
            # Add body
            mime_type = 'html' if html else 'plain'
            message.attach(MIMEText(body, mime_type))
            
            # Add attachments
            if attachments:
                for attachment_path in attachments:
                    self._attach_file(message, attachment_path)
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                
                recipients = [to]
                if cc:
                    recipients.extend(cc)
                if bcc:
                    recipients.extend(bcc)
                
                server.sendmail(self.sender_email, recipients, message.as_string())
            
            # Log event
            message_id = f"EMAIL_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            self.vault_manager.log_event(
                event_type="email_sent",
                task_id=message_id,
                details={
                    'to': to,
                    'subject': subject,
                    'cc': cc or [],
                    'bcc': bcc or [],
                },
                agent="email_server"
            )
            
            logger.info(f"Email sent to {to}: {subject}")
            
            return {
                'status': 'success',
                'message_id': message_id,
                'recipient': to,
                'timestamp': datetime.utcnow().isoformat() + 'Z',
            }
            
        except Exception as e:
            logger.error(f"Error sending email: {e}", exc_info=True)
            
            return {
                'status': 'error',
                'error': str(e),
                'recipient': to,
                'timestamp': datetime.utcnow().isoformat() + 'Z',
            }
    
    def _attach_file(self, message: MIMEMultipart, file_path: str):
        """Attach a file to email."""
        try:
            from email.mime.base import MIMEBase
            from email import encoders
            import os
            
            with open(file_path, 'rb') as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
            
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {os.path.basename(file_path)}',
            )
            message.attach(part)
            
        except Exception as e:
            logger.error(f"Error attaching file {file_path}: {e}")
    
    def send_reply(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        """
        Send a reply email (auto-adds "Re:" prefix).
        
        Args:
            to: Recipient email
            subject: Original subject
            body: Reply body
            
        Returns:
            Result dict
        """
        reply_subject = f"Re: {subject}" if not subject.startswith("Re:") else subject
        return self.send_email(to=to, subject=reply_subject, body=body)
    
    def send_notification(self, to: str, title: str, message: str) -> Dict[str, Any]:
        """
        Send a notification email.
        
        Args:
            to: Recipient email
            title: Notification title
            message: Notification message
            
        Returns:
            Result dict
        """
        body = f"""
{title}

{message}

---
Sent by AI Employee System
{datetime.utcnow().isoformat()}Z
"""
        return self.send_email(to=to, subject=f"Notification: {title}", body=body)


if __name__ == "__main__":
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    server = EmailServer()
    
    # Test sending email (requires configuration)
    # result = server.send_email(
    #     to="test@example.com",
    #     subject="Test Email",
    #     body="This is a test email"
    # )
    # print(result)
