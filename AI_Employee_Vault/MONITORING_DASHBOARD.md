# AI Employee - Monitoring Dashboard

Real-time system monitoring and status overview for the Obsidian vault.

**Last Updated:** 2026-02-08 02:20:38 UTC  
**System Status:** 🟢 Ready for Deployment

---

## 📊 Quick Status Overview

| Component | Status | Last Check | Next Action |
|-----------|--------|-----------|------------|
| **Orchestrator** | 🟡 Not Started | - | Start: `python3 orchestrator.py` |
| **Watchdog** | 🔴 Not Started | - | Start: `python3 watchdog_monitor.py` |
| **Vault Structure** | 🟢 Ready | Now | All directories exist |
| **Configuration** | 🟡 Pending | - | Edit `.env` with credentials |
| **Tests** | 🟢 Passing | Now | 53/53 tests passing ✅ |
| **Documentation** | 🟢 Complete | Now | All guides ready |

---

## 🎯 Deployment Checklist

Use this checklist to track your deployment progress:

### Phase 1: Environment Setup
- [ ] Python 3.10+ installed
- [ ] Virtual environment created and activated
- [ ] Dependencies installed: `pip install -r requirements.txt`
- [ ] All tests passing: `pytest tests/ -v` (53/53)

### Phase 2: Credentials Configuration
- [ ] Gmail OAuth credentials obtained
- [ ] GMAIL_CLIENT_ID added to .env
- [ ] GMAIL_CLIENT_SECRET added to .env
- [ ] GMAIL_REFRESH_TOKEN added to .env
- [ ] Twilio Account SID added to .env
- [ ] Twilio Auth Token added to .env
- [ ] Twilio phone number added to .env
- [ ] SMTP credentials configured
- [ ] (Optional) Stripe API key added

### Phase 3: Service Integration Testing
- [ ] Gmail watcher tested: `python3 -c "from watchers.gmail_watcher import GmailWatcher; print('✅ OK')"`
- [ ] WhatsApp watcher tested: `python3 -c "from watchers.whatsapp_watcher import WhatsAppWatcher; print('✅ OK')"`
- [ ] Vault manager tested: `python3 -c "from vault_manager import VaultManager; m = VaultManager(); print('✅ OK')"`
- [ ] Email server tested: `python3 -c "from mcp_servers.email_server import EmailServer; print('✅ OK')"`

### Phase 4: Deployment
- [ ] PM2 installed: `npm install -g pm2`
- [ ] ecosystem.config.js configured
- [ ] Orchestrator started: `pm2 start ecosystem.config.js`
- [ ] Watchdog started and monitoring
- [ ] Dashboard accessible in Obsidian
- [ ] Logs being written to AI_Employee_Vault/Logs/

### Phase 5: Post-Deployment Verification
- [ ] Test email creates task in Needs_Action/
- [ ] Test WhatsApp message creates task
- [ ] Approval workflow tested end-to-end
- [ ] Backup script configured: `bash setup_cron_backups.sh`
- [ ] Cron jobs installed for daily backups
- [ ] Monitoring dashboard updated daily

---

## 📈 Performance Metrics

Track system performance and health:

### CPU & Memory Usage
```
Monitor with: pm2 monit

Healthy Ranges:
- Orchestrator CPU: < 5%
- Orchestrator Memory: < 200MB
- Watchdog CPU: < 2%
- Watchdog Memory: < 100MB
```

### Process Uptime
```
Check with: pm2 status

Target: 99.9% uptime (< 43 seconds downtime per month)
```

### Task Processing
- **Tasks Created Today:** See Needs_Action/ folder count
- **Tasks Completed Today:** See Done/ folder count
- **Pending Approvals:** See Pending_Approval/ folder count
- **Average Process Time:** Check Logs/ folder timestamps

### Error Rate
```
Check with: tail -f AI_Employee_Vault/Logs/$(date +%Y-%m-%d).json

Target: < 0.1% errors (99.9% success rate)
```

---

## 🔍 Daily Health Check Procedure

**Time Required:** 5 minutes  
**Frequency:** Daily (morning recommended)

### Step 1: Check Process Status (1 min)
```bash
pm2 status

Expected:
- ai-employee: online
- watchdog: online
```

### Step 2: Review Recent Logs (1 min)
```bash
tail -20 AI_Employee_Vault/Logs/$(date +%Y-%m-%d).json

Look for:
- No ERROR events
- No authentication failures
- Normal task processing
```

### Step 3: Check Task Queues (1 min)
```bash
# Count tasks in each folder
echo "Needs_Action: $(ls -1 AI_Employee_Vault/Needs_Action | wc -l)"
echo "In_Progress: $(ls -1 AI_Employee_Vault/In_Progress 2>/dev/null | wc -l || echo 0)"
echo "Pending_Approval: $(ls -1 AI_Employee_Vault/Pending_Approval 2>/dev/null | wc -l || echo 0)"
echo "Done: $(ls -1 AI_Employee_Vault/Done 2>/dev/null | wc -l || echo 0)"
```

### Step 4: Verify No Stuck Processes (1 min)
```bash
# Check for processes older than 6 hours
find AI_Employee_Vault/In_Progress -type f -mtime +0.25 -ls

If any files found: Investigate and move to Done/ or Rejected/
```

### Step 5: Review Dashboard.md (1 min)
Open Dashboard.md and verify:
- All watchers operational
- No critical alerts
- Backup completed recently
- System health indicators green

---

## 🚨 Troubleshooting Quick Reference

### Issue: Orchestrator Won't Start

**Check:**
```bash
# 1. Verify Python environment
python --version  # Should be 3.10+

# 2. Test imports
python -c "from orchestrator import Orchestrator; print('OK')"

# 3. Check configuration
python -c "from config import get_settings; s = get_settings(); print('OK')"

# 4. View detailed error
python orchestrator.py  # Run directly to see errors
```

**Common Fixes:**
- Re-activate virtual environment: `source venv/bin/activate`
- Reinstall dependencies: `pip install -r requirements.txt`
- Check .env file exists and is readable

### Issue: No Tasks Being Created

**Check:**
```bash
# 1. Verify watcher is running
pm2 logs ai-employee | grep -i "watcher"

# 2. Check Gmail authentication
python -c "from watchers.gmail_watcher import GmailWatcher; w = GmailWatcher(); print(w.gmail_service)"

# 3. Verify vault structure
ls -la AI_Employee_Vault/Needs_Action/

# 4. Check file permissions
stat AI_Employee_Vault/Needs_Action
```

**Common Fixes:**
- Refresh Gmail token (see DEPLOYMENT_GUIDE.md)
- Check vault folder permissions: `chmod 755 AI_Employee_Vault/Needs_Action`
- Verify .env contains correct credentials

### Issue: Approvals Not Executing

**Check:**
```bash
# 1. Verify filesystem watcher is running
pm2 logs watchdog | grep -i "approved"

# 2. Check MCP servers available
python -c "from mcp_servers.email_server import EmailServer; print('Email OK')"
python -c "from mcp_servers.payment_server import PaymentServer; print('Payment OK')"

# 3. Review approval workflow
ls -la AI_Employee_Vault/Approved/
ls -la AI_Employee_Vault/Done/
```

**Common Fixes:**
- Verify files are MOVED (not copied) to Approved/
- Check MCP server credentials in .env
- Review error logs for specific failure reason

### Issue: High Memory Usage

**Check:**
```bash
# Monitor in real-time
pm2 monit

# Check specific process
ps aux | grep "orchestrator\|watchdog"
```

**Common Fixes:**
- Restart process: `pm2 restart ai-employee`
- Check for memory leaks in logs
- Reduce polling interval if needed

---

## 📅 Maintenance Schedule

### Daily (Every Morning)
- [ ] Run 5-minute health check (above)
- [ ] Review Logs/ folder for errors
- [ ] Check task processing is normal

### Weekly (Every Monday)
- [ ] Run `pytest tests/ -v` to verify no regressions
- [ ] Review backups were created
- [ ] Check PM2 process status: `pm2 status`
- [ ] Review Dashboard.md for trends

### Monthly (First Sunday)
- [ ] Full backup verification: `tar -tzf backups/fte-vault-*.tar.gz`
- [ ] Rotate API credentials
- [ ] Review and update Company_Handbook.md if needed
- [ ] Analyze Financial Auditor logs for anomalies
- [ ] Check disk usage: `du -sh *`

### Quarterly (Every 3 months)
- [ ] Full system load test
- [ ] Update Business_Goals.md
- [ ] Review and update DEPLOYMENT_GUIDE.md
- [ ] Plan upgrades or new features

---

## 📊 Key Metrics to Monitor

### System Health
| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Uptime | 99.9% | - | 🟡 Not running |
| Response Time | < 2s | - | 🟡 TBD |
| Error Rate | < 0.1% | - | 🟡 TBD |
| Memory Usage | < 500MB | - | 🟡 TBD |
| CPU Usage | < 5% | - | 🟡 TBD |

### Task Processing
| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Tasks/Hour | > 20 | - | 🟡 TBD |
| Avg Process Time | < 5 min | - | 🟡 TBD |
| Success Rate | > 99% | - | 🟡 TBD |
| Approval Rate | 100% | - | 🟡 TBD |

### Service Integration
| Service | Status | Last Test | Next Test |
|---------|--------|-----------|-----------|
| Gmail | 🟡 Pending | - | After credential setup |
| WhatsApp | 🟡 Pending | - | After credential setup |
| Email | 🟡 Pending | - | After SMTP setup |
| Payments | 🟡 Pending | - | After Stripe setup (optional) |

---

## 🔐 Security Checklist

Monthly security review:

- [ ] .env file permissions: `ls -la .env` (should be 600)
- [ ] credentials.json permissions: `ls -la credentials.json` (should be 600)
- [ ] Vault folder permissions: `ls -la AI_Employee_Vault` (should be 700)
- [ ] No secrets in logs: `grep -r "password\|token\|secret" AI_Employee_Vault/Logs/`
- [ ] API keys rotated: Check last rotation date
- [ ] Backups are encrypted: Verify backup integrity
- [ ] Audit logs reviewed: Check for unauthorized access
- [ ] Git history clean: No credentials committed

---

## 📝 Notes & Observations

Use this section to track observations and improvements:

```
2026-02-08 - System ready for deployment
- All 53 tests passing
- Credentials configured
- Backup system ready

[Add your observations here as you deploy]
```

---

## 📞 Quick Links & Resources

### Documentation
- [DEPLOYMENT_GUIDE.md](../DEPLOYMENT_GUIDE.md) - Complete setup instructions
- [README.md](../README.md) - Project overview
- [SILVER_TIER_SETUP.md](../SILVER_TIER_SETUP.md) - Email & messaging setup

### Commands Reference
```bash
# Start system
pm2 start ecosystem.config.js

# Monitor
pm2 monit
pm2 logs ai-employee
pm2 logs watchdog

# Backup
bash scripts/backup_vault.sh

# Testing
pytest tests/ -v
pytest tests/test_watchers.py -v

# Configuration
nano .env
cat .env.credentials.example
```

### Troubleshooting
- Check logs: `tail -f AI_Employee_Vault/Logs/$(date +%Y-%m-%d).json`
- Process status: `pm2 status`
- System health: `pm2 monit`
- Test services: `python -c "from [module] import [class]; print('OK')"`

---

## ✅ Deployment Complete Checklist

After completing all phases, verify:

- [ ] All checklist items above marked complete
- [ ] 53/53 tests passing
- [ ] PM2 showing both processes online
- [ ] Vault structure complete with all directories
- [ ] Dashboard.md displays without errors
- [ ] Logs are being created and populated
- [ ] Backup system verified and working
- [ ] Cron jobs installed and scheduled
- [ ] Team notified of deployment
- [ ] Monitoring scheduled (daily health checks)

**When all items checked:** System is production-ready! 🚀

---

**Next Step:** Follow [DEPLOYMENT_GUIDE.md](../DEPLOYMENT_GUIDE.md) Phase 1-2 to configure credentials and begin deployment.

**Support:** Review troubleshooting section or check logs in AI_Employee_Vault/Logs/
