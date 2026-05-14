"""
Filesystem watcher - monitors vault folders for changes and executes approved actions.
Uses watchdog library to detect file system events.
"""

import logging
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestrator.base_watcher import BaseWatcher
from utilities.vault_manager import VaultManager

logger = logging.getLogger(__name__)


class VaultFileHandler(FileSystemEventHandler):
    """Handle file system events in the vault."""
    
    def __init__(self, watcher: 'FilesystemWatcher'):
        """
        Initialize file handler.
        
        Args:
            watcher: Parent FilesystemWatcher instance
        """
        self.watcher = watcher
    
    def on_created(self, event):
        """Handle file creation."""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        
        # Ignore non-markdown files
        if file_path.suffix != '.md':
            return
        
        # Check which folder the file is in
        if 'Approved' in str(file_path):
            self.watcher.on_file_approved(file_path)
        elif 'Rejected' in str(file_path):
            self.watcher.on_file_rejected(file_path)
    
    def on_moved(self, event):
        """Handle file move (also called for rename)."""
        if event.is_directory:
            return
        
        src_path = Path(event.src_path)
        dest_path = Path(event.dest_path)
        
        # Ignore non-markdown files
        if dest_path.suffix != '.md':
            return
        
        # Check if moved to Approved folder
        if 'Approved' in str(dest_path):
            self.watcher.on_file_approved(dest_path)
        elif 'Rejected' in str(dest_path):
            self.watcher.on_file_rejected(dest_path)


class FilesystemWatcher(BaseWatcher):
    """Monitor vault folders for file changes and execute approved actions."""
    
    def __init__(self):
        """Initialize filesystem watcher."""
        super().__init__(
            name="filesystem",
            poll_interval=1  # Check frequently
        )
        
        self.vault_manager = VaultManager()
        self.observer: Optional[Observer] = None
        self.event_handler = VaultFileHandler(self)
    
    def start_monitoring(self):
        """Start watching vault folders."""
        try:
            self.observer = Observer()
            
            # Watch Approved folder for user approvals
            approved_path = self.vault_manager.vault_path / "Approved"
            self.observer.schedule(
                self.event_handler,
                str(approved_path),
                recursive=False
            )
            
            # Watch Rejected folder for rejections
            rejected_path = self.vault_manager.vault_path / "Rejected"
            self.observer.schedule(
                self.event_handler,
                str(rejected_path),
                recursive=False
            )
            
            self.observer.start()
            logger.info("Filesystem watcher started")
            self.running = True
            
        except Exception as e:
            logger.error(f"Error starting observer: {e}", exc_info=True)
    
    def stop_monitoring(self):
        """Stop watching vault folders."""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.running = False
            logger.info("Filesystem watcher stopped")
    
    def poll(self):
        """
        Poll for approved actions (called by base watcher loop).
        
        Returns:
            List of approved actions
        """
        # Get all approved action files
        approved_actions = self.vault_manager.get_approved_actions()
        return approved_actions
    
    def on_file_approved(self, file_path: Path):
        """
        Handle file moved to Approved folder.
        
        Args:
            file_path: Path to approved action file
        """
        try:
            logger.info(f"File approved: {file_path.name}")
            
            # Small delay to ensure file write is complete
            import time
            time.sleep(0.5)
            
            # Read the approved action
            action = self.vault_manager.read_task_file(file_path)
            
            # Execute the action
            self.execute_action(action, file_path)
            
        except Exception as e:
            logger.error(f"Error handling approved file: {e}", exc_info=True)
    
    def on_file_rejected(self, file_path: Path):
        """
        Handle file moved to Rejected folder.
        
        Args:
            file_path: Path to rejected action file
        """
        try:
            logger.info(f"File rejected: {file_path.name}")
            
            # Read the rejected action
            action = self.vault_manager.read_task_file(file_path)
            
            # Log rejection
            self.vault_manager.log_event(
                event_type="action_rejected",
                task_id=file_path.name,
                details={"reason": "User rejected"},
                agent="filesystem"
            )
            
        except Exception as e:
            logger.error(f"Error handling rejected file: {e}", exc_info=True)
    
    def execute_action(self, action: Dict[str, Any], file_path: Path):
        """
        Execute an approved action.
        
        Args:
            action: Action dictionary from vault
            file_path: Path to action file
        """
        try:
            action_type = action.get('metadata', {}).get('type', 'unknown')
            
            logger.info(f"Executing action: {action_type}")
            
            # Route to appropriate executor based on action type
            if action_type == 'payment_approval':
                self.execute_payment(action)
            elif action_type == 'email_approval':
                self.execute_email(action)
            elif action_type == 'action_approval':
                self.execute_generic_action(action)
            else:
                logger.warning(f"Unknown action type: {action_type}")
                return
            
            # Log successful execution
            self.vault_manager.log_event(
                event_type="action_executed",
                task_id=file_path.name,
                details={"action_type": action_type},
                agent="filesystem"
            )
            
            # Move to Done
            done_path = self.vault_manager.vault_path / "Done" / file_path.name
            file_path.rename(done_path)
            logger.info(f"Action completed: {file_path.name}")
            
        except Exception as e:
            logger.error(f"Error executing action: {e}", exc_info=True)
    
    def execute_payment(self, action: Dict[str, Any]):
        """
        Execute a payment action.
        
        Args:
            action: Payment action dictionary
        """
        try:
            # Extract payment details from action content
            content = action.get('content', '')
            
            # In production, would call payment MCP server:
            # - Parse amount, recipient, reference
            # - Call payment processor
            # - Log transaction
            # - Confirm execution
            
            logger.info("Payment action executed (stub)")
            
        except Exception as e:
            logger.error(f"Error executing payment: {e}", exc_info=True)
    
    def execute_email(self, action: Dict[str, Any]):
        """
        Execute an email action.
        
        Args:
            action: Email action dictionary
        """
        try:
            # Extract email details from action content
            content = action.get('content', '')
            
            # In production, would call email MCP server:
            # - Parse recipient, subject, body
            # - Call email service
            # - Log sent email
            
            logger.info("Email action executed (stub)")
            
        except Exception as e:
            logger.error(f"Error executing email: {e}", exc_info=True)
    
    def execute_generic_action(self, action: Dict[str, Any]):
        """
        Execute a generic action.
        
        Args:
            action: Generic action dictionary
        """
        try:
            # Extract action details from content
            content = action.get('content', '')
            
            # In production, would call appropriate service based on action type
            logger.info("Generic action executed (stub)")
            
        except Exception as e:
            logger.error(f"Error executing generic action: {e}", exc_info=True)
    
    def process_item(self, item: Dict[str, Any]) -> Optional[str]:
        """
        Process an approved action item.
        
        Args:
            item: Action item dictionary
            
        Returns:
            Path if processed, None otherwise
        """
        # This is called by the base watcher's run_loop
        # For filesystem watcher, processing is event-driven
        # So we just return None here
        return None
    
    def get_pending_approvals(self) -> Dict[str, Any]:
        """
        Get all pending approval actions.
        
        Returns:
            Dictionary of pending approvals
        """
        try:
            approvals = self.vault_manager.check_pending_approvals()
            return {
                'count': len(approvals),
                'approvals': approvals,
            }
        except Exception as e:
            logger.error(f"Error getting pending approvals: {e}")
            return {'count': 0, 'approvals': []}
    
    def get_approved_actions(self) -> Dict[str, Any]:
        """
        Get all approved actions waiting for execution.
        
        Returns:
            Dictionary of approved actions
        """
        try:
            actions = self.vault_manager.get_approved_actions()
            return {
                'count': len(actions),
                'actions': actions,
            }
        except Exception as e:
            logger.error(f"Error getting approved actions: {e}")
            return {'count': 0, 'actions': []}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    watcher = FilesystemWatcher()
    
    try:
        print("Starting filesystem watcher...")
        watcher.start_monitoring()
        
        # Keep running until interrupted
        import time
        while True:
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("Stopping filesystem watcher...")
        watcher.stop_monitoring()
