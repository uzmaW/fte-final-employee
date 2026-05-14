"""
whatsapp_handler.py - WhatsApp message handler with full processing pipeline.

Backs the .claude/skills/whatsapp-handler/SKILL.md specification.
Handles incoming WhatsApp messages via Twilio webhooks and creates actionable task files.
"""

import os
import re
import json
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
import hmac
import hashlib

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config import get_settings
from utilities.vault_manager import VaultManager
from utilities.retry_handler import with_retry, TransientError

logger = logging.getLogger(__name__)


@dataclass
class WhatsAppMessage:
    """Represents a WhatsApp message."""
    message_sid: str
    from_number: str
    to_number: str
    body: str
    timestamp: str
    num_media: int = 0
    media_urls: List[str] = field(default_factory=list)
    media_types: List[str] = field(default_factory=list)
    sender_name: str = ""
    priority: str = "medium"
    categories: List[str] = field(default_factory=list)
    requires_response: bool = True


class WhatsAppWebhookHandler(BaseHTTPRequestHandler):
    """HTTP handler for Twilio WhatsApp webhooks."""
    
    processor = None  # Set to WhatsAppHandler instance
    
    def log_message(self, format, *args):
        """Custom logging for HTTP requests."""
        logger.info(f"[Webhook] {args[0]}")
    
    def do_POST(self):
        """Handle incoming POST requests from Twilio."""
        if self.path != '/webhooks/whatsapp':
            self.send_error(404)
            return
        
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            form_data = {}
            
            # Parse URL-encoded form data
            for pair in post_data.decode('utf-8').split('&'):
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    import urllib.parse
                    form_data[key] = urllib.parse.unquote_plus(value)
            
            # Verify signature
            if self.processor and not self.processor.verify_signature(form_data):
                logger.warning("Invalid Twilio signature")
                self.send_response(401)
                self.end_headers()
                self.wfile.write(b'Unauthorized')
                return
            
            # Process message
            if self.processor:
                result = self.processor.handle_webhook(form_data)
                if result:
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b'OK')
                else:
                    self.send_response(500)
                    self.end_headers()
                    self.wfile.write(b'Error')
            else:
                self.send_response(503)
                self.end_headers()
                self.wfile.write(b'No processor configured')
                
        except Exception as e:
            logger.error(f"Webhook error: {e}", exc_info=True)
            try:
                self.send_response(500)
                self.end_headers()
            except Exception:
                pass


class WhatsAppHandler:
    """
    WhatsApp message handler for the AI Employee system.
    
    Handles:
    - Receiving WhatsApp messages via Twilio webhooks
    - Parsing and prioritizing messages
    - Creating task files in the vault
    - Auto-responding to common queries
    - Media attachment handling
    """
    
    # Auto-response triggers
    AUTO_RESPONSES = {
        'hello': "Hi there! 👋 I'm your AI assistant. How can I help you today?",
        'hi': "Hello! 😊 I'm ready to assist. What do you need?",
        'hey': "Hey! What's up?",
        'thanks': "You're welcome! Happy to help. 😊",
        'thank you': "You're welcome! Glad I could help. 😊",
        'thx': "No problem! 👍",
        'status': "I'm active and ready to help. What's the status you'd like to check?",
        'help': "Of course! Tell me what you need and I'll take care of it. I can help with:\n• Business inquiries\n• Scheduling\n• Information lookups\n• File requests\n• General questions",
        'good morning': "Good morning! ☀️ Ready to start the day. How can I assist?",
        'good evening': "Good evening! 🌙 How was your day? How can I help?",
        'what can you do': "I can help with:\n📧 Processing emails\n💬 WhatsApp messages\n📊 Financial analysis\n📋 Task management\n📅 Scheduling\n\nJust let me know what you need!",
        'busy': "I'm currently processing some tasks, but I'll get back to you shortly!",
        'bye': "Goodbye! Have a great day! 👋",
        'goodbye': "See you later! Take care! 👋",
    }
    
    # Priority keywords
    CRITICAL_KEYWORDS = [
        'urgent', 'emergency', 'help', 'critical', 'down', 'broken',
        'asap', 'right away', 'immediately', 'fire', 'crisis', '!!!', '!!!'
    ]
    HIGH_KEYWORDS = [
        'important', 'need help', 'question', 'decision', 'approval',
        'please send', 'can you', 'need to', 'must', 'required',
        'invoice', 'payment', 'deadline', 'today', 'tomorrow'
    ]
    MEDIUM_KEYWORDS = [
        'update', 'fyi', 'status', 'when', 'where', 'how',
        'reminder', 'follow up', 'check', 'confirm', 'verify'
    ]
    
    # Known contact phone numbers and their classifications
    KNOWN_CONTACTS = {}
    
    def __init__(self, vault_path: str = None, webhook_port: int = 8080):
        """
        Initialize WhatsApp handler.
        
        Args:
            vault_path: Path to Obsidian vault
            webhook_port: Port for the webhook server
        """
        self.settings = get_settings()
        self.vault_path = Path(vault_path) if vault_path else self.settings.vault_path
        self.vault_manager = VaultManager()
        self.webhook_port = webhook_port
        
        # Twilio credentials
        self.twilio_account_sid = self.settings.twilio_account_sid
        self.twilio_auth_token = self.settings.twilio_auth_token
        self.twilio_phone_number = self.settings.twilio_phone_number
        
        # Stats
        self.stats = {
            'messages_processed': 0,
            'auto_responses_sent': 0,
            'tasks_created': 0,
            'errors': 0,
            'last_message': None,
            'started_at': datetime.now().isoformat()
        }
        
        # Webhook server
        self._server = None
        self._server_thread = None
        self._running = False
    
    def verify_signature(self, form_data: Dict[str, str]) -> bool:
        """
        Verify Twilio webhook signature for security.
        
        Args:
            form_data: Parsed form data from the request
            
        Returns:
            True if signature is valid
        """
        if not self.twilio_auth_token:
            logger.warning("No Twilio auth token configured, skipping signature verification")
            return True
        
        twilio_signature = form_data.get('X-Twilio-Signature', '')
        if not twilio_signature:
            logger.warning("No Twilio signature in request")
            return False
        
        # Build the validation URL and parameters
        # The URL should match what Twilio sends to
        from urllib.parse import urlencode
        
        sorted_keys = sorted(form_data.keys())
        param_string = ''.join(f'{k}{form_data[k]}' for k in sorted_keys if k != 'X-Twilio-Signature')
        
        # Validate using the request URL
        expected = hmac.new(
            self.twilio_auth_token.encode('utf-8'),
            param_string.encode('utf-8'),
            hashlib.sha1
        ).digest()
        expected_sig = hashlib.new('sha1', expected).hexdigest()
        
        return hmac.compare_digest(expected_sig, twilio_signature)
    
    def handle_webhook(self, form_data: Dict[str, str]) -> bool:
        """
        Process an incoming Twilio webhook payload.
        
        Args:
            form_data: Parsed form data from webhook
            
        Returns:
            True if processed successfully
        """
        try:
            message = self._parse_webhook(form_data)
            if not message:
                return False
            
            # Categorize priority
            message.priority = self._categorize_priority(message)
            
            # Create task file
            task_file = self.create_task_file(message)
            if task_file:
                self.stats['tasks_created'] += 1
                logger.info(f"Created task: {task_file}")
            
            # Try auto-response
            auto_response = self.get_auto_response(message)
            if auto_response:
                self._send_response(message.from_number, auto_response)
                self.stats['auto_responses_sent'] += 1
            
            self.stats['messages_processed'] += 1
            self.stats['last_message'] = datetime.now().isoformat()
            
            return True
            
        except Exception as e:
            logger.error(f"Error handling webhook: {e}", exc_info=True)
            self.stats['errors'] += 1
            return False
    
    def _parse_webhook(self, form_data: Dict[str, str]) -> Optional[WhatsAppMessage]:
        """Parse Twilio webhook form data into a WhatsAppMessage."""
        try:
            message_sid = form_data.get('MessageSid', '')
            from_number = form_data.get('From', '').replace('whatsapp:', '')
            to_number = form_data.get('To', '').replace('whatsapp:', '')
            body = form_data.get('Body', '')
            
            # Handle media
            num_media = int(form_data.get('NumMedia', 0))
            media_urls = []
            media_types = []
            for i in range(num_media):
                url = form_data.get(f'MediaUrl{i}')
                content_type = form_data.get(f'MediaContentType{i}')
                if url:
                    media_urls.append(url)
                    media_types.append(content_type or 'unknown')
            
            return WhatsAppMessage(
                message_sid=message_sid,
                from_number=from_number,
                to_number=to_number,
                body=body,
                timestamp=datetime.now().isoformat(),
                num_media=num_media,
                media_urls=media_urls,
                media_types=media_types
            )
        except Exception as e:
            logger.error(f"Error parsing webhook: {e}")
            return None
    
    def _categorize_priority(self, message: WhatsAppMessage) -> str:
        """Determine message priority."""
        text = f"{message.body} {message.from_number}".lower()
        
        # Check critical keywords
        for kw in self.CRITICAL_KEYWORDS:
            if kw in text:
                return 'critical'
        
        # Check high keywords
        for kw in self.HIGH_KEYWORDS:
            if kw in text:
                return 'high'
        
        # Check medium keywords
        for kw in self.MEDIUM_KEYWORDS:
            if kw in text:
                return 'medium'
        
        # Check known contacts
        if message.from_number in self.KNOWN_CONTACTS:
            contact_priority = self.KNOWN_CONTACTS[message.from_number]
            if contact_priority == 'critical':
                return 'critical'
            elif contact_priority == 'high':
                return 'high'
        
        # Media messages are higher priority
        if message.num_media > 0:
            return 'high'
        
        return 'medium'
    
    def get_auto_response(self, message: WhatsAppMessage) -> Optional[str]:
        """
        Generate automatic response for common queries.
        
        Args:
            message: Incoming WhatsApp message
            
        Returns:
            Response text or None if no auto-response matches
        """
        body_lower = message.body.strip().lower()
        
        # Exact match first
        if body_lower in self.AUTO_RESPONSES:
            return self.AUTO_RESPONSES[body_lower]
        
        # Partial match
        for trigger, response in self.AUTO_RESPONSES.items():
            if trigger in body_lower:
                return response
        
        return None
    
    def _send_response(self, phone_number: str, message_text: str) -> bool:
        """
        Send a WhatsApp response using Twilio API.
        
        Args:
            phone_number: Recipient phone number
            message_text: Message to send
            
        Returns:
            True if successful
        """
        if not self.twilio_account_sid or not self.twilio_auth_token:
            logger.warning("Twilio credentials not configured, cannot send response")
            return False
        
        try:
            from twilio.rest import Client
            
            client = Client(self.twilio_account_sid, self.twilio_auth_token)
            
            message = client.messages.create(
                from_=f"whatsapp:{self.twilio_phone_number}",
                body=message_text,
                to=f"whatsapp:{phone_number}"
            )
            
            logger.info(f"Sent WhatsApp response to {phone_number}: {message.sid}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending WhatsApp response: {e}")
            return False
    
    def create_task_file(self, message: WhatsAppMessage) -> Optional[Path]:
        """
        Create a task file in the vault Needs_Action folder.
        
        Args:
            message: Parsed WhatsApp message
            
        Returns:
            Path to created task file or None
        """
        try:
            timestamp = message.timestamp
            task_id = f"WHATSAPP_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{message.message_sid[:8]}"
            
            # Format media section
            media_section = ""
            if message.num_media > 0 and message.media_urls:
                media_section = "\n## Attachments\n"
                for i, (url, media_type) in enumerate(zip(message.media_urls, message.media_types)):
                    media_section += f"- [{media_type}]({url})\n"
            
            # Format auto-response suggestion
            auto_response = self.get_auto_response(message)
            auto_response_section = ""
            if auto_response:
                auto_response_section = f"\n**Suggested Auto-Response:**\n> {auto_response}"
            
            # Build content
            content = f"""## WhatsApp Message

**From:** {message.from_number}
**To:** {message.to_number}
**Timestamp:** {timestamp}
**Priority:** {message.priority.upper()}
**Message SID:** {message.message_sid}
**Media Count:** {message.num_media}

## Message Content

{message.body}

{media_section}
{auto_response_section}

## Suggested Actions

- [ ] Read and categorize the message
- [ ] Determine appropriate response
- [ ] Respond via WhatsApp (requires approval for sensitive content)
- [ ] Create follow-up task if needed
- [ ] Archive after processing

---

*Captured by WhatsAppHandler | Priority: {message.priority}*
"""
            
            metadata = {
                'type': 'whatsapp_task',
                'priority': message.priority,
                'source': 'whatsapp_twilio',
                'created': timestamp,
                'message_sid': message.message_sid,
                'from': message.from_number,
                'has_media': str(message.num_media > 0).lower()
            }
            
            filename = f"{task_id}.md"
            filepath = self.vault_path / 'Needs_Action' / filename
            
            # Write with YAML frontmatter
            yaml_lines = ['---']
            for key, value in metadata.items():
                val_str = str(value)
                if any(c in val_str for c in ':{}[]&*#?|-<>=!%@\\'):
                    val_str = f'"{val_str}"'
                yaml_lines.append(f'{key}: {val_str}')
            yaml_lines.append('---')
            
            filepath.write_text('\n'.join(yaml_lines) + '\n\n' + content)
            
            # Log event
            self.vault_manager.log_event(
                event_type='whatsapp_processed',
                task_id=task_id,
                details={'priority': message.priority, 'from': message.from_number}
            )
            
            logger.info(f"Created WhatsApp task: {filename}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error creating WhatsApp task file: {e}")
            self.stats['errors'] += 1
            return None
    
    def process_batch(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Process multiple webhook payloads in batch.
        
        Args:
            messages: List of webhook form data dictionaries
            
        Returns:
            Processing results summary
        """
        result = {
            'processed': 0,
            'tasks_created': 0,
            'auto_responses': 0,
            'errors': 0
        }
        
        for form_data in messages:
            if self.handle_webhook(form_data):
                result['processed'] += 1
                if self.stats['tasks_created'] > result['tasks_created']:
                    result['tasks_created'] += 1
                if self.stats['auto_responses_sent'] > result['auto_responses']:
                    result['auto_responses'] += 1
            else:
                result['errors'] += 1
        
        return result
    
    def start_webhook_server(self, host: str = '0.0.0.0', port: int = None):
        """
        Start the HTTP webhook server.
        
        Args:
            host: Bind address
            port: Port to listen on (defaults to self.webhook_port)
        """
        port = port or self.webhook_port
        
        # Set class variable for handler
        WhatsAppWebhookHandler.processor = self
        
        self._server = HTTPServer((host, port), WhatsAppWebhookHandler)
        self._running = True
        
        logger.info(f"WhatsApp webhook server starting on {host}:{port}")
        
        # Run in background thread
        self._server_thread = Thread(target=self._server.serve_forever)
        self._server_thread.daemon = True
        self._server_thread.start()
        
        logger.info("WhatsApp webhook server running")
    
    def stop_webhook_server(self):
        """Stop the HTTP webhook server."""
        if self._server:
            self._server.shutdown()
            self._server = None
            self._running = False
            logger.info("WhatsApp webhook server stopped")
    
    def run(self):
        """Keep handler alive (for daemon mode)."""
        self._running = True
        logger.info(f"WhatsApp handler running. Processing messages...")
        
        try:
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("WhatsApp handler interrupted")
        finally:
            self.stop_webhook_server()
    
    def get_stats(self) -> Dict[str, Any]:
        """Return handler statistics."""
        return {
            **self.stats,
            'webhook_running': self._running,
            'webhook_port': self.webhook_port,
            'auto_responses_available': len(self.AUTO_RESPONSES)
        }


# ─── Standalone Execution ────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='WhatsApp Handler')
    parser.add_argument('--vault-path', default='AI_Employee_Vault', help='Vault path')
    parser.add_argument('--port', type=int, default=8080, help='Webhook port')
    parser.add_argument('--daemon', action='store_true', help='Run as daemon')
    parser.add_argument('--test', action='store_true', help='Run self-test')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    handler = WhatsAppHandler(vault_path=args.vault_path, webhook_port=args.port)
    
    if args.test:
        print("=" * 60)
        print("WhatsApp Handler Self-Test")
        print("=" * 60)
        
        # Test webhook parsing
        test_form = {
            'MessageSid': 'SM_TEST123456789',
            'From': '+1234567890',
            'To': '+0987654321',
            'Body': 'Test urgent message about the invoice',
            'NumMedia': '0'
        }
        
        result = handler.handle_webhook(test_form)
        print(f"✓ Webhook processed: {result}")
        
        # Test priority categorization
        msg = WhatsAppMessage(
            message_sid='SM_TEST',
            from_number='+1234567890',
            to_number='+0987654321',
            body='URGENT: Server is down!',
            timestamp=datetime.now().isoformat()
        )
        priority = handler._categorize_priority(msg)
        assert priority == 'critical', f"Expected critical, got {priority}"
        print(f"✓ Priority 'critical' detected correctly")
        
        msg.body = 'Hey, can you check the status of our project?'
        priority = handler._categorize_priority(msg)
        assert priority == 'high', f"Expected high, got {priority}"
        print(f"✓ Priority 'high' detected correctly")

        # Low priority test
        msg.body = 'Random FYI update, no action needed'
        priority = handler._categorize_priority(msg)
        assert priority == 'medium', f"Expected medium, got {priority}"
        print(f"✓ Priority 'medium' detected correctly")
        
        # Test auto-response
        msg.body = 'hello'
        response = handler.get_auto_response(msg)
        assert response is not None, "Expected auto-response"
        print(f"✓ Auto-response triggered: '{response[:30]}...'")
        
        msg.body = 'thanks for your help'
        response = handler.get_auto_response(msg)
        assert response is not None, "Expected auto-response"
        print(f"✓ Auto-response for 'thanks': '{response[:30]}...'")
        
        # Check stats
        print(f"\nStats: {json.dumps(handler.get_stats(), indent=2, default=str)}")
        print("\n✓ All WhatsApp Handler tests passed!")
    
    elif args.daemon:
        print(f"Starting WhatsApp Handler on port {args.port}...")
        print(f"Webhook URL: http://<your-server>:{args.port}/webhooks/whatsapp")
        handler.run()
    
    else:
        # One-shot test mode
        print("Run with --test for self-test or --daemon for server mode")