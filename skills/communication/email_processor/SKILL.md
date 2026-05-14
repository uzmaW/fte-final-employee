---
name: gmail-processor
description: Process incoming Gmail messages, extract actionable items, and create task files in the vault. Integrates with Google Gmail API.
allowed-tools: Read, Write, Glob, HTTP
---

# Gmail Processor Skill

Process incoming Gmail emails, extract actionable items, prioritize them, and create task files in the vault for Claude to process.

## Overview

This skill handles:
- Authenticating with Gmail API (OAuth)
- Polling unread emails
- Extracting key information (sender, subject, content)
- Categorizing emails by importance
- Creating task files in `/Needs_Action/`
- Marking emails as processed
- Handling email attachments

## Email Categorization

### Priority Mapping

```
CRITICAL (High Priority)
├─ From CEO/leadership
├─ Contains: "URGENT", "ASAP", "TODAY"
├─ Subject contains: "Emergency", "Down", "Crisis"
└─ Response needed within 1 hour

HIGH (High Priority)
├─ From key clients/partners
├─ Contains: "Important", "Request", "Approval needed"
├─ Subject contains: "Decision", "Review", "Action"
└─ Response needed within 4 hours

MEDIUM (Medium Priority)
├─ Standard business emails
├─ Contains: "FYI", "Update", "Discussion"
├─ Subject contains: "Update", "Info", "Follow-up"
└─ Response needed within 1 day

LOW (Low Priority)
├─ General information
├─ Contains: "Archive", "Reference", "FYI"
├─ Subject contains: "Newsletter", "Digest", "Notification"
└─ Response needed within 1 week
```

## Gmail API Integration

### Authentication Flow

1. **Initial Setup**
   - User authorizes app via OAuth consent screen
   - Receives authorization code
   - Exchange code for refresh token
   - Store refresh token in .env

2. **Token Refresh**
   - Use refresh token to get new access token
   - Access token expires in 1 hour
   - Automatically refresh on each request

3. **Required Scopes**
   ```
   https://www.googleapis.com/auth/gmail.readonly
   https://www.googleapis.com/auth/gmail.modify
   ```

### Email Fetching

**List Unread Emails:**
```
GET https://www.googleapis.com/gmail/v1/users/me/messages?q=is:unread
Headers: Authorization: Bearer <access_token>

Response:
{
  "messages": [
    {"id": "msg123", "threadId": "thread123"},
    {"id": "msg124", "threadId": "thread124"}
  ]
}
```

**Get Email Details:**
```
GET https://www.googleapis.com/gmail/v1/users/me/messages/msg123?format=full
Headers: Authorization: Bearer <access_token>

Response:
{
  "id": "msg123",
  "threadId": "thread123",
  "payload": {
    "headers": [
      {"name": "From", "value": "sender@example.com"},
      {"name": "Subject", "value": "Email subject"},
      {"name": "Date", "value": "2026-02-08T10:30:00Z"}
    ],
    "parts": [
      {
        "mimeType": "text/plain",
        "body": {"data": "base64_encoded_content"}
      }
    ]
  }
}
```

**Mark as Read:**
```
POST https://www.googleapis.com/gmail/v1/users/me/messages/msg123/modify
Headers: Authorization: Bearer <access_token>
Body: {
  "removeLabelIds": ["UNREAD"]
}
```

## Email Processing Pipeline

```
1. Authenticate with Gmail API
   ↓
2. Fetch unread emails (max 10 per poll)
   ↓
3. For each email:
   ├─ Extract sender, subject, content
   ├─ Determine priority level
   ├─ Extract action items
   ├─ Check for attachments
   ├─ Create task file in Needs_Action/
   └─ Mark email as read
   ↓
4. Handle errors gracefully
   ├─ Log failed emails
   ├─ Retry transient errors
   └─ Alert on auth failures
```

## Task File Format

### Basic Email Task

```markdown
---
type: email_task
priority: high
source: gmail
created: 2026-02-08T10:30:00Z
email_id: abc123xyz789
thread_id: thread123
from: sender@example.com
subject: Original email subject
has_attachment: false
---

# Email: Original Email Subject

**From:** sender@example.com  
**Date:** 2026-02-08T10:30:00Z  
**Priority:** High  

## Email Content

[Email body content here - plain text extracted]

## Extracted Actions

Based on email content, these actions are suggested:
- Action 1: [description]
- Action 2: [description]

## Keywords Detected

- URGENT ⚠️
- Review needed
- Approval required

## Suggested Response

[Brief suggestion for response if applicable]

## Original Thread

Email ID: abc123xyz789
Thread ID: thread123
```

### Email with Attachments

```markdown
---
type: email_task
priority: high
source: gmail
created: 2026-02-08T10:30:00Z
email_id: abc123xyz789
thread_id: thread123
from: sender@example.com
subject: Original email subject
has_attachment: true
attachments:
  - filename: document.pdf
    mimetype: application/pdf
    size: 1024000
  - filename: spreadsheet.xlsx
    mimetype: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
    size: 512000
---

# Email: Original Email Subject (With Attachments)

[Same format as above]

## Attachments

- `document.pdf` (1.0 MB) - Action: Download and review
- `spreadsheet.xlsx` (512 KB) - Action: Analyze data

## Action Required

Review attachments and respond.
```

## Conversation Threads

### Tracking Reply Context

When processing email threads, preserve context:

```markdown
---
type: email_task
priority: medium
source: gmail
created: 2026-02-08T10:30:00Z
email_id: latest_msg
thread_id: thread123
from: sender@example.com
subject: RE: Project Discussion
is_reply: true
thread_message_count: 5
---

# Email Thread: Project Discussion

**Latest Message From:** sender@example.com  
**Thread Contains:** 5 messages  

## Thread Summary

Previous messages:
1. 2026-02-05: Initial proposal from sender
2. 2026-02-06: Your response
3. 2026-02-07: Sender's reply
4. 2026-02-08: New message (THIS ONE)

## Latest Message

[New message content]

## Thread Context

See Gmail thread ID: thread123 for full conversation history.
```

## Sender Classification

### Known Senders

Keep a simple sender database to improve prioritization:

```markdown
---
type: email_task
priority: critical
source: gmail
sender_classification: executive
---

# Email from CEO

[Email from classified sender gets CRITICAL priority]
```

### Automatically Adjust Priority

- If from: CEO/leadership → CRITICAL
- If from: Key client → HIGH
- If reply to: CRITICAL email → HIGH
- If mentions: CEO/urgent → CRITICAL
- If flagged in Gmail → HIGH

## Error Handling

### Transient Errors
- Network timeout → Retry in 1 minute
- Rate limit hit → Backoff exponentially
- Temporary auth failure → Retry with refresh token

### Permanent Errors
- Invalid credentials → Alert and stop
- Email deleted → Skip and continue
- Quota exceeded → Alert and stop

### Recovery

```python
if error_type == "network_timeout":
    wait(60)  # Wait 1 minute
    retry()
elif error_type == "rate_limit":
    wait(300)  # Wait 5 minutes
    retry()
elif error_type == "auth_error":
    alert_user("Gmail authentication failed")
    stop()
```

## Performance Considerations

### Rate Limiting
- Gmail API: 10 queries per second per user
- Watcher poll interval: 5 minutes (12 queries/hour)
- Safe margin: Well below quota

### Email Batch Size
- Max emails per poll: 10
- Rationale: Prevents overwhelming vault
- Can adjust based on volume

### Caching
- Cache email list for 30 seconds
- Prevents duplicate processing
- Refresh on new unread count change

## Integration Points

### With Vault
- Create files in `AI_Employee_Vault/Needs_Action/`
- Use naming: `EMAIL_YYYYMMDD_HHMM_001.md`
- Parse with vault_manager.py

### With Config
- Read Gmail credentials from .env
- Gmail OAuth settings from config.py
- Feature flag: ENABLE_GMAIL_WATCHER

### With Dashboard
- Update task count in Dashboard.md
- Log email processing events
- Report watcher health

## Best Practices

1. **Extract Clear Actions**
   - What specifically needs to be done?
   - Who should do it?
   - By when?

2. **Preserve Original Content**
   - Always include original email in task
   - Keep sender/date information
   - Store email ID for threading

3. **Smart Prioritization**
   - Use keywords (URGENT, ASAP, etc.)
   - Consider sender importance
   - Check email length (longer = more important)

4. **Handle Sensitive Emails**
   - PII should be noted but not exposed
   - Financial info should trigger approval gates
   - Personal emails might be filtered

5. **Thread Management**
   - Group replies in threads
   - Don't create duplicate tasks for same thread
   - Link related tasks together

## Example Implementation

```python
class GmailProcessor:
    def __init__(self, config):
        self.gmail_service = self.authenticate_gmail()
        self.vault_manager = VaultManager()
    
    def authenticate_gmail(self):
        # Load credentials from .env
        # Exchange refresh token for access token
        # Return Gmail service
        pass
    
    def fetch_unread_emails(self):
        # Call Gmail API to get unread messages
        # Return list of message IDs
        pass
    
    def get_email_details(self, message_id):
        # Call Gmail API to get full message
        # Parse headers and body
        # Return structured email data
        pass
    
    def categorize_priority(self, email):
        # Analyze sender, subject, content
        # Return priority level
        pass
    
    def create_task_file(self, email, priority):
        # Format as markdown task
        # Write to Needs_Action/
        pass
    
    def mark_as_read(self, message_id):
        # Call Gmail API to remove UNREAD label
        pass
    
    def process_all(self):
        # Main loop: fetch → process → mark as read
        pass
```

## Testing

### Unit Tests
- Test email parsing
- Test priority categorization
- Test task file creation
- Test error handling

### Integration Tests
- Test Gmail API authentication
- Test end-to-end email to task flow
- Test thread handling
- Test with real Gmail account (test email)

### Mock Tests
- Mock Gmail API responses
- Test without requiring real Gmail
- Test error scenarios
- Test rate limiting

## Security Considerations

✅ Store refresh token in .env only
✅ Never log email content or credentials
✅ Use service account for testing
✅ Limit scopes to readonly + modify labels
✅ Rotate refresh tokens periodically
✅ Implement rate limiting
✅ Validate email senders

## See Also

- [Gmail API Documentation](https://developers.google.com/gmail/api)
- [Gmail API OAuth Setup](https://developers.google.com/gmail/api/quickstart/python)
- [Email Task Template](.../templates/email-task-template.md)
