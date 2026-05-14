"""
linkedin_watcher.py - Monitors LinkedIn for business opportunities and triggers posts.

From the hackathon PDF Silver Tier:
  "Automatically Post on LinkedIn about business to generate sales"

This watcher:
1. Monitors for business milestones reached (reads Business_Goals.md)
2. Detects new blog posts / content to share
3. Creates action files for LinkedIn posting
4. Suggests engagement with connections' activity
"""

import time
import logging
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import re

from orchestrator.base_watcher import BaseWatcher
from config import get_settings
from utilities.vault_manager import VaultManager

logger = logging.getLogger(__name__)


class LinkedInWatcher(BaseWatcher):
    """
    Monitors LinkedIn for business opportunities and creates posting tasks.
    
    Two modes of operation:
    1. Sales generation: Detects milestones and creates promotional posts
    2. Content sharing: Monitors for new content to share on LinkedIn
    """
    
    # Keywords indicating a new blog post or content to share
    CONTENT_KEYWORDS = [
        'new blog post', 'article published', 'guide published',
        'research paper', 'whitepaper', 'case study', 'webinar',
        'product launch', 'feature release', 'changelog', 'release notes'
    ]
    
    # Milestone keywords that trigger celebratory posts
    MILESTONE_KEYWORDS = [
        'milestone', 'anniversary', 'achievement', 'reached',
        'crossed', 'surpassed', 'exceeded', 'hit', 'unlocked',
        'completed', 'acquired', 'partnership', 'funding',
        'growth', 'expansion', 'launch', 'record'
    ]
    
    # Sales-generating post templates
    SALES_TEMPLATES = {
        'milestone': """🏆 Milestone Alert!

We just {action} at {company}!

📊 Stats:
• {metric_1}: {value_1}
• {metric_2}: {value_2}

This wouldn't be possible without our amazing team and customers.

Want to achieve similar results? Let's talk → {cta_link}

#B2B #SaaS #Growth #Milestone""",
        'case_study': """📖 New Case Study: {title}

{client} achieved {result} using our solution.

The challenge:
{challenge}

The solution:
{solution}

The impact:
{impact}

Read the full story: {link}

#CaseStudy #B2B #Results""",
        'product_update': """🚀 Product Update: {feature_name}

We just shipped: {description}

Key benefits:
• {benefit_1}
• {benefit_2}
• {benefit_3}

Try it now: {link}

#ProductLaunch #Innovation #SaaS"""
    }
    
    def __init__(
        self,
        vault_path: str,
        check_interval: int = 900,  # Check every 15 minutes
        api_key: Optional[str] = None,
        company_page_id: Optional[str] = None,
        track_competitors: bool = False
    ):
        """
        Initialize LinkedIn watcher.
        
        Args:
            vault_path: Path to Obsidian vault
            check_interval: Seconds between checks (default: 900 = 15 min)
            api_key: LinkedIn API key (from .env)
            company_page_id: LinkedIn company page ID
            track_competitors: Also monitor competitor pages
        """
        super().__init__(
            name="linkedin",
            poll_interval=check_interval
        )
        
        self.vault_path = Path(vault_path)
        self.api_key = api_key
        self.company_page_id = company_page_id
        self._track_competitors = track_competitors
        self.vault_manager = VaultManager(vault_path)
        
        # Track processed content to avoid duplicates
        self._processed_content: set = set()
        self._load_processed_content()
        
        # Stats
        self._stats = {
            'total_checks': 0,
            'milestones_detected': 0,
            'content_detected': 0,
            'posts_created': 0,
            'last_check': None
        }
    
    def _load_processed_content(self):
        """Load previously processed content IDs."""
        id_file = self.vault_path / '.linkedin' / 'processed.json'
        if id_file.exists():
            try:
                self._processed_content = set(json.loads(id_file.read_text()))
                logger.info(f"Loaded {len(self._processed_content)} processed content IDs")
            except Exception as e:
                logger.warning(f"Could not load processed content: {e}")
    
    def _save_processed_content(self):
        """Save processed content IDs."""
        try:
            id_file = self.vault_path / '.linkedin' / 'processed.json'
            id_file.parent.mkdir(parents=True, exist_ok=True)
            recent = set(list(self._processed_content)[-1000:])
            id_file.write_text(json.dumps(list(recent)))
        except Exception as e:
            logger.warning(f"Could not save processed content: {e}")
    
    def check_for_updates(self) -> List[Dict[str, Any]]:
        """
        Check for LinkedIn-worthy events and content.
        
        Returns:
            List of action item dictionaries
        """
        self._stats['total_checks'] += 1
        actions = []
        
        try:
            # 1. Check Business_Goals.md for reached milestones
            milestone_actions = self._check_milestones()
            actions.extend(milestone_actions)
            
            # 2. Check for new blog posts / content in vault
            content_actions = self._check_new_content()
            actions.extend(content_actions)
            
            # 3. Check for competitor activity (if enabled)
            if self._track_competitors:
                competitor_actions = self._check_competitor_activity()
                actions.extend(competitor_actions)
            
            # 4. Check for engagement opportunities
            engagement_actions = self._check_engagement_opportunities()
            actions.extend(engagement_actions)
            
        except Exception as e:
            logger.error(f"Error in LinkedIn check: {e}", exc_info=True)
        
        self._stats['last_check'] = datetime.now().isoformat()
        return actions
    
    def _check_milestones(self) -> List[Dict[str, Any]]:
        """
        Read Business_Goals.md and detect milestones that should be celebrated.
        
        Returns:
            List of milestone action dictionaries
        """
        actions = []
        goals_file = self.vault_path / 'Business_Goals.md'
        
        if not goals_file.exists():
            return actions
        
        try:
            content = goals_file.read_text()
            
            # Look for recently completed milestones
            # Pattern: lines containing ✓ or "completed" or milestone indicators
            lines = content.split('\n')
            current_milestone = None
            
            for i, line in enumerate(lines):
                line_lower = line.lower()
                
                # Check for completed items
                if '✅' in line or '[x]' in line.lower():
                    # Extract the milestone text
                    milestone_text = line.strip()
                    # Remove markdown checkboxes
                    milestone_text = re.sub(r'[-*]\s*\[[ xX]\]', '', milestone_text).strip()
                    
                    if any(kw in line_lower for kw in self.MILESTONE_KEYWORDS):
                        current_milestone = milestone_text
                        actions.append({
                            'type': 'milestone',
                            'content': milestone_text,
                            'timestamp': datetime.now().isoformat(),
                            'priority': 'high',
                            'template': 'milestone'
                        })
                        self._stats['milestones_detected'] += 1
                        logger.info(f"Milestone detected: {milestone_text[:60]}...")
                        
        except Exception as e:
            logger.error(f"Error checking milestones: {e}")
        
        return actions
    
    def _check_new_content(self) -> List[Dict[str, Any]]:
        """
        Check for new blog posts, articles, or content in the vault.
        
        Returns:
            List of content action dictionaries
        """
        actions = []
        
        # Check for content files in designated folders
        content_dirs = [
            self.vault_path / 'Content',
            self.vault_path / 'Blog',
            self.vault_path / 'Articles',
            self.vault_path / 'Published'
        ]
        
        for content_dir in content_dirs:
            if not content_dir.exists():
                continue
                
            for file_path in content_dir.glob('*.md'):
                content_id = f"content_{file_path.stem}"
                if content_id in self._processed_content:
                    continue
                
                try:
                    content = file_path.read_text()
                    frontmatter = self._parse_frontmatter(content)
                    
                    actions.append({
                        'type': 'content',
                        'title': frontmatter.get('title', file_path.stem),
                        'path': str(file_path),
                        'date': frontmatter.get('date', datetime.now().isoformat()),
                        'summary': self._extract_summary(content),
                        'priority': 'medium',
                        'template': 'content_share'
                    })
                    self._stats['content_detected'] += 1
                    self._processed_content.add(content_id)
                    
                except Exception as e:
                    logger.error(f"Error processing content file {file_path}: {e}")
        
        return actions
    
    def _check_competitor_activity(self) -> List[Dict[str, Any]]:
        """
        Monitor competitor LinkedIn pages for activity.
        
        Returns:
            List of competitor activity action dictionaries
        """
        # This would integrate with LinkedIn API to monitor competitor pages
        # For now, create a placeholder action structure
        actions = []
        
        # Example: detect when competitor posts a major update
        competitors_file = self.vault_path / 'Competitors.md'
        if competitors_file.exists():
            # Parse competitor tracking file and create monitoring tasks
            pass
        
        return actions
    
    def _check_engagement_opportunities(self) -> List[Dict[str, Any]]:
        """
        Identify opportunities to engage with relevant LinkedIn content.
        
        Returns:
            List of engagement action dictionaries
        """
        actions = []
        
        # Check for mentions of our brand/company
        mentions_file = self.vault_path / 'Mentions.md'
        if mentions_file.exists():
            try:
                content = mentions_file.read_text()
                # Parse mentions and create engagement tasks
                if 'mention' in content.lower():
                    actions.append({
                        'type': 'engagement',
                        'action': 'respond_to_mention',
                        'timestamp': datetime.now().isoformat(),
                        'priority': 'medium',
                    })
            except Exception as e:
                logger.error(f"Error checking engagement: {e}")
        
        return actions
    
    def create_action_file(self, action: Dict[str, Any]) -> Path:
        """
        Create a LinkedIn task file in Needs_Action folder.
        
        Args:
            action: Action dictionary from check_for_updates
            
        Returns:
            Path to the created action file
        """
        action_type = action.get('type', 'unknown')
        timestamp = action.get('timestamp', datetime.now().isoformat())
        
        if action_type == 'milestone':
            task_id = f"LINKEDIN_MILESTONE_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            content = f"""## LinkedIn Milestone Post

**Milestone:** {action.get('content', 'Unknown')}
**Detected:** {timestamp}
**Priority:** {action.get('priority', 'normal')}

## Suggested Post

Use template: {action.get('template', 'milestone')}

## Action
- [ ] Review milestone details
- [ ] Customize post copy
- [ ] Add relevant image/visual
- [ ] Submit for approval
- [ ] Post to LinkedIn

---

*Auto-detected by LinkedInWatcher*
"""
        elif action_type == 'content':
            task_id = f"LINKEDIN_CONTENT_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            content = f"""## LinkedIn Content Sharing

**Title:** {action.get('title', 'Unknown')}
**Source:** {action.get('path', 'Unknown')}
**Summary:** {action.get('summary', 'No summary')}
**Detected:** {timestamp}
**Priority:** {action.get('priority', 'normal')}

## Suggested Post

Share this content on LinkedIn with a brief commentary.

## Action
- [ ] Review content summary
- [ ] Write engaging LinkedIn post
- [ ] Add link to content
- [ ] Submit for approval
- [ ] Post to LinkedIn

---

*Auto-detected by LinkedInWatcher*
"""
        else:
            task_id = f"LINKEDIN_{action_type.upper()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            content = f"""## LinkedIn Task

**Type:** {action_type}
**Detected:** {timestamp}
**Priority:** {action.get('priority', 'normal')}

## Details

{json.dumps(action, indent=2, default=str)}

## Action
- [ ] Review and create LinkedIn post
- [ ] Submit for approval

---

*Auto-detected by LinkedInWatcher*
"""
        
        frontmatter = {
            'type': 'linkedin_task',
            'action_type': action_type,
            'created': timestamp,
            'priority': action.get('priority', 'normal'),
            'status': 'pending',
        }
        
        filename = f"{task_id}.md"
        filepath = self.needs_action / filename
        
        # Write with frontmatter
        yaml_lines = ['---']
        for key, value in frontmatter.items():
            yaml_lines.append(f'{key}: {value}')
        yaml_lines.append('---')
        full_content = f"{'\n'.join(yaml_lines)}\n\n{content}"
        filepath.write_text(full_content)
        
        self._stats['posts_created'] += 1
        logger.info(f"Created LinkedIn task: {filename}")
        return filepath
    
    def _parse_frontmatter(self, content: str) -> Dict[str, Any]:
        """Parse YAML frontmatter from markdown content."""
        frontmatter = {}
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                for line in parts[1].split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        frontmatter[key.strip()] = value.strip()
        return frontmatter
    
    def _extract_summary(self, content: str) -> str:
        """Extract first paragraph as summary."""
        lines = content.split('\n')
        summary_lines = []
        in_frontmatter = content.startswith('---')
        in_body = False
        
        for line in lines:
            if in_frontmatter and line == '---':
                in_frontmatter = False
                in_body = True
                continue
            if in_body and line.strip():
                if not line.startswith('#'):
                    summary_lines.append(line.strip())
                    if len(summary_lines) >= 3:
                        break
        
        return ' '.join(summary_lines)[:300]
    
    def run_once(self):
        """Override base class run_once for LinkedIn-specific behavior."""
        try:
            actions = self.check_for_updates()
            for action in actions:
                try:
                    filepath = self.create_action_file(action)
                    self.logger.info(f"Created LinkedIn action file: {filepath.name}")
                except Exception as e:
                    self.logger.error(f"Error creating LinkedIn action file: {e}")
        except Exception as e:
            self.logger.error(f"Error in LinkedIn watcher run_once: {e}", exc_info=True)
        
        self._save_processed_content()
    
    def get_stats(self) -> dict:
        """Return current watcher statistics."""
        return {
            **self._stats,
            'processed_content_count': len(self._processed_content),
        }


# ─── Standalone Execution ────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    
    vault = 'AI_Employee_Vault'
    if len(sys.argv) > 1:
        vault = sys.argv[1]
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    watcher = LinkedInWatcher(vault_path=vault)
    print("LinkedIn Watcher started. Press Ctrl+C to stop.")
    
    try:
        watcher.run()
    except KeyboardInterrupt:
        print(f"\nStats: {json.dumps(watcher.get_stats(), indent=2, default=str)}")
        print("Stopped.")