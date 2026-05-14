---
name: financial-auditor
description: Analyze transactions, categorize expenses, generate CEO briefings, and provide financial intelligence. Autonomous financial decision-making with human oversight.
allowed-tools: Read, Write, Glob, HTTP, Math
---

# Financial Auditor Skill

Analyze financial transactions, track spending patterns, generate executive briefings, and provide autonomous financial decision-making with built-in approval gates.

## Overview

This skill handles:
- Parsing bank transaction feeds (CSV, JSON, API)
- Categorizing expenses by type and department
- Identifying spending patterns and anomalies
- Calculating financial metrics (revenue, expenses, margins)
- Generating Monday morning CEO briefings
- Recommending cost optimizations
- Creating approval requests for out-of-policy spending
- Forecasting cash flow and identifying bottlenecks

## Transaction Import

### Supported Formats

#### CSV Format
```csv
Date,Amount,Description,Category,Account
2026-02-08,1500.00,Vendor Payment,Operations,Business Checking
2026-02-08,-500.00,Product Sale,Revenue,Business Checking
2026-02-07,25000.00,Payroll Deposit,Revenue,Business Checking
2026-02-07,-35000.00,Payroll,Personnel,Business Checking
```

#### JSON Format
```json
{
  "transactions": [
    {
      "date": "2026-02-08",
      "amount": 1500.00,
      "description": "Vendor Payment",
      "category": "Operations",
      "account": "Business Checking",
      "status": "posted",
      "type": "debit"
    }
  ]
}
```

#### Plaid API Format
```python
transactions = plaid_client.get_transactions(
    access_token=token,
    start_date='2026-02-01',
    end_date='2026-02-08'
)
# Returns structured transaction data
```

### Import Process

```
1. Fetch transactions from source
   ↓
2. Validate and clean data
   ↓
3. Categorize transactions
   ↓
4. Update Accounting/Current_Month.md
   ↓
5. Calculate metrics
   ↓
6. Identify anomalies
   ↓
7. Update Dashboard.md
   ↓
8. Generate insights
```

## Expense Categories

### Standard Categories

```
REVENUE
├── Product Sales
├── Services Revenue
├── Consulting Fees
├── Subscriptions
└── Other Income

OPERATING EXPENSES
├── Payroll & Benefits
│   ├── Salaries
│   ├── Taxes
│   └── Benefits
├── Technology & Infrastructure
│   ├── Cloud Services (AWS, GCP)
│   ├── Software Licenses
│   ├── Tools & Services
│   └── Hosting
├── Office & Operations
│   ├── Rent
│   ├── Utilities
│   ├── Office Supplies
│   └── Equipment
├── Marketing & Sales
│   ├── Advertising
│   ├── Events & Sponsorships
│   ├── Content Marketing
│   └── Sales Tools
├── Professional Services
│   ├── Legal
│   ├── Accounting
│   ├── Consulting
│   └── Contractors
├── Travel & Entertainment
│   ├── Business Travel
│   ├── Client Entertainment
│   └── Team Events
└── Other Operating
    ├── Insurance
    ├── Subscriptions
    ├── Memberships
    └── Miscellaneous
```

### Categorization Rules

```python
CATEGORY_RULES = {
    "Payroll": ["payroll", "salary", "wage", "bonus", "fica", "withholding"],
    "Cloud Services": ["aws", "azure", "gcp", "heroku", "datadog"],
    "Marketing": ["ads", "facebook", "google ads", "marketing", "advertising"],
    "Contractors": ["contractor", "freelance", "upwork", "fiverr"],
    "Travel": ["airline", "hotel", "uber", "lyft", "rental car"],
}

# Match transaction description to rules
# If matches multiple: use longest match
# If no match: "Uncategorized" (flag for review)
```

## CEO Briefing Generation

### Briefing Structure

**Timing:** Monday 8:00 AM UTC

**Contents:**
1. Executive Summary (2-3 sentences)
2. Key Metrics (last 7 days + week-over-week change)
3. Top Revenue Sources
4. Major Expenses
5. Cash Position & Days Runway
6. Anomalies & Alerts
7. Recommendations
8. Strategic Outlook

### Example Briefing Template

```markdown
---
type: executive_briefing
period: Week of Feb 3-9, 2026
generated: 2026-02-09T08:00:00Z
status: final
---

# Monday Morning CEO Briefing

## Executive Summary

Strong week with $85K revenue (+37% WoW), but payroll at capacity. Two vendor payments due this week. Recommend strategy review on hiring timeline.

## Key Metrics

### Revenue
| Metric | This Week | Last Week | Change |
|--------|-----------|-----------|--------|
| Total Revenue | $85,000 | $62,000 | +37% ✅ |
| New Customers | 3 | 2 | +50% ✅ |
| Average Deal | $28,333 | $31,000 | -9% ⚠️ |

### Expenses
| Category | Amount | Budget | Status |
|----------|--------|--------|--------|
| Payroll | $35,000 | $35,000 | 100% ⚠️ |
| Marketing | $12,000 | $15,000 | 80% ✅ |
| Operations | $8,500 | $10,000 | 85% ✅ |
| Vendors | $15,000 | $12,000 | 125% 🔴 |
| **TOTAL** | **$70,500** | **$72,000** | **98%** ✅ |

### Cash Position
- Opening: $245,000
- Revenue: +$85,000
- Expenses: -$70,500
- **Closing: $259,500**
- **Days Runway: 127 days** ✅

## Top Revenue Sources

1. Acme Corp - $25,000 (enterprise annual)
2. TechStart Inc - $18,000 (quarterly)
3. Global Logistics - $15,000 (subscription)

## Major Expenses

1. Payroll - $35,000 (weekly)
2. Vendor Services - $15,000 (contractor team)
3. Marketing - $12,000 (campaigns)

## Anomalies & Alerts

⚠️ **Vendor Spending Spike**
- Jumped from $12K to $15K this week
- Contractor team costs increased
- Action: Verify if ongoing or temporary

⚠️ **Average Order Value Decline**
- Down 9% (mix shift or pricing pressure?)
- Need sales analysis
- Action: Schedule sales review

🔴 **Payroll at Capacity**
- Already at 100% of budget
- New hires incoming
- Action: Review hiring timeline vs. revenue

## Recommendations

### Immediate (This Week)
1. Approve or reject Q1 budget increase ($50K)
2. Verify vendor contract for ongoing costs
3. Analyze pricing trends

### Strategic (This Quarter)
1. Implement automated billing (save 80% processing)
2. Hire 2 more account executives (scaling constraint)
3. Optimize cash management (vendor payment timing)

## Cash Flow Outlook

**Next 30 Days:**
- Expected Revenue: $340K (based on pipeline)
- Expected Expenses: $285K (normal operations)
- **Projected Balance: $314.5K**

**Runway:** 132 days (strong position)

**Action Items:**
- [ ] Approve Q1 budget
- [ ] Review vendor contracts
- [ ] Sales trend analysis
- [ ] Hiring timeline decision

---

Generated: 2026-02-09T08:00:00Z
Status: Final - Ready for CEO Review
```

## Financial Metrics

### Core Metrics

```python
METRICS = {
    # Revenue
    "total_revenue": sum(income_transactions),
    "revenue_growth": (current - previous) / previous,
    "average_deal_size": total_revenue / num_deals,
    "customer_acquisition": new_customers_this_week,
    
    # Expenses
    "total_expenses": sum(expense_transactions),
    "expense_ratio": total_expenses / total_revenue,
    "payroll_percentage": payroll / total_revenue,
    "burn_rate": daily_expenses * 30,
    
    # Cash
    "cash_balance": current_balance,
    "days_runway": cash_balance / daily_expenses,
    "cash_flow": revenue - expenses,
    "cash_conversion": revenue_to_cash_delay,
    
    # Margins
    "gross_margin": (revenue - cogs) / revenue,
    "operating_margin": (revenue - operating_expenses) / revenue,
    "net_margin": (revenue - all_expenses) / revenue,
    
    # Efficiency
    "customer_lifetime_value": avg_customer_revenue * retention_months,
    "customer_acquisition_cost": marketing_spend / new_customers,
    "payback_period": cac / (monthly_arpu * (1 - churn)),
}
```

### Anomaly Detection

```python
ANOMALIES = {
    "unusually_large_transaction": amount > mean + (3 * std_dev),
    "new_vendor": vendor_first_appearance,
    "unusual_category": description_mismatch_with_category,
    "weekend_transaction": day_of_week == "Saturday" or "Sunday",
    "duplicate_transaction": same_amount_description_within_1_hour,
    "category_spike": category_spending > average * 1.5,
    "missing_data": transaction_without_description,
}
```

## Approval Workflow Integration

### Out-of-Policy Spending

Automatically flag and create approval requests for:

```python
OUT_OF_POLICY = {
    "vendor_first_payment": {
        "threshold": 0,
        "reason": "New recipient",
        "approval": "required"
    },
    "unusual_amount": {
        "threshold": lambda: mean + (2 * std_dev),
        "reason": "Amount unusual for category",
        "approval": "required"
    },
    "category_overspend": {
        "threshold": lambda: monthly_budget * 1.1,
        "reason": "Category budget exceeded",
        "approval": "required"
    },
    "weekend_travel": {
        "threshold": 0,
        "reason": "Weekend travel (verify business purpose)",
        "approval": "recommended"
    },
    "vendor_consolidation": {
        "threshold": lambda: num_vendors_in_category > 5,
        "reason": "Too many vendors - consolidate?",
        "approval": "recommended"
    }
}
```

### Example Approval Request

```markdown
---
type: financial_approval
action_id: ACTION_VENDOR_NEW_001
amount: 1500.00
vendor: "New Contractor Services"
category: "Professional Services"
risk_level: medium
---

# Financial Approval: New Vendor Payment

## Transaction Details
- **Vendor:** New Contractor Services
- **Amount:** $1,500.00
- **Category:** Professional Services
- **Date:** 2026-02-08
- **Description:** Custom integration development

## Risk Assessment

**Risk Level:** Medium

**Reasons:**
- First payment to this vendor
- No prior relationship
- Amount within normal range

**Verification:**
- [ ] Vendor legitimacy confirmed
- [ ] SOW or contract in place
- [ ] Budget available
- [ ] Manager approval obtained

## Recommendation

**Status:** ✅ APPROVED
**Reason:** Standard vendor on-boarding, within budget, work verified

**Conditions:**
- Process payment only after work completion
- Request invoice with detailed breakdown
- Add to approved vendor list for future

---

Approval Deadline: 2026-02-09 EOD
```

## Monthly Close Process

### Week 1: Data Collection
```
1. Fetch transactions from all accounts
2. Download bank statements
3. Reconcile with accounting system
4. Flag discrepancies
```

### Week 2: Categorization & Review
```
1. Categorize all uncategorized transactions
2. Review unusual items
3. Validate expense allocations
4. Confirm revenue recognition
```

### Week 3: Analysis & Reporting
```
1. Calculate all metrics
2. Identify trends and anomalies
3. Generate reports
4. Create recommendations
```

### Week 4: Closing & Review
```
1. Final reconciliation
2. Adjust for accruals
3. Board review (if applicable)
4. Archive month
5. Archive for tax/audit
```

## Forecasting

### Cash Flow Projection

```python
FORECAST = {
    "period": "30 days",
    "method": "historical_average + pipeline",
    
    "revenue": {
        "base": average_weekly_revenue * 4,
        "pipeline": sum(deal_size * probability),
        "seasonal_adjustment": seasonal_factor,
        "total": base + pipeline + adjustment
    },
    
    "expenses": {
        "fixed": payroll + rent + insurance,
        "variable": marketing + commissions,
        "discretionary": travel + conferences,
        "total": fixed + variable + discretionary
    },
    
    "net_change": revenue - expenses,
    "ending_balance": current_balance + net_change,
    "days_runway": ending_balance / daily_burn,
}
```

### Scenario Planning

```
BASE CASE: Normal operations
├── Revenue: $340K
├── Expenses: $285K
└── Balance: $314.5K

OPTIMISTIC: Strong sales + cost control
├── Revenue: $420K (+23%)
├── Expenses: $275K (-4%)
└── Balance: $384.5K

PESSIMISTIC: Slow sales + unexpected costs
├── Revenue: $280K (-18%)
├── Expenses: $310K (+9%)
└── Balance: $229.5K ⚠️ (Watch runway)
```

## Integration Points

### With Vault

```
Accounting/Current_Month.md
├── Transaction ledger
├── Category totals
├── Monthly metrics
└── Anomaly flags

Logs/YYYY-MM-DD.json
├── Transaction imports
├── Categorization updates
├── Approval requests created
└── Briefings generated
```

### With Company_Handbook

```
Financial Decision Rules
├── Approval thresholds
├── Category budgets
├── Daily spending limits
└── Policy exceptions
```

### With Dashboard

```
Dashboard.md
├── Cash position (updated daily)
├── Weekly revenue/expenses
├── Key metrics
├── Pending approvals
└── Anomaly alerts
```

## Best Practices

1. **Daily Updates**
   - Import transactions daily
   - Flag anomalies immediately
   - Update cash position
   - Alert on policy violations

2. **Weekly Reviews**
   - Analyze spending patterns
   - Verify categorizations
   - Check budget status
   - Forecast next week

3. **Monthly Close**
   - Reconcile all accounts
   - Finalize metrics
   - Generate reports
   - Archive data

4. **Accuracy**
   - Validate all categorizations
   - Flag uncertain items
   - Get human verification
   - Maintain audit trail

5. **Transparency**
   - Show all calculations
   - Document assumptions
   - Explain anomalies
   - Provide context

## Example Implementation

```python
class FinancialAuditor:
    def __init__(self):
        self.vault_manager = VaultManager()
        self.current_month_file = "Accounting/Current_Month.md"
    
    def import_transactions(self, source="plaid"):
        # Fetch from bank/API
        transactions = self.fetch_transactions(source)
        # Clean and validate
        transactions = self.clean_transactions(transactions)
        # Categorize
        transactions = self.categorize_transactions(transactions)
        # Store in vault
        self.store_transactions(transactions)
    
    def categorize_transaction(self, transaction):
        # Match description to category rules
        # Return best match
        pass
    
    def detect_anomalies(self, transactions):
        # Identify unusual transactions
        # Return list of anomalies
        pass
    
    def calculate_metrics(self):
        # Read all transactions for month
        # Calculate all financial metrics
        # Return metrics dict
        pass
    
    def generate_briefing(self):
        # Gather metrics and data
        # Analyze trends
        # Create recommendations
        # Format briefing markdown
        # Return briefing content
    
    def create_approval_request(self, transaction, reason):
        # Format as approval request
        # Move to Pending_Approval/
        pass
```

## See Also

- [Approval Workflow Skill](.../approval-workflow/SKILL.md)
- [CEO Briefing Template](.../templates/briefing-template.md)
- [Company_Handbook Financial Rules](../../../../AI_Employee_Vault/Company_Handbook.md)
- [Accounting Ledger](../../../../AI_Employee_Vault/Accounting/Current_Month.md)
