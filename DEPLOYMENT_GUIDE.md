# AI Employee Deployment Guide

Complete step-by-step guide for deploying the Digital FTE system.

## Prerequisites

- Python 3.10+
- Obsidian (for vault monitoring)
- Google Cloud account (for Gmail)
- Twilio account (for WhatsApp)
- Stripe account (for payments, optional)

## Phase 1: Environment Setup

### Step 1.1: Create Python Virtual Environment

```bash
# Create venv
python3 -m venv venv

# Activate venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Verify activation
python --version  # Should show 3.10+
```

### Step 1.2: Install Dependencies

```bash
# Install all required packages
pip install -r requirements.txt

# Verify installation
python -c "import anthropic, fastapi, watchdog; print('✅ Dependencies OK')"
```

### Step 1.3: Create .env Configuration

```bash
# Copy template
cp .env.example .env

# Edit with your credentials
nano .env  # or use your preferred editor
```

## Phase 2: Gmail Setup

### Step 2.1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project: "AI Employee"
3. Enable Gmail API:
   - Search for "Gmail API"
   - Click Enable
4. Create OAuth 2.0 credentials:
   - Click "Create Credentials" → "OAuth client ID"
   - Choose "Desktop application"
   - Download JSON file
5. Save as `credentials.json` in project root

### Step 2.2: Get Gmail OAuth Token

```bash
# Run the authorization script
python3 << 'EOF'
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify'
]

flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
creds = flow.run_local_server(port=0)

print(f"\n✅ Refresh Token: {creds.refresh_token}")
print(f"Client ID: {creds.client_id}")
print(f"Client Secret: {creds.client_secret}")
EOF
```

This will:
- Open browser for OAuth consent
- Display your refresh token
- Copy these values to .env

### Step 2.3: Add to .env

```bash
GMAIL_CLIENT_ID=<your_client_id>.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=<your_client_secret>
GMAIL_REFRESH_TOKEN=<your_refresh_token>
GMAIL_POLL_INTERVAL=300
ENABLE_GMAIL_WATCHER=true
```

### Step 2.4: Test Gmail Connection

```bash
python3 << 'EOF'
from watchers.gmail_watcher import GmailWatcher

watcher = GmailWatcher()
print("✅ Gmail watcher initialized")
print(f"Service status: {watcher.gmail_service}")
EOF
```

## Phase 3: WhatsApp/Twilio Setup

### Step 3.1: Create Twilio Account

1. Go to [Twilio Console](https://www.twilio.com/console)
2. Sign up (free trial available)
3. Verify your phone number
4. Go to "Account" → Copy your:
   - Account SID
   - Auth Token

### Step 3.2: Enable WhatsApp Sandbox

1. In Twilio console, go to "Messaging" → "Try it out" → "WhatsApp"
2. Request WhatsApp sandbox access
3. Get sandbox phone number (e.g., +1 415 523 8886)
4. Get your Twilio phone number (for sending)

### Step 3.3: Add to .env

```bash
TWILIO_ACCOUNT_SID=AC<your_account_sid>
TWILIO_AUTH_TOKEN=<your_auth_token>
TWILIO_PHONE_NUMBER=+1234567890  # Your Twilio number
WHATSAPP_POLL_INTERVAL=60
ENABLE_WHATSAPP_WATCHER=true
```

### Step 3.4: Configure Webhook

1. In Twilio console, go to "WhatsApp" → "Sandbox Settings"
2. Set webhook URL: `https://your-domain.com:8000/webhooks/whatsapp`
3. Authentication method: Basic Auth (optional but recommended)

### Step 3.5: Test WhatsApp Connection

```bash
python3 << 'EOF'
from watchers.whatsapp_watcher import WhatsAppWatcher

watcher = WhatsAppWatcher()
print("✅ WhatsApp watcher initialized")
print(f"Message queue: {len(watcher.message_queue)}")
EOF
```

## Phase 4: Stripe Setup (Optional - for Payments)

### Step 4.1: Create Stripe Account

1. Go to [Stripe Dashboard](https://dashboard.stripe.com)
2. Sign up and verify email
3. Get API keys:
   - Publishable key (test mode)
   - Secret key (test mode)

### Step 4.2: Add to .env

```bash
STRIPE_API_KEY=sk_test_<your_secret_key>
STRIPE_SIGNING_SECRET=whsec_<your_webhook_secret>
```

### Step 4.3: Test Payment Server

```bash
python3 << 'EOF'
from mcp_servers.payment_server import PaymentServer

server = PaymentServer()
result = server.process_payment(
    amount=50.00,
    recipient="test@example.com",
    description="Test payment"
)
print(f"✅ Payment test: {result}")
EOF
```

## Phase 5: Email Configuration (SMTP for Sending)

### Step 5.1: Configure Gmail SMTP

If using Gmail to send emails:

1. Enable 2-factor authentication
2. Create App Password:
   - Go to [Google Account](https://myaccount.google.com)
   - Security → App passwords
   - Select "Mail" and "Windows Computer"
   - Copy generated password

3. Add to .env:
```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_EMAIL=your-email@gmail.com
SMTP_PASSWORD=<app_password>
```

### Step 5.2: Test Email Server

```bash
python3 << 'EOF'
from mcp_servers.email_server import EmailServer

server = EmailServer()
result = server.send_email(
    to="test@example.com",
    subject="Test Email",
    body="This is a test email from AI Employee"
)
print(f"✅ Email test: {result}")
EOF
```

## Phase 6: Vault Setup

### Step 6.1: Open Vault in Obsidian

1. Open Obsidian
2. File → Open vault folder
3. Select `AI_Employee_Vault/`
4. Accept as workspace

### Step 6.2: Verify Vault Structure

```bash
# Check all directories exist
ls -la AI_Employee_Vault/

# Should show:
# - Needs_Action/
# - In_Progress/
# - Plans/
# - Done/
# - Pending_Approval/
# - Approved/
# - Rejected/
# - Logs/
# - Accounting/
```

### Step 6.3: Review Initial Files

- Open `Dashboard.md` - System status
- Open `Company_Handbook.md` - Decision rules
- Open `Business_Goals.md` - Quarterly objectives

## Phase 7: System Configuration

### Step 7.1: Complete .env File

```bash
# ============================================================
# VAULT CONFIGURATION
# ============================================================
VAULT_PATH=AI_Employee_Vault
SKILLS_PATH=.claude/skills
LOGS_DIR=AI_Employee_Vault/Logs
LOG_LEVEL=INFO
TIMEZONE=UTC

# ============================================================
# GMAIL
# ============================================================
GMAIL_CLIENT_ID=<your_client_id>.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=<your_client_secret>
GMAIL_REFRESH_TOKEN=<your_refresh_token>
GMAIL_POLL_INTERVAL=300
ENABLE_GMAIL_WATCHER=true

# ============================================================
# TWILIO / WHATSAPP
# ============================================================
TWILIO_ACCOUNT_SID=AC<your_account_sid>
TWILIO_AUTH_TOKEN=<your_auth_token>
TWILIO_PHONE_NUMBER=+1234567890
WHATSAPP_POLL_INTERVAL=60
ENABLE_WHATSAPP_WATCHER=true

# ============================================================
# STRIPE (OPTIONAL)
# ============================================================
STRIPE_API_KEY=sk_test_<your_key>
STRIPE_SIGNING_SECRET=whsec_<your_secret>

# ============================================================
# EMAIL (SMTP)
# ============================================================
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_EMAIL=your-email@gmail.com
SMTP_PASSWORD=<your_app_password>

# ============================================================
# SYSTEM
# ============================================================
WATCHDOG_CHECK_INTERVAL=30
MAX_RETRIES=3
RETRY_BACKOFF=1.0
ENABLE_ORCHESTRATOR=true

# ============================================================
# FEATURE FLAGS
# ============================================================
ENABLE_GMAIL_WATCHER=true
ENABLE_WHATSAPP_WATCHER=true
ENABLE_ORCHESTRATOR=true
ENABLE_WATCHDOG=true
TEST_MODE=false
```

### Step 7.2: Verify Configuration

```bash
# Test that .env loads correctly
python3 << 'EOF'
from config import get_settings

settings = get_settings()
print("✅ Configuration loaded successfully")
print(f"Vault path: {settings.vault_path}")
print(f"Gmail enabled: {settings.enable_gmail_watcher}")
print(f"WhatsApp enabled: {settings.enable_whatsapp_watcher}")
EOF
```

## Phase 8: Testing Before Production

### Step 8.1: Run All Tests

```bash
# Run complete test suite
python3 -m pytest tests/ -v

# Expected: 53/53 tests passing ✅
```

### Step 8.2: Test Gmail Integration

```bash
# 1. Send test email to your account
# 2. Run orchestrator and wait for poll (5 minutes)
# 3. Check AI_Employee_Vault/Needs_Action/ for new task
```

### Step 8.3: Test WhatsApp Integration

```bash
# 1. Get your Twilio sandbox number from console
# 2. Send WhatsApp message: "join <sandbox_code>"
# 3. Send test message: "Hi, testing AI Employee"
# 4. Check AI_Employee_Vault/Needs_Action/ for new task
```

### Step 8.4: Manual Approval Test

```bash
# 1. Create a task in Needs_Action/
# 2. Wait for Claude to process
# 3. Check Pending_Approval/ for approval request
# 4. Move file to Approved/
# 5. Wait for execution
# 6. Verify task moved to Done/
```

## Phase 9: Deployment

### Step 9.1: Start Orchestrator (Main Process)

```bash
# Start the master orchestrator
python3 orchestrator.py

# Expected output:
# === AI Employee Orchestrator Starting ===
# Starting watchers...
# FastAPI server started
# Orchestrator main loop started
```

### Step 9.2: Start Watchdog (Optional - Health Monitoring)

In a separate terminal:

```bash
python3 watchdog_monitor.py

# Expected output:
# === Watchdog Started ===
# Watchdog monitoring loop started
```

### Step 9.3: Monitor Dashboard

1. Open Obsidian
2. Click on `Dashboard.md`
3. Refresh every minute to see real-time updates
4. Check `Logs/` folder for audit trail

## Phase 10: Production Hardening

### Step 10.1: Set Up Process Manager (PM2)

```bash
# Install PM2 (Node.js process manager)
npm install -g pm2

# Start orchestrator with PM2
pm2 start orchestrator.py --name "ai-employee" --interpreter python3

# Start watchdog with PM2
pm2 start watchdog_monitor.py --name "watchdog" --interpreter python3

# Save PM2 configuration
pm2 save

# Enable startup on reboot
pm2 startup
```

### Step 10.2: Configure Logging

```bash
# View logs in real-time
pm2 logs ai-employee
pm2 logs watchdog

# Or check vault logs
tail -f AI_Employee_Vault/Logs/*.json
```

### Step 10.3: Set Up Backups

```bash
# Backup vault daily
crontab -e

# Add this line:
0 2 * * * cp -r /path/to/AI_Employee_Vault /backup/fte-vault-$(date +\%Y\%m\%d)

# Keep 7 days of backups
find /backup -name "fte-vault-*" -mtime +7 -delete
```

### Step 10.4: Security Hardening

```bash
# Secure .env file
chmod 600 .env

# Secure vault directory
chmod 700 AI_Employee_Vault

# Remove credentials from git
echo ".env" >> .gitignore
echo "credentials.json" >> .gitignore
git rm --cached .env credentials.json 2>/dev/null || true
```

## Phase 11: Monitoring & Maintenance

### Step 11.1: Daily Checks

```bash
# Check system status
python3 << 'EOF'
from orchestrator import Orchestrator

orch = Orchestrator()
status = orch.get_status()
print(f"Orchestrator running: {status['running']}")
print(f"Processes: {status['processes']}")
EOF
```

### Step 11.2: Weekly Maintenance

- Review audit logs in `Logs/` folder
- Check for any errors in Dashboard
- Verify all watchers are running
- Test approval workflow with dummy task

### Step 11.3: Monthly Tasks

- Rotate API credentials
- Review Company_Handbook thresholds
- Update Business_Goals if needed
- Backup vault to external storage
- Review and archive old logs

## Troubleshooting

### Issue: Gmail Watcher Not Starting

```bash
# Check credentials
python3 << 'EOF'
from watchers.gmail_watcher import GmailWatcher
watcher = GmailWatcher()
print(f"Service: {watcher.gmail_service}")
EOF

# If None, refresh token needed:
# - Delete credentials.json
# - Run authorization flow again (Step 2.2)
```

### Issue: WhatsApp Not Receiving Messages

```bash
# Check webhook URL is correct in Twilio
# Verify TWILIO_AUTH_TOKEN in .env is correct
# Check that FastAPI server is running

python3 server.py  # Should show "FastAPI server started"
```

### Issue: Tasks Not Being Created

```bash
# Check vault permissions
chmod 755 AI_Employee_Vault
chmod 755 AI_Employee_Vault/Needs_Action

# Verify watcher is polling
tail -f AI_Employee_Vault/Logs/$(date +%Y-%m-%d).json
```

### Issue: Approvals Not Executing

```bash
# Verify filesystem watcher is running
# Check that file is moved to Approved/ (not just copied)
# Verify MCP servers are configured

python3 << 'EOF'
from mcp_servers.email_server import EmailServer
server = EmailServer()
print("✅ Email server ready")
EOF
```

## Next Steps

1. ✅ Complete Phase 1-7 (setup & configuration)
2. ✅ Run Phase 8 tests
3. ✅ Deploy Phase 9 (start orchestrator)
4. ✅ Monitor Phase 11
5. Send test emails/messages to verify
6. Create test approvals to verify workflow
7. Monitor Dashboard.md daily
8. Check logs weekly

## Support Resources

- **Logs:** `AI_Employee_Vault/Logs/`
- **Dashboard:** Open `AI_Employee_Vault/Dashboard.md` in Obsidian
- **Tests:** `python3 -m pytest tests/ -v`
- **Configuration:** Edit `.env` file
- **Documentation:** See `README.md` and `SILVER_TIER_SETUP.md`

## Deployment Checklist

Before going to production:

- [ ] All 53 tests passing
- [ ] .env configured with all credentials
- [ ] Gmail OAuth token obtained and stored
- [ ] Twilio account created with WhatsApp
- [ ] Webhook URL configured in Twilio
- [ ] SMTP credentials tested
- [ ] Vault structure verified in Obsidian
- [ ] Orchestrator starts without errors
- [ ] Dashboard.md displays correctly
- [ ] Test email creates task in Needs_Action/
- [ ] Test WhatsApp creates task in Needs_Action/
- [ ] Approval workflow tested end-to-end
- [ ] PM2 configured for auto-restart
- [ ] Backups configured
- [ ] Monitoring logs reviewed
- [ ] Team notified of deployment

## Going Live

Once all checks pass:

```bash
# Start with PM2 for production
pm2 start orchestrator.py --name "ai-employee"
pm2 start watchdog_monitor.py --name "watchdog"
pm2 save
pm2 startup

# Monitor logs
pm2 logs ai-employee

# Done! System is now running 24/7 ✅
```

---

**Estimated Setup Time:** 2-4 hours  
**Deployment Ready After:** Phase 8 tests pass  
**Go-Live After:** Phase 10 hardening complete  

Good luck with your AI Employee deployment! 🚀
