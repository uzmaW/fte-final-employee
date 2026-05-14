---
name: google_workspace_onboarding
description: Automated Google Workspace account creation and onboarding email delivery for new employees. Queries HR task files in the vault, provisions email accounts via Google Workspace Directory API, and sends personalized onboarding instructions.
allowed-tools: Read, Write, Glob, Call, HTTP
---

# Google Workspace Onboarding Skill

## Purpose

Automate new employee onboarding by:
1. **Detecting new employee tasks** in `AI_Employee_Vault/Needs_Action/` with `type: employee_onboarding`
2. **Creating Google Workspace accounts** via Directory API
3. **Sending personalized onboarding emails** with setup instructions
4. **Tracking provisioning status** and updating task files

## Google Workspace Directory API Integration

### Prerequisites
1. Create a Google Workspace admin account with Domain-Wide Delegation
2. Enable the **Admin SDK Directory API** in Google Cloud Console
3. Create a service account with domain-wide delegation:
   - `https://www.googleapis.com/auth/admin.directory.user`
   - `https://www.googleapis.com/auth/admin.directory.group`
   - `https://www.googleapis.com/auth/gmail.send`
4. Set the following credentials in `.env`:
   - `GOOGLE_WORKSPACE_ADMIN_EMAIL` — Super admin email
   - `GOOGLE_WORKSPACE_DOMAIN` — Your domain (e.g., `company.com`)
   - `GOOGLE_SERVICE_ACCOUNT_JSON` — Path to service account JSON key file
   - `GOOGLE_WORKSPACE_OU` — Default organizational unit path (optional)

### Authentication Flow
```
1. Load service account credentials from JSON file
2. Create JWT assertion with domain-wide delegation
3. Exchange for access token via Google OAuth
4. Use token for Directory API and Gmail API calls
```

## New Employee Detection

### Trigger: Vault Task File
When a task file with the following metadata appears in `Needs_Action/`:
```markdown
---
type: employee_onboarding
employee_name: Jane Doe
employee_email: jane.doe@company.com
department: Engineering
start_date: 2026-06-01
---
```

The watcher detects the new task and triggers the provisioning pipeline.

## Provisioning Pipeline

### Step 1: Validate Employee Data
- Check required fields: `employee_name`, `employee_email`, `department`, `start_date`
- Verify email domain matches `GOOGLE_WORKSPACE_DOMAIN`
- Check if account already exists (idempotent)

### Step 2: Create Google Workspace User Account
```
POST https://www.googleapis.com/admin/directory/v1/users
{
  "primaryEmail": "jane.doe@company.com",
  "name": {
    "givenName": "Jane",
    "familyName": "Doe"
  },
  "password": "{auto-generated-secure-password}",
  "changePasswordAtNextLogin": true,
  "orgUnitPath": "/Engineering",
  "isEnrolledIn2Sv": false
}
```

### Step 3: Add to Standard Groups
- Add user to department-specific Google Group
- Add user to `all-employees@company.com`
- Configure email aliases if specified

### Step 4: Send Onboarding Email
Send personalized onboarding email via Gmail API with:
- Welcome message with account credentials
- Setup instructions for devices and VPN
- Links to internal resources and documentation
- FAQ and contact information
- Security policy acknowledgment

### Step 5: Update Task Status
- Move task from `Needs_Action/` to `In_Progress/`
- Log provisioning result to `AI_Employee_Vault/Logs/onboarding.json`
- On completion, move to `Done/` with summary

## Onboarding Email Template

```html
Subject: Welcome to [Company] — Your Account Setup

Hi {{employee_name}},

Welcome to the team! Your Google Workspace account has been created:

📧 Email: {{employee_email}}
🔐 Temporary Password: {{temporary_password}} (you'll be prompted to change this on first login)
🖥️ Google Workspace: https://workspace.google.com

## Setup Checklist

1. [ ] Sign in to Google Workspace at https://mail.google.com
2. [ ] Change your temporary password
3. [ ] Set up 2FA (recommended) at https://myaccount.google.com/security
4. [ ] Install Google Drive for Desktop
5. [ ] Join {{department}} Google Group
6. [ ] Review the Employee Handbook
7. [ ] Complete security training

## Important Links

- Company Intranet: {{intranet_url}}
- IT Help Desk: {{helpdesk_email}}
- HR Portal: {{hr_portal_url}}

## First-Day Schedule

- 9:00 AM — Welcome meeting with your manager
- 10:00 AM — IT setup and account configuration
- 11:00 AM — Team introduction
- 12:00 PM — Team lunch
- 1:00 PM — Project overview
- 3:00 PM — Security and compliance training

If you have any questions, don't hesitate to reach out.

Best,
IT Operations
```

## Configuration

### Environment Variables
```env
# Google Workspace
GOOGLE_WORKSPACE_ADMIN_EMAIL=admin@company.com
GOOGLE_WORKSPACE_DOMAIN=company.com
GOOGLE_SERVICE_ACCOUNT_JSON=/path/to/service-account-key.json
GOOGLE_WORKSPACE_OU=/

# Onboarding Settings
ONBOARDING_AUTO_GENERATE_PASSWORD=true
ONBOARDING_SEND_WELCOME_EMAIL=true
ONBOARDING_DEFAULT_GROUP=all-employees
ONBOARDING_INTRANET_URL=https://intranet.company.com
ONBOARDING_HELP_DESK=it-help@company.com
```

## Error Handling

| Error | Recovery |
|-------|----------|
| 409 Conflict (user exists) | Skip creation, verify account, continue |
| 403 Forbidden | Check service account permissions, alert admin |
| 429 Rate Limit | Exponential backoff, retry after delay |
| Invalid domain | Reject task, alert HR |
| API unavailable | Retry up to 3 times with backoff |

## Security Considerations

✅ Service account credentials stored securely outside vault
✅ Temporary passwords expire on first login
✅ All provisioning actions logged to audit trail
✅ Only provisioned for approved domains
✅ Passwords never included in task files or logs

## Integration Points

- **Vault**: Reads `type: employee_onboarding` tasks, updates status
- **Approval Workflow**: Onboarding creation requires approval for external hires
- **Audit Logger**: All provisioning steps logged
- **Financial Auditor**: Equipment/software costs tracked for new hire budget
- **Dashboard**: Onboarding statistics and recent provisions
```