---
plan_id: EXAMPLE_GMAIL_FLOW_001
type: email_processing_example
created: 2026-02-08T10:00:00Z
---

# Email Processing Workflow - Complete Example

## Scenario

An urgent email arrives from a key client requesting budget approval for additional resources. The system should:
1. Fetch the email from Gmail
2. Categorize priority as HIGH or CRITICAL
3. Extract key information
4. Create task file for Claude to process
5. Mark email as read in Gmail

## Step-by-Step Walkthrough

### Step 1: Email Arrives

```
From: john.doe@client.com
Subject: URGENT: Q1 Budget Increase Needed
Date: 2026-02-08T10:30:00Z

Hi there,

We need to increase our Q1 budget by $50K to add more engineering resources to the project. This will allow us to accelerate the product roadmap.

Can you review this and let us know if it's possible?

Thanks,
John
```

### Step 2: Gmail Watcher Detects Email

- Polls Gmail API for unread emails
- Finds 1 unread message (MSG_ID_123)
- Fetches full email details
- Extracts: from, subject, body, date

### Step 3: Priority Categorization

Analysis:
- Subject contains "URGENT" → Check for critical
- Body mentions "budget increase" → Check for approval needed
- Sender is from key client → HIGH priority
- **Result: Priority = HIGH**

### Step 4: Action Extraction

Patterns matched:
- "Can you review this and let us know" → Action: Review and respond
- "increase our Q1 budget" → Action: Consider budget impact

**Extracted Actions:**
- Review budget request
- Check Company_Handbook thresholds
- Get financial impact
- Respond to client

### Step 5: Create Task File

**File:** `AI_Employee_Vault/Needs_Action/EMAIL_20260208_103000_001.md`

```markdown
---
type: email_task
priority: high
source: gmail
created: 2026-02-08T10:30:00Z
email_id: MSG_ID_123
thread_id: THREAD_123
from: john.doe@client.com
subject: URGENT: Q1 Budget Increase Needed
has_attachment: false
---

# Email: URGENT: Q1 Budget Increase Needed

**From:** john.doe@client.com  
**Date:** 2026-02-08T10:30:00Z  
**Priority:** High  

## Email Content

Hi there,

We need to increase our Q1 budget by $50K to add more engineering resources to the project. This will allow us to accelerate the product roadmap.

Can you review this and let us know if it's possible?

Thanks,
John

## Extracted Actions

- [ ] Review budget request details
- [ ] Check Company_Handbook approval thresholds
- [ ] Assess financial impact
- [ ] Respond to client with decision

## Keywords Detected

- URGENT ⚠️
- Budget increase
- Approval needed
- Client request

## Quick Response

Reply to: john.doe@client.com
Subject: Re: URGENT: Q1 Budget Increase Needed

---

Email ID: MSG_ID_123
Thread ID: THREAD_123
```

### Step 6: Mark as Read

Gmail Watcher calls:
```
gmail_service.users().messages().modify(
    userId='me',
    id='MSG_ID_123',
    body={'removeLabelIds': ['UNREAD']}
)
```

Result: Email marked as read in Gmail

## Claude Processing

Now Claude can:
1. Read the task file
2. Check Company_Handbook.md for thresholds
3. Create approval request (since $50K > $5K threshold)
4. Move approval to Pending_Approval folder
5. Wait for user approval
6. Once approved, send response email
7. Move task to Done

## Integration Points

### With Vault
- Task file created in Needs_Action/
- Claude claims it → moves to In_Progress/
- High-risk action → creates approval request
- User reviews → moves to Approved/
- Claude executes → sends response
- Completes → moves to Done/

### With Gmail API
- Fetch unread emails (10 max per poll)
- Get full message details
- Mark as read
- (Future) Send replies directly

### With Company_Handbook
```markdown
## Payment/Budget Thresholds
- < $5K: Auto-approved
- $5K-50K: Human approval needed
- > $50K: CEO approval + Finance review
```

Since this is $50K, it requires human approval.

## Success Criteria

✅ Email fetched from Gmail  
✅ Priority correctly categorized as HIGH  
✅ Task file created with extracted actions  
✅ Email marked as read in Gmail  
✅ Claude can process task from vault  
✅ Approval workflow triggered for high-risk decision  
✅ User can approve/reject in Obsidian  
✅ Response sent only after approval  

## Performance Metrics

- Email fetch time: < 1 second
- Task file creation: < 100ms
- Total processing: < 2 seconds
- Gmail mark-as-read: < 1 second

## Error Handling

**If email fetch fails:**
- Retry with exponential backoff (1s, 2s, 4s)
- Log failed email ID
- Alert if 3 retries fail

**If task creation fails:**
- Log error with email ID
- Skip marking as read
- Alert system administrator

**If mark-as-read fails:**
- Email still processed
- Will be fetched again next poll
- Log warning
- Continue with next email

## Next Steps

1. User opens Obsidian vault
2. Sees EMAIL_20260208_103000_001.md in Needs_Action/
3. Claude automatically claims it (moves to In_Progress/)
4. Claude creates approval request for $50K budget increase
5. Approval request appears in Pending_Approval/ folder
6. User reviews budget impact in Company_Handbook
7. User moves approval to Approved/ folder
8. Claude detects approval and sends response email
9. Task moves to Done/ folder
10. Email thread is complete

## Related

- [Gmail Processor Skill](.../SKILL.md)
- [Company Handbook](../../../../AI_Employee_Vault/Company_Handbook.md)
- [Task Workflow](../../../../AI_Employee_Vault/Dashboard.md)
