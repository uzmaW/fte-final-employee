---
name: linkedin_poster
description: Post business updates to LinkedIn for lead generation and sales. Automatically formats and publishes content about business achievements, milestones, industry insights, and company news to generate engagement and sales opportunities.
allowed-tools: Read, Write, Glob, Call
---

# LinkedIn Poster Skill

## Purpose
Automatically post business-related content to LinkedIn to generate sales leads,
build brand presence, and share company milestones.

## LinkedIn API Integration

### Prerequisites
1. Create a LinkedIn Developer App at https://www.linkedin.com/developers/
2. Obtain the following credentials:
   - `LINKEDIN_CLIENT_ID`
   - `LINKEDIN_CLIENT_SECRET`
   - `LINKEDIN_REDIRECT_URI`
   - `LINKEDIN_ACCESS_TOKEN` (obtained via OAuth flow)

### OAuth Flow (First-Time Setup)
```
1. Direct user to: https://www.linkedin.com/oauth/v2/authorization
   ?response_type=code
   &client_id={CLIENT_ID}
   &redirect_uri={REDIRECT_URI}
   &state={STATE}
   &scope=w_member_social,r_liteprofile,r_emailaddress

2. LinkedIn redirects to your callback with authorization code

3. Exchange code for access token:
   POST https://www.linkedin.com/oauth/v2/accessToken
   grant_type=authorization_code
   &code={AUTHORIZATION_CODE}
   &redirect_uri={REDIRECT_URI}
   &client_id={CLIENT_ID}
   &client_secret={CLIENT_SECRET}
```

## Post Scheduling

### Trigger: LinkedIn Watcher
When the LinkedIn watcher detects:
- New blog post or article to share
- Business milestone reached
- New product/feature announcement
- Weekly industry insights sharing

### Post Types

#### 1. Milestone Announcement
```markdown
We just hit a new milestone! 🎉

[Company Name] has achieved [milestone description].
This represents [impact/metric].

Thank you to our amazing team and customers for making this possible!

#StartupGrowth #Milestones #BusinessGrowth
```

#### 2. Industry Insight
```markdown
💡 [Industry insight or observation]

[Expanded commentary on the trend and what it means for the industry]

What's your take? I'd love to hear your thoughts in the comments.

#[IndustryHashtag] #Leadership #Innovation
```

#### 3. Product/Feature Announcement
```markdown
🚀 Exciting news!

We've just launched [feature/product name]!

Here's what it does:
• [Key benefit 1]
• [Key benefit 2]
• [Key benefit 3]

Try it out: [link]

#ProductLaunch #Innovation #SaaS
```

#### 4. Sales-Generating Post
```markdown
Looking for [target audience] who need [solution]?

We help [company type] achieve [outcome] by [key differentiator].

Here's a recent case study:
[Client]: [Brief result]

DM me or comment below to learn more. 📩

#[TargetIndustry] #B2B #Sales
```

## Content Calendar Integration

Posts are scheduled based on optimal LinkedIn engagement times:
- **Best days:** Tuesday, Wednesday, Thursday
- **Best times:** 8-10 AM, 12 PM, 5-6 PM (audience timezone)
- **Frequency:** 2-3 posts per week maximum

## Engagement Tracking

After each post, the following metrics are logged:
- Impressions
- Clicks
- Likes/Reactions
- Comments
- New connection requests generated

These are stored in `/Analytics/LinkedIn_Performance.md` for weekly review.

## API Endpoint

```
POST https://api.linkedin.com/v2/ugcPosts

Authorization: Bearer {access_token}
Content-Type: application/json

{
  "author": "urn:li:person:{person_urn}",
  "lifecycleState": "PUBLISHED",
  "specificContent": {
    "com.linkedin.ugc.ShareContent": {
      "shareCommentary": {
        "text": "{post_text}"
      },
      "shareMediaCategory": "NONE"
    }
  },
  "visibility": {
    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
  }
}
```

## Usage Example

When Business_Goals.md shows a milestone was reached:
1. LinkedIn watcher reads milestone update
2. Formats as milestone announcement post
3. Creates approval request in /Pending_Approval/
4. After approval, posts to LinkedIn via API
5. Logs result to /Analytics/LinkedIn_Performance.md

## Error Handling

| Error | Recovery |
|-------|----------|
| 429 Rate Limit | Exponential backoff, retry after delay |
| 401 Unauthorized | Refresh access token, retry once |
| 403 Forbidden | Log permanently, do not retry |
| Network timeout | Retry up to 3 times with backoff |

See examples/linkedin-post-example.md for a complete workflow example.