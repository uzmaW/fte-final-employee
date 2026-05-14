# Invoice Creation Example

## Scenario
Creating an invoice in Odoo when a customer pays for services.

## Transaction Data
```json
{
  "customer": "Acme Corporation",
  "amount": 2500.00,
  "description": "Professional consulting services for Q1 2026",
  "date": "2026-02-08",
  "reference": "TXN-2026-0208-001"
}
```

## Python Code
```python
from skills.finance.accounting_manager.accounting_manager import AccountingManager

# Initialize
manager = AccountingManager()

# Create invoice
result = manager.create_invoice_from_transaction(
    transaction={
        'customer': 'Acme Corporation',
        'amount': 2500.00,
        'description': 'Professional consulting services for Q1 2026',
        'date': '2026-02-08',
        'reference': 'TXN-2026-0208-001'
    }
)

# Check result
if result['success']:
    print(f"✅ Invoice created: {result['invoice_id']}")
    print(f"   Customer: Acme Corporation")
    print(f"   Amount: $2,500.00")
else:
    print(f"❌ Error: {result['error']}")
```

## Odoo Result
- **Invoice ID:** 15
- **Partner:** Acme Corporation (ID: 8)
- **Status:** Draft
- **Amount Due:** $2,500.00
- **Invoice Date:** 2026-02-08

## Vault Log Entry
File: `AI_Employee_Vault/Logs/accounting.json`
```json
{
  "type": "invoice_created",
  "invoice_id": 15,
  "partner_id": 8,
  "transaction": {
    "customer": "Acme Corporation",
    "amount": 2500.00,
    "description": "Professional consulting services for Q1 2026",
    "date": "2026-02-08",
    "reference": "TXN-2026-0208-001"
  },
  "timestamp": "2026-02-08T15:30:45.123456"
}
```

## Next Steps
1. Invoice is created in Draft status
2. Finance review and approval (via Approval Manager skill)
3. Post invoice to customer
4. Track payment
5. Reconcile when payment received
