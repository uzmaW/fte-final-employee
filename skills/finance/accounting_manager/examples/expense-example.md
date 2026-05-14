# Expense Posting Example

## Scenario
Recording office supplies purchase as an expense in Odoo.

## Expense Data
```json
{
  "amount": 350.00,
  "category": "supplies",
  "description": "Office supplies - notebooks, pens, printer paper",
  "vendor": "Office Depot",
  "date": "2026-02-07"
}
```

## Python Code
```python
from skills.finance.accounting_manager.accounting_manager import AccountingManager

# Initialize
manager = AccountingManager()

# Post expense
result = manager.post_expense(
    amount=350.00,
    category='supplies',
    description='Office supplies - notebooks, pens, printer paper',
    vendor='Office Depot',
    date='2026-02-07'
)

# Check result
if result['success']:
    print(f"✅ Expense posted: {result['entry_id']}")
    print(f"   Amount: $350.00")
    print(f"   Category: Supplies")
    print(f"   Vendor: Office Depot")
else:
    print(f"❌ Error: {result['error']}")
```

## Odoo Result
- **Journal Entry ID:** 147
- **Journal:** General
- **Date:** 2026-02-07
- **Status:** Posted

### Ledger Lines
| Account | Name | Debit | Credit |
|---------|------|-------|--------|
| 6100 | Office Supplies | $350.00 | - |
| 1010 | Bank Account | - | $350.00 |

## Vault Log Entry
File: `AI_Employee_Vault/Logs/accounting.json`
```json
{
  "type": "expense_posted",
  "entry_id": 147,
  "amount": 350.00,
  "category": "supplies",
  "description": "Office supplies - notebooks, pens, printer paper",
  "timestamp": "2026-02-08T10:15:30.654321"
}
```

## Expense Categories
Supported categories and their default Odoo accounts:
- `supplies` → 6100 (Office Supplies)
- `utilities` → 6200 (Utilities)
- `rent` → 6300 (Rent)
- `salaries` → 6400 (Salaries)
- `advertising` → 6500 (Advertising)
- `professional_fees` → 6600 (Professional Services)
