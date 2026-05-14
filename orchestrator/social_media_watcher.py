"""
social_media_watcher.py - Monitors social media platforms for engagement and posting opportunities.

From the hackathon PDF Gold Tier:
  - "Integrate Facebook and Instagram and post messages and generate summary"
  - "Integrate Twitter (X) and post messages and generate summary"

This watcher handles:
1. Monitors vault for social media posting requests
2. Tracks engagement on existing posts
3. Creates task files for content review and scheduling
"""

import time
import logging
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod

from orchestrator.base_watcher import BaseWatcher
from config import get_settings

logger = logging.getLogger(__name__)


class SocialMediaPlatform(ABC):
    """Abstract base class for social media platform integrations."""
    
    def __init__(self, platform_name: str, api_key: str = None):
        self.platform_name = platform_name
        self.api_key = api_key
        self._connected = False
    
    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with the platform API."""
        pass
    
    @abstractmethod
    def get_recent_posts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch recent posts and their engagement metrics."""
        pass
    
    @abstractmethod
    def post_content(self, content: Dict[str, Any]) -> Optional[str]:
        """Publish content to the platform. Returns post ID or None."""
        pass
    
    @abstractmethod
    def get_engagement(self, post_id: str) -> Dict[str, Any]:
        """Get engagement metrics for a specific post."""
        pass
    
    @abstractmethod
    def get_mentions(self, since: datetime = None) -> List[Dict[str, Any]]:
        """Get mentions and replies since the given time."""
        pass
    
    def is_connected(self) -> bool:
        return self._connected


class FacebookAPI(SocialMediaPlatform):
    """Facebook Graph API integration for Page management."""
    
    GRAPH_API_BASE = "https://graph.facebook.com/v18.0"
    
    def __init__(self, page_id: str, access_token: str):
        super().__init__("facebook")
        self.page_id = page_id
        self.access_token = access_token
        self._api_version = "18.0"
    
    def authenticate(self) -> bool:
        """Validate the access token."""
        try:
            import urllib.request
            url = f"{self.GRAPH_API_BASE}/debug_token"
            params = f"input_token={self.access_token}&access_token={self.access_token}"
            req = urllib.request.urlopen(f"{url}?{params}")
            data = json.loads(req.read())
            self._connected = data.get('data', {}).get('is_valid', False)
            if not self._connected:
                logger.error("Facebook token validation failed")
            return self._connected
        except Exception as e:
            logger.error(f"Facebook authentication error: {e}")
            return False
    
    def get_recent_posts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch recent posts from the Facebook Page."""
        posts = []
        try:
            import urllib.request
            url = (
                f"{self.GRAPH_API_BASE}/{self.page_id}/posts"
                f"?fields=id,message,created_time,shares,likes.summary(true),comments.summary(true)"
                f"&limit={limit}"
                f"&access_token={self.access_token}"
            )
            req = urllib.request.urlopen(url)
            data = json.loads(req.read())
            
            for post in data.get('data', []):
                posts.append({
                    'id': post.get('id'),
                    'message': post.get('message', ''),
                    'created_time': post.get('created_time'),
                    'shares': post.get('shares', {}).get('count', 0),
                    'likes': post.get('likes', {}).get('summary', {}).get('total_count', 0),
                    'comments': post.get('comments', {}).get('summary', {}).get('total_count', 0),
                    'platform': 'facebook'
                })
        except Exception as e:
            logger.error(f"Error fetching Facebook posts: {e}")
        return posts
    
    def post_content(self, content: Dict[str, Any]) -> Optional[str]:
        """Publish a post to the Facebook Page."""
        try:
            import urllib.request
            message = content.get('message', '')
            link = content.get('link', '')
            
            url = f"{self.GRAPH_API_BASE}/{self.page_id}/feed"
            params = f"message={urllib.parse.quote(message)}&access_token={self.access_token}"
            if link:
                params += f"&link={urllib.parse.quote(link)}"
            
            req = urllib.request.urlopen(f"{url}?{params}")
            result = json.loads(req.read())
            post_id = result.get('id')
            
            logger.info(f"Facebook post published: {post_id}")
            return post_id
            
        except Exception as e:
            logger.error(f"Error posting to Facebook: {e}")
            return None
    
    def get_engagement(self, post_id: str) -> Dict[str, Any]:
        """Get engagement metrics for a Facebook post."""
        try:
            import urllib.request
            url = (
                f"{self.GRAPH_API_BASE}/{post_id}"
                f"?fields=shares,likes.summary(true),comments.summary(true),impressions"
                f"&access_token={self.access_token}"
            )
            req = urllib.request.urlopen(url)
            data = json.loads(req.read())
            
            return {
                'post_id': post_id,
                'likes': data.get('likes', {}).get('summary', {}).get('total_count', 0),
                'comments': data.get('comments', {}).get('summary', {}).get('total_count', 0),
                'shares': data.get('shares', {}).get('count', 0),
                'impressions': data.get('impressions', {}).get('data', [{}])[0].get('value', 0),
                'platform': 'facebook'
            }
        except Exception as e:
            logger.error(f"Error getting Facebook engagement: {e}")
            return {'post_id': post_id, 'platform': 'facebook', 'error': str(e)}
    
    def get_mentions(self, since: datetime = None) -> List[Dict[str, Any]]:
        """Get mentions and comments on the Facebook Page."""
        mentions = []
        try:
            import urllib.request
            since_str = since.strftime('%Y-%m-%dT%H:%M:%S+0000') if since else None
            url = (
                f"{self.GRAPH_API_BASE}/{self.page_id}/mentions"
                f"?fields=message,from,created_time"
                f"&access_token={self.access_token}"
            )
            if since_str:
                url += f"&since={since_str}"
            
            req = urllib.request.urlopen(url)
            data = json.loads(req.read())
            mentions = data.get('data', [])
        except Exception as e:
            logger.error(f"Error fetching Facebook mentions: {e}")
        return mentions


class InstagramAPI(SocialMediaPlatform):
    """Instagram Graph API integration for Business accounts."""
    
    GRAPH_API_BASE = "https://graph.facebook.com/v18.0"
    
    def __init__(self, ig_user_id: str, access_token: str):
        super().__init__("instagram")
        self.ig_user_id = ig_user_id
        self.access_token = access_token
    
    def authenticate(self) -> bool:
        """Validate the Instagram Business account connection."""
        try:
            import urllib.request
            url = f"{self.GRAPH_API_BASE}/{self.ig_user_id}"
            params = f"fields=id,username&access_token={self.access_token}"
            req = urllib.request.urlopen(f"{url}?{params}")
            data = json.loads(req.read())
            self._connected = bool(data.get('id'))
            return self._connected
        except Exception as e:
            logger.error(f"Instagram authentication error: {e}")
            return False
    
    def get_recent_posts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch recent Instagram posts."""
        posts = []
        try:
            import urllib.request
            url = (
                f"{self.GRAPH_API_BASE}/{self.ig_user_id}/media"
                f"?fields=id,caption,like_count,comments_count,impressions,media_type,timestamp"
                f"&limit={limit}"
                f"&access_token={self.access_token}"
            )
            req = urllib.request.urlopen(url)
            data = json.loads(req.read())
            
            for post in data.get('data', []):
                posts.append({
                    'id': post.get('id'),
                    'caption': post.get('caption', ''),
                    'created_time': post.get('timestamp'),
                    'likes': post.get('like_count', 0),
                    'comments': post.get('comments_count', 0),
                    'impressions': post.get('impressions', 0),
                    'media_type': post.get('media_type', 'UNKNOWN'),
                    'platform': 'instagram'
                })
        except Exception as e:
            logger.error(f"Error fetching Instagram posts: {e}")
        return posts
    
    def post_content(self, content: Dict[str, Any]) -> Optional[str]:
        """Publish a post to Instagram (image with caption)."""
        try:
            # Step 1: Create the media object
            import urllib.request
            image_url = content.get('image_url', '')
            caption = content.get('caption', '')
            
            create_url = f"{self.GRAPH_API_BASE}/{self.ig_user_id}/media"
            params = f"image_url={urllib.parse.quote(image_url)}&caption={urllib.parse.quote(caption)}&access_token={self.access_token}"
            
            req = urllib.request.urlopen(f"{create_url}?{params}")
            creation_data = json.loads(req.read())
            creation_id = creation_data.get('id')
            
            # Step 2: Publish the media
            publish_url = f"{self.GRAPH_API_BASE}/{self.ig_user_id}/media_publish"
            publish_params = f"creation_id={creation_id}&access_token={self.access_token}"
            
            req = urllib.request.urlopen(f"{publish_url}?{publish_params}")
            publish_data = json.loads(req.read())
            post_id = publish_data.get('id')
            
            logger.info(f"Instagram post published: {post_id}")
            return post_id
            
        except Exception as e:
            logger.error(f"Error posting to Instagram: {e}")
            return None
    
    def get_engagement(self, post_id: str) -> Dict[str, Any]:
        """Get engagement metrics for an Instagram post."""
        try:
            import urllib.request
            url = (
                f"{self.GRAPH_API_BASE}/{post_id}"
                f"?fields=like_count,comments_count,impressions,caption"
                f"&access_token={self.access_token}"
            )
            req = urllib.request.urlopen(url)
            data = json.loads(req.read())
            
            return {
                'post_id': post_id,
                'likes': data.get('like_count', 0),
                'comments': data.get('comments_count', 0),
                'impressions': data.get('impressions', 0),
                'caption': data.get('caption', ''),
                'platform': 'instagram'
            }
        except Exception as e:
            logger.error(f"Error getting Instagram engagement: {e}")
            return {'post_id': post_id, 'platform': 'instagram', 'error': str(e)}
    
    def get_mentions(self, since: datetime = None) -> List[Dict[str, Any]]:
        """Get mentions and comments on Instagram posts."""
        # Instagram mentions are fetched via the comments endpoint
        mentions = []
        try:
            import urllib.request
            url = f"{self.GRAPH_API_BASE}/{self.ig_user_id}/mentions"
            params = f"fields=like_count,comments_count,caption,timestamp&access_token={self.access_token}"
            req = urllib.request.urlopen(f"{url}?{params}")
            data = json.loads(req.read())
            mentions = data.get('data', [])
        except Exception as e:
            logger.error(f"Error fetching Instagram mentions: {e}")
        return mentions


class TwitterAPI(SocialMediaPlatform):
    """Twitter (X) API v2 integration."""
    
    API_BASE = "https://api.twitter.com/2"
    UPLOAD_BASE = "https://upload.twitter.com/1.1"
    
    def __init__(self, api_key: str, api_secret: str, access_token: str, access_token_secret: str):
        super().__init__("twitter")
        self.api_key = api_key
        self.api_secret = api_secret
        self.access_token = access_token
        self.access_token_secret = access_token_secret
    
    def _get_auth_header(self) -> str:
        """Generate OAuth 1.0a authorization header."""
        import hmac
        import hashlib
        import base64
        import time
        
        nonce = str(int(time.time() * 1000))
        timestamp = str(int(time.time()))
        
        # Build signature base string
        param_string = (
            f"oauth_consumer_key={self.api_key}"
            f"&oauth_nonce={nonce}"
            f"&oauth_signature_method=HMAC-SHA1"
            f"&oauth_timestamp={timestamp}"
            f"&oauth_token={self.access_token}"
            f"&oauth_version=1.0"
        )
        
        signing_key = f"{self._encode(self.api_secret)}&{self._encode(self.access_token_secret)}"
        signature = hmac.new(
            signing_key.encode(),
            f"GET&{self._encode(f'{self.API_BASE}/tweets')}&{self._encode(param_string)}".encode(),
            hashlib.sha1
        ).digest()
        
        sig_b64 = base64.b64encode(signature).decode()
        
        return (
            f'OAuth oauth_consumer_key="{self.api_key}",'
            f'oauth_nonce="{nonce}",'
            f'oauth_signature="{self._encode(sig_b64)}",'
            f'oauth_signature_method="HMAC-SHA1",'
            f'oauth_timestamp="{timestamp}",'
            f'oauth_token="{self.access_token}",'
            f'oauth_version="1.0"'
        )
    
    def _encode(self, s: str) -> str:
        import urllib.parse
        return urllib.parse.quote(s, safe='')
    
    def authenticate(self) -> bool:
        """Validate credentials by looking up the authenticated user."""
        try:
            import urllib.request
            url = f"{self.API_BASE}/users/me"
            req = urllib.request.Request(url, headers={'Authorization': self._get_auth_header()})
            response = urllib.request.urlopen(req)
            data = json.loads(response.read())
            self._connected = bool(data.get('data'))
            return self._connected
        except Exception as e:
            logger.error(f"Twitter authentication error: {e}")
            return False
    
    def get_recent_posts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch recent tweets from the authenticated account."""
        posts = []
        try:
            import urllib.request
            url = f"{self.API_BASE}/users/me/tweets?max_results={limit}&tweet.fields=created_at,public_metrics"
            req = urllib.request.Request(url, headers={'Authorization': self._get_auth_header()})
            response = urllib.request.urlopen(req)
            data = json.loads(response.read())
            
            for tweet in data.get('data', []):
                metrics = tweet.get('public_metrics', {})
                posts.append({
                    'id': tweet.get('id'),
                    'text': tweet.get('text', ''),
                    'created_time': tweet.get('created_at'),
                    'likes': metrics.get('like_count', 0),
                    'retweets': metrics.get('retweet_count', 0),
                    'replies': metrics.get('reply_count', 0),
                    'impressions': metrics.get('impression_count', 0),
                    'platform': 'twitter'
                })
        except Exception as e:
            logger.error(f"Error fetching Twitter posts: {e}")
        return posts
    
    def post_content(self, content: Dict[str, Any]) -> Optional[str]:
        """Publish a tweet."""
        try:
            import urllib.request
            text = content.get('text', '')
            
            url = f"{self.API_BASE}/tweets"
            body = json.dumps({'text': text})
            
            req = urllib.request.Request(
                url,
                data=body.encode(),
                headers={
                    'Authorization': self._get_auth_header(),
                    'Content-Type': 'application/json'
                },
                method='POST'
            )
            response = urllib.request.urlopen(req)
            result = json.loads(response.read())
            tweet_id = result.get('data', {}).get('id')
            
            logger.info(f"Tweet published: {tweet_id}")
            return tweet_id
            
        except Exception as e:
            logger.error(f"Error posting tweet: {e}")
            return None
    
    def post_thread(self, tweets: List[str]) -> Optional[str]:
        """Publish a thread of tweets."""
        try:
            import urllib.request
            tweet_id = None
            
            for i, text in enumerate(tweets):
                body = {'text': text}
                if tweet_id and i > 0:
                    body['reply'] = {'in_reply_to_tweet_id': tweet_id}
                
                url = f"{self.API_BASE}/tweets"
                req = urllib.request.Request(
                    url,
                    data=json.dumps(body).encode(),
                    headers={
                        'Authorization': self._get_auth_header(),
                        'Content-Type': 'application/json'
                    },
                    method='POST'
                )
                response = urllib.request.urlopen(req)
                result = json.loads(response.read())
                tweet_id = result.get('data', {}).get('id')
                time.sleep(2)  # Brief delay between tweets
            
            logger.info(f"Thread published, first tweet: {tweet_id}")
            return tweet_id
            
        except Exception as e:
            logger.error(f"Error posting tweet thread: {e}")
            return None
    
    def get_engagement(self, post_id: str) -> Dict[str, Any]:
        """Get engagement metrics for a tweet."""
        try:
            import urllib.request
            url = f"{self.API_BASE}/tweets/{post_id}?tweet.fields=public_metrics"
            req = urllib.request.Request(url, headers={'Authorization': self._get_auth_header()})
            response = urllib.request.urlopen(req)
            data = json.loads(response.read())
            
            metrics = data.get('data', {}).get('public_metrics', {})
            return {
                'post_id': post_id,
                'likes': metrics.get('like_count', 0),
                'retweets': metrics.get('retweet_count', 0),
                'replies': metrics.get('reply_count', 0),
                'impressions': metrics.get('impression_count', 0),
                'platform': 'twitter'
            }
        except Exception as e:
            logger.error(f"Error getting Twitter engagement: {e}")
            return {'post_id': post_id, 'platform': 'twitter', 'error': str(e)}
    
    def get_mentions(self, since: datetime = None) -> List[Dict[str, Any]]:
        """Get mentions of the account."""
        mentions = []
        try:
            import urllib.request
            url = f"{self.API_BASE}/users/me/mentions?tweet.fields=created_at,public_metrics"
            if since:
                url += f"&start_time={since.strftime('%Y-%m-%dT%H:%M:%SZ')}"
            req = urllib.request.Request(url, headers={'Authorization': self._get_auth_header()})
            response = urllib.request.urlopen(req)
            data = json.loads(response.read())
            mentions = data.get('data', [])
        except Exception as e:
            logger.error(f"Error fetching Twitter mentions: {e}")
        return mentions


class SocialMediaWatcher(BaseWatcher):
    """
    Unified watcher for social media platforms.
    Monitors multiple platforms and creates task files for content posting and engagement.
    """
    
    def __init__(
        self,
        vault_path: str,
        check_interval: int = 1800,  # Check every 30 minutes
        platforms: Optional[List[str]] = None
    ):
        """
        Initialize social media watcher.
        
        Args:
            vault_path: Path to Obsidian vault
            check_interval: Seconds between checks
            platforms: List of platforms to monitor ('facebook', 'instagram', 'twitter', 'linkedin')
        """
        super().__init__(
            name="social_media",
            poll_interval=check_interval
        )
        
        self.vault_path = Path(vault_path)
        self.platforms = platforms or ['facebook', 'instagram', 'twitter']
        self._apis: Dict[str, SocialMediaPlatform] = {}
        self._content_tracker: Dict[str, set] = {p: set() for p in self.platforms}
        self._setup_apis()
        
        # Stats
        self._stats = {
            'total_checks': 0,
            'content_detected': 0,
            'posts_created': 0,
            'engagement_updates': 0,
            'last_check': None,
            'by_platform': {p: {'posts': 0, 'engagement': 0} for p in self.platforms}
        }
    
    def _setup_apis(self):
        """Initialize platform API clients from environment variables."""
        settings = get_settings()
        
        try:
            # Facebook
            if 'facebook' in self.platforms and settings.facebook_page_id and settings.facebook_access_token:
                self._apis['facebook'] = FacebookAPI(
                    page_id=settings.facebook_page_id,
                    access_token=settings.facebook_access_token
                )
            
            # Instagram
            if 'instagram' in self.platforms and settings.instagram_user_id and settings.instagram_access_token:
                self._apis['instagram'] = InstagramAPI(
                    ig_user_id=settings.instagram_user_id,
                    access_token=settings.instagram_access_token
                )
            
            # Twitter
            if 'twitter' in self.platforms and all([
                settings.twitter_api_key,
                settings.twitter_api_secret,
                settings.twitter_access_token,
                settings.twitter_access_token_secret
            ]):
                self._apis['twitter'] = TwitterAPI(
                    api_key=settings.twitter_api_key,
                    api_secret=settings.twitter_api_secret,
                    access_token=settings.twitter_access_token,
                    access_token_secret=settings.twitter_access_token_secret
                )
            
            logger.info(f"Social media APIs initialized: {list(self._apis.keys())}")
            
        except Exception as e:
            logger.warning(f"Error setting up social media APIs: {e}")
    
    def authenticate_all(self) -> bool:
        """Authenticate with all configured platforms."""
        success = True
        for name, api in self._apis.items():
            try:
                if not api.authenticate():
                    logger.warning(f"Failed to authenticate with {name}")
                    success = False
                else:
                    logger.info(f"Authenticated with {name}")
            except Exception as e:
                logger.error(f"Authentication error for {name}: {e}")
                success = False
        return success
    
    def check_for_updates(self) -> List[Dict[str, Any]]:
        """
        Check all platforms for new content and engagement.
        
        Returns:
            List of action item dictionaries
        """
        self._stats['total_checks'] += 1
        actions = []
        
        try:
            # Check for new content to post from vault
            posting_actions = self._check_vault_for_content()
            actions.extend(posting_actions)
            
            # Check each platform for engagement and mentions
            for platform_name, api in self._apis.items():
                if not api.is_connected():
                    try:
                        api.authenticate()
                    except Exception:
                        continue
                
                # Check recent posts for engagement tracking
                engagement_actions = self._check_engagement(platform_name, api)
                actions.extend(engagement_actions)
                
                # Check for mentions/replies
                mention_actions = self._check_mentions(platform_name, api)
                actions.extend(mention_actions)
                
        except Exception as e:
            logger.error(f"Error in social media check: {e}", exc_info=True)
        
        self._stats['last_check'] = datetime.now().isoformat()
        return actions
    
    def _check_vault_for_content(self) -> List[Dict[str, Any]]:
        """
        Check for social media content in designated vault folders.
        
        Content files should have YAML frontmatter with:
        - platform: facebook | instagram | twitter | all
        - type: post | thread | story | reel
        - status: draft | ready | scheduled
        - schedule_time: ISO datetime (if scheduled)
        """
        actions = []
        content_dir = self.vault_path / 'Social' / 'Drafts'
        
        if not content_dir.exists():
            return actions
        
        for file_path in content_dir.glob('*.md'):
            try:
                content = file_path.read_text()
                frontmatter = self._parse_frontmatter(content)
                
                if frontmatter.get('status') not in ('draft', 'ready', 'scheduled'):
                    continue
                
                platforms = frontmatter.get('platform', 'all').split(',')
                for platform in platforms:
                    platform = platform.strip().lower()
                    if platform not in self.platforms:
                        continue
                    
                    content_id = f"{file_path.stem}_{platform}"
                    if content_id in self._content_tracker[platform]:
                        continue
                    
                    self._content_tracker[platform].add(content_id)
                    actions.append({
                        'type': 'post_content',
                        'platform': platform,
                        'content_id': content_id,
                        'source_file': str(file_path),
                        'frontmatter': frontmatter,
                        'priority': 'high' if frontmatter.get('status') == 'scheduled' else 'medium',
                        'timestamp': datetime.now().isoformat()
                    })
                    
                    self._stats['content_detected'] += 1
                    
            except Exception as e:
                logger.error(f"Error processing content file {file_path}: {e}")
        
        return actions
    
    def _check_engagement(self, platform: str, api: SocialMediaPlatform) -> List[Dict[str, Any]]:
        """Check for new engagement on existing posts."""
        actions = []
        
        try:
            recent_posts = api.get_recent_posts(limit=5)
            for post in recent_posts:
                post_id = post.get('id')
                engagement_key = f"{platform}_{post_id}"
                
                # Skip if already tracked
                if engagement_key in self._content_tracker.get(platform, set()):
                    continue
                
                metrics = api.get_engagement(post_id)
                actions.append({
                    'type': 'engagement_update',
                    'platform': platform,
                    'post_id': post_id,
                    'metrics': metrics,
                    'priority': 'low',
                    'timestamp': datetime.now().isoformat()
                })
                self._stats['engagement_updates'] += 1
                self._stats['by_platform'][platform]['engagement'] += 1
                
                if platform in self._content_tracker:
                    self._content_tracker[platform].add(engagement_key)
                    
        except Exception as e:
            logger.error(f"Error checking engagement for {platform}: {e}")
        
        return actions
    
    def _check_mentions(self, platform: str, api: SocialMediaPlatform) -> List[Dict[str, Any]]:
        """Check for mentions and replies."""
        actions = []
        
        try:
            since = datetime.now() - timedelta(hours=24)
            mentions = api.get_mentions(since=since)
            
            for mention in mentions:
                mention_text = mention.get('text', '') or mention.get('message', '')
                mention_id = mention.get('id')
                mention_key = f"{platform}_mention_{mention_id}"
                
                if mention_key in self._content_tracker.get(platform, set()):
                    continue
                
                # Determine priority based on content
                priority = 'medium'
                keywords = ['help', 'question', 'need', 'problem', 'issue', 'bug', 'urgent']
                if any(kw in mention_text.lower() for kw in keywords):
                    priority = 'high'
                
                actions.append({
                    'type': 'mention',
                    'platform': platform,
                    'mention_id': mention_id,
                    'content': mention_text[:200],
                    'priority': priority,
                    'timestamp': datetime.now().isoformat()
                })
                
                if platform in self._content_tracker:
                    self._content_tracker[platform].add(mention_key)
                    
        except Exception as e:
            logger.error(f"Error checking mentions for {platform}: {e}")
        
        return actions
    
    def create_action_file(self, action: Dict[str, Any]) -> Path:
        """
        Create a social media task file in Needs_Action folder.
        """
        action_type = action.get('type', 'unknown')
        platform = action.get('platform', 'unknown')
        
        if action_type == 'post_content':
            frontmatter = action.get('frontmatter', {})
            task_id = f"SOCIAL_POST_{platform.upper()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            content = f"""## Social Media Post - {platform.upper()}

**Platform:** {platform}
**Source:** {action.get('source_file', 'Unknown')}
**Detected:** {action.get('timestamp')}
**Priority:** {action.get('priority', 'normal')}
**Status:** {frontmatter.get('status', 'draft')}

## Content Preview

{frontmatter.get('caption', 'No caption')}

## Platform Details

- **Type:** {frontmatter.get('type', 'post')}
- **Scheduled:** {frontmatter.get('schedule_time', 'Not scheduled')}

## Action
- [ ] Review content for platform suitability
- [ ] Approve and post to {platform}
- [ ] Track engagement metrics

---

*Auto-detected by SocialMediaWatcher*
"""
        elif action_type == 'mention':
            task_id = f"SOCIAL_MENTION_{platform.upper()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            content = f"""## Social Media Mention - {platform.upper()}

**Platform:** {platform}
**Mention ID:** {action.get('mention_id', 'Unknown')}
**Detected:** {action.get('timestamp')}
**Priority:** {action.get('priority', 'normal')}

## Content

{action.get('content', 'No content available')}

## Action
- [ ] Review mention
- [ ] Draft and send appropriate response
- [ ] Submit for approval if needed

---

*Auto-detected by SocialMediaWatcher*
"""
        else:
            task_id = f"SOCIAL_{action_type.upper()}_{platform.upper()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            content = f"""## Social Media Task - {platform.upper()}

**Type:** {action_type}
**Platform:** {platform}
**Detected:** {action.get('timestamp')}
**Priority:** {action.get('priority', 'normal')}

## Details

{json.dumps(action.get('metrics', {}), indent=2)}

## Action
- [ ] Review and take appropriate action

---

*Auto-detected by SocialMediaWatcher*
"""
        
        frontmatter = {
            'type': 'social_media_task',
            'platform': platform,
            'action_type': action_type,
            'created': action.get('timestamp', datetime.now().isoformat()),
            'priority': action.get('priority', 'normal'),
            'status': 'pending',
        }
        
        filename = f"{task_id}.md"
        filepath = self.needs_action / filename
        
        yaml_lines = ['---']
        for key, value in frontmatter.items():
            yaml_lines.append(f'{key}: {value}')
        yaml_lines.append('---')
        full_content = f"{'\n'.join(yaml_lines)}\n\n{content}"
        filepath.write_text(full_content)
        
        self._stats['posts_created'] += 1
        logger.info(f"Created social media task: {filename}")
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
    
    def run_once(self):
        """Override base class for social media watcher."""
        try:
            actions = self.check_for_updates()
            for action in actions:
                try:
                    filepath = self.create_action_file(action)
                    self.logger.info(f"Created social media task: {filepath.name}")
                except Exception as e:
                    self.logger.error(f"Error creating social media task: {e}")
        except Exception as e:
            self.logger.error(f"Error in social media watcher: {e}", exc_info=True)
    
    def get_stats(self) -> dict:
        """Return current watcher statistics."""
        return {
            **self._stats,
            'platforms_active': list(self._apis.keys()),
            'content_tracked': {k: len(v) for k, v in self._content_tracker.items()},
        }


# ─── Standalone Execution ────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='Social Media Watcher')
    parser.add_argument('--vault-path', default='AI_Employee_Vault', help='Path to Obsidian vault')
    parser.add_argument('--interval', type=int, default=1800, help='Check interval in seconds')
    parser.add_argument('--platforms', default='facebook,instagram,twitter', help='Comma-separated platforms')
    parser.add_argument('--debug', action='store_true', help='Debug logging')
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    
    platforms = [p.strip() for p in args.platforms.split(',')]
    watcher = SocialMediaWatcher(
        vault_path=args.vault_path,
        check_interval=args.interval,
        platforms=platforms
    )
    
    print("=" * 60)
    print("Social Media Watcher")
    print("=" * 60)
    print(f"Platforms: {', '.join(platforms)}")
    print(f"Interval: {args.interval}s")
    print()
    print("Press Ctrl+C to stop.")
    
    try:
        watcher.run()
    except KeyboardInterrupt:
        print(f"\nStats: {json.dumps(watcher.get_stats(), indent=2, default=str)}")
        print("Stopped.")