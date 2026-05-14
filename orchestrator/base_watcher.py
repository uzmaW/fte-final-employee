"""
Base watcher class for all source monitors.
Provides common functionality for polling sources and creating tasks.
"""

import logging
import time
from abc import ABC, abstractmethod
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_settings
from utilities.vault_manager import VaultManager

logger = logging.getLogger(__name__)


class BaseWatcher(ABC):
    """Abstract base class for all watchers."""
    
    def __init__(self, name: str, poll_interval: int = 300):
        """
        Initialize watcher.
        
        Args:
            name: Watcher name (used for In_Progress folder)
            poll_interval: Polling interval in seconds (default 5 minutes)
        """
        self.name = name
        self.poll_interval = poll_interval
        self.settings = get_settings()
        self.vault_manager = VaultManager()
        self.last_poll_time = 0
        self.error_count = 0
        self.max_errors = 5
        self.running = False
    
    @abstractmethod
    def poll(self) -> List[Dict[str, Any]]:
        """
        Poll the source for new items.
        
        Returns:
            List of new items to process.
        """
        pass
    
    @abstractmethod
    def process_item(self, item: Dict[str, Any]) -> Optional[str]:
        """
        Process a single item and create a vault task.
        
        Args:
            item: Item to process
            
        Returns:
            Path to created task file, or None if failed
        """
        pass
    
    def should_poll(self) -> bool:
        """Check if enough time has passed since last poll."""
        current_time = time.time()
        if current_time - self.last_poll_time >= self.poll_interval:
            return True
        return False
    
    def mark_polled(self):
        """Update last poll timestamp."""
        self.last_poll_time = time.time()
    
    def run_once(self) -> int:
        """
        Run one polling cycle.
        
        Returns:
            Number of items processed
        """
        if not self.should_poll():
            return 0
        
        try:
            logger.debug(f"{self.name}: Starting poll cycle")
            
            # Poll for new items
            items = self.poll()
            logger.debug(f"{self.name}: Found {len(items)} items")
            
            # Process each item
            processed = 0
            for item in items:
                try:
                    task_file = self.process_item(item)
                    if task_file:
                        processed += 1
                        logger.info(f"{self.name}: Created task {task_file}")
                except Exception as e:
                    logger.error(f"{self.name}: Error processing item: {e}", exc_info=True)
                    self.error_count += 1
                    if self.error_count >= self.max_errors:
                        logger.error(f"{self.name}: Max errors reached, stopping")
                        return processed
            
            # Reset error count on successful cycle
            self.error_count = 0
            self.mark_polled()
            
            logger.debug(f"{self.name}: Processed {processed} items")
            return processed
            
        except Exception as e:
            logger.error(f"{self.name}: Poll error: {e}", exc_info=True)
            self.error_count += 1
            if self.error_count >= self.max_errors:
                logger.error(f"{self.name}: Max errors reached, stopping")
            return 0
    
    def run_loop(self):
        """
        Run continuous polling loop.
        Call stop() to exit loop.
        """
        self.running = True
        logger.info(f"{self.name}: Starting watcher loop (interval: {self.poll_interval}s)")
        
        try:
            while self.running:
                self.run_once()
                time.sleep(1)  # Sleep 1 second between checks
        except KeyboardInterrupt:
            logger.info(f"{self.name}: Interrupted by user")
        except Exception as e:
            logger.error(f"{self.name}: Unexpected error: {e}", exc_info=True)
        finally:
            self.stop()
    
    def stop(self):
        """Stop the watcher."""
        self.running = False
        logger.info(f"{self.name}: Stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """Get watcher status."""
        return {
            "name": self.name,
            "running": self.running,
            "error_count": self.error_count,
            "last_poll_time": datetime.fromtimestamp(self.last_poll_time).isoformat() if self.last_poll_time else None,
            "poll_interval": self.poll_interval,
        }
    
    def create_task_file(
        self,
        task_id: str,
        task_type: str,
        title: str,
        priority: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Path]:
        """
        Create a task file in the vault.
        
        Args:
            task_id: Unique task identifier
            task_type: Task type (email_task, whatsapp_task, etc.)
            title: Task title
            priority: Task priority (critical, high, medium, low)
            content: Task content (markdown)
            metadata: Additional YAML metadata
            
        Returns:
            Path to created task file, or None if failed
        """
        try:
            # Build YAML frontmatter
            yaml_lines = [
                "---",
                f"type: {task_type}",
                f"priority: {priority}",
                f"source: {self.name}",
                f"created: {datetime.utcnow().isoformat()}Z",
            ]
            
            # Add custom metadata
            if metadata:
                for key, value in metadata.items():
                    if isinstance(value, str):
                        yaml_lines.append(f'{key}: "{value}"')
                    elif isinstance(value, bool):
                        yaml_lines.append(f'{key}: {str(value).lower()}')
                    elif isinstance(value, (int, float)):
                        yaml_lines.append(f'{key}: {value}')
                    elif isinstance(value, list):
                        yaml_lines.append(f'{key}:')
                        for item in value:
                            yaml_lines.append(f'  - {item}')
            
            yaml_lines.append("---")
            yaml_str = "\n".join(yaml_lines)
            
            # Create task file
            task_file = self.vault_manager.vault_path / "Needs_Action" / f"{task_id}.md"
            with open(task_file, 'w') as f:
                f.write(f"{yaml_str}\n\n# {title}\n\n{content}")
            
            # Log event
            self.vault_manager.log_event(
                event_type="task_created",
                task_id=task_id,
                details={"task_type": task_type, "priority": priority},
                agent=self.name
            )
            
            return task_file
            
        except Exception as e:
            logger.error(f"{self.name}: Error creating task file: {e}", exc_info=True)
            return None
