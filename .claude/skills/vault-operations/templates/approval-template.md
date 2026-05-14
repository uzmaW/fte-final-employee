---
type: approval_request
priority: {{ priority }}
created: {{ timestamp }}
action_id: {{ action_id }}
risk_level: {{ risk_level }}
status: pending
requires_approval_by: {{ deadline }}
---

# Approval Request: {{ action_type }}

## Action Summary
{{ brief_description }}

## Detailed Description
{{ detailed_description }}

## Business Justification
Why this action is needed and what value it creates.

## Risk Assessment

**Risk Level:** {{ risk_level }}

**Potential Impacts:**
- Impact 1: Description
- Impact 2: Description
- Impact 3: Description

**Mitigation Strategies:**
- [ ] Mitigation 1
- [ ] Mitigation 2
- [ ] Mitigation 3

## Financial Impact (if applicable)
- Amount: ${{ amount }}
- Budget Category: {{ category }}
- Cost Center: {{ cost_center }}
- ROI Expected: {{ roi }}

## Decision Required
**Decision Deadline:** {{ deadline }}

To approve this action:
1. Review the details above
2. Move this file to `/Approved/APPROVAL_{{ action_id }}.md`

To reject this action:
1. Review the details above
2. Move this file to `/Rejected/APPROVAL_{{ action_id }}_REJECTED.md`
3. Add rejection reason in a comment

## Approval History
| Date | Decision | Approver | Notes |
|------|----------|----------|-------|
| Pending | - | Awaiting user | - |
