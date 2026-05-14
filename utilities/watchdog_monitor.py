"""
Watchdog Monitor - Health monitoring and process auto-restart.
Ensures all critical processes stay running 24/7.
"""

import logging
import time
import subprocess
import psutil
import signal
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from pathlib import Path

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_settings
from utilities.vault_manager import VaultManager

logger = logging.getLogger(__name__)


class Watchdog:
    """Monitor process health and auto-restart failed processes."""
    
    def __init__(self, check_interval: int = 30):
        """
        Initialize watchdog.
        
        Args:
            check_interval: Seconds between health checks
        """
        self.check_interval = check_interval
        self.settings = get_settings()
        self.vault_manager = VaultManager()
        self.running = False
        self.processes: Dict[str, Dict] = {}
        self.restart_count: Dict[str, int] = {}
        self.max_restarts = 3
        self.restart_backoff = 60  # seconds
    
    def register_process(self, name: str, pid: int, restart_command: List[str]):
        """
        Register a process to monitor.
        
        Args:
            name: Process name
            pid: Process ID
            restart_command: Command to restart process
        """
        self.processes[name] = {
            'pid': pid,
            'restart_command': restart_command,
            'status': 'running',
            'started_at': datetime.utcnow(),
            'last_restart': None,
            'restart_count': 0,
        }
        self.restart_count[name] = 0
        logger.info(f"Registered process: {name} (PID: {pid})")
    
    def start(self):
        """Start the watchdog monitoring loop."""
        logger.info("=== Watchdog Started ===")
        self.running = True
        
        try:
            # Register signal handlers
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
            
            # Main monitoring loop
            self._monitor_loop()
            
        except Exception as e:
            logger.error(f"Watchdog error: {e}", exc_info=True)
        finally:
            self.stop()
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Watchdog received signal {signum}")
        self.running = False
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        logger.info("Watchdog monitoring loop started")
        
        while self.running:
            try:
                # Check all registered processes
                for name in list(self.processes.keys()):
                    self._check_process(name)
                
                # Log health status
                self._log_health_status()
                
                # Sleep before next check
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}", exc_info=True)
                time.sleep(self.check_interval * 2)
    
    def _check_process(self, name: str):
        """
        Check if a process is running.
        
        Args:
            name: Process name
        """
        process_info = self.processes[name]
        pid = process_info['pid']
        
        # Check if process exists
        if not self._process_exists(pid):
            logger.warning(f"Process {name} (PID: {pid}) is not running")
            
            # Try to restart
            self._attempt_restart(name)
        else:
            # Check process health
            try:
                proc = psutil.Process(pid)
                
                # Check CPU/Memory usage
                cpu_percent = proc.cpu_percent(interval=1)
                memory_info = proc.memory_info()
                
                if cpu_percent > 90:
                    logger.warning(f"Process {name} high CPU usage: {cpu_percent}%")
                
                if memory_info.rss > 1024 * 1024 * 500:  # 500 MB
                    logger.warning(f"Process {name} high memory usage: {memory_info.rss / 1024 / 1024:.1f} MB")
                
                process_info['status'] = 'healthy'
                
            except Exception as e:
                logger.error(f"Error checking process {name}: {e}")
    
    def _process_exists(self, pid: int) -> bool:
        """
        Check if a process with given PID exists.
        
        Args:
            pid: Process ID
            
        Returns:
            True if process exists
        """
        try:
            return psutil.pid_exists(pid)
        except Exception:
            return False
    
    def _attempt_restart(self, name: str):
        """
        Attempt to restart a failed process.
        
        Args:
            name: Process name
        """
        process_info = self.processes[name]
        restart_count = self.restart_count.get(name, 0)
        
        # Check max restarts
        if restart_count >= self.max_restarts:
            logger.error(f"Process {name} exceeded max restart attempts ({self.max_restarts})")
            logger.error(f"Manual intervention required for {name}")
            
            # Alert
            self._alert_critical_failure(name, restart_count)
            return
        
        # Calculate backoff
        backoff = self.restart_backoff * (2 ** restart_count)  # Exponential backoff
        logger.info(f"Restarting {name} (attempt {restart_count + 1}/{self.max_restarts}) after {backoff}s")
        
        time.sleep(backoff)
        
        # Attempt restart
        try:
            logger.info(f"Starting process: {' '.join(process_info['restart_command'])}")
            
            new_process = subprocess.Popen(
                process_info['restart_command'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True
            )
            
            # Update process info
            process_info['pid'] = new_process.pid
            process_info['status'] = 'restarted'
            process_info['last_restart'] = datetime.utcnow()
            process_info['restart_count'] += 1
            
            self.restart_count[name] = restart_count + 1
            
            logger.info(f"Successfully restarted {name} (new PID: {new_process.pid})")
            
            # Log event
            self.vault_manager.log_event(
                event_type="process_restarted",
                task_id=name,
                details={
                    'old_pid': process_info['pid'],
                    'new_pid': new_process.pid,
                    'restart_attempt': restart_count + 1,
                },
                agent="watchdog"
            )
            
        except Exception as e:
            logger.error(f"Failed to restart {name}: {e}", exc_info=True)
    
    def _log_health_status(self):
        """Log overall health status."""
        try:
            healthy_count = sum(
                1 for p in self.processes.values()
                if p['status'] == 'healthy'
            )
            
            total_count = len(self.processes)
            health_status = 'healthy' if healthy_count == total_count else 'degraded'
            
            logger.debug(f"Health status: {health_status} ({healthy_count}/{total_count} processes)")
            
            # Log to vault
            self.vault_manager.log_event(
                event_type="watchdog_health_check",
                details={
                    'healthy': healthy_count,
                    'total': total_count,
                    'status': health_status,
                },
                agent="watchdog"
            )
            
        except Exception as e:
            logger.error(f"Error logging health status: {e}")
    
    def _alert_critical_failure(self, name: str, restart_count: int):
        """
        Alert about critical process failure.
        
        Args:
            name: Process name
            restart_count: Number of restart attempts
        """
        message = f"CRITICAL: Process {name} failed after {restart_count} restart attempts"
        logger.critical(message)
        
        # Log event
        self.vault_manager.log_event(
            event_type="critical_process_failure",
            task_id=name,
            details={
                'restart_attempts': restart_count,
                'max_allowed': self.max_restarts,
                'requires_manual_intervention': True,
            },
            agent="watchdog"
        )
        
        # Would send alert (email, SMS, etc.)
        # self._send_alert(message)
    
    def get_status(self) -> Dict:
        """Get watchdog status."""
        return {
            'running': self.running,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'processes': {
                name: {
                    'status': info['status'],
                    'pid': info['pid'],
                    'restart_count': info['restart_count'],
                    'started_at': info['started_at'].isoformat() if info['started_at'] else None,
                }
                for name, info in self.processes.items()
            },
        }
    
    def stop(self):
        """Stop the watchdog."""
        logger.info("Stopping watchdog...")
        self.running = False
        logger.info("=== Watchdog Stopped ===")


if __name__ == "__main__":
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    watchdog = Watchdog(check_interval=30)
    
    # Example: Register processes to monitor
    # watchdog.register_process('server', 12345, ['python3', 'server.py'])
    # watchdog.register_process('orchestrator', 12346, ['python3', 'orchestrator.py'])
    
    try:
        watchdog.start()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Watchdog failed: {e}", exc_info=True)
        sys.exit(1)
