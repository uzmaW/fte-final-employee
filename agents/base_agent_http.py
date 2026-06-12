"""
Base agent class with HTTP MCP server integration.
All specialized agents extend this.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

import httpx

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_settings
from utilities.vault_manager import VaultManager
from orchestrator.base_watcher import BaseWatcher

logger = logging.getLogger(__name__)


class BaseAgentHTTP(BaseWatcher, ABC):
    """
    Base agent that communicates with MCP servers via HTTP.

    All specialized agents inherit from this and implement:
    - poll(): Fetch new items to process
    - process_item(): Process a single item
    """

    def __init__(
        self,
        name: str,
        mcp_url: str = "http://localhost:8000",
        poll_interval: int = 300
    ):
        super().__init__(name=name, poll_interval=poll_interval)
        self.mcp_url = mcp_url
        self.client = httpx.Client(base_url=mcp_url, timeout=30.0)
        self.settings = get_settings()
        self.vault_manager = VaultManager()

        logger.info(f"✅ Agent '{name}' initialized (MCP: {mcp_url})")

    def _mcp_call(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Call MCP server endpoint.

        Args:
            method: 'GET', 'POST'
            endpoint: API endpoint (e.g., '/api/payment/process')
            **kwargs: Query params or JSON body

        Returns:
            Response dict
        """
        try:
            if method == "GET":
                response = self.client.get(endpoint, params=kwargs)
            elif method == "POST":
                response = self.client.post(endpoint, json=kwargs)
            else:
                raise ValueError(f"Unsupported method: {method}")

            response.raise_for_status()
            return response.json()

        except httpx.ConnectError:
            logger.error(f"❌ Cannot connect to MCP server at {self.mcp_url}")
            return {'success': False, 'error': 'MCP server unavailable'}
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ MCP call failed: {e.response.status_code}")
            return {'success': False, 'error': str(e)}
        except Exception as e:
            logger.error(f"❌ Error calling MCP: {e}")
            return {'success': False, 'error': str(e)}

    def check_mcp_health(self) -> bool:
        """Check if MCP server is healthy."""
        try:
            response = self.client.get("/health", timeout=5.0)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"MCP health check failed: {e}")
            return False

    @abstractmethod
    def poll(self) -> List[Dict[str, Any]]:
        """Poll for new items to process. Must be implemented by subclass."""
        pass

    @abstractmethod
    def process_item(self, item: Dict[str, Any]) -> Optional[str]:
        """Process a single item. Must be implemented by subclass."""
        pass

    def run_once(self) -> int:
        """Run one iteration of polling and processing."""
        if not self.running:
            self.running = True

        items = self.poll()
        processed = 0

        for item in items:
            result = self.process_item(item)
            if result:
                processed += 1

        return processed

    def stop(self):
        """Stop the agent."""
        self.running = False

    def __del__(self):
        """Cleanup HTTP client."""
        try:
            self.client.close()
        except Exception:
            pass