# Accounting Manager Skill

## Overview
The Accounting Manager skill integrates with Odoo Community Edition to manage invoices, journal entries, payments, and financial records. It bridges the gap between the AI Employee's transaction analysis and formal accounting in Odoo.

## Capabilities

### Invoice Management
- **Create invoices** from transaction records
- **Track invoice status** (draft, posted, paid)
- **Manage line items** with products and amounts
- **Generate invoice PDFs** for distribution

### Journal Entries
- **Post journal entries** to the general ledger
- **Handle multi-currency** transactions
- **Manage account reconciliation**
- **Track debit/credit balances**

### Payment Reconciliation
- **Record customer payments**
- **Reconcile paid invoices**
- **Track outstanding amounts**
- **Generate aging reports**

### Financial Reporting
- **Generate balance sheets**
- **Create income statements**
- **Produce trial balances**
- **Export financial data**

### Partner Management
- **Sync customer information**
- **Manage supplier details**
- **Track contact information**
- **Maintain payment terms**

## Configuration

### Required Environment Variables
```bash
ODOO_URL=http://localhost:8069
ODOO_DB=odoo_db
ODOO_USER=admin
ODOO_PASSWORD=admin
```

### Setup Steps

1. **Install Odoo Community Edition**
   ```bash
   # Self-hosted option
   git clone https://github.com/odoo/odoo.git
   cd odoo
   pip install -r requirements.txt
   ./odoo-bin -d odoo_db
   
   # Or use Odoo Online
   # Sign up at https://www.odoo.com/app/sign_up
   ```

2. **Initial Configuration**
   - Access Odoo at http://localhost:8069
   - Create company and chart of accounts
   - Set up customer/supplier records
   - Configure sales/purchase journals

3. **Enable Accounting Module**
   - Go to Apps → Search "Accounting"
   - Install the Accounting module

4. **Configure API Access**
   - Admin user should have API access enabled
   - Test connection with `test_odoo_connection.py`

## Usage Examples

### Create Invoice from Transaction
```python
from skills.finance.accounting_manager.accounting_manager import AccountingManager

manager = AccountingManager()

# Create invoice
result = manager.create_invoice_from_transaction(
    transaction={
        'customer': 'Acme Corp',
        'amount': 1500.00,
        'description': 'Professional Services',
        'date': '2026-02-08'
    }
)

if result['success']:
    print(f"Created invoice {result['invoice_id']}")
```

### Post Journal Entry
```python
# Record expense
result = manager.post_expense(
    amount=250.00,
    category='supplies',
    description='Office supplies purchase',
    date='2026-02-08'
)
```

### Reconcile Payment
```python
# Record customer payment
result = manager.reconcile_payment(
    invoice_id=1,
    payment_amount=1500.00,
    payment_date='2026-02-08'
)
```

### Generate Financial Report
```python
# Get balance sheet
report = manager.get_financial_report('balance_sheet')
print(f"Total Assets: {report['total_assets']}")
```

## Integration Points

### With Financial Auditor
The Accounting Manager works with the Financial Auditor to:
- Categorize transactions into Odoo accounts
- Create invoices from recognized revenue
- Post expenses to appropriate accounts
- Generate audit-ready reports

### With Approval Workflow
- Invoices over threshold require approval
- Payment reconciliation triggers approval
- Large journal entries need approval gate

### With Vault Operations
- Stores invoice references in vault
- Links transactions to Odoo records
- Maintains audit trail in vault logs

### With Orchestrator
- Triggered by financial events
- Scheduled for monthly reconciliation
- Auto-posts revenue transactions

## Data Flow

```
Transaction Analysis (Financial Auditor)
        ↓
Categorization (Accounting Manager)
        ↓
Invoice Creation (Odoo)
        ↓
Payment Tracking (Odoo Payment Reconciliation)
        ↓
Financial Reporting (Odoo + CEO Briefing)
        ↓
Audit Trail (Vault)
```

## Error Handling

The skill handles:
- **Connection errors** - Retries with backoff
- **Authentication failures** - Alerts and requires manual intervention
- **Invalid data** - Logs and skips with notification
- **Odoo errors** - Parses and presents user-friendly messages

## Performance

- **Invoice creation:** ~1 second
- **Journal entry posting:** ~1 second
- **Financial report generation:** ~2-3 seconds
- **Payment reconciliation:** ~1 second

## Limitations & Future Enhancements

### Current Limitations
- Single-currency support (multi-currency coming)
- Manual partner synchronization
- No automatic bank feed integration
- Limited report customization

### Future Enhancements
- Automatic bank transaction import
- Multi-currency support
- Bulk invoice creation
- Custom report designer
- Tax calculation automation
- Intercompany transactions
- Budget vs. actual tracking

## Testing

Run integration tests:
```bash
pytest tests/integration_tests/test_odoo_accounting.py -v
```

## Troubleshooting

### Connection Issues
```bash
# Test connection
python mcp_servers/odoo_server.py

# Check Odoo logs
tail -f ~/odoo/logs/odoo.log
```

### Authentication Problems
- Verify credentials in `.env`
- Check user permissions in Odoo
- Ensure XML-RPC is enabled

### Invoice Creation Failures
- Verify customer/partner exists in Odoo
- Check products are configured
- Ensure sales journal is set up

## Support

For issues with:
- **Odoo integration:** See Odoo documentation at https://www.odoo.com/documentation
- **This skill:** Check examples/ and templates/ directories
- **Financial logic:** Review Financial Auditor skill documentation

## Changelog

### Version 1.0 (2026-02-08)
- Initial release with core accounting operations
- Invoice management
- Journal entry posting
- Payment reconciliation
- Financial reporting
- Odoo Community Edition support

## Related Skills
- [Transaction Analyzer](../transaction_analyzer/SKILL.md) - Financial analysis
- [Vault Operations](../../system/vault_operations/SKILL.md) - Data storage
- [Approval Manager](../../system/approval_manager/SKILL.md) - Workflow gates
