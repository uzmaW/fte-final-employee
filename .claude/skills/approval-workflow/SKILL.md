---
name: approval-workflow
description: Implement human-in-the-loop approval gates for high-risk actions. Route decisions based on risk levels and company policies.
allowed-tools: Read, Write, Glob
---

# Approval Workflow Skill

Implement human-in-the-loop safety gates for high-risk financial and operational decisions. Route approval requests based on risk assessment and Company Handbook policies.

## Overview

This skill manages:
- Risk assessment for proposed actions
- Routing approvals based on risk level
- Policy compliance checking
- Approval deadline management
- Escalation procedures
- Audit logging of all decisions

## Risk Assessment Framework

### Risk Levels

```
CRITICAL (Immediate escalation to CEO)
├── Actions > $50,000
├── New vendor relationships
├── Policy violations
├── Security incidents
├── Data breaches
└── Regulatory issues

HIGH (CFO/Finance approval required)
├── Payments $5K - $50K
├── New customer contracts > $10K
├── Vendor contract changes
├── Budget overruns
└── Unusual spending patterns

MEDIUM (Manager/Team lead approval)
├── Payments $500 - $5K
├── New vendors under $5K
├── Hiring/contractors
├── Travel expenses
└── Equipment purchases

LOW (Auto-approved, logged only)
├── Payments < $500
├── Routine operational expenses
├── Standard vendor payments
├── Documented recurring expenses
└── Policy-compliant actions
```

## Company Handbook Integration

### Decision Thresholds

Read from `Company_Handbook.md`:

```markdown
## Financial Decision Thresholds

### Payment Authorization
| Amount | Decision Authority | Approval Time |
|--------|-------------------|---------------|
| < $100 | Auto-approved | Immediate |
| $100-$500 | Finance review | < 4 hours |
| $500-$5,000 | Manager approval | < 24 hours |
| $5K-$50K | CFO approval | < 24 hours |
| > $50K | CEO approval | < 48 hours |

### New Recipients
- Always require approval (first payment)
- Verify vendor legitimacy
- Check for conflicts of interest
- Document approval reason

### Policy Exceptions
- HR exceptions: HR Director approval
- Finance exceptions: CFO approval
- Executive exceptions: CEO approval
```

## Approval Request Format

### Complete Approval Request

```markdown
---
type: approval_request
action_id: ACTION_2026_02_08_001
action_type: payment
priority: high
risk_level: medium
created: 2026-02-08T10:30:00Z
deadline: 2026-02-09T17:00:00Z
status: pending
amount: 1500.00
vendor: example@company.com
---

# Approval Request: Payment to New Vendor

## What

Payment of $1,500.00 to new contractor for custom development work.

## Why

Project Alpha requires custom integration development. This contractor has been vetted and is ready to start.

## Details

- **Vendor:** New Contractor Services
- **Amount:** $1,500.00
- **Category:** Professional Services
- **Timeline:** Week of Feb 8-15
- **Deliverable:** Custom API integration
- **Terms:** Net 30 upon completion

## Risk Assessment

**Risk Level:** Medium

**Why Medium:**
- First payment to this vendor (new relationship)
- Amount is within normal category range
- Work is documented with SOW
- No policy violations identified

**Checks Passed:**
- ✅ Budget available
- ✅ Manager approval obtained
- ✅ Vendor background verified
- ✅ SOW/contract in place
- ✅ No conflicts of interest

**Mitigation:**
- Payment only after work completion
- Escrow arrangement available if needed
- 30-day payment terms allow verification period

## Decision Required

**Deadline:** 2026-02-09 17:00:00 UTC (24 hours)

**Options:**
1. **APPROVE** - Move to `/Approved/` folder
2. **REJECT** - Move to `/Rejected/` folder with reason
3. **REQUEST CHANGES** - Add comment with requirements

## Escalation Path

If not approved by deadline:
- 12-hour alert to approver
- 1-hour final notice
- Auto-escalate to next level if no response

---

**Next Approver:** Finance Manager  
**Approval Chain:** Finance → CFO (if escalated)  
**Action ID:** ACTION_2026_02_08_001
```

## Approval Routing

### Automatic Routing Based on Risk

```python
def route_approval(action):
    amount = action.get('amount', 0)
    action_type = action.get('action_type')
    
    if action.get('risk_level') == 'critical':
        return route_to('CEO')
    
    if amount > 50000:
        return route_to('CEO')
    elif amount > 5000:
        return route_to('CFO')
    elif amount > 500:
        return route_to('FinanceManager')
    else:
        return auto_approve()  # Low risk
```

### By Action Type

```
PAYMENT
├── New vendor → Always HIGH
├── Under $100 → AUTO
├── $100-$500 → MEDIUM
├── $500-$5K → HIGH
└── > $5K → CRITICAL

HIRING
├── Executive → CRITICAL
├── Manager → HIGH
├── Contractor > $5K → HIGH
└── Contractor < $5K → MEDIUM

CONTRACT
├── New customer > $10K → HIGH
├── New vendor > $5K → HIGH
├── Amendment > 20% → MEDIUM
└── Renewal → AUTO

BUDGET
├── Override > 10% → HIGH
├── Override 5-10% → MEDIUM
└── Within variance → AUTO

POLICY
├── New exception → HIGH
├── Deviation > 20% → HIGH
└── Minor variance → MEDIUM
```

## Approval Workflow States

```
PENDING (awaiting decision)
├── Approver notified
├── Deadline set
├── Can request changes
└── Can escalate

APPROVED (decision made)
├── Move to Approved/ folder
├── Log approval
├── Execute action
├── Archive record

REJECTED (decision made)
├── Move to Rejected/ folder
├── Log reason
├── Notify requester
├── Archive record

ESCALATED (moved up chain)
├── Original approver unable
├── Next level in chain
├── Extended deadline
├── Higher authority required

EXPIRED (deadline passed)
├── Auto-escalate
├── Alert all parties
├── Require CEO override
└── Document exception
```

## Deadline Management

### Deadline Calculation

```python
def calculate_deadline(risk_level, amount=0):
    base_time = {
        'critical': 48 * 3600,  # 48 hours
        'high': 24 * 3600,      # 24 hours
        'medium': 4 * 3600,     # 4 hours
        'low': 0,               # Immediate
    }
    
    hours = base_time.get(risk_level, 24 * 3600)
    deadline = now() + timedelta(seconds=hours)
    return deadline
```

### Escalation Timeline

```
T + 0h: Approval request created
        ↓ Approver notified

T + 0.5h: Status: Pending
          ↓ Continue

T + 2h (if HIGH): 50% reminder
        ↓ Approver notified

T + 4h (if HIGH): 75% reminder
        ↓ Final notice

T + 23.5h (if deadline 24h): Final notice
        ↓ 30 minute warning

T + 24h: DEADLINE REACHED
        ├── If approved: Execute
        ├── If rejected: Log rejection
        └── If pending: AUTO-ESCALATE
            ↓ Move to next approver
            ↓ Extended deadline
            ↓ Alert CEO
```

## Approval Types

### Auto-Approval (No Human Required)

```markdown
---
type: approval_request
auto_approved: true
reason: Policy-compliant, under threshold
---

# Auto-Approved: Routine Expense

This expense has been auto-approved because:
- Amount under $100
- Category within budget
- Policy compliant
- No exceptions needed

**Action:** Execution approved
**Timestamp:** 2026-02-08T10:30:00Z
```

### Conditional Approval

```markdown
---
type: approval_request
status: conditional_approved
conditions:
  - "Payment only after invoice received"
  - "Amount cannot exceed $1,500"
  - "Escrow arrangement required"
---

# Conditional Approval: Contractor Payment

**Status:** APPROVED WITH CONDITIONS

**Conditions:**
- [ ] Work must be completed per SOW
- [ ] Invoice must be detailed
- [ ] Payment must be net 30
- [ ] Quality assurance review passed

**Approver:** Finance Manager
**Date:** 2026-02-08T14:00:00Z

Action may proceed when conditions are met.
```

### Rejection

```markdown
---
type: approval_request
status: rejected
rejected_by: CFO
rejection_reason: Budget exceeded
rejected_at: 2026-02-08T15:00:00Z
---

# Rejection: Payment Request

**Status:** REJECTED

**Reason:** This payment would exceed the Q1 budget for this category by 15%.

**Options:**
1. Reduce scope to bring cost under budget
2. Move to next quarter
3. Request budget adjustment (new approval)
4. Request CEO override (executive decision)

**Rejection Details:**
- Requested: $15,000
- Category Budget Remaining: $8,500
- Overage: $6,500 (76% over)

**Next Steps:**
Resubmit with:
- Reduced scope, OR
- Adjusted timeline, OR
- CEO budget override request

---

**Rejected by:** CFO Smith  
**Date:** 2026-02-08T15:00:00Z  
**Can appeal to:** CEO
```

## Integration with Company Handbook

### Reading Thresholds

```python
def get_approval_threshold(action_type):
    # Read from Company_Handbook.md
    handbook = read_file("Company_Handbook.md")
    
    # Parse decision thresholds section
    thresholds = parse_markdown_table(handbook, "Decision Thresholds")
    
    # Return threshold for action type
    return thresholds.get(action_type)
```

### Checking Policy Compliance

```python
def check_policy_compliance(action):
    handbook = read_file("Company_Handbook.md")
    
    # Check against policies
    violations = []
    
    if not policy_check_1(action):
        violations.append("Policy 1 violated")
    
    if not policy_check_2(action):
        violations.append("Policy 2 violated")
    
    return violations
```

## Audit Logging

### Log Entry Format

```json
{
  "timestamp": "2026-02-08T10:30:00Z",
  "event_type": "approval_requested",
  "action_id": "ACTION_2026_02_08_001",
  "action_type": "payment",
  "amount": 1500.00,
  "risk_level": "medium",
  "approver": "finance_manager",
  "status": "pending",
  "deadline": "2026-02-09T17:00:00Z"
}
```

### Complete Audit Trail

```json
{
  "action_id": "ACTION_2026_02_08_001",
  "created": "2026-02-08T10:30:00Z",
  "created_by": "claude",
  "action": {
    "type": "payment",
    "amount": 1500.00,
    "vendor": "contractor@example.com"
  },
  "approval_chain": [
    {
      "timestamp": "2026-02-08T10:30:00Z",
      "step": "approval_requested",
      "approver": "finance_manager",
      "status": "pending",
      "deadline": "2026-02-09T17:00:00Z"
    },
    {
      "timestamp": "2026-02-08T14:00:00Z",
      "step": "approval_granted",
      "approver": "finance_manager",
      "comment": "Verified contractor background, SOW in order",
      "conditions": ["Payment upon completion"]
    },
    {
      "timestamp": "2026-02-08T14:05:00Z",
      "step": "action_executed",
      "executor": "payment_processor",
      "result": "success",
      "transaction_id": "TXN_12345"
    }
  ]
}
```

## Best Practices

1. **Clear Justification**
   - Always explain WHY the action is needed
   - Show impact and benefits
   - Address potential concerns

2. **Complete Information**
   - All relevant details included
   - Supporting documents attached
   - Contact info for questions

3. **Risk Assessment**
   - Honest risk evaluation
   - Don't minimize risks
   - Suggest mitigations

4. **Timely Submission**
   - Submit well before deadline
   - Account for approval time
   - Don't rush last-minute

5. **Follow Up**
   - Track approval status
   - Escalate if needed
   - Thank approvers

## Escalation Procedures

### When to Escalate

- Approver not responding after 50% of deadline
- Request denied, but new information available
- Higher authority input needed
- Policy conflict identified
- Urgent business need

### How to Escalate

1. Add comment explaining escalation
2. Move to next approver folder
3. Send notification
4. Extend deadline
5. Log escalation event

## See Also

- [Company Handbook](../../../../AI_Employee_Vault/Company_Handbook.md)
- [Financial Auditor Skill](.../financial-auditor/SKILL.md)
- [Approval Request Templates](.../templates/)
