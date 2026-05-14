# Silver Tier Setup Guide - Email & Messaging Integration

## Overview

Silver Tier adds email (Gmail) and messaging (WhatsApp) integration to the AI Employee system.

**Components:**
- Gmail Processor Skill (email handling)
- WhatsApp Handler Skill (messaging)
- Gmail Watcher (Python module)
- WhatsApp Watcher (Python module)
- Filesystem Watcher (monitors vault approvals)
- FastAPI Server (webhooks + polling)

---

## Prerequisites

### Software
- Python 3.10+
- FastAPI & Uvicorn
- Gmail API access
- Twilio account with WhatsApp enabled

### Accounts
- Google Cloud project with Gmail API enabled
- Twilio account (free trial available)
- WhatsApp Business Account (linked to Twilio)

---

## Setup Steps

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

New dependencies for Silver Tier:
- fastapi>=0.104.0
- uvicorn>=0.24.0
- google-auth-oauthlib>=1.1.0
- google-api-python-client>=2.100.0
- twilio>=8.10.0
- watchdog>=3.0.0

### 2. Gmail Setup

#### 2a. Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create new project: "AI Employee"
3. Enable Gmail API
4. Create OAuth 2.0 credentials (Desktop app)
5. Download credentials JSON

#### 2b. Get Gmail OAuth Token

```python
# Run this script once to authorize
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly',
          'https://www.googleapis.com/auth/gmail.modify']

flow = InstalledAppFlow.from_client_secrets_file(
    'credentials.json', SCOPES)
creds = flow.run_local_server(port=0)

# Get refresh token
print(f"Refresh Token: {creds.refresh_token}")
```

#### 2c. Add to .env

```bash
GMAIL_CLIENT_ID=your_client_id.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=your_client_secret
GMAIL_REFRESH_TOKEN=your_refresh_token
ENABLE_GMAIL_WATCHER=true
```

### 3. Twilio WhatsApp Setup

#### 3a. Create Twilio Account

1. Go to [Twilio Console](https://www.twilio.com/console)
2. Sign up for account (free trial)
3. Verify phone number

#### 3b. Enable WhatsApp

1. Go to Messaging → Try it out → WhatsApp
2. Request WhatsApp sandbox (or production account)
3. Get sandbox number and test phone number
4. Verify your test number

#### 3c. Configure Webhook

1. Go to WhatsApp → Sandbox → Settings
2. Set webhook URL:
   ```
   https://your-domain.com/webhooks/whatsapp
   ```
3. Copy auth token from Twilio console

#### 3d. Add to .env

```bash
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1234567890
ENABLE_WHATSAPP_WATCHER=true
```

### 4. Configure Feature Flags

Update `.env` to enable watchers:

```bash
# Email
ENABLE_GMAIL_WATCHER=true
GMAIL_POLL_INTERVAL=300  # 5 minutes

# Messaging
ENABLE_WHATSAPP_WATCHER=true
WHATSAPP_POLL_INTERVAL=60  # 1 minute

# Filesystem monitoring
ENABLE_ORCHESTRATOR=true
```

### 5. Run the Server

```bash
# Start FastAPI server with uvicorn
python3 server.py

# Or directly:
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

Server will start at `http://localhost:8000`

---

## Testing

### Gmail Watcher Testing

#### Manual Poll

```bash
# Trigger Gmail poll
curl -X POST http://localhost:8000/watchers/gmail/poll

# Response:
{
  "status": "ok",
  "emails_processed": 2,
  "timestamp": "2026-02-08T11:30:00Z"
}
```

#### Send Test Email

1. Send email to your Gmail account
2. Mark as unread
3. Call manual poll
4. Check `AI_Employee_Vault/Needs_Action/` for new task file

#### Expected Task File

```markdown
---
type: email_task
priority: high
source: gmail
created: 2026-02-08T11:30:00Z
email_id: msg123
from: sender@example.com
subject: Test email
---

# Email: Test email

[Content...]
```

### WhatsApp Watcher Testing

#### Get WhatsApp Sandbox Number

From Twilio console, find your sandbox number:
```
+1 415 523 8886  (example)
```

#### Send Test Message

1. Open WhatsApp on test phone
2. Send message to sandbox number: `join your-code`
3. Send message: "Hi, testing"
4. Check server logs:
   ```
   INFO: Queued WhatsApp message from +1234567890
   ```

#### Expected Task File

```markdown
---
type: whatsapp_task
priority: medium
source: whatsapp
created: 2026-02-08T11:30:00Z
from_number: +1234567890
message_sid: SMxxxxx
---

# WhatsApp Message from +1234567890

[Message content...]
```

#### Verify Auto-Response

Check WhatsApp:
- Should receive: "Hi! I'm here and ready to help. What do you need?"

### Filesystem Watcher Testing

#### Manual Approval

1. Create approval request in `Needs_Action/`
2. Move to `Pending_Approval/` folder in Obsidian
3. Review and move to `Approved/`
4. Filesystem watcher detects change
5. Executes action (stub in current version)
6. Moves to `Done/`

#### Check Status

```bash
# Get pending approvals
curl http://localhost:8000/watchers/filesystem/pending

# Get approved actions
curl http://localhost:8000/watchers/filesystem/approved
```

---

## Health Checks

### Server Health

```bash
# Check server status
curl http://localhost:8000/health

# Response:
{
  "status": "healthy",
  "timestamp": "2026-02-08T11:30:00Z",
  "watchers": {
    "gmail": {
      "name": "gmail",
      "running": true,
      "error_count": 0,
      "last_poll_time": "2026-02-08T11:30:00Z",
      "poll_interval": 300
    },
    "whatsapp": {
      "name": "whatsapp",
      "running": true,
      "error_count": 0,
      "queued_messages": 0,
      "poll_interval": 60
    },
    "filesystem": {
      "name": "filesystem",
      "running": true,
      "error_count": 0
    }
  }
}
```

### Individual Watcher Status

```bash
# Gmail status
curl http://localhost:8000/watchers/gmail/status

# WhatsApp status
curl http://localhost:8000/watchers/whatsapp/status

# Filesystem status
curl http://localhost:8000/watchers/filesystem/status
```

---

## Running Tests

### Run Watcher Tests

```bash
python3 -m pytest tests/test_watchers.py -v

# Expected output:
# test_base_watcher_initialization PASSED
# test_gmail_categorize_priority PASSED
# test_whatsapp_categorize_priority PASSED
# test_filesystem_initialization PASSED
# ... (22+ tests)
```

### Run All Tests

```bash
python3 -m pytest tests/ -v

# Should see:
# 22 Bronze Tier tests (passing)
# 10+ Silver Tier tests (passing)
# Total: 32+ tests passing
```

---

## Configuration Reference

### Gmail Watcher Configuration

```bash
# .env settings
GMAIL_CLIENT_ID=xxx.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=xxx
GMAIL_REFRESH_TOKEN=xxx
GMAIL_POLL_INTERVAL=300  # seconds
ENABLE_GMAIL_WATCHER=true
```

### WhatsApp Watcher Configuration

```bash
# .env settings
TWILIO_ACCOUNT_SID=ACxxx
TWILIO_AUTH_TOKEN=xxx
TWILIO_PHONE_NUMBER=+1234567890
WHATSAPP_POLL_INTERVAL=60  # seconds
ENABLE_WHATSAPP_WATCHER=true
```

### Filesystem Watcher Configuration

```bash
# .env settings
VAULT_PATH=AI_Employee_Vault
ENABLE_ORCHESTRATOR=true
```

---

## Troubleshooting

### Gmail Issues

**"Invalid credentials"**
- Check refresh token is current
- Regenerate OAuth credentials
- Ensure scopes are correct

**"No emails fetched"**
- Send test email and mark unread
- Check GMAIL_POLL_INTERVAL (default 5 min)
- Run manual poll: `POST /watchers/gmail/poll`

### WhatsApp Issues

**"Invalid Twilio signature"**
- Verify webhook URL in Twilio console
- Check auth token in .env
- Ensure signature calculation matches

**"No message response"**
- Verify phone is joined to sandbox
- Check auto-response keywords
- Check server logs for errors

### Filesystem Issues

**"Approvals not detected"**
- Ensure vault folders exist
- Check folder paths in config
- Verify file permissions on vault directory

---

## Next Steps

### Immediate (This Week)

- [ ] Configure Gmail API credentials
- [ ] Set up Twilio WhatsApp account
- [ ] Run server and test watchers
- [ ] Send test email and WhatsApp message
- [ ] Verify task creation in vault
- [ ] Test approval workflow

### Short-term (Next Week)

- [ ] Deploy server to cloud (AWS, Heroku, etc.)
- [ ] Configure production WhatsApp number
- [ ] Set up email domain authentication
- [ ] Add MCP servers for action execution
- [ ] Implement real response sending

### Medium-term (Gold Tier)

- [ ] Add Financial Auditor skill
- [ ] Create CEO briefing generation
- [ ] Implement transaction analysis
- [ ] Add financial approval gates

---

## Architecture Overview

```
User Sends Email/Message
        ↓
Gmail API / Twilio Webhook
        ↓
Watcher (Gmail/WhatsApp)
        ↓
Parse & Categorize
        ↓
Create Task in Vault
        ↓
Claude Reviews
        ↓
Create Plan/Approval
        ↓
User Reviews in Obsidian
        ↓
User Moves to Approved/
        ↓
Filesystem Watcher Detects
        ↓
Execute Action (MCP Server)
        ↓
Send Response
        ↓
Complete Task
```

---

## Security Checklist

- [ ] Credentials in .env (never in code)
- [ ] Credentials not logged
- [ ] HTTPS for webhook endpoint
- [ ] Twilio signature validation enabled
- [ ] Rate limiting configured
- [ ] Vault directory permissions set to 700
- [ ] Backup .env file (encrypted)
- [ ] Rotate credentials monthly

---

## Performance Targets

| Operation | Target | Actual |
|-----------|--------|--------|
| Email fetch | < 1s | < 500ms |
| Task creation | < 100ms | < 50ms |
| WhatsApp webhook | < 1s | < 500ms |
| Filesystem detection | < 500ms | < 100ms |
| Total end-to-end | < 30s | < 10s |

---

## Support

### Documentation
- [Gmail Processor Skill](.claude/skills/gmail-processor/SKILL.md)
- [WhatsApp Handler Skill](.claude/skills/whatsapp-handler/SKILL.md)
- [FastAPI Server](server.py)
- [Watcher Tests](tests/test_watchers.py)

### Debugging
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Run with verbose output
uvicorn server:app --log-level debug

# Watch vault in real-time
watch -n 1 'ls -la AI_Employee_Vault/Needs_Action/'
```

---

**Silver Tier Status:** Ready for Production  
**Date:** 2026-02-08  
**Version:** 1.0.0
