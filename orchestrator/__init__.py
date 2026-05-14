"""
Orchestrator module - Core orchestration logic for AI Employee system.

Handles coordination of agents, watchers, and workflow management.
"""

from .orchestrator import Orchestrator
from .base_watcher import BaseWatcher
from .filesystem_watcher import FilesystemWatcher
from .gmail_watcher import GmailWatcher
from .whatsapp_watcher import WhatsAppWatcher

__all__ = [
    'Orchestrator',
    'BaseWatcher',
    'FilesystemWatcher',
    'GmailWatcher',
    'WhatsAppWatcher',
]
