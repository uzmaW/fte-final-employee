---
plan_id: EXAMPLE_WHATSAPP_FLOW_001
type: whatsapp_processing_example
created: 2026-02-08T11:00:00Z
---

# WhatsApp Message Handling - Complete Example

## Scenario

An urgent WhatsApp message arrives from the CEO asking for immediate status update on a critical project. The system should:
1. Receive message via Twilio webhook
2. Validate webhook signature
3. Categorize priority as CRITICAL
4. Send auto-acknowledgment
5. Create high-priority task for Claude
6. Process request and send response

## Step-by-Step Walkthrough

### Step 1: WhatsApp Message Sent

```
From: +1234567890 (CEO)
Timestamp: 2026-02-08T11:00:00Z
Body: "URGENT: Project status? System down?"
Media: None
```

### Step 2: Twilio Webhook Received

Twilio sends POST request to `/webhooks/whatsapp`:

```json
{
  "From": "whatsapp:+1234567890",
  "To": "whatsapp:+0987654321",
  "Body": "URGENT: Project status? System down?",
  "MessageSid": "SM123abc456def",
  "AccountSid": "ACxxxxxxxxxxxxx",
  "NumMedia": "0",
  "X-Twilio-Signature": "..."
}
```

### Step 3: Signature Validation

WhatsApp watcher validates signature:

```python
# Expected signature calculation
message = url + "Body" + "URGENT: Project status? System down?"
expected_sig = HMAC-SHA1(auth_token, message)

if twilio_signature == expected_sig:
    # Valid - process message
else:
    # Invalid - reject
    return 401 Unauthorized
```

Result: ✅ Signature valid

### Step 4: Priority Categorization

Analysis:
- Body contains "URGENT" → Critical indicator
- Body mentions "System down" → Critical indicator
- From: +1234567890 → Check if CEO (YES - in known contacts)
- **Result: Priority = CRITICAL**

### Step 5: Auto-Response

Since this is a CEO asking for status, send immediate acknowledgment:

```
Message: "Acknowledged! Reviewing now. Will respond shortly."
Send to: +1234567890
Status: ✅ Sent
```

### Step 6: Create Task File

**File:** `AI_Employee_Vault/Needs_Action/WHATSAPP_20260208_110000_001.md`

```markdown
---
type: whatsapp_task
priority: critical
source: whatsapp
created: 2026-02-08T11:00:00Z
from_number: +1234567890
from_name: CEO
message_sid: SM123abc456def
media_count: 0
replied: false
---

# WhatsApp Message from CEO

**From:** +1234567890 (CEO)  
**Received:** 2026-02-08T11:00:00Z  
**Priority:** Critical  

## Message Content

URGENT: Project status? System down?

## Extracted Actions

- [ ] Check system status
- [ ] Verify if services are actually down
- [ ] Gather incident details
- [ ] Send status update to CEO
- [ ] If down, initiate incident response

## Context

This is a critical message from the CEO asking about system status. Immediate response required.

## Auto-Response Sent

✅ Acknowledgment message sent to +1234567890

---

Message SID: SM123abc456def
Status: Awaiting response
```

### Step 7: Claude Processing

Claude receives task notification:

1. **Reads task file** from Needs_Action/
2. **Assesses urgency** - Critical from CEO
3. **Checks system status** - Can call monitoring API
4. **Gathers info** - System UP or DOWN?
5. **Creates response** - Factual status update
6. **Sends via WhatsApp** - Reply directly to +1234567890

### Step 8: System Status Check

Claude checks infrastructure:
- API endpoints: ✅ OK
- Database: ✅ OK
- Cache layer: ✅ OK
- **Overall: System is UP**

### Step 9: Compose Response

```
"System status is OK - all services operational. 
- API: ✅
- DB: ✅  
- Cache: ✅

No incidents detected. Green across the board."
```

### Step 10: Send WhatsApp Response

WhatsApp watcher (MCP server) sends:

```
To: +1234567890
Message: "System status is OK - all services operational. API: ✅ DB: ✅ Cache: ✅ No incidents detected. Green across the board."
Status: ✅ Delivered
```

### Step 11: Update Task

Task file updated in vault:

```markdown
---
type: whatsapp_task
priority: critical
source: whatsapp
created: 2026-02-08T11:00:00Z
from_number: +1234567890
from_name: CEO
message_sid: SM123abc456def
media_count: 0
replied: true
response_sent: 2026-02-08T11:05:00Z
---

[Previous content]

## Response Sent

✅ Response delivered at 2026-02-08T11:05:00Z

Response text:
"System status is OK - all services operational. API: ✅ DB: ✅ Cache: ✅ No incidents detected. Green across the board."

Status: Complete
```

## Integration Flow

```
WhatsApp Message
    ↓
Twilio Webhook
    ↓
Signature Validation ✅
    ↓
Parse Message
    ↓
Determine Priority (CRITICAL)
    ↓
Send Auto-Ack to CEO
    ↓
Create Task in Vault
    ↓
Claude Detects Task
    ↓
Check System Status
    ↓
Compose Response
    ↓
Send WhatsApp Reply
    ↓
Update Task as Complete
    ↓
Move to Done/
```

## Performance Metrics

- Webhook received: 0ms
- Signature validation: <5ms
- Message parsing: <5ms
- Priority categorization: <10ms
- Auto-response sent: <500ms
- Task creation: <100ms
- **Total webhook response time: <1 second**

- Claude processing: <5 seconds
- System check: <1 second
- Response composition: <2 seconds
- Send WhatsApp: <1 second
- **Total end-to-end: <10 seconds**

## Error Handling

**Invalid signature:**
```
Return: 401 Unauthorized
Action: Log and alert
```

**Webhook timeout:**
```
Queue message for retry
Retry in 30 seconds
Max 3 retries
```

**Send response failure:**
```
Log error with message SID
Mark task as "response_failed"
Alert system
Retry at next opportunity
```

**Missing required fields:**
```
Log warning
Create task with available data
Alert for manual review
```

## Success Criteria

✅ WhatsApp message received  
✅ Signature validated  
✅ Priority correctly categorized as CRITICAL  
✅ Auto-response sent immediately  
✅ Task created in Needs_Action/  
✅ Claude processes within 10 seconds  
✅ System status checked  
✅ Response sent back via WhatsApp  
✅ Task marked as complete  
✅ Entire flow under 1 minute  

## Group Messages

If this were a group message instead:

```markdown
---
type: whatsapp_task
priority: high
source: whatsapp
group_name: "Executive Team"
group_participants: 8
is_group_message: true
---

[Different handling for group]
```

Group messages get slightly lower priority but same flow.

## Related

- [WhatsApp Handler Skill](.../SKILL.md)
- [Company Handbook](../../../../AI_Employee_Vault/Company_Handbook.md)
- [FastAPI Server](../../../../server.py)
- [Twilio Integration Guide](https://www.twilio.com/docs/whatsapp)
