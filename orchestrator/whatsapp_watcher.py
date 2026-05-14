"""
WhatsApp watcher - receives messages via Twilio webhooks and creates task files.
Requires Twilio account with WhatsApp integration configured.
"""

import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from fastapi import FastAPI, Request
import hmac
import hashlib

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestrator.base_watcher import BaseWatcher

logger = logging.getLogger(__name__)


class WhatsAppWatcher(BaseWatcher):
    """Handle WhatsApp messages via Twilio webhook."""
    
    def __init__(self, app: Optional[FastAPI] = None):
        """
        Initialize WhatsApp watcher.
        
        Args:
            app: FastAPI app for webhook endpoint
        """
        # Initialize settings first
        from config import get_settings
        from utilities.vault_manager import VaultManager
        settings = get_settings()
        
        super().__init__(
            name="whatsapp",
            poll_interval=settings.whatsapp_poll_interval
        )
        
        # Message queue for webhook-based processing
        self.message_queue: List[Dict[str, Any]] = []
        
        # Setup FastAPI webhook if provided
        self.app = app
        if app:
            self.register_webhook()
    
    def register_webhook(self):
        """Register FastAPI route for Twilio webhook."""
        if not self.app:
            return
        
        @self.app.post('/webhooks/whatsapp')
        async def whatsapp_webhook(request: Request):
            """Handle incoming WhatsApp message webhook."""
            try:
                # Validate Twilio signature
                if not await self.validate_twilio_request(request):
                    logger.warning("Invalid Twilio signature")
                    return {"status": "error", "message": "Unauthorized"}, 401
                
                # Parse message
                message_data = await self.parse_webhook_data(request)
                
                # Queue for processing
                self.message_queue.append(message_data)
                logger.info(f"Queued WhatsApp message from {message_data.get('from')}")
                
                return {"status": "ok"}, 200
                
            except Exception as e:
                logger.error(f"Webhook error: {e}", exc_info=True)
                return {"status": "error"}, 500
    
    async def validate_twilio_request(self, request: Request) -> bool:
        """
        Validate Twilio webhook signature.
        
        Args:
            request: FastAPI request object
            
        Returns:
            True if signature is valid
        """
        try:
            # Get signature from header
            twilio_signature = request.headers.get('X-Twilio-Signature', '')
            if not twilio_signature:
                return False
            
            # Construct validation string
            url = str(request.url)
            body = await request.body()
            form_data = await request.form()
            
            # Create message string
            message = url
            for key in sorted(form_data.keys()):
                message += key + form_data[key]
            
            # Generate HMAC
            auth_token = self.settings.twilio_auth_token
            if not auth_token:
                logger.warning("Twilio auth token not configured")
                return False
            
            expected_hash = hmac.new(
                auth_token.encode(),
                message.encode(),
                hashlib.sha1
            ).digest()
            expected_signature = str(
                hashlib.new('sha1', expected_hash).hexdigest()
            )
            
            # Compare signatures
            return twilio_signature == expected_signature
            
        except Exception as e:
            logger.error(f"Signature validation error: {e}")
            return False
    
    async def parse_webhook_data(self, request: Request) -> Dict[str, Any]:
        """
        Parse Twilio webhook data.
        
        Args:
            request: FastAPI request object
            
        Returns:
            Parsed message dictionary
        """
        form_data = await request.form()
        
        # Extract message info
        message_data = {
            'from': form_data.get('From', '').replace('whatsapp:', ''),
            'to': form_data.get('To', '').replace('whatsapp:', ''),
            'body': form_data.get('Body', ''),
            'message_sid': form_data.get('MessageSid', ''),
            'account_sid': form_data.get('AccountSid', ''),
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'media': [],
        }
        
        # Handle media attachments
        num_media = int(form_data.get('NumMedia', 0))
        if num_media > 0:
            for i in range(num_media):
                media_url = form_data.get(f'MediaUrl{i}')
                media_type = form_data.get(f'MediaContentType{i}')
                if media_url:
                    message_data['media'].append({
                        'url': media_url,
                        'type': media_type,
                        'index': i,
                    })
        
        return message_data
    
    def poll(self) -> List[Dict[str, Any]]:
        """
        Get queued WhatsApp messages (from webhook).
        
        Returns:
            List of queued messages
        """
        if not self.message_queue:
            return []
        
        messages = self.message_queue.copy()
        self.message_queue.clear()
        logger.debug(f"Processing {len(messages)} queued messages")
        return messages
    
    def categorize_priority(self, message: Dict[str, Any]) -> str:
        """
        Determine message priority based on content and sender.
        
        Args:
            message: Message dictionary
            
        Returns:
            Priority level: critical, high, medium, low
        """
        body = message.get('body', '').lower()
        sender = message.get('from', '').lower()
        
        # Critical indicators
        critical_keywords = ['urgent', 'emergency', 'help', 'down', 'crisis', '!!!']
        if any(kw in body for kw in critical_keywords):
            return 'critical'
        
        # High priority indicators
        high_keywords = ['important', 'need help', 'question', 'decision', 'approval']
        if any(kw in body for kw in high_keywords):
            return 'high'
        
        # Check known contacts (would be configurable)
        known_critical_contacts = [
            '+1234567890',  # CEO, etc.
        ]
        if sender in known_critical_contacts:
            return 'high'
        
        # Has media attachment = higher priority
        if message.get('media'):
            return 'high'
        
        return 'medium'
    
    def send_response(self, phone_number: str, message_text: str) -> bool:
        """
        Send response via WhatsApp.
        
        Args:
            phone_number: Recipient phone number
            message_text: Message to send
            
        Returns:
            True if successful
        """
        try:
            # In production, use Twilio client:
            # self.twilio_client.messages.create(
            #     from_=f"whatsapp:{self.settings.twilio_phone_number}",
            #     to=f"whatsapp:{phone_number}",
            #     body=message_text
            # )
            
            logger.info(f"Sent response to {phone_number}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending response: {e}")
            return False
    
    def get_auto_response(self, message: Dict[str, Any]) -> Optional[str]:
        """
        Generate automatic response for common queries.
        
        Args:
            message: Message dictionary
            
        Returns:
            Response text or None
        """
        body = message.get('body', '').lower().strip()
        
        # Common patterns
        if body in ['hi', 'hello', 'hey', 'whats up', 'status?']:
            return "Hi! I'm here and ready to help. What do you need?"
        
        if 'help' in body:
            return "Of course! Tell me what you need and I'll take care of it."
        
        if any(word in body for word in ['thanks', 'thank you', 'thx', 'ty']):
            return "Happy to help! 👍"
        
        # No auto-response for other messages
        return None
    
    def process_item(self, message: Dict[str, Any]) -> Optional[str]:
        """
        Process a WhatsApp message and create task file.
        
        Args:
            message: Message dictionary from webhook
            
        Returns:
            Path to created task file
        """
        try:
            phone = message.get('from')
            body = message.get('body', '')
            message_sid = message.get('message_sid')
            
            logger.info(f"Processing WhatsApp from {phone}: {body[:50]}")
            
            # Send auto-response if applicable
            auto_response = self.get_auto_response(message)
            if auto_response:
                self.send_response(phone, auto_response)
            
            # Determine priority
            priority = self.categorize_priority(message)
            
            # Generate task ID
            task_id = f"WHATSAPP_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_001"
            
            # Build content
            media_section = ""
            if message.get('media'):
                media_section = "\n## Attachments\n"
                for i, media in enumerate(message['media'], 1):
                    media_type = media.get('type', 'unknown')
                    media_section += f"- [{media_type}]({media['url']})\n"
            
            content = f"""**From:** {phone}  
**Received:** {message.get('timestamp')}  
**Priority:** {priority}  

## Message

{body}
{media_section}

## Action Required

Respond to {phone}

---

Message SID: {message_sid}"""
            
            # Build metadata
            metadata = {
                'phone': phone,
                'message_sid': message_sid,
                'has_media': len(message.get('media', [])) > 0,
            }
            
            # Create task file
            task_file = self.create_task_file(
                task_id=task_id,
                task_type='whatsapp_task',
                title=f"WhatsApp from {phone}",
                priority=priority,
                content=content,
                metadata=metadata
            )
            
            return task_file
            
        except Exception as e:
            logger.error(f"Error processing WhatsApp message: {e}", exc_info=True)
            return None


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    
    # For testing without Flask
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        watcher = WhatsAppWatcher()
        
        # Simulate a message
        test_message = {
            'from': '+1234567890',
            'to': '+0987654321',
            'body': 'Hi, this is a test message',
            'message_sid': 'SM123456789',
            'account_sid': 'AC123456',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'media': [],
        }
        
        task_file = watcher.process_item(test_message)
        print(f"Created task: {task_file}")
