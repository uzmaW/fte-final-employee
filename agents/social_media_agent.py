"""
Social Media Agent - Handles posting, scheduling, engagement tracking.
"""

import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.base_agent_http import BaseAgentHTTP

logger = logging.getLogger(__name__)


class SocialMediaAgent(BaseAgentHTTP):
    """
    Social Media agent for content distribution and engagement.

    Responsibilities:
    - Post to Twitter, LinkedIn
    - Schedule posts
    - Track engagement metrics
    - Monitor mentions
    """

    def __init__(self, mcp_url: str = "http://localhost:8000", poll_interval: int = 1800):
        super().__init__(
            name="social-media-agent",
            mcp_url=mcp_url,
            poll_interval=poll_interval
        )
        self._posted_content = set()  # Track posted content to avoid duplicates

    def poll(self) -> List[Dict[str, Any]]:
        """
        Poll vault for social media content.

        Looks for:
        - Social/Drafts/ folder with markdown files
        - Files with platform, status, and content frontmatter
        """
        items = []

        try:
            drafts_dir = self.vault_manager.vault_path / "Social" / "Drafts"
            if not drafts_dir.exists():
                return items

            for content_file in drafts_dir.glob("*.md"):
                content = content_file.read_text()
                frontmatter = self._parse_frontmatter(content)

                # Only process 'ready' status
                if frontmatter.get('status') != 'ready':
                    continue

                # Skip if already posted
                content_id = f"{content_file.stem}_{frontmatter.get('platform', 'all')}"
                if content_id in self._posted_content:
                    continue

                items.append({
                    'id': content_id,
                    'file': content_file,
                    'frontmatter': frontmatter,
                    'content': self._extract_content(content)
                })

            logger.debug(f"Found {len(items)} social media items")
            return items

        except Exception as e:
            logger.error(f"Error polling for social content: {e}")
            return []

    def process_item(self, item: Dict[str, Any]) -> Optional[str]:
        """Post social media content."""
        try:
            frontmatter = item['frontmatter']
            content = item['content']
            platform = frontmatter.get('platform', 'all').lower()

            platforms = [platform] if platform != 'all' else ['twitter', 'linkedin']

            for plat in platforms:
                if plat == 'twitter':
                    result = self._post_twitter(content)
                    if not result.get('success'):
                        return None

                elif plat == 'linkedin':
                    result = self._post_linkedin(content)
                    if not result.get('success'):
                        return None

            # Mark as posted
            self._posted_content.add(item['id'])

            # Move to Posted folder
            posted_dir = self.vault_manager.vault_path / "Social" / "Posted"
            posted_dir.mkdir(parents=True, exist_ok=True)
            item['file'].rename(posted_dir / item['file'].name)

            logger.info(f"✅ Posted to {platform}: {item['file'].name}")
            return str(item['file'])

        except Exception as e:
            logger.error(f"Error processing social media item: {e}")
            return None

    def _post_twitter(self, text: str) -> Dict[str, Any]:
        """Post to Twitter."""
        try:
            # Truncate to 280 chars
            text = text[:280]

            result = self._mcp_call(
                "POST",
                "/api/social/post-twitter",
                text=text
            )

            return result
        except Exception as e:
            logger.error(f"Error posting to Twitter: {e}")
            return {'success': False, 'error': str(e)}

    def _post_linkedin(self, text: str) -> Dict[str, Any]:
        """Post to LinkedIn."""
        try:
            result = self._mcp_call(
                "POST",
                "/api/social/post-linkedin",
                text=text
            )

            return result
        except Exception as e:
            logger.error(f"Error posting to LinkedIn: {e}")
            return {'success': False, 'error': str(e)}

    def _parse_frontmatter(self, content: str) -> Dict[str, Any]:
        """Parse YAML frontmatter."""
        frontmatter = {}
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 2:
                for line in parts[1].split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        frontmatter[key.strip()] = value.strip()
        return frontmatter

    def _extract_content(self, content: str) -> str:
        """Extract content after frontmatter."""
        if '---' in content:
            parts = content.split('---', 2)
            return parts[2].strip() if len(parts) > 2 else ""
        return content


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)

    agent = SocialMediaAgent()
    agent.run_once()