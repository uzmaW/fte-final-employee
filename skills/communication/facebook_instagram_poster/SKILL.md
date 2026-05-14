---
name: facebook_instagram_poster
description: Post content to Facebook Pages and Instagram Business accounts. Supports text posts, image posts, link shares, and carousel posts. Integrates with Meta Graph API for publishing and engagement tracking.
allowed-tools: Read, Write, Glob, Call
---

# Facebook & Instagram Poster Skill

## Purpose
Automatically publish business content to Facebook Pages and Instagram Business
accounts to increase brand visibility, drive traffic, and generate leads.

## Meta API Integration

### Prerequisites
1. Create a Facebook Developer App at https://developers.facebook.com/
2. Configure a Facebook Page and/or Instagram Business Account
3. Obtain credentials:
   - `FACEBOOK_APP_ID`
   - `FACEBOOK_APP_SECRET`
   - `FACEBOOK_PAGE_ACCESS_TOKEN` (with pages_manage_posts, pages_read_engagement permissions)
   - `INSTAGRAM_ACCESS_TOKEN` (with instagram_basic, instagram_manage_insights permissions)

### Token Setup
```
1. Go to https://developers.facebook.com/apps/
2. Create app → Business type
3. Add "Facebook Page" and "Instagram Graph API" products
4. Generate a System User access token with:
   - pages_manage_posts
   - pages_read_engagement
   - instagram_basic
   - instagram_manage_insights
   - instagram_content_publish
5. Store tokens in .env file (NEVER commit)
```

## Post Types

### 1. Facebook Page Post (Text + Link)
Posts a status update to the linked Facebook Page.

```
POST https://graph.facebook.com/v18.0/{page-id}/feed
message={text}&link={url}&access_token={token}
```

### 2. Facebook Page Post (Image)
Uploads an image and creates a post with it.

```
POST https://graph.facebook.com/v18.0/{page-id}/photos
url={image_url}&caption={text}&access_token={token}
```

### 3. Instagram Business Post (Image + Caption)
Creates a post on the Instagram Business account.

```
POST https://graph.facebook.com/v18.0/{ig-user-id}/media
image_url={url}&caption={caption}&access_token={token}

Then publish:
POST https://graph.facebook.com/v18.0/{ig-user-id}/media_publish
creation_id={creation_id}&access_token={token}
```

### 4. Instagram Business Carousel Post
Creates a multi-image carousel post.

```
POST https://graph.facebook.com/v18.0/{ig-user-id}/media
media_type=CAROUSEL
&children=[{image_url, caption}, ...]
&caption={main_caption}
&access_token={token}
```

## Content Categories

### Business Milestones
- Product launches
- Partnership announcements
- Milestone achievements (revenue, customers, team growth)
- Awards and recognition

### Educational / Thought Leadership
- Industry insights
- Tips and how-tos relevant to your niche
- Behind-the-scenes of company operations
- Team spotlights

### Engagement / Community
- Polls and questions
- User testimonials and case studies
- Event announcements and recaps
- Holiday/seasonal content

### Promotional
- Special offers and discounts
- Feature announcements
- Webinar/event invitations
- Free resource downloads

## Usage Examples

### Automatic Post: Milestone Celebration
When Business_Goals.md shows a milestone was reached, the orchestrator triggers:

```markdown
{
  "platform": "facebook",
  "type": "milestone",
  "message": "🎉 Big news! We just crossed 500 customers!",
  "link": "https://example.com/blog/500-customers",
  "image": "/Vault/Images/milestone-500.png"
}
```

### Automatic Post: New Blog Article
When a new article is published:

```markdown
{
  "platform": "instagram",
  "type": "link_share",
  "caption": "Just published our latest guide on AI automation for businesses.
📖 Link in bio!

#AI #Automation #BusinessTips #StartupLife",
  "link": "https://example.com/blog/ai-automation-guide",
  "image": "/Vault/Images/blog-thumbnail.jpg"
}
```

### Content Calendar
Posts are optimized for each platform's engagement patterns:
- **Facebook:** Tues–Thurs, 1–4 PM (audience timezone)
- **Instagram:** Mon–Fri, 11 AM–1 PM, 7–9 PM (audience timezone)
- **Frequency:** 3-5 posts per week across both platforms

## Engagement Tracking

After each post:
1. Post ID is stored in `/Social/Facebook_Posts.md` or `/Social/Instagram_Posts.md`
2. Metrics are updated daily by a polling script:
   - Reach / Impressions
   - Engagements (likes, comments, shares, saves)
   - Link clicks
   - New followers gained
3. Weekly summary in the Monday Morning CEO Briefing

## Approval Workflow

| Action | Auto-Approve? |
|--------|---------------|
| Scheduled text post | ✅ Yes (if content matches template) |
| Promotional post | ❌ Requires approval |
| Image with custom caption | ❌ Requires approval |
| Crisis/emergency post | ❌ Always requires approval |

## Error Handling

| Error | Response |
|-------|----------|
| 429 Rate Limited | Wait and retry with exponential backoff |
| Token Expired | Trigger re-authentication flow |
| Image Upload Failed | Retry 2x, then skip and log |
| API Changed (breaking) | Log critical alert, switch to manual posting |

See examples/facebook-ig-workflow.md for a complete workflow example.