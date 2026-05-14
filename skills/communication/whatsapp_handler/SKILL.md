---
name: whatsapp-handler
description: Handle incoming WhatsApp messages, extract actionable items, and create urgent task files. Integrates with Twilio WhatsApp API.
allowed-tools: Read, Write, Glob, HTTP
---

# WhatsApp Handler Skill

Process incoming WhatsApp messages, extract urgent items, and create high-priority task files in the vault.

## Overview

This skill handles:
- Receiving WhatsApp messages via Twilio webhooks
- Parsing message content for actionable items
- Responding to common queries automatically
- Creating high-priority task files
- Sending confirmations back via WhatsApp
- Handling media attachments (images, files)

## Message Priority Mapping

### Message Analysis

```
CRITICAL (Immediate Action)
├─ From: Known urgent contacts (CEO, COO, key client)
├─ Contains: "URGENT", "EMERGENCY", "HELP"
├─ Keywords: "Down", "Crisis", "Fire"
└─ Response: Within 15 minutes

HIGH (Soon)
├─ From: Regular business contacts
├─ Contains: "Important", "Need help", "Question"
├─ Keywords: "Decision", "Approval", "Quick review"
└─ Response: Within 1 hour

MEDIUM (Standard)
├─ From: Team members
├─ Contains: "Update", "FYI", "When you get a chance"
├─ Keywords: "Info", "Status", "Confirm"
└─ Response: Within 4 hours
```

## Twilio WhatsApp Integration

### Webhook Setup

Twilio sends incoming messages to your webhook endpoint:

```
POST /webhooks/whatsapp
Headers:
  Content-Type: application/x-www-form-urlencoded
  X-Twilio-Signature: [signature]

Body:
  From=+1234567890
  To=+0987654321
  MessageSid=SM123456789
  AccountSid=AC123456
  Body=Message text here
  MediaUrl0=https://api.twilio.com/2010-04-01/Accounts/AC.../Media/MG...
  NumMedia=1
  NumSegments=1
```

### Message Format

```
{
  "from": "+1234567890",
  "to": "+0987654321",
  "message_sid": "SM123456789",
  "account_sid": "AC123456",
  "body": "Message text",
  "timestamp": "2026-02-08T10:30:00Z",
  "media": [
    {
      "url": "https://api.twilio.com/2010-04-01/Accounts/AC.../Media/MG...",
      "type": "image/jpeg",
      "file_size": 102400
    }
  ]
}
```

### Sending Replies

**Send Text Message:**
```
POST https://api.twilio.com/2010-04-01/Accounts/{AccountSid}/Messages.json
Headers:
  Authorization: Basic {encoded_credentials}
  Content-Type: application/x-www-form-urlencoded

Body:
  From=whatsapp:+0987654321
  To=whatsapp:+1234567890
  Body=Your response message
```

**Send Media:**
```
Body:
  From=whatsapp:+0987654321
  To=whatsapp:+1234567890
  MediaUrl=https://example.com/image.jpg
```

## Task File Format

### Basic WhatsApp Message Task

```markdown
---
type: whatsapp_task
priority: high
source: whatsapp
created: 2026-02-08T10:30:00Z
from_number: +1234567890
from_name: John Doe
message_sid: SM123456789
media_count: 0
replied: false
---

# WhatsApp Message from John Doe

**From:** +1234567890 (John Doe)  
**Received:** 2026-02-08T10:30:00Z  
**Priority:** High  

## Message Content

The actual message content here. User asked about project status.

## Extracted Actions

- [ ] Review project status
- [ ] Send update to John
- [ ] Schedule follow-up call if needed

## Quick Response Needed

User expects response within 1 hour.

## Send Reply

Use this format to reply:
```
whatsapp +1234567890 "Your message here"
```

**Message ID:** SM123456789
**Status:** Awaiting response
```

### Message with Media

```markdown
---
type: whatsapp_task
priority: high
source: whatsapp
created: 2026-02-08T10:30:00Z
from_number: +1234567890
from_name: John Doe
message_sid: SM123456789
media_count: 1
media:
  - url: https://api.twilio.com/2010-04-01/Accounts/.../Media/MG...
    type: image/jpeg
    size: 102400
replied: false
---

# WhatsApp Message with Image from John Doe

[Message content with note about attached image]

## Attachment

📷 Image attachment (102.4 KB)
- Type: image/jpeg
- Download: Check Twilio console

## Action Required

Review image and respond.
```

## Automatic Responses

### Common Queries

```
"status?" or "whats up" or "how are you?"
→ "I'm here and ready to help! What do you need?"

"help" or "can you help"
→ "Of course! Tell me what you need and I'll take care of it."

"reminder" or "remind me"
→ "I'll create a reminder task for you. What should I remind you about?"

"thanks" or "thank you" or "thx"
→ "Happy to help! 👍"
```

### Escalation to Vault

If message contains:
- Sender number + "critical", "urgent", "asap"
- "action needed", "review required", "approval needed"
- High-priority keywords from Company_Handbook.md

Then create task with appropriate priority and notify immediately.

## Media Handling

### Supported Attachments

- **Images:** jpeg, png, gif, webp
- **Documents:** pdf, docx, xlsx, pptx
- **Audio:** mp3, wav, m4a
- **Video:** mp4, mov (limited by Twilio)

### Processing Pipeline

```
1. Receive media URL from Twilio
2. Download file metadata
3. Store reference in task file
4. Create task with media note
5. Store media link for later retrieval
6. Set appropriate priority based on media type
```

### Example: Image Review Task

```markdown
---
type: whatsapp_task
priority: high
source: whatsapp
media_count: 1
media:
  - type: image/jpeg
    description: Screenshot showing bug report
---

# WhatsApp Image from Developer

[Message explaining the bug]

## Attached Image

📷 Screenshot (image/jpeg)
Link: [Twilio media URL]

## Action Required

- Review screenshot
- Diagnose issue
- Send instructions
```

## Contact Management

### Known Contacts

Store contacts for priority classification:

```python
KNOWN_CONTACTS = {
    "+1234567890": {
        "name": "John Doe",
        "title": "CEO",
        "priority_boost": "critical",
        "auto_response": "Acknowledged, reviewing now"
    },
    "+1987654321": {
        "name": "Jane Smith",
        "title": "Sales Lead",
        "priority_boost": "high",
        "auto_response": "Got it, will respond shortly"
    }
}
```

### Dynamic Classification

```
If sender in KNOWN_CONTACTS:
  priority = base_priority + contact.priority_boost
  send_auto_response(contact.auto_response)
```

## Message Threading

### Group Conversations

WhatsApp supports group messages. Track them:

```markdown
---
type: whatsapp_task
priority: medium
source: whatsapp
group_name: "Project Alpha Team"
group_participants: 5
message_sid: SM123456789
is_group_message: true
---

# WhatsApp Group Message

**Group:** Project Alpha Team (5 members)  
**From:** John Doe  

[Message content]

## Context

This is part of a group conversation. Other participants may respond.
Check WhatsApp directly for full thread.
```

## Response Workflow

### Reply Options

1. **Quick Reply** - Pre-written responses for common queries
2. **Custom Message** - Type new response
3. **Task Created** - Create vault task and respond later
4. **Escalate** - Mark critical and notify immediately

### Confirmation Flow

```
1. User sends WhatsApp message
2. Watcher receives via webhook
3. Create task in Needs_Action/
4. Send auto-response: "Message received, processing..."
5. Claude reviews and responds
6. Send actual response via WhatsApp
7. Log in task: "replied: true"
```

## Error Handling

### Message Processing Errors

```
If parse_error:
  → Send: "Sorry, I couldn't understand. Can you rephrase?"
  → Create task anyway for manual review

If media_download_error:
  → Send: "I received your message but couldn't download the attachment"
  → Create task with media URL for manual download

If rate_limit_hit:
  → Queue message
  → Process in 1 minute
  → Notify user of slight delay

If auth_error:
  → Alert system
  → Stop processing new messages
  → Log for debugging
```

### Retry Logic

```python
max_retries = 3
backoff_seconds = [1, 5, 30]

for attempt in range(max_retries):
    try:
        process_message()
        break
    except TransientError:
        if attempt < max_retries - 1:
            wait(backoff_seconds[attempt])
        else:
            log_failed_message()
            alert_user()
```

## Integration Points

### With Vault
- Create files in `AI_Employee_Vault/Needs_Action/`
- Use naming: `WHATSAPP_YYYYMMDD_HHMM_001.md`
- Higher default priority than email

### With Config
- Read Twilio credentials from .env
- Webhook URL from config
- Feature flag: ENABLE_WHATSAPP_WATCHER

### With Gmail
- Can cross-reference between email and WhatsApp
- Create summary if same topic in both
- Link related messages

## Security & Privacy

### Message Security
✅ Don't log full message content
✅ Don't store PII in task files
✅ Encrypt Twilio webhook data
✅ Validate webhook signature
✅ Rate limit responses
✅ Authenticate users

### Contact Privacy
✅ Encrypt phone numbers in vault
✅ Don't share contact lists
✅ Respect group message privacy
✅ Delete old message data periodically

## Performance

### Rate Limiting
- Twilio: 10 messages per second
- Watcher: Process as they arrive
- Response: Send within 5 seconds
- Safe buffer: Plenty of capacity

### Webhook Timeout
- Process message in < 2 seconds
- Queue slow operations
- Return 200 OK immediately
- Handle async in background

## Testing

### Unit Tests
- Parse message formats
- Categorize priorities
- Generate auto-responses
- Handle errors

### Integration Tests
- Receive webhook messages
- Send replies via Twilio
- Create task files
- Handle media attachments

### Staging Tests
- Use Twilio test account
- Send real messages from test number
- Verify task creation
- Verify response sending

## Best Practices

1. **Fast Response**
   - Send confirmation immediately
   - Process detailed response in background
   - User expects WhatsApp speed

2. **Clear Communication**
   - Keep messages short and clear
   - Use emoji for visual clarity
   - Confirm receipt of important info

3. **Context Preservation**
   - Always include original message in task
   - Link to related tasks
   - Store media attachments

4. **Priority Accuracy**
   - Don't over-prioritize
   - Use keywords wisely
   - Escalate only when necessary

5. **Contact Management**
   - Keep known contacts list updated
   - Regular review of priority assignments
   - Respect communication preferences

## Example Implementation

```python
class WhatsAppHandler:
    def __init__(self, config):
        self.twilio_client = self.setup_twilio()
        self.vault_manager = VaultManager()
        self.known_contacts = self.load_contacts()
    
    def setup_twilio(self):
        # Initialize Twilio client with credentials
        pass
    
    def receive_webhook(self, request):
        # Parse incoming WhatsApp message
        # Validate signature
        # Extract: from, body, media
        return self.process_message(request)
    
    def process_message(self, message):
        # Determine priority
        # Create task file
        # Send auto-response
        # Return webhook response
        pass
    
    def categorize_priority(self, message):
        # Analyze content and sender
        # Return priority level
        pass
    
    def send_response(self, phone_number, message):
        # Send via Twilio WhatsApp
        pass
    
    def create_task_file(self, message, priority):
        # Format as markdown task
        # Write to Needs_Action/
        pass
```

## See Also

- [Twilio WhatsApp API](https://www.twilio.com/docs/whatsapp)
- [Twilio Webhooks](https://www.twilio.com/docs/usage/webhooks)
- [WhatsApp Task Template](.../templates/whatsapp-task-template.md)
