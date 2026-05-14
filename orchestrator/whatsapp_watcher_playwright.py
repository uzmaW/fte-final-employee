"""
whatsapp_watcher_playwright.py - Playwright-based WhatsApp Web watcher.

From the hackathon PDF §2A:
  Uses Playwright for browser automation to monitor WhatsApp Web directly.
  This runs alongside the Twilio-based watcher as an alternative approach.
"""

import time
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestrator.base_watcher import BaseWatcher
from config import get_settings

logger = logging.getLogger(__name__)


class WhatsAppWebWatcher(BaseWatcher):
    """
    Monitors WhatsApp Web via Playwright browser automation.
    
    This approach:
    - Launches a persistent browser context (keeps WhatsApp session alive)
    - Periodically checks for new unread messages
    - Creates task files in Needs_Action for Claude to process
    
    Requires:
    - Playwright installed and browsers downloaded (playwright install chromium)
    - WhatsApp Web session (first run requires QR code scan)
    
    Usage:
        python whatsapp_watcher_playwright.py
        
    Or as a module:
        from orchestrator.whatsapp_watcher_playwright import WhatsAppWebWatcher
        watcher = WhatsAppWebWatcher(vault_path='/path/to/vault')
        watcher.run()
    """
    
    # Keywords that trigger priority processing
    PRIORITY_KEYWORDS = [
        'urgent', 'asap', 'invoice', 'payment', 'help',
        'deadline', 'important', 'emergency', 'right away',
        'please send', 'can you', 'need this', 'as soon'
    ]
    
    # CSS selectors for WhatsApp Web elements
    SELECTORS = {
        'chat_list': '[data-testid="chat-list"]',
        'unread_indicator': '[aria-label*="unread"]',
        'chat_title': '[data-testid="cell-frame-title"]',
        'chat_preview': '[data-testid="cell-frame-description"]',
        'last_message': '[data-testid="last-msg-container"]',
        'search_input': '[data-testid="chat-search"]',
        'message_input': '[data-testid="conversation-compose-box-input"]',
        'send_button': '[data-testid="conversation-compose-box-send"]',
    }

    def __init__(
        self,
        vault_path: str,
        session_dir: str = '.whatsapp_sessions',
        check_interval: int = 60,
        headless: bool = True,
        user_data_dir: Optional[str] = None,
        keywords: Optional[List[str]] = None
    ):
        """
        Initialize the Playwright-based WhatsApp Web watcher.
        
        Args:
            vault_path: Path to Obsidian vault
            session_dir: Directory to store browser session data
            check_interval: Seconds between checks (default: 60)
            headless: Run browser in headless mode (default: True)
            user_data_dir: Custom user data directory for browser profile
            keywords: Custom keywords to filter for priority messages
        """
        super().__init__(
            name="whatsapp_web",
            poll_interval=check_interval
        )
        
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(parents=True, exist_ok=True)
        
        self._session_file = self.session_dir / 'whatsapp_session'
        self._headless = headless
        self._user_data_dir = user_data_dir
        self._keywords = keywords or self.PRIORITY_KEYWORDS
        self._browser = None
        self._context = None
        self._page = None
        
        # Track processed messages to avoid duplicates
        self._processed_messages: set = set()
        self._load_processed_ids()
        
        # Stats
        self._stats = {
            'total_checks': 0,
            'messages_found': 0,
            'messages_processed': 0,
            'last_check': None,
            'started_at': datetime.now().isoformat()
        }
    
    def _load_processed_ids(self):
        """Load previously processed message IDs from disk."""
        id_file = self.session_dir / 'processed_ids.json'
        if id_file.exists():
            try:
                self._processed_messages = set(json.loads(id_file.read_text()))
                logger.info(f"Loaded {len(self._processed_messages)} previously processed message IDs")
            except Exception as e:
                logger.warning(f"Could not load processed IDs: {e}")
    
    def _save_processed_ids(self):
        """Save processed message IDs to disk."""
        try:
            id_file = self.session_dir / 'processed_ids.json'
            # Keep only recent IDs to prevent unbounded growth
            recent_ids = set(list(self._processed_messages)[-500:])
            id_file.write_text(json.dumps(list(recent_ids), indent=2))
        except Exception as e:
            logger.warning(f"Could not save processed IDs: {e}")
    
    def _init_browser(self):
        """Initialize or reinitialize the browser instance."""
        try:
            if self._browser is not None:
                try:
                    self._browser.close()
                except Exception:
                    pass
            
            playwright = sync_playwright().start()
            
            launch_options = {
                'headless': self._headless,
                'timeout': 30000,
            }
            
            if self._user_data_dir:
                launch_options['user_data_dir'] = self._user_data_dir
                # Use persistent context with user data dir
                self._browser = playwright.chromium.launch(**launch_options)
                self._context = self._browser.new_context(
                    viewport={'width': 1280, 'height': 800},
                    locale='en-US',
                    timezone_id='UTC'
                )
            else:
                # Use server-side browser (no user data)
                self._browser = playwright.chromium.launch(**launch_options)
                self._context = self._browser.new_context(
                    viewport={'width': 1280, 'height': 800},
                    locale='en-US',
                    timezone_id='UTC',
                    storage_state=str(self._session_file) if self._session_file.exists() else None
                )
            
            self._page = self._context.pages[0] if self._context.pages else self._context.new_page()
            logger.info("Browser initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize browser: {e}")
            return False
    
    def _navigate_to_whatsapp(self) -> bool:
        """Navigate to WhatsApp Web and wait for it to load."""
        try:
            self._page.goto('https://web.whatsapp.com', timeout=60000)
            
            # Wait for the chat list to load
            self._page.wait_for_selector(
                self.SELECTORS['chat_list'],
                timeout=30000
            )
            
            # Small delay for initial rendering
            time.sleep(3)
            
            logger.info("WhatsApp Web loaded successfully")
            return True
            
        except PlaywrightTimeout:
            logger.warning("Timeout waiting for WhatsApp Web to load")
            return False
        except Exception as e:
            logger.error(f"Error navigating to WhatsApp: {e}")
            return False
    
    def check_for_updates(self) -> List[Dict[str, Any]]:
        """
        Check for new WhatsApp messages.
        
        Returns:
            List of message dictionaries with sender, text, and metadata
        """
        self._stats['total_checks'] += 1
        messages = []
        
        try:
            if not self._page or self._page.is_closed():
                if not self._init_browser():
                    return messages
                if not self._navigate_to_whatsapp():
                    return messages
            
            # Keep session alive
            try:
                self._page.reload(timeout=30000)
                time.sleep(2)
            except Exception:
                # Page might already be in good state
                pass
            
            # Find all chat elements with unread indicators
            unread_chats = self._page.query_selector_all(
                self.SELECTORS['unread_indicator']
            )
            
            for chat_element in unread_chats:
                try:
                    # Get the parent chat container
                    chat = chat_element.evaluate_handle(
                        'el => el.closest("[data-testid^=cell-frame-]")'
                    )
                    
                    if not chat:
                        continue
                    
                    # Extract sender name
                    sender_elem = chat.query_selector(self.SELECTORS['chat_title'])
                    sender = sender_elem.inner_text() if sender_elem else "Unknown"
                    
                    # Extract message preview
                    preview_elem = chat.query_selector(self.SELECTORS['chat_preview'])
                    preview_text = preview_elem.inner_text() if preview_elem else ""
                    
                    # Extract timestamp
                    last_msg_elem = chat.query_selector(self.SELECTORS['last_message'])
                    timestamp_str = ""
                    if last_msg_elem:
                        timestamp_attr = last_msg_elem.get_attribute('data-testid') or ""
                        timestamp_str = datetime.now().isoformat()
                    
                    # Create unique message ID
                    msg_id = f"{sender}_{hash(preview_text[:100])}_{int(time.time())}"
                    
                    # Skip if already processed
                    if msg_id in self._processed_messages:
                        continue
                    
                    messages.append({
                        'sender': sender,
                        'preview': preview_text,
                        'id': msg_id,
                        'timestamp': timestamp_str,
                        'unread': True,
                        'source': 'whatsapp_web'
                    })
                    
                    self._processed_messages.add(msg_id)
                    
                except Exception as e:
                    logger.debug(f"Error processing chat element: {e}")
                    continue
            
            # Also scan all visible chats for keywords (even if read)
            all_chats = self._page.query_selector_all('[data-testid^="cell-frame-"]')
            for chat_element in all_chats[-20:]:  # Check last 20 chats
                try:
                    preview_elem = chat_element.query_selector(self.SELECTORS['chat_preview'])
                    if not preview_elem:
                        continue
                    
                    preview_text = preview_elem.inner_text().lower()
                    
                    # Check for priority keywords
                    if any(kw in preview_text for kw in self._keywords):
                        sender_elem = chat_element.query_selector(self.SELECTORS['chat_title'])
                        sender = sender_elem.inner_text() if sender_elem else "Unknown"
                        
                        # Full message text (click into chat for full content)
                        full_text = self._get_full_message(chat_element, sender)
                        
                        msg_id = f"{sender}_{hash(full_text[:100])}_{int(time.time())}"
                        if msg_id not in self._processed_messages:
                            messages.append({
                                'sender': sender,
                                'preview': full_text[:300],
                                'id': msg_id,
                                'timestamp': datetime.now().isoformat(),
                                'unread': False,
                                'source': 'whatsapp_web_keyword',
                                'keyword_match': True
                            })
                            self._processed_messages.add(msg_id)
                            
                except Exception:
                    continue
            
            self._stats['messages_found'] += len(messages)
            
            # Save processed IDs periodically
            self._save_processed_ids()
            
        except Exception as e:
            logger.error(f"Error in WhatsApp Web check: {e}", exc_info=True)
            # Attempt browser recovery on next check
            self._browser = None
            self._context = None
            self._page = None
        
        self._stats['last_check'] = datetime.now().isoformat()
        return messages
    
    def _get_full_message(self, chat_element, sender: str) -> str:
        """
        Click into a chat and extract the most recent message text.
        
        Args:
            chat_element: The chat list element
            sender: Sender name
            
        Returns:
            The full message text
        """
        try:
            # Click on the chat
            chat_element.click()
            time.sleep(1.5)
            
            # Get message container
            message_selectors = [
                'div[data-testid="msg-container"] div.copyable-text span',
                'div.message-in span[dir="auto"]',
                'div.message-out span[dir="auto"]',
                'div[class*="message-in"] div[class*="text"]',
            ]
            
            for selector in message_selectors:
                try:
                    messages = self._page.query_selector_all(selector)
                    if messages:
                        # Get the last message
                        last_msg = messages[-1].inner_text()
                        return last_msg if last_msg.strip() else ""
                except Exception:
                    continue
            
            return ""
            
        except Exception as e:
            logger.debug(f"Error getting full message from {sender}: {e}")
            return ""
    
    def create_action_file(self, message: Dict[str, Any]) -> Path:
        """
        Create a WHATSAPP_*.md task file in the Needs_Action folder.
        
        Args:
            message: Message dictionary from check_for_updates
            
        Returns:
            Path to the created action file
        """
        frontmatter = {
            'type': 'whatsapp_message',
            'from': message.get('sender', 'Unknown'),
            'received': message.get('timestamp', datetime.now().isoformat()),
            'message_id': message.get('id', 'unknown'),
            'priority': 'high' if message.get('keyword_match') or message.get('unread') else 'normal',
            'status': 'pending',
            'source': message.get('source', 'whatsapp_web'),
        }
        
        # Build content
        content = f"""## Message Preview

**Sender:** {message.get('sender', 'Unknown')}
**Received:** {message.get('timestamp', 'Unknown')}
**Priority:** {frontmatter['priority']}

### Content

{message.get('preview', 'No preview available')}

## Suggested Actions

- [ ] Read full message in WhatsApp Web
- [ ] Determine response type
- [ ] Draft reply (if needed)
- [ ] Send response (requires approval)
- [ ] Archive after processing

---

*Captured by WhatsAppWebWatcher | Source: {message.get('source', 'whatsapp_web')}*
"""
        
        filename = f"WHATSAPP_{message.get('id', datetime.now().strftime('%Y%m%d_%H%M%S'))}.md"
        return self._create_markdown_file(filename, frontmatter, content)
    
    def _create_markdown_file(self, filename: str, frontmatter: dict, content: str) -> Path:
        """Helper to create properly formatted markdown file with YAML frontmatter."""
        yaml_lines = ['---']
        for key, value in frontmatter.items():
            yaml_lines.append(f'{key}: {value}')
        yaml_lines.append('---')
        yaml_section = '\n'.join(yaml_lines)
        full_content = f'{yaml_section}\n\n{content}'
        
        filepath = self.needs_action / filename
        filepath.write_text(full_content)
        self.logger.info(f"Created action file: {filename}")
        return filepath
    
    def run_once(self):
        """Override base class to handle browser lifecycle."""
        try:
            if not self._init_browser():
                logger.error("Browser initialization failed, skipping this cycle")
                return
            
            if not self._navigate_to_whatsapp():
                logger.error("WhatsApp Web navigation failed, skipping this cycle")
                return
            
            messages = self.check_for_updates()
            for msg in messages:
                try:
                    filepath = self.create_action_file(msg)
                    self.logger.info(f"Created action file for: {msg.get('sender')}")
                except Exception as e:
                    self.logger.error(f"Error creating action file: {e}")
                    
        except Exception as e:
            self.logger.error(f"Error in run_once: {e}", exc_info=True)
        finally:
            # Keep browser alive for next cycle (don't close)
            pass
    
    def stop(self):
        """Clean shutdown - close browser and save state."""
        self._save_processed_ids()
        if self._browser:
            try:
                self._browser.close()
            except Exception:
                pass
        logger.info(f"WhatsApp Web watcher stopped. Stats: {json.dumps(self._stats, default=str, indent=2)}")
    
    def get_stats(self) -> dict:
        """Return current watcher statistics."""
        return {
            **self._stats,
            'processed_ids_count': len(self._processed_messages),
            'headless': self._headless,
            'session_exists': self._session_file.exists() if self._session_file else False,
        }


# ─── Standalone Execution ────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(description='WhatsApp Web watcher (Playwright)')
    parser.add_argument('--vault-path', default='AI_Employee_Vault', help='Path to Obsidian vault')
    parser.add_argument('--session-dir', default='.whatsapp_sessions', help='Session storage directory')
    parser.add_argument('--check-interval', type=int, default=60, help='Seconds between checks')
    parser.add_argument('--headless', action='store_true', default=True, help='Run headless')
    parser.add_argument('--no-headless', action='store_true', help='Show browser window')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('whatsapp_web_watcher.log'),
        ]
    )
    
    watcher = WhatsAppWebWatcher(
        vault_path=args.vault_path,
        session_dir=args.session_dir,
        check_interval=args.check_interval,
        headless=not args.no_headless,
    )
    
    print("=" * 60)
    print("WhatsApp Web Watcher (Playwright)")
    print("=" * 60)
    print(f"Vault path: {args.vault_path}")
    print(f"Session dir: {args.session_dir}")
    print(f"Check interval: {args.check_interval}s")
    print(f"Headless: {not args.no_headless}")
    print()
    print("First run will require QR code scan to link WhatsApp Web.")
    print("After initial setup, the session will be persisted.")
    print()
    print("Press Ctrl+C to stop.")
    print("=" * 60)
    
    try:
        watcher.run()
    except KeyboardInterrupt:
        watcher.stop()
        print("\nStopped by user.")