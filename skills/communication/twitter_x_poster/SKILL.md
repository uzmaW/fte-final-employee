---
name: twitter_x_poster
description: Post tweets and threads to Twitter (X) for brand visibility, lead generation, and real-time engagement. Supports text, images, polls, quote tweets, and thread creation.
allowed-tools: Read, Write, Glob, Call
---

# Twitter (X) Poster Skill

## Purpose
Automatically publish business content to Twitter/X for brand awareness,
community engagement, and lead generation through strategic posting.

## Twitter API v2 Integration

### Prerequisites
1. Apply for a Twitter/X API Developer Account at https://developer.twitter.com/
2. Create a Project and App with elevated access (or basic access minimum)
3. Obtain credentials:
   - `TWITTER_API_KEY` (Consumer Key)
   - `TWITTER_API_SECRET` (Consumer Secret)
   - `TWITTER_ACCESS_TOKEN` (Access Token)
   - `TWITTER_ACCESS_TOKEN_SECRET` (Access Token Secret)
   - `TWITTER_BEARER_TOKEN` (Bearer Token)

### Required OAuth Scopes
```
tweet.read, tweet.write, users.read, offline.access
+ For media upload: tweet.read, tweet.write, users.read, media.write
```

## Post Types

### 1. Standard Tweet (≤280 chars)
```
POST https://api.twitter.com/2/tweets
{
  "text": "🚀 Excited to announce our latest feature!..."
}
```

### 2. Tweet with Media (Image)
```
POST https://upload.twitter.com/1.1/media/upload
→ Get media_id
POST https://api.twitter.com/2/tweets
{
  "text": "Check out our new dashboard!",
  "media": { "media_ids": ["<media_id>"] }
}
```

### 3. Thread (Multi-Tweet)
```
Tweet 1: POST /2/tweets { "text": "🧵 Thread: 5 lessons from 1 year of AI automation..." }
Tweet 2: POST /2/tweets { "text": "1/ ...", "reply": { "in_reply_to_tweet_id": "<id_1>" } }
Tweet 3: POST /2/tweets { "text": "2/ ...", "reply": { "in_reply_to_tweet_id": "<id_2>" } }
...
```

### 4. Poll Tweet
```
POST https://api.twitter.com/2/tweets
{
  "text": "Which tool do you use for project management?",
  "poll": {
    "options": ["Notion", "Jira", "Trello", "Linear"],
    "duration_minutes": 1440
  }
}
```

## Content Categories

### Thought Leadership
- Industry observations and hot takes
- Lessons learned from building AI employees
- Predictions about automation trends
- Thread-style educational content

### Product / Business Updates
- Feature announcements
- Milestone celebrations
- Customer wins (with permission)
- Behind-the-scenes development

### Engagement Content
- Polls about industry trends
- Questions for the community
- Retweets with commentary on relevant news
- Responses to trending topics in your niche

### Promotional Content
- Blog post teasers with links
- Webinar/event announcements
- Free resource drops
- Partnership announcements

## Content Calendar Rules

Based on Twitter engagement data:
- **Best days:** Tuesday, Wednesday, Thursday
- **Best times:** 9 AM, 12 PM, 3 PM, 5 PM (audience timezone)
- **Frequency:** 2-4 tweets per day maximum
- **Thread cadence:** 1 thread per week

## Usage Examples

### Automatic Tweet: Milestone
```json
{
  "platform": "twitter",
  "type": "milestone",
  "text": "🎉 Just crossed 500 customers! From 0→500 in 12 months. Grateful to every customer who trusted us. Here's to the next 500! 🚀",
  "hashtags": ["#startup", "#milestone", "#growth"]
}
```

### Automatic Tweet: Blog Post
```json
{
  "platform": "twitter",
  "type": "blog_promotion",
  "text": "📝 New blog post: 'How we automated 80% of our customer support with AI'\n\nKey takeaways:\n→ AI agents handle routine tickets\n→ Human agents focus on complex issues\n→ 40% cost reduction\n\nRead more: [link]",
  "hashtags": ["#AI", "#automation", "#customersupport"]
}
```

### Automatic Thread: Weekly Insights
```markdown
🧵 Weekly Insights: AI Automation Trends (Week of 2026-02-07)

1/ 📊 73% of companies now use some form of AI in operations (up from 55% last quarter)

2/ The biggest shift: Companies moving from "AI assistants" to "AI employees" — autonomous agents handling full workflows

3/ Top sectors adopting: SaaS, E-commerce, Professional Services

4/ The barrier isn't technology anymore — it's organizational readiness and trust

5/ Our take: Start small with one domain (e.g., email), prove value, then expand. The compound ROI is enormous.
```

## Engagement Tracking

After each post:
1. Tweet ID stored in `/Social/Twitter_Posts.md`
2. Metrics polled daily:
   - Impressions
   - Engagements (likes, retweets, replies, quotes)
   - Link clicks (if included)
   - New followers from post
3. Weekly summary in Monday Morning CEO Briefing

## Approval Workflow

| Action | Auto-Approve? |
|--------|---------------|
| Scheduled routine tweet | ✅ If matches approved template |
| Thread post | ❌ Requires review |
| Poll | ❌ Requires approval |
| Public reply to unknown user | ❌ Requires approval |
| Promotional/sponsored content | ❌ Always requires approval |

## Error Handling

| Error | Response |
|-------|----------|
| 429 Rate Limited | Back off and retry after Rate-Limit-Reset header |
| 403 Forbidden | Content violation – log and alert human |
| 401 Unauthorized | Refresh tokens and retry once |
| Network timeout | Retry up to 3 times |
| Duplicate tweet (409) | Skip, already posted |

## Character Count Helper

The skill includes a utility to craft tweets within the 280-character limit:
- Counts Unicode characters correctly
- Shortens URLs automatically via t.co
- Suggests text revisions if over limit
- Warns on hashtag stuffing (>3 hashtags)

See examples/twitter-workflow.md for a complete workflow example.