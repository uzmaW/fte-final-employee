# AI Employee - Automated Deployment Guide

Complete guide for deploying the AI Employee system using Playwright automation.

## Overview

The automated deployment system uses Playwright to:
1. ✅ Validate environment and dependencies
2. ✅ Collect API credentials (interactive or from environment)
3. ✅ Generate secure `.env` configuration
4. ✅ Run complete test suite (53 tests)
5. ✅ Setup PM2 process manager
6. ✅ Configure automated backups
7. ✅ Start monitoring dashboard

**Total time: ~30 minutes** (depending on network speed)

---

## Quick Start (One Command)

### Option 1: Interactive Deployment (Recommended)

```bash
# Start interactive deployment (will prompt for credentials)
bash deploy.sh --interactive
```

This will:
- Ask you for Gmail, Twilio, and SMTP credentials one by one
- Validate all credentials
- Create `.env` file securely
- Run all tests
- Start PM2 processes
- Setup monitoring

### Option 2: Automated Deployment (Environment Variables)

```bash
# Set credentials as environment variables
export GMAIL_CLIENT_ID="your-id"
export GMAIL_CLIENT_SECRET="your-secret"
export GMAIL_REFRESH_TOKEN="your-token"
export TWILIO_ACCOUNT_SID="your-sid"
export TWILIO_AUTH_TOKEN="your-token"
export TWILIO_PHONE_NUMBER="+1234567890"
export SMTP_EMAIL="your-email@gmail.com"
export SMTP_PASSWORD="your-app-password"

# Run automated deployment
bash deploy.sh --automated
```

---

## Prerequisites

### System Requirements
- Python 3.10 or higher
- Node.js 14+ (for PM2)
- bash shell
- ~500MB disk space

### API Accounts (Get These Before Starting)

1. **Gmail OAuth**
   - https://console.cloud.google.com
   - Create OAuth 2.0 credentials (Desktop app)
   - Download credentials.json and run authorization

2. **Twilio WhatsApp**
   - https://www.twilio.com/console
   - Get Account SID and Auth Token
   - Setup WhatsApp sandbox

3. **SMTP Email**
   - https://myaccount.google.com/apppasswords
   - Create Gmail App Password (2FA required)

4. **Stripe (Optional)**
   - https://dashboard.stripe.com/apikeys
   - Get test API key

---

## Step-by-Step Deployment

### Step 1: Prepare Credentials (10 minutes)

Gather the following information before deployment:

```
Gmail:
  - GMAIL_CLIENT_ID: xxx-yyy.apps.googleusercontent.com
  - GMAIL_CLIENT_SECRET: GOCSPX-xxxxx
  - GMAIL_REFRESH_TOKEN: 1//0gUxxx...

Twilio:
  - TWILIO_ACCOUNT_SID: ACxxx
  - TWILIO_AUTH_TOKEN: xxxxx
  - TWILIO_PHONE_NUMBER: +1234567890

Email:
  - SMTP_EMAIL: your-email@gmail.com
  - SMTP_PASSWORD: xxxx xxxx xxxx xxxx (16 chars with spaces)

Optional:
  - STRIPE_API_KEY: sk_test_xxxxx
```

**Links to get credentials:**
- Gmail: https://console.cloud.google.com
- Twilio: https://www.twilio.com/console
- SMTP: https://myaccount.google.com/apppasswords
- Stripe: https://dashboard.stripe.com/apikeys

### Step 2: Clone/Setup Project

```bash
# Navigate to project directory
cd /path/to/fte-employee

# Verify structure
ls -la .claude/skills
ls -la AI_Employee_Vault
```

### Step 3: Run Deployment

```bash
# Make deploy script executable (if needed)
chmod +x deploy.sh

# Run deployment
bash deploy.sh --interactive
```

**During interactive mode, you'll be prompted for:**
1. GMAIL_CLIENT_ID
2. GMAIL_CLIENT_SECRET
3. GMAIL_REFRESH_TOKEN
4. TWILIO_ACCOUNT_SID
5. TWILIO_AUTH_TOKEN
6. TWILIO_PHONE_NUMBER
7. SMTP_EMAIL
8. SMTP_PASSWORD
9. STRIPE_API_KEY (optional)

### Step 4: Verify Deployment

After deployment completes, verify everything is working:

```bash
# Check PM2 status
pm2 status

# Expected output:
# id  │ name         │ namespace   │ version │ mode    │ pid      │ status    │ cpu │ mem
# 0   │ ai-employee  │ default     │ 1.0.0   │ fork    │ 12345    │ online    │ 0%  │ 45.2mb
# 1   │ watchdog     │ default     │ 1.0.0   │ fork    │ 12346    │ online    │ 0%  │ 32.1mb

# View logs
pm2 logs ai-employee

# Monitor in real-time
pm2 monit
```

### Step 5: Setup Backups (Optional)

```bash
# Install cron jobs for automated backups
bash setup_cron_backups.sh

# Follow prompts to install:
# - Daily backups at 2 AM
# - Weekly health checks
# - Weekly process restart
```

### Step 6: Start Monitoring

```bash
# Open Obsidian vault
open AI_Employee_Vault

# Open MONITORING_DASHBOARD.md
# This dashboard shows:
# - Real-time status
# - Daily health check checklist
# - Performance metrics
# - Troubleshooting guide
```

---

## What Gets Automated

### Configuration
✅ Reads credentials from prompt or environment  
✅ Validates all credentials  
✅ Generates `.env` with secure permissions (600)  
✅ Never logs or exposes credentials  

### Testing
✅ Runs complete test suite (53 tests)  
✅ Validates configuration loads correctly  
✅ Confirms all dependencies installed  

### Process Management
✅ Installs PM2 if not present  
✅ Starts Orchestrator process  
✅ Starts Watchdog process  
✅ Configures auto-start on reboot  
✅ Sets up log rotation  

### Monitoring Setup
✅ Verifies PM2 process status  
✅ Displays process list  
✅ Shows monitoring commands  
✅ Points to monitoring dashboard  

---

## Automated Deployment Architecture

```
deploy.sh (Shell wrapper)
    │
    ├─ Check Python 3.10+
    ├─ Setup virtual environment
    ├─ Install dependencies
    ├─ Check/Install Node.js
    ├─ Install/Verify PM2
    │
    └─> deployment_automation.py (Main orchestrator)
            │
            ├─ Phase 1: Pre-flight Checks
            │   ├─ Python version
            │   ├─ Core dependencies
            │   ├─ Required directories
            │   └─ Vault structure
            │
            ├─ Phase 2: Get Credentials
            │   ├─ Interactive prompts OR
            │   └─ Environment variables
            │
            ├─ Phase 3: Generate .env
            │   ├─ Create config file
            │   ├─ Set permissions (600)
            │   └─ Validate format
            │
            ├─ Phase 4: Run Tests
            │   ├─ Verify config loads
            │   └─ Run pytest (53 tests)
            │
            ├─ Phase 5: Setup PM2
            │   ├─ Start processes
            │   ├─ Configure auto-start
            │   └─ Display status
            │
            ├─ Phase 6: Setup Backups
            │   ├─ Verify backup scripts
            │   └─ Show cron commands
            │
            └─ Phase 7: Start Monitoring
                ├─ Check PM2 status
                └─ Display next steps
```

---

## Troubleshooting Automated Deployment

### Issue: "Python 3.10+ not found"

**Solution:**
```bash
# Install Python 3.10 or higher
# macOS: brew install python@3.10
# Ubuntu: sudo apt-get install python3.10
# Windows: Download from python.org

# Verify
python3 --version  # Should be 3.10+
```

### Issue: "Virtual environment creation failed"

**Solution:**
```bash
# Remove old venv and try again
rm -rf venv
python3 -m venv venv
source venv/bin/activate
```

### Issue: "Credential prompt not appearing"

**Solution:**
```bash
# Make sure you're using --interactive flag
bash deploy.sh --interactive

# Or set DEPLOY_MODE explicitly
export DEPLOY_MODE=interactive
python3 deployment_automation.py
```

### Issue: "Tests failing after deployment"

**Solution:**
```bash
# Check which tests are failing
pytest tests/ -v

# Review logs
pm2 logs ai-employee

# Check .env file is correct
cat .env | grep GMAIL  # Should show your credentials
```

### Issue: "PM2 command not found"

**Solution:**
```bash
# Install Node.js first
# macOS: brew install node
# Ubuntu: sudo apt-get install nodejs npm

# Then install PM2
npm install -g pm2

# Verify
pm2 --version
```

### Issue: "Can't access Obsidian vault"

**Solution:**
```bash
# Verify vault structure
ls -la AI_Employee_Vault/

# Fix permissions if needed
chmod 755 AI_Employee_Vault
chmod 755 AI_Employee_Vault/*

# Open vault in Obsidian
open AI_Employee_Vault  # macOS
# or right-click folder → Open with Obsidian
```

---

## Environment Variables Reference

If using `--automated` mode, set these variables:

```bash
# Required
GMAIL_CLIENT_ID=xxx
GMAIL_CLIENT_SECRET=xxx
GMAIL_REFRESH_TOKEN=xxx
TWILIO_ACCOUNT_SID=xxx
TWILIO_AUTH_TOKEN=xxx
TWILIO_PHONE_NUMBER=+1234567890
SMTP_EMAIL=your@email.com
SMTP_PASSWORD=your-app-password

# Optional
STRIPE_API_KEY=sk_test_xxx
LOG_LEVEL=INFO
VAULT_PATH=AI_Employee_Vault
```

---

## Verification Checklist

After deployment completes successfully:

- [ ] `.env` file created with secure permissions (600)
- [ ] 53/53 tests passing
- [ ] PM2 showing both processes online
- [ ] `pm2 logs` showing activity
- [ ] `pm2 monit` showing low CPU/memory usage
- [ ] Obsidian vault accessible
- [ ] MONITORING_DASHBOARD.md displays correctly
- [ ] Backup script ready (`bash setup_cron_backups.sh`)

---

## Monitoring After Deployment

### Real-time Monitoring
```bash
# Watch logs in real-time
pm2 logs ai-employee

# Monitor CPU/Memory
pm2 monit

# See process list
pm2 status
```

### Daily Health Checks
```bash
# Run 5-minute health check
bash scripts/daily_health_check.sh

# Or manually:
pm2 status
tail -20 AI_Employee_Vault/Logs/$(date +%Y-%m-%d).json
pm2 logs --lines 100
```

### Backup Verification
```bash
# List backups
ls -lh backups/fte-vault-*.tar.gz

# Verify backup integrity
tar -tzf backups/fte-vault-*.tar.gz > /dev/null && echo "✅ Backup OK"
```

---

## Performance Monitoring

Monitor these metrics after deployment:

| Metric | Target | Command |
|--------|--------|---------|
| CPU Usage | < 5% | `pm2 monit` |
| Memory | < 300MB | `pm2 monit` |
| Uptime | 99.9% | `pm2 status` |
| Test Pass Rate | 100% | `pytest tests/ -q` |

---

## Next Steps After Deployment

1. **Send Test Email**
   ```bash
   # Send email to yourself
   # Check AI_Employee_Vault/Needs_Action/ for new task
   ```

2. **Send Test WhatsApp**
   ```bash
   # Text your Twilio number
   # Check AI_Employee_Vault/Needs_Action/ for new task
   ```

3. **Test Approval Workflow**
   - Create a task in `/Needs_Action/`
   - Claude processes it
   - Move approval to `/Approved/`
   - Watch execution in logs

4. **Schedule Backups**
   ```bash
   bash setup_cron_backups.sh
   ```

5. **Monitor Daily**
   - Open `MONITORING_DASHBOARD.md` in Obsidian
   - Review `pm2 logs` for any issues
   - Run health checks weekly

---

## Deployment Complete!

Your AI Employee is now running 24/7! 🚀

```
✅ Configuration: .env created with secure permissions
✅ Testing: 53/53 tests passing
✅ Processes: Orchestrator + Watchdog running
✅ Monitoring: Dashboard ready in Obsidian
✅ Backups: Ready to setup with cron jobs
```

**Next:** Follow the monitoring guide in `AI_Employee_Vault/MONITORING_DASHBOARD.md`

---

## Support & Troubleshooting

- **Logs:** `AI_Employee_Vault/Logs/YYYY-MM-DD.json`
- **Status:** `pm2 status`
- **Monitoring:** `pm2 monit`
- **Dashboard:** `AI_Employee_Vault/MONITORING_DASHBOARD.md`
- **Issues:** Check `DEPLOYMENT_GUIDE.md` for detailed troubleshooting
