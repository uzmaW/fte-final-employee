"""
Compatibility shim - imports moved to orchestrator.whatsapp_watcher
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Re-export from new location for backward compatibility
from orchestrator.whatsapp_watcher import *

__all__ = ['WhatsAppWatcher']
