"""
Orchestrator - Master process coordinator for AI Employee system.
Manages watchers, scheduling, and process lifecycle.
"""

import logging
import time
import subprocess
import signal
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json
from pathlib import Path

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_settings
from utilities.vault_manager import VaultManager

logger = logging.getLogger(__name__)


class Orchestrator:
    """Master orchestrator for AI Employee system."""
    
    def __init__(self):
        """Initialize orchestrator."""
        self.settings = get_settings()
        self.vault_manager = VaultManager()
        self.running = False
        self.processes: Dict[str, subprocess.Popen] = {}
        self.scheduled_tasks: Dict[str, Dict[str, Any]] = {}
        self.last_run: Dict[str, float] = {}
    
    def start(self):
        """Start the orchestrator."""
        logger.info("=== AI Employee Orchestrator Starting ===")
        self.running = True
        
        try:
            # Register signal handlers
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
            
            # Initialize scheduled tasks
            self._setup_schedules()
            
            # Start watchers
            self._start_watchers()
            
            # Start main loop
            self._main_loop()
            
        except Exception as e:
            logger.error(f"Orchestrator error: {e}", exc_info=True)
        finally:
            self.stop()
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
    
    def _setup_schedules(self):
        """Setup recurring tasks."""
        now = datetime.utcnow()
        
        # Daily tasks
        self.scheduled_tasks['daily_digest'] = {
            'interval': 86400,  # 24 hours
            'run_at': '17:00',  # 5 PM UTC
            'function': self._run_daily_digest,
            'last_run': 0,
        }
        
        # Weekly tasks
        self.scheduled_tasks['ceo_briefing'] = {
            'interval': 604800,  # 7 days
            'run_at': 'Monday 08:00',  # Monday 8 AM UTC
            'function': self._run_ceo_briefing,
            'last_run': 0,
        }
        
        # Hourly tasks
        self.scheduled_tasks['process_check'] = {
            'interval': 3600,  # 1 hour
            'function': self._process_health_check,
            'last_run': 0,
        }
        
        logger.info(f"Scheduled {len(self.scheduled_tasks)} tasks")
    
    def _start_watchers(self):
        """Start all enabled watchers."""
        logger.info("Starting watchers...")
        
        # Start FastAPI server (contains Gmail, WhatsApp, Filesystem watchers)
        if self.settings.enable_gmail_watcher or self.settings.enable_whatsapp_watcher:
            try:
                logger.info("Starting FastAPI server (server.py)")
                process = subprocess.Popen(
                    ['python3', 'server.py'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    start_new_session=True
                )
                self.processes['server'] = process
                time.sleep(2)  # Wait for server to start
                logger.info("FastAPI server started")
            except Exception as e:
                logger.error(f"Error starting FastAPI server: {e}")
    
    def _main_loop(self):
        """Main orchestration loop."""
        logger.info("Orchestrator main loop started")
        
        while self.running:
            try:
                # Check for scheduled tasks
                self._check_schedules()
                
                # Check process health
                self._monitor_processes()
                
                # Process any vault actions
                self._process_vault_actions()
                
                # Sleep before next iteration
                time.sleep(10)
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
                time.sleep(30)  # Back off on error
    
    def _check_schedules(self):
        """Check and run scheduled tasks."""
        now = time.time()
        
        for task_name, task in self.scheduled_tasks.items():
            # Check if enough time has passed
            if now - task['last_run'] >= task['interval']:
                try:
                    logger.info(f"Running scheduled task: {task_name}")
                    task['function']()
                    task['last_run'] = now
                    logger.info(f"Completed scheduled task: {task_name}")
                except Exception as e:
                    logger.error(f"Error running {task_name}: {e}", exc_info=True)
    
    def _run_daily_digest(self):
        """Generate daily digest of completed tasks."""
        try:
            done_dir = self.vault_manager.vault_path / "Done"
            done_files = list(done_dir.glob("*.md"))
            
            # Get tasks from today
            today = datetime.utcnow().date()
            today_tasks = []
            
            for task_file in done_files:
                if task_file.stat().st_mtime > (datetime.utcnow() - timedelta(days=1)).timestamp():
                    today_tasks.append(task_file.name)
            
            logger.info(f"Daily digest: {len(today_tasks)} tasks completed today")
            
            # Would send via email/notification
            # self.send_digest(today_tasks)
            
        except Exception as e:
            logger.error(f"Error generating daily digest: {e}")
    
    def _run_ceo_briefing(self):
        """Generate CEO briefing."""
        try:
            logger.info("Generating CEO briefing")
            
            # Import financial auditor
            from financial_auditor import FinancialAuditor
            
            auditor = FinancialAuditor()
            
            # Get current month transactions
            accounting_file = self.vault_manager.vault_path / "Accounting" / "Current_Month.md"
            
            # This would read transactions and generate briefing
            # briefing = auditor.generate_briefing(transactions)
            
            logger.info("CEO briefing generated")
            
        except Exception as e:
            logger.error(f"Error generating CEO briefing: {e}")
    
    def _monitor_processes(self):
        """Monitor subprocess health."""
        for name, process in list(self.processes.items()):
            if process.poll() is not None:
                # Process has exited
                logger.warning(f"Process {name} has exited with code {process.returncode}")
                # Would trigger watchdog restart
    
    def _process_vault_actions(self):
        """Process any pending vault actions."""
        try:
            # Check for newly created tasks
            needs_action = self.vault_manager.vault_path / "Needs_Action"
            if needs_action.exists():
                tasks = list(needs_action.glob("*.md"))
                if tasks:
                    logger.debug(f"Found {len(tasks)} tasks in Needs_Action")
            
            # Check for approved actions awaiting execution
            approved = self.vault_manager.vault_path / "Approved"
            if approved.exists():
                actions = list(approved.glob("*.md"))
                if actions:
                    logger.debug(f"Found {len(actions)} approved actions ready for execution")
        
        except Exception as e:
            logger.error(f"Error processing vault actions: {e}")
    
    def _process_health_check(self):
        """Perform system health check."""
        try:
            health = {
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'uptime': time.time(),
                'processes': {},
                'vault': {
                    'tasks_pending': 0,
                    'tasks_approved': 0,
                    'tasks_pending_approval': 0,
                }
            }
            
            # Check processes
            for name, process in self.processes.items():
                health['processes'][name] = {
                    'running': process.poll() is None,
                    'pid': process.pid if process.poll() is None else None,
                }
            
            # Check vault
            needs_action = self.vault_manager.vault_path / "Needs_Action"
            if needs_action.exists():
                health['vault']['tasks_pending'] = len(list(needs_action.glob("*.md")))
            
            approved = self.vault_manager.vault_path / "Approved"
            if approved.exists():
                health['vault']['tasks_approved'] = len(list(approved.glob("*.md")))
            
            pending = self.vault_manager.vault_path / "Pending_Approval"
            if pending.exists():
                health['vault']['tasks_pending_approval'] = len(list(pending.glob("*.md")))
            
            logger.debug(f"Health check: {health['vault']}")
            
            # Log health status
            self.vault_manager.log_event(
                event_type="health_check",
                details=health,
                agent="orchestrator"
            )
            
        except Exception as e:
            logger.error(f"Error in health check: {e}")
    
    def stop(self):
        """Stop the orchestrator."""
        logger.info("Stopping orchestrator...")
        self.running = False
        
        # Stop all processes
        for name, process in self.processes.items():
            try:
                logger.info(f"Stopping {name}...")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                logger.info(f"Stopped {name}")
            except Exception as e:
                logger.error(f"Error stopping {name}: {e}")
        
        logger.info("=== Orchestrator Stopped ===")
    
    def get_status(self) -> Dict[str, Any]:
        """Get orchestrator status."""
        return {
            'running': self.running,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'processes': {
                name: {
                    'running': proc.poll() is None,
                    'pid': proc.pid if proc.poll() is None else None,
                }
                for name, proc in self.processes.items()
            },
            'scheduled_tasks': list(self.scheduled_tasks.keys()),
        }


if __name__ == "__main__":
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    orchestrator = Orchestrator()
    
    try:
        orchestrator.start()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Orchestrator failed: {e}", exc_info=True)
        sys.exit(1)
