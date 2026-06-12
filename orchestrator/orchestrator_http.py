"""
Multi-agent orchestrator coordinating 6 specialized agents via HTTP MCP servers.
"""

import logging
import time
import signal
import json
from typing import Dict, List, Any

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_settings
from utilities.vault_manager import VaultManager
from agents.base_agent_http import BaseAgentHTTP
from agents.finance_agent import FinanceAgent
from agents.social_media_agent import SocialMediaAgent

logger = logging.getLogger(__name__)


class MultiAgentOrchestrator:
    """Orchestrates 6 specialized agents."""

    def __init__(self, mcp_url: str = "http://localhost:8000"):
        """Initialize orchestrator with all agents."""
        self.settings = get_settings()
        self.vault_manager = VaultManager()
        self.mcp_url = mcp_url
        self.running = False
        self.agents: List[BaseAgentHTTP] = []
        self.last_run: Dict[str, float] = {}

        logger.info("=" * 70)
        logger.info("🚀 AI Employee Multi-Agent Orchestrator")
        logger.info("=" * 70)

        # Initialize agents
        self._initialize_agents()

    def _initialize_agents(self):
        """Initialize all agents."""
        # Note: Other agents (audit_review, odoo, decision_review, local_operations)
        # would be added here once implemented
        agents_config = [
            ("finance", FinanceAgent, {"poll_interval": 60}),
            ("social-media", SocialMediaAgent, {"poll_interval": 1800}),
        ]

        for name, agent_class, kwargs in agents_config:
            try:
                agent = agent_class(mcp_url=self.mcp_url, **kwargs)
                self.agents.append(agent)
                logger.info(f"✅ Initialized agent: {name}")
            except Exception as e:
                logger.error(f"❌ Failed to initialize agent {name}: {e}")

        logger.info(f"\n✅ Orchestrator ready with {len(self.agents)} agents\n")

    def start(self):
        """Start the orchestrator."""
        logger.info("Starting orchestrator main loop...")
        self.running = True

        try:
            # Register signal handlers
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)

            # Main loop
            self._main_loop()

        except Exception as e:
            logger.error(f"Orchestrator error: {e}", exc_info=True)
        finally:
            self.stop()

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"\n📋 Received signal {signum}, shutting down...")
        self.running = False

    def _main_loop(self):
        """Main orchestration loop."""
        logger.info("Orchestrator main loop started")
        iteration = 0

        while self.running:
            try:
                iteration += 1
                logger.debug(f"\n--- Iteration {iteration} ({datetime.now().isoformat()}) ---")

                # Run each agent (only if poll interval has passed)
                for agent in self.agents:
                    agent_key = agent.name
                    last_run = self.last_run.get(agent_key, 0)
                    current_time = time.time()

                    if current_time - last_run >= agent.poll_interval:
                        try:
                            logger.debug(f"Running agent: {agent_key}")
                            processed = agent.run_once()
                            if processed > 0:
                                logger.info(f"  → {agent_key}: processed {processed} items")
                            self.last_run[agent_key] = current_time

                        except Exception as e:
                            logger.error(f"  ✗ {agent_key} error: {e}", exc_info=True)

                # Health check
                self._health_check()

                # Sleep before next iteration
                time.sleep(10)

            except KeyboardInterrupt:
                self.running = False
            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
                time.sleep(30)  # Back off on error

    def _health_check(self):
        """Perform system health check."""
        try:
            from datetime import datetime

            health = {
                'timestamp': datetime.utcnow().isoformat(),
                'agents_running': len([a for a in self.agents if a.running]),
                'agents_total': len(self.agents),
                'vault': {
                    'needs_action': 0,
                    'in_progress': 0,
                    'pending_approval': 0,
                    'done': 0,
                }
            }

            # Count vault items
            for folder, key in [
                ("Needs_Action", "needs_action"),
                ("In_Progress", "in_progress"),
                ("Pending_Approval", "pending_approval"),
                ("Done", "done"),
            ]:
                path = self.vault_manager.vault_path / folder
                if path.exists():
                    health['vault'][key] = len(list(path.glob("*.md")))

            # Log health status
            self.vault_manager.log_event(
                event_type="health_check",
                details=health,
                agent="orchestrator"
            )

            logger.debug(f"Health: {json.dumps(health['vault'], indent=2)}")

        except Exception as e:
            logger.error(f"Health check error: {e}")

    def stop(self):
        """Stop the orchestrator and all agents."""
        logger.info("\n" + "=" * 70)
        logger.info("🛑 Shutting Down Orchestrator")
        logger.info("=" * 70)

        self.running = False

        # Stop all agents
        for agent in self.agents:
            try:
                agent.stop()
                logger.info(f"✅ Stopped agent: {agent.name}")
            except Exception as e:
                logger.error(f"Error stopping agent {agent.name}: {e}")

        logger.info("✅ Orchestrator stopped")

    def get_status(self) -> Dict[str, Any]:
        """Get orchestrator and agents status."""
        from datetime import datetime
        return {
            'running': self.running,
            'timestamp': datetime.utcnow().isoformat(),
            'agents': [
                {
                    'name': agent.name,
                    'running': agent.running,
                    'poll_interval': agent.poll_interval,
                    'error_count': agent.error_count,
                }
                for agent in self.agents
            ]
        }


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    )

    orchestrator = MultiAgentOrchestrator(
        mcp_url=sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    )

    try:
        orchestrator.start()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Orchestrator failed: {e}", exc_info=True)
        sys.exit(1)