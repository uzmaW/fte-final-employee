# Odoo Integration Setup Guide

## Overview

This guide walks you through setting up Odoo Community Edition to work with the AI Employee system. The integration enables:

- Invoice creation and management
- Journal entry posting
- Payment reconciliation
- Financial reporting (Balance Sheet, Income Statement, Trial Balance)
- Partner/customer management
- Complete accounting workflow automation

## Prerequisites

- Python 3.8+ (on the server running Odoo)
- PostgreSQL 10+ database
- 2GB RAM minimum
- 10GB disk space for Odoo installation

## Installation Options

### Option 1: Self-Hosted Odoo (Recommended for Development)

#### 1.1 Install Odoo from Source

```bash
# Clone Odoo repository
git clone https://github.com/odoo/odoo.git
cd odoo
git checkout 16.0  # Use latest stable version

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create database user (PostgreSQL)
sudo -u postgres createuser --createdb odoo
sudo -u postgres psql -c "ALTER USER odoo WITH PASSWORD 'odoo';"

# Create Odoo directories
mkdir -p ~/odoo/logs
mkdir -p ~/odoo/addons

# Run Odoo
./odoo-bin -d odoo_db -u base --load=base,web --db_user=odoo --db_password=odoo
```

#### 1.2 Initial Odoo Setup

1. **Access Odoo Web Interface**
   - Open http://localhost:8069 in your browser
   - Email: admin@example.com
   - Password: admin (default)

2. **Create Your Company**
   - Go to Settings → Users & Companies → Companies
   - Create a new company or update existing
   - Set company name, address, currency

3. **Configure Chart of Accounts**
   - Go to Accounting → Configuration → Chart of Accounts
   - Verify account codes match your accounting needs
   - Default setup works for most businesses

4. **Create Journals**
   - Go to Accounting → Configuration → Journals
   - Ensure these exist:
     - **Sales Journal** (for customer invoices)
     - **Bank Journal** (for bank transactions)
     - **General Journal** (for manual entries)

5. **Create Tax Configuration**
   - Go to Accounting → Configuration → Taxes
   - Set up tax rates for your region

### Option 2: Odoo Online (Easiest for Non-Technical Users)

1. **Sign Up**
   - Go to https://www.odoo.com/app/sign_up
   - Create account and company
   - Choose "Accounting" module

2. **Get API Credentials**
   - Odoo Online uses API tokens for authentication
   - Admin panel → Users → Security → API Tokens
   - Copy your API token

3. **Configure AI Employee**
   - Update `.env` with Odoo Online URL
   - Use your company name as `ODOO_DB`
   - Use `__api_key__` as username
   - Paste API token as password

---

## Configuration

### Step 1: Create .env File

```bash
cp .env.example .env
```

### Step 2: Update .env with Odoo Details

```bash
# Self-hosted
ODOO_URL=http://localhost:8069
ODOO_DB=odoo_db
ODOO_USER=admin
ODOO_PASSWORD=admin

# Or Odoo Online
ODOO_URL=https://your-company.odoo.com
ODOO_DB=your_company
ODOO_USER=__api_key__
ODOO_PASSWORD=your_api_token
```

### Step 3: Verify Connection

```bash
# Test Odoo connection
python3 mcp_servers/odoo_server.py

# Expected output:
# ✅ Odoo MCP Server initialized successfully
# Connected to http://localhost:8069/odoo_db
```

---

## API Configuration

### Enable XML-RPC (Self-Hosted)

1. **Edit odoo.conf**
   ```bash
   nano ~/.odoorc
   ```

2. **Ensure these settings exist**
   ```ini
   [options]
   xmlrpc_port = 8069
   xmlrpc_interface = 0.0.0.0
   ```

3. **Restart Odoo**
   ```bash
   ./odoo-bin --config=~/.odoorc --stop-after-init
   ```

### Create API User (Optional - for Odoo Online)

1. Go to Settings → Users & Companies → Users
2. Create new user with these roles:
   - Accounting / Accountant
   - Accounting / Auditor (optional)
3. Enable API token: Security tab → API Tokens
4. Use this token in `.env` with `__api_key__` as username

---

## Account Setup

### Chart of Accounts Template

The system uses these default account codes:

| Code | Name | Type | Purpose |
|------|------|------|---------|
| 1010 | Bank Account | Asset | Primary cash account |
| 1200 | Accounts Receivable | Asset | Customer invoices |
| 1500 | Equipment | Asset | Fixed assets |
| 2100 | Accounts Payable | Liability | Vendor bills |
| 4000 | Sales Revenue | Income | Product/service sales |
| 5000 | Cost of Goods Sold | Expense | Direct costs |
| 6100 | Office Supplies | Expense | Supplies purchases |
| 6200 | Utilities | Expense | Electric, water, internet |
| 6300 | Rent | Expense | Rent/lease payments |
| 6400 | Salaries | Expense | Employee compensation |
| 6500 | Advertising | Expense | Marketing costs |
| 6600 | Professional Fees | Expense | Consultants, legal, etc |

**To customize accounts:**
1. Edit `AccountingManager.ACCOUNT_MAP` in `skills/finance/accounting_manager/accounting_manager.py`
2. Map expense categories to your chart of accounts
3. Test with `pytest tests/integration_tests/test_odoo_accounting.py`

### Customer/Partner Setup

1. **Manual Entry**
   - Accounting → Customers
   - Click "Create"
   - Enter name, email, phone
   - Set payment terms (Net 30, etc)

2. **Auto-Creation**
   - System auto-creates customers on first invoice
   - Edit customer details in Odoo afterward

---

## Daily Operations

### Creating Invoices

```python
from skills.finance.accounting_manager.accounting_manager import AccountingManager

manager = AccountingManager()

result = manager.create_invoice_from_transaction({
    'customer': 'Acme Corp',
    'amount': 1500.00,
    'description': 'Professional services',
    'date': '2026-02-08',
    'reference': 'INV-001'
})

if result['success']:
    print(f"Invoice {result['invoice_id']} created")
```

### Recording Expenses

```python
result = manager.post_expense(
    amount=250.00,
    category='supplies',
    description='Office supplies',
    vendor='Office Depot',
    date='2026-02-08'
)
```

### Recording Revenue

```python
result = manager.post_revenue(
    amount=2500.00,
    description='Consulting services',
    customer='Acme Corp',
    date='2026-02-08'
)
```

### Reconciling Payments

```python
result = manager.reconcile_payment(
    invoice_id=1,
    payment_amount=1500.00,
    payment_date='2026-02-08',
    payment_method='bank'
)
```

### Generating Reports

```python
# Balance Sheet
report = manager.get_financial_report('balance_sheet')

# Income Statement
report = manager.get_financial_report('income_statement')

# Trial Balance
report = manager.get_financial_report('trial_balance')
```

---

## Testing

### Unit Tests

```bash
# Run Odoo integration tests
pytest tests/integration_tests/test_odoo_accounting.py -v

# Run specific test
pytest tests/integration_tests/test_odoo_accounting.py::TestAccountingManager::test_create_invoice_success -v
```

### Manual Testing with Live Odoo

```bash
# Test connection and operations
python3 << 'EOF'
from skills.finance.accounting_manager.accounting_manager import AccountingManager

manager = AccountingManager()

# Check connection
if manager.is_connected():
    print("✅ Connected to Odoo")
    
    # Test invoice creation
    result = manager.create_invoice_from_transaction({
        'customer': 'Test Customer',
        'amount': 100.00,
        'description': 'Test Invoice'
    })
    
    if result['success']:
        print(f"✅ Invoice created: {result['invoice_id']}")
    else:
        print(f"❌ Error: {result['error']}")
else:
    print("❌ Not connected to Odoo")
EOF
```

---

## Troubleshooting

### Connection Issues

**Error: "Connection refused"**
```
Cause: Odoo server not running
Fix: Start Odoo and verify port 8069 is accessible
./odoo-bin -d odoo_db
```

**Error: "Authentication failed"**
```
Cause: Invalid credentials
Fix: 
1. Verify ODOO_USER and ODOO_PASSWORD in .env
2. Test login at Odoo web interface
3. Check user permissions (should be admin)
```

**Error: "Database not found"**
```
Cause: Wrong database name
Fix:
1. Check ODOO_DB matches actual database
2. List databases: python3 -c "import psycopg2; conn = psycopg2.connect('dbname=postgres'); cur = conn.cursor(); cur.execute('SELECT datname FROM pg_database'); print([row[0] for row in cur.fetchall()])"
```

### Permission Issues

**Error: "User lacks permissions"**
```
Solution:
1. Go to Odoo → Settings → Users → Your User
2. Add "Accounting / Accountant" role
3. Refresh API token if needed
```

### Invoice Creation Failures

**Error: "Partner not found"**
```
Solution:
1. Customer auto-created if doesn't exist
2. Edit customer details in Odoo afterward
3. Or manually create in Odoo first
```

**Error: "Product not found"**
```
Solution:
1. Default product (ID 1) created automatically
2. Or specify product_id in invoice_lines
```

---

## Monitoring & Maintenance

### View Odoo Logs

```bash
# Self-hosted
tail -f ~/odoo/logs/odoo.log

# Docker
docker logs odoo
```

### Check Database Health

```bash
# PostgreSQL
sudo -u postgres psql -d odoo_db -c "\dt"  # List tables
sudo -u postgres psql -d odoo_db -c "SELECT * FROM account_move LIMIT 5;"  # View invoices
```

### Backup Database

```bash
# PostgreSQL backup
pg_dump odoo_db > odoo_backup_$(date +%Y%m%d).sql

# Restore
psql odoo_db < odoo_backup_20260208.sql
```

---

## Performance Optimization

### Database Indexes

Odoo automatically creates indexes. To verify:
```bash
sudo -u postgres psql -d odoo_db -c "\d account_move"
```

### Caching

The MCP server caches partner and account lists:
```python
# Clear cache (if using memcached)
from skills.finance.accounting_manager.accounting_manager import AccountingManager
manager = AccountingManager()
manager.odoo.models.execute_kw(...)  # Direct API calls bypass cache
```

---

## Security Considerations

### 1. Protect API Credentials
- Never commit `.env` to version control
- Use environment-specific `.env` files
- Rotate API tokens regularly

### 2. API Access Control
```bash
# Restrict Odoo API to localhost only
# In odoo.conf:
xmlrpc_interface = 127.0.0.1
```

### 3. Database Security
```bash
# Limit PostgreSQL access
sudo nano /etc/postgresql/*/main/pg_hba.conf
# Ensure local connections only
```

### 4. Audit Trail
- All operations logged to `AI_Employee_Vault/Logs/accounting.json`
- Review periodically for unauthorized access
- Archive logs monthly

---

## Integration with Other Skills

### Financial Auditor → Accounting Manager
```
Transaction Analysis (Financial Auditor)
        ↓ (sends transactions)
Categorization (Accounting Manager)
        ↓ (creates invoices/entries)
Odoo Accounting
        ↓ (generates reports)
CEO Briefing Dashboard
```

### Approval Workflow
```
Large Transaction (> threshold)
        ↓
Approval Request (Approval Manager)
        ↓ (if approved)
Post to Odoo (Accounting Manager)
        ↓
Log to Vault
```

---

## Advanced Configuration

### Multi-Currency Support (Future)

```python
# Not yet implemented, coming in v1.1
manager.create_invoice_from_transaction({
    'customer': 'International Corp',
    'amount': 1000.00,
    'currency': 'EUR',  # Euro
    'exchange_rate': 1.08
})
```

### Tax Automation

```python
# Configure tax rates in Odoo
# System automatically applies on invoice creation
# See: Accounting → Configuration → Taxes
```

### Multi-Company Support

```python
# Switch companies
manager.odoo.current_company_id = 2
# Then perform operations
```

---

## FAQ

**Q: Do I need Odoo Pro?**
A: No, Odoo Community Edition (free) includes all accounting features needed.

**Q: Can I use cloud hosting?**
A: Yes, Odoo Online or any cloud Postgres provider works. Update ODOO_URL.

**Q: How often should I reconcile?**
A: Monthly is standard. Set up recurring task in Orchestrator.

**Q: Can I modify accounts?**
A: Yes, edit `AccountingManager.ACCOUNT_MAP` to match your chart of accounts.

**Q: What about taxes and multi-currency?**
A: Coming in v1.1. Currently supports single currency, single tax rate.

---

## Support & Resources

- **Odoo Documentation:** https://www.odoo.com/documentation/16.0/
- **Odoo Community:** https://github.com/odoo/odoo
- **PostgreSQL:** https://www.postgresql.org/docs/
- **Python XML-RPC:** https://docs.python.org/3/library/xmlrpc.client.html

---

## Next Steps

1. ✅ Install Odoo (Option 1 or 2)
2. ✅ Complete initial setup (Company, Accounts, Journals)
3. ✅ Create `.env` file with Odoo credentials
4. ✅ Test connection: `python3 mcp_servers/odoo_server.py`
5. ✅ Run integration tests: `pytest tests/integration_tests/test_odoo_accounting.py`
6. ✅ Enable Odoo features in config/agent_config.yaml
7. ✅ Monitor `AI_Employee_Vault/Logs/accounting.json` for activities

---

**Created:** February 8, 2026  
**Version:** 1.0  
**Status:** Production Ready
