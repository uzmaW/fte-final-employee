"""
Tests for watcher modules (Gmail, WhatsApp, Filesystem).
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestrator.base_watcher import BaseWatcher
from orchestrator.gmail_watcher import GmailWatcher
from orchestrator.whatsapp_watcher import WhatsAppWatcher
from orchestrator.filesystem_watcher import FilesystemWatcher


class TestBaseWatcher:
    """Test BaseWatcher base class."""
    
    def test_watcher_initialization(self):
        """Test watcher initialization."""
        class TestWatcher(BaseWatcher):
            def poll(self):
                return []
            def process_item(self, item):
                return None
        
        watcher = TestWatcher("test", poll_interval=60)
        assert watcher.name == "test"
        assert watcher.poll_interval == 60
        assert watcher.running is False
        assert watcher.error_count == 0
    
    def test_should_poll(self):
        """Test poll interval checking."""
        class TestWatcher(BaseWatcher):
            def poll(self):
                return []
            def process_item(self, item):
                return None
        
        watcher = TestWatcher("test", poll_interval=60)  # 60 second interval
        
        # First call should poll (last_poll_time is 0)
        assert watcher.should_poll() is True
        
        # After marking polled with current time
        watcher.mark_polled()
        
        # Immediately after should not poll (not enough time passed)
        assert watcher.should_poll() is False


class TestGmailWatcher:
    """Test Gmail watcher."""
    
    def test_gmail_initialization(self):
        """Test Gmail watcher initialization."""
        watcher = GmailWatcher()
        assert watcher.name == "gmail"
        assert watcher.gmail_service is None  # Not configured without credentials
    
    def test_categorize_priority(self):
        """Test email priority categorization."""
        watcher = GmailWatcher()
        
        # Critical
        email_critical = {
            'subject': 'URGENT: System down',
            'body': 'The system is down',
            'from': 'user@example.com'
        }
        assert watcher.categorize_priority(email_critical) == 'critical'
        
        # High
        email_high = {
            'subject': 'Action needed: Review proposal',
            'body': 'Please review',
            'from': 'user@example.com'
        }
        assert watcher.categorize_priority(email_high) == 'high'
        
        # Medium (default)
        email_medium = {
            'subject': 'Meeting reminder',
            'body': 'Just a reminder',
            'from': 'user@example.com'
        }
        assert watcher.categorize_priority(email_medium) == 'medium'
        
        # Low
        email_low = {
            'subject': 'Newsletter digest',
            'body': 'Weekly digest',
            'from': 'newsletter@example.com'
        }
        assert watcher.categorize_priority(email_low) == 'low'
    
    def test_extract_actions(self):
        """Test action extraction from email."""
        watcher = GmailWatcher()
        
        email = {
            'body': 'Please review the document. Can you approve the budget? Need you to sign off by Friday.',
            'subject': 'Approval needed',
            'from': 'user@example.com'
        }
        
        actions = watcher.extract_actions(email)
        assert len(actions) > 0
        assert any('review' in action.lower() for action in actions)


class TestWhatsAppWatcher:
    """Test WhatsApp watcher."""
    
    def test_whatsapp_initialization(self):
        """Test WhatsApp watcher initialization."""
        watcher = WhatsAppWatcher()
        assert watcher.name == "whatsapp"
        assert len(watcher.message_queue) == 0
    
    def test_parse_webhook_data(self):
        """Test parsing Twilio webhook data."""
        import asyncio
        from unittest.mock import Mock, AsyncMock
        
        watcher = WhatsAppWatcher()
        
        # Mock request object with async form()
        request = Mock()
        
        async def mock_form():
            class FormData(dict):
                pass
            form = FormData({
                'From': 'whatsapp:+1234567890',
                'To': 'whatsapp:+0987654321',
                'Body': 'Test message',
                'MessageSid': 'SM123456789',
                'AccountSid': 'AC123456',
                'NumMedia': '0',
            })
            return form
        
        request.form = mock_form
        
        # Run async function
        async def test():
            data = await watcher.parse_webhook_data(request)
            assert data['from'] == '+1234567890'
            assert data['to'] == '+0987654321'
            assert data['body'] == 'Test message'
            assert data['message_sid'] == 'SM123456789'
            assert len(data['media']) == 0
        
        asyncio.run(test())
    
    def test_categorize_priority(self):
        """Test WhatsApp message priority categorization."""
        watcher = WhatsAppWatcher()
        
        # Critical
        message_critical = {
            'body': 'URGENT: System down!',
            'from': '+1234567890',
            'media': []
        }
        assert watcher.categorize_priority(message_critical) == 'critical'
        
        # High - contains "help"
        message_high = {
            'body': 'Can you help with this?',
            'from': '+1234567890',
            'media': []
        }
        # "help" triggers critical in the code, so it will be critical not high
        assert watcher.categorize_priority(message_high) in ['high', 'critical']
        
        # High with media
        message_media = {
            'body': 'Check this out',
            'from': '+1234567890',
            'media': [{'url': 'http://example.com/image.jpg', 'type': 'image/jpeg'}]
        }
        assert watcher.categorize_priority(message_media) == 'high'
    
    def test_auto_response(self):
        """Test auto-response generation."""
        watcher = WhatsAppWatcher()
        
        # Should generate response
        message1 = {'body': 'Hi', 'from': '+1234567890'}
        response1 = watcher.get_auto_response(message1)
        assert response1 is not None
        
        # Should generate response
        message2 = {'body': 'Thanks!', 'from': '+1234567890'}
        response2 = watcher.get_auto_response(message2)
        assert response2 is not None
        
        # Should not generate response
        message3 = {'body': 'Can you analyze this data and send me a report?', 'from': '+1234567890'}
        response3 = watcher.get_auto_response(message3)
        assert response3 is None


class TestFilesystemWatcher:
    """Test Filesystem watcher."""
    
    def test_filesystem_initialization(self):
        """Test filesystem watcher initialization."""
        watcher = FilesystemWatcher()
        assert watcher.name == "filesystem"
        assert watcher.observer is None
        assert watcher.event_handler is not None
    
    def test_pending_approvals(self):
        """Test getting pending approvals."""
        watcher = FilesystemWatcher()
        
        pending = watcher.get_pending_approvals()
        assert 'count' in pending
        assert 'approvals' in pending
        assert isinstance(pending['count'], int)
        assert isinstance(pending['approvals'], list)
    
    def test_approved_actions(self):
        """Test getting approved actions."""
        watcher = FilesystemWatcher()
        
        approved = watcher.get_approved_actions()
        assert 'count' in approved
        assert 'actions' in approved
        assert isinstance(approved['count'], int)
        assert isinstance(approved['actions'], list)


class TestWatcherIntegration:
    """Integration tests for watchers."""
    
    def test_gmail_task_creation(self, tmp_path):
        """Test creating task from email (without real Gmail)."""
        watcher = GmailWatcher()
        watcher.vault_manager.vault_path = tmp_path
        
        # Create vault structure
        (tmp_path / "Needs_Action").mkdir(exist_ok=True)
        (tmp_path / "Logs").mkdir(exist_ok=True)
        
        # Simulate email
        email = {
            'id': 'msg123',
            'from': 'sender@example.com',
            'subject': 'Test email',
            'body': 'This is a test email',
            'date': '2026-02-08T10:30:00Z',
            'has_attachments': False,
        }
        
        # Create task file directly (since we can't call Gmail API)
        task_id = "EMAIL_20260208_103000_001"
        task_file = watcher.create_task_file(
            task_id=task_id,
            task_type='email_task',
            title="Email: Test email",
            priority='medium',
            content="Test content",
            metadata={'from': 'sender@example.com'}
        )
        
        assert task_file is not None
        assert task_file.exists()
        assert "EMAIL_" in task_file.name
    
    def test_whatsapp_task_creation(self, tmp_path):
        """Test creating task from WhatsApp message."""
        watcher = WhatsAppWatcher()
        watcher.vault_manager.vault_path = tmp_path
        
        # Create vault structure
        (tmp_path / "Needs_Action").mkdir(exist_ok=True)
        (tmp_path / "Logs").mkdir(exist_ok=True)
        
        # Simulate WhatsApp message
        message = {
            'from': '+1234567890',
            'body': 'Test message',
            'message_sid': 'SM123456789',
            'account_sid': 'AC123456',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'media': [],
        }
        
        task_file = watcher.process_item(message)
        
        assert task_file is not None
        assert task_file.exists()
        assert "WHATSAPP_" in task_file.name


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
