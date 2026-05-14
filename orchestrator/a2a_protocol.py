"""
a2a_protocol.py - Agent-to-Agent (A2A) communication protocol.

From the hackathon PDF Platinum Tier, Phase 2:
  "Optional A2A Upgrade (Phase 2): Replace some file handoffs with direct A2A messages
   later, while keeping the vault as the audit record."

This module provides a framework for direct agent communication using:
1. Message-based protocol with structured envelopes
2. Discovery mechanism for finding other agents
3. Request-Response and Publish-Subscribe patterns
4. Vault-backed audit trail for all A2A communications
"""

import json
import uuid
import time
import logging
import hashlib
import hmac
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_settings

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """A2A message types."""
    REQUEST = "request"
    RESPONSE = "response"
    PUBLISH = "publish"
    SUBSCRIBE = "subscribe"
    EVENT = "event"
    ACK = "ack"
    ERROR = "error"
    HEARTBEAT = "heartbeat"
    DISCOVER = "discover"


class Priority(Enum):
    """Message priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class A2AMessage:
    """Structured A2A message envelope."""
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    message_type: str = MessageType.REQUEST.value
    sender_id: str = ""
    sender_name: str = ""
    recipient_id: str = ""
    recipient_name: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    priority: str = Priority.NORMAL.value
    ttl_seconds: int = 3600  # Time to live
    correlation_id: str = ""  # For request-response correlation
    payload: Dict[str, Any] = field(default_factory=dict)
    signature: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentEndpoint:
    """Represents a discoverable agent endpoint."""
    agent_id: str
    agent_name: str
    capabilities: List[str]
    address: str  # Could be a file path, URL, or queue name
    last_seen: str = ""
    status: str = "online"
    metadata: Dict[str, Any] = field(default_factory=dict)


class A2AProtocol:
    """
    Agent-to-Agent communication protocol.
    
    Supports multiple transport mechanisms:
    1. File-based (vault-backed) - for local agents
    2. HTTP-based - for distributed agents
    3. Queue-based - for async communication
    """
    
    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        vault_path: Optional[Path] = None,
        capabilities: Optional[List[str]] = None,
        transport: str = "file"
    ):
        """
        Initialize A2A protocol for an agent.
        
        Args:
            agent_id: Unique identifier for this agent
            agent_name: Human-readable agent name
            vault_path: Path to shared vault (for file-based transport)
            capabilities: List of capabilities this agent offers
            transport: 'file', 'http', or 'queue'
        """
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.vault_path = Path(vault_path) if vault_path else None
        self.capabilities = capabilities or []
        self.transport = transport
        self.settings = get_settings()
        
        # Agent registry - tracks known agents
        self._registry: Dict[str, AgentEndpoint] = {}
        
        # Message handlers
        self._handlers: Dict[str, Callable] = {}
        
        # Pending requests awaiting response
        self._pending_requests: Dict[str, Dict[str, Any]] = {}
        
        # Message inbox (for file-based transport)
        self._inbox_dir = self.vault_path / 'A2A_Inbox' if self.vault_path else None
        self._outbox_dir = self.vault_path / 'A2A_Outbox' if self.vault_path else None
        self._audit_dir = self.vault_path / 'A2A_Audit' if self.vault_path else None
        
        if self.vault_path:
            for d in [self._inbox_dir, self._outbox_dir, self._audit_dir]:
                d.mkdir(parents=True, exist_ok=True)
        
        # Shared secret for message signing (in production, use proper key management)
        self._shared_secret = self.settings.a2a_shared_secret or "default-secret-change-me"
        
        # Stats
        self._stats = {
            'messages_sent': 0,
            'messages_received': 0,
            'messages_processed': 0,
            'errors': 0,
            'started_at': datetime.now().isoformat()
        }
    
    def register_capability(self, capability: str, handler: Callable):
        """
        Register a capability handler for incoming A2A requests.
        
        Args:
            capability: Capability name (e.g., 'email_send', 'calendar_read')
            handler: Async callable that handles requests for this capability
        """
        self._handlers[capability] = handler
        if capability not in self.capabilities:
            self.capabilities.append(capability)
        logger.info(f"Registered capability: {capability}")
    
    def discover_agents(self) -> List[AgentEndpoint]:
        """
        Discover other agents on the network.
        
        For file-based transport: reads agent registry from vault.
        For HTTP-based: broadcasts discovery request.
        """
        if self.transport == 'file':
            return self._discover_file_based()
        elif self.transport == 'http':
            return self._discover_http_based()
        return []
    
    def _discover_file_based(self) -> List[AgentEndpoint]:
        """Discover agents via vault registry files."""
        agents = []
        if not self._inbox_dir or not self._inbox_dir.exists():
            return agents
        
        # Look for agent registry files
        registry_file = self.vault_path / 'A2A_Registry.json'
        if registry_file.exists():
            try:
                data = json.loads(registry_file.read_text())
                for agent_data in data.get('agents', []):
                    endpoint = AgentEndpoint(**agent_data)
                    if endpoint.agent_id != self.agent_id:
                        agents.append(endpoint)
                        self._registry[endpoint.agent_id] = endpoint
            except Exception as e:
                logger.error(f"Error reading agent registry: {e}")
        
        return agents
    
    def _discover_http_based(self) -> List[AgentEndpoint]:
        """Discover agents via HTTP broadcast (placeholder)."""
        # In production, this would use mDNS, SSDP, or a central registry
        logger.info("HTTP-based discovery not yet implemented")
        return []
    
    def announce_presence(self):
        """Announce this agent's presence to the network."""
        if self.transport == 'file':
            self._announce_file_based()
        elif self.transport == 'http':
            self._announce_http_based()
    
    def _announce_file_based(self):
        """Announce presence via vault registry file."""
        registry_file = self.vault_path / 'A2A_Registry.json'
        
        try:
            # Read existing registry or create new
            if registry_file.exists():
                data = json.loads(registry_file.read_text())
            else:
                data = {'agents': [], 'last_updated': ''}
            
            # Update or add this agent
            agent_entry = {
                'agent_id': self.agent_id,
                'agent_name': self.agent_name,
                'capabilities': self.capabilities,
                'address': str(self._inbox_dir),
                'last_seen': datetime.now().isoformat(),
                'status': 'online',
                'metadata': {
                    'transport': self.transport,
                    'version': '1.0'
                }
            }
            
            # Remove old entry if exists
            data['agents'] = [
                a for a in data['agents'] if a['agent_id'] != self.agent_id
            ]
            data['agents'].append(agent_entry)
            data['last_updated'] = datetime.now().isoformat()
            
            registry_file.write_text(json.dumps(data, indent=2))
            logger.info(f"Agent presence announced to registry")
            
        except Exception as e:
            logger.error(f"Error announcing presence: {e}")
    
    def _announce_http_based(self):
        """Announce via HTTP (placeholder)."""
        logger.info("HTTP-based announcement not yet implemented")
    
    def send_request(
        self,
        recipient_id: str,
        capability: str,
        payload: Dict[str, Any],
        priority: Priority = Priority.NORMAL,
        timeout_seconds: int = 60
    ) -> Optional[Dict[str, Any]]:
        """
        Send a request to another agent and wait for response.
        
        Args:
            recipient_id: Target agent's ID
            capability: Capability to invoke
            payload: Request data
            priority: Message priority
            timeout_seconds: Max wait time for response
            
        Returns:
            Response payload or None on timeout
        """
        correlation_id = str(uuid.uuid4())
        
        message = A2AMessage(
            message_type=MessageType.REQUEST.value,
            sender_id=self.agent_id,
            sender_name=self.agent_name,
            recipient_id=recipient_id,
            priority=priority.value,
            correlation_id=correlation_id,
            payload={
                'capability': capability,
                **payload
            }
        )
        
        # Sign the message
        message.signature = self._sign_message(message)
        
        # Store pending request
        self._pending_requests[correlation_id] = {
            'message': message,
            'sent_at': datetime.now(),
            'timeout': timeout_seconds,
            'response': None
        }
        
        # Send the message
        if self._send_message(message):
            self._stats['messages_sent'] += 1
            
            # Wait for response (synchronous)
            return self._wait_for_response(correlation_id, timeout_seconds)
        
        return None
    
    def send_message(
        self,
        recipient_id: str,
        message_type: MessageType,
        payload: Dict[str, Any],
        priority: Priority = Priority.NORMAL
    ) -> bool:
        """
        Send a one-way message to another agent (fire-and-forget).
        
        Args:
            recipient_id: Target agent ID
            message_type: Type of message
            payload: Message content
            priority: Message priority
            
        Returns:
            True if message was sent successfully
        """
        message = A2AMessage(
            message_type=message_type.value,
            sender_id=self.agent_id,
            sender_name=self.agent_name,
            recipient_id=recipient_id,
            priority=priority.value,
            payload=payload
        )
        message.signature = self._sign_message(message)
        
        if self._send_message(message):
            self._stats['messages_sent'] += 1
            return True
        return False
    
    def _send_message(self, message: A2AMessage) -> bool:
        """Send a message using the configured transport."""
        try:
            serialized = json.dumps(asdict(message), indent=2)
            
            if self.transport == 'file' and self._outbox_dir:
                outbox_file = self._outbox_dir / f"A2A_{message.message_id}.json"
                outbox_file.write_text(serialized)
                logger.info(f"A2A message sent to outbox: {message.message_id}")
                return True
                
            elif self.transport == 'http':
                # Would POST to recipient's endpoint
                # Placeholder for HTTP transport
                logger.info(f"A2A HTTP message prepared: {message.message_id}")
                return True
                
            else:
                # Fallback: log to audit
                self._log_audit(message, 'sent')
                return True
                
        except Exception as e:
            logger.error(f"Error sending A2A message: {e}")
            self._stats['errors'] += 1
            return False
    
    def check_inbox(self) -> int:
        """
        Check for incoming messages and process them.
        
        Returns:
            Number of messages processed
        """
        processed = 0
        
        if not self._inbox_dir or not self._inbox_dir.exists():
            return processed
        
        for msg_file in sorted(self._inbox_dir.glob('A2A_*.json')):
            try:
                data = json.loads(msg_file.read_text())
                message = A2AMessage(**{
                    k: v for k, v in data.items() if k in A2AMessage.__dataclass_fields__
                })
                
                # Verify signature
                if not self._verify_signature(message):
                    logger.warning(f"A2A message signature invalid: {message.message_id}")
                    msg_file.unlink()
                    continue
                
                # Check TTL
                msg_time = datetime.fromisoformat(message.timestamp)
                if datetime.now() - msg_time > timedelta(seconds=message.ttl_seconds):
                    logger.warning(f"A2A message expired: {message.message_id}")
                    msg_file.unlink()
                    continue
                
                # Process the message
                response = self._process_message(message)
                
                if response and message.message_type == MessageType.REQUEST.value:
                    # Send response back
                    response_msg = A2AMessage(
                        message_type=MessageType.RESPONSE.value,
                        sender_id=self.agent_id,
                        sender_name=self.agent_name,
                        recipient_id=message.sender_id,
                        correlation_id=message.correlation_id,
                        payload=response
                    )
                    response_msg.signature = self._sign_message(response_msg)
                    self._send_message(response_msg)
                
                # Archive processed message
                archived = self._audit_dir / f"PROCESSED_{msg_file.name}"
                msg_file.rename(archived)
                
                processed += 1
                self._stats['messages_received'] += 1
                
            except Exception as e:
                logger.error(f"Error processing A2A message {msg_file}: {e}")
                self._stats['errors'] += 1
        
        return processed
    
    def _process_message(self, message: A2AMessage) -> Optional[Dict[str, Any]]:
        """
        Process an incoming A2A message and return a response if needed.
        
        Args:
            message: The incoming message
            
        Returns:
            Response payload or None
        """
        msg_type = message.message_type
        
        if msg_type == MessageType.REQUEST.value:
            capability = message.payload.get('capability', '')
            
            if capability in self._handlers:
                try:
                    result = self._handlers[capability](message.payload)
                    return {'status': 'success', 'result': result}
                except Exception as e:
                    return {'status': 'error', 'error': str(e)}
            else:
                return {'status': 'error', 'error': f'Unknown capability: {capability}'}
        
        elif msg_type == MessageType.RESPONSE.value:
            correlation_id = message.correlation_id
            if correlation_id in self._pending_requests:
                req = self._pending_requests[correlation_id]
                req['response'] = message.payload
        
        elif msg_type == MessageType.EVENT.value:
            # Handle event notifications
            event_type = message.payload.get('event_type')
            logger.info(f"Received event: {event_type}")
        
        elif msg_type == MessageType.HEARTBEAT.value:
            # Respond to heartbeat
            return {'status': 'alive', 'capabilities': self.capabilities}
        
        elif msg_type == MessageType.DISCOVER.value:
            # Respond with our info
            return {
                'agent_id': self.agent_id,
                'agent_name': self.agent_name,
                'capabilities': self.capabilities,
                'status': 'online'
            }
        
        return None
    
    def _wait_for_response(
        self,
        correlation_id: str,
        timeout: int,
        poll_interval: float = 0.5
    ) -> Optional[Dict[str, Any]]:
        """
        Wait for a response to a pending request.
        
        Args:
            correlation_id: The correlation ID to match
            timeout: Max seconds to wait
            poll_interval: Seconds between checks
            
        Returns:
            Response payload or None on timeout
        """
        start = time.time()
        
        while time.time() - start < timeout:
            if correlation_id in self._pending_requests:
                req = self._pending_requests[correlation_id]
                if req.get('response') is not None:
                    return req['response']
            
            # Check inbox for responses
            if self._inbox_dir:
                for msg_file in self._inbox_dir.glob('A2A_*.json'):
                    try:
                        data = json.loads(msg_file.read_text())
                        if data.get('correlation_id') == correlation_id:
                            msg_file.unlink()
                            return data.get('payload')
                    except Exception:
                        continue
            
            time.sleep(poll_interval)
        
        logger.warning(f"A2A request timeout: correlation_id={correlation_id}")
        return None
    
    def _sign_message(self, message: A2AMessage) -> str:
        """Create a signature for message integrity."""
        payload_str = json.dumps(asdict(message), sort_keys=True, default=str)
        return hmac.new(
            self._shared_secret.encode(),
            payload_str.encode(),
            hashlib.sha256
        ).hexdigest()
    
    def _verify_signature(self, message: A2AMessage) -> bool:
        """Verify message signature."""
        expected_sig = message.signature
        message.signature = ""
        calculated_sig = self._sign_message(message)
        message.signature = expected_sig
        
        return hmac.compare_digest(expected_sig, calculated_sig)
    
    def _log_audit(self, message: A2AMessage, action: str):
        """Log A2A communication to audit trail."""
        audit_entry = {
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'message_id': message.message_id,
            'type': message.message_type,
            'sender': message.sender_id,
            'recipient': message.recipient_id,
            'priority': message.priority,
            'correlation_id': message.correlation_id
        }
        
        if self._audit_dir:
            audit_file = self._audit_dir / f"A2A_AUDIT_{datetime.now().strftime('%Y%m%d')}.jsonl"
            audit_file.write_text(json.dumps(audit_entry) + '\n', append=True)
    
    def send_heartbeat(self) -> Dict[str, Any]:
        """
        Send heartbeat to check agent connectivity.
        
        Returns:
            Response from the other agent or error info
        """
        return {
            'agent_id': self.agent_id,
            'status': 'online',
            'timestamp': datetime.now().isoformat(),
            'uptime_seconds': (datetime.now() - datetime.fromisoformat(self._stats['started_at'])).total_seconds(),
            'messages_sent': self._stats['messages_sent'],
            'messages_received': self._stats['messages_received'],
            'errors': self._stats['errors']
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Return protocol statistics."""
        return {
            **self._stats,
            'pending_requests': len(self._pending_requests),
            'registered_capabilities': list(self._handlers.keys()),
            'known_agents': len(self._registry),
            'transport': self.transport
        }


# ─── Example: Local Agent ↔ Cloud Agent Communication ───────────────────────

def create_local_to_cloud_flow(vault_path: str):
    """
    Create a complete A2A flow for local-to-cloud communication.
    
    This demonstrates the Platinum-tier pattern where:
    - Local sends email draft request to Cloud
    - Cloud drafts the email
    - Cloud sends draft back to Local
    - Local approves and sends
    """
    # Local agent
    local = A2AProtocol(
        agent_id='local_agent',
        agent_name='Local AI Employee',
        vault_path=Path(vault_path),
        capabilities=[
            'email_send',
            'whatsapp_send',
            'payment_process',
            'approval_decision'
        ],
        transport='file'
    )
    
    # Cloud agent
    cloud = A2AProtocol(
        agent_id='cloud_agent',
        agent_name='Cloud AI Employee',
        vault_path=Path(vault_path),
        capabilities=[
            'email_draft',
            'social_draft',
            'accounting_draft',
            'web_search'
        ],
        transport='file'
    )
    
    # Register handlers
    def email_draft_handler(payload):
        """Cloud drafts an email based on the request."""
        recipient = payload.get('recipient', '')
        subject = payload.get('subject', '')
        context = payload.get('context', '')
        return {
            'draft': f"Draft email to: {recipient}\nSubject: {subject}\n\n{context}",
            'status': 'draft_complete'
        }
    
    cloud.register_capability('email_draft', email_draft_handler)
    
    # Local requests Cloud to draft an email
    result = local.send_request(
        recipient_id='cloud_agent',
        capability='email_draft',
        payload={
            'recipient': 'client@example.com',
            'subject': 'Follow up on project milestone',
            'context': 'The client asked about the status of Project Alpha milestone 2.'
        },
        priority=Priority.HIGH,
        timeout_seconds=30
    )
    
    logger.info(f"Cloud response: {result}")
    local._stats['messages_processed'] += 1
    
    return local, cloud


# ─── Standalone Execution ────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='A2A Protocol - Agent-to-Agent Communication')
    parser.add_argument('--agent-id', default='local_agent', help='Agent ID')
    parser.add_argument('--agent-name', default='Local Agent', help='Agent display name')
    parser.add_argument('--vault-path', default='AI_Employee_Vault', help='Vault path')
    parser.add_argument('--transport', default='file', choices=['file', 'http'], help='Transport')
    parser.add_argument('--demo', action='store_true', help='Run demo flow')
    parser.add_argument('--check-inbox', action='store_true', help='Check for incoming messages')
    parser.add_argument('--announce', action='store_true', help='Announce presence')
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    agent = A2AProtocol(
        agent_id=args.agent_id,
        agent_name=args.agent_name,
        vault_path=Path(args.vault_path),
        transport=args.transport
    )
    
    if args.demo:
        print("=" * 60)
        print("A2A Protocol Demo: Local ↔ Cloud Communication")
        print("=" * 60)
        local, cloud = create_local_to_cloud_flow(args.vault_path)
        print(f"\nLocal stats: {json.dumps(local.get_stats(), indent=2, default=str)}")
        print(f"Cloud stats: {json.dumps(cloud.get_stats(), indent=2, default=str)}")
    
    if args.announce:
        agent.announce_presence()
        print(f"Presence announced for {args.agent_name}")
    
    if args.check_inbox:
        count = agent.check_inbox()
        print(f"Processed {count} messages from inbox")
    
    print(f"\nAgent status: {agent.send_heartbeat()}")