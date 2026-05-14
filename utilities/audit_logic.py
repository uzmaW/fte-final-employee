"""
audit_logic.py - Subscription pattern matching and financial audit analysis.

From the hackathon PDF Section 4 (Business Handover):
  Uses pattern matching to identify subscription usage from bank transactions,
  flags unused subscriptions, and generates cost optimization suggestions
  for the Monday Morning CEO Briefing.
"""

import re
from datetime import datetime, timedelta
from typing import Optional

# ─── Subscription Pattern Database ────────────────────────────────────────────
# Maps common transaction description patterns to human-readable subscription names.
# Extend this dictionary as new subscriptions are identified.

SUBSCRIPTION_PATTERNS = {
    # ── Entertainment & Media ──
    'netflix.com': 'Netflix',
    'hulu.com': 'Hulu',
    'disneyplus.com': 'Disney+',
    'spotify.com': 'Spotify',
    'apple.com/music': 'Apple Music',
    'youtube.com/premium': 'YouTube Premium',
    'paramount.com': 'Paramount+',
    'peacocktv.com': 'Peacock',
    'hbomax.com': 'HBO Max',
    'pandora.com': 'Pandora',
    'audible.com': 'Audible',
    'kindle.com': 'Amazon Kindle',

    # ── Productivity & SaaS ──
    'notion.so': 'Notion',
    'slack.com': 'Slack',
    'slack.com/billing': 'Slack',
    'zoom.us': 'Zoom',
    'dropbox.com': 'Dropbox',
    'box.com': 'Box',
    'microsoft365.com': 'Microsoft 365',
    'office.com': 'Microsoft Office',
    'google.com/maps': 'Google Maps API',
    'googleworkspace': 'Google Workspace',
    'figma.com': 'Figma',
    'canva.com': 'Canva',
    'miro.com': 'Miro',
    'trello.com': 'Trello',
    'asana.com': 'Asana',
    'jira.com': 'Jira',
    'github.com': 'GitHub',
    'gitlab.com': 'GitLab',
    'bitbucket.org': 'Bitbucket',
    'linear.app': 'Linear',
    'notion.so': 'Notion',
    'obsidian.md': 'Obsidian Sync',
    'logseq.com': 'Logseq',

    # ── Cloud & Infrastructure ──
    'aws.amazon.com': 'AWS',
    'console.aws.amazon': 'AWS',
    'digitalocean.com': 'DigitalOcean',
    'heroku.com': 'Heroku',
    'railway.app': 'Railway',
    'render.com': 'Render',
    'vercel.com': 'Vercel',
    'netlify.com': 'Netlify',
    'cloudflare.com': 'Cloudflare',
    'namecheap.com': 'Namecheap',
    'godaddy.com': 'GoDaddy',
    'domains.google': 'Google Domains',
    'sentry.io': 'Sentry',
    'datadoghq.com': 'Datadog',
    'newrelic.com': 'New Relic',
    'rollbar.com': 'Rollbar',

    # ── Communication ──
    'zoom.us': 'Zoom',
    'meet.google.com': 'Google Meet',
    'teams.microsoft.com': 'Microsoft Teams',
    'webex.com': 'Cisco Webex',
    'discord.com': 'Discord',
    'twilio.com': 'Twilio',

    # ── Marketing & Growth ──
    'mailchimp.com': 'Mailchimp',
    'sendgrid.com': 'SendGrid',
    'hubspot.com': 'HubSpot',
    'semrush.com': 'SEMrush',
    'ahrefs.com': 'Ahrefs',
    'moz.com': 'Moz',
    'hootsuite.com': 'Hootsuite',
    'buffer.com': 'Buffer',
    'later.com': 'Later',
    'convertkit.com': 'ConvertKit',
    'beehiiv.com': 'Beehiiv',
    'substack.com': 'Substack',
    'medium.com': 'Medium Membership',
    'linkedin.com/sales': 'LinkedIn Sales Navigator',
    'salesforce.com': 'Salesforce',
    'intercom.com': 'Intercom',
    'zendesk.com': 'Zendesk',
    'freshdesk.com': 'Freshdesk',
    'stripe.com': 'Stripe',
    'squareup.com': 'Square',
    'paypal.com': 'PayPal',
}

# ─── Subscription Category Mapping ────────────────────────────────────────────

CATEGORY_MAP = {
    'Netflix': 'Entertainment',
    'Hulu': 'Entertainment',
    'Disney+': 'Entertainment',
    'Spotify': 'Entertainment',
    'Apple Music': 'Entertainment',
    'YouTube Premium': 'Entertainment',
    'Paramount+': 'Entertainment',
    'Peacock': 'Entertainment',
    'HBO Max': 'Entertainment',
    'Pandora': 'Entertainment',
    'Audible': 'Entertainment',
    'Amazon Kindle': 'Entertainment',
    'Notion': 'Productivity',
    'Slack': 'Productivity',
    'Zoom': 'Productivity',
    'Dropbox': 'Productivity',
    'Box': 'Productivity',
    'Microsoft 365': 'Productivity',
    'Microsoft Office': 'Productivity',
    'Google Maps API': 'Infrastructure',
    'Google Workspace': 'Productivity',
    'Figma': 'Productivity',
    'Canva': 'Productivity',
    'Miro': 'Productivity',
    'Trello': 'Productivity',
    'Asana': 'Productivity',
    'Jira': 'Productivity',
    'GitHub': 'Infrastructure',
    'GitLab': 'Infrastructure',
    'Bitbucket': 'Infrastructure',
    'Linear': 'Productivity',
    'Obsidian Sync': 'Productivity',
    'Logseq': 'Productivity',
    'AWS': 'Infrastructure',
    'DigitalOcean': 'Infrastructure',
    'Heroku': 'Infrastructure',
    'Railway': 'Infrastructure',
    'Render': 'Infrastructure',
    'Vercel': 'Infrastructure',
    'Netlify': 'Infrastructure',
    'Cloudflare': 'Infrastructure',
    'Namecheap': 'Infrastructure',
    'GoDaddy': 'Infrastructure',
    'Google Domains': 'Infrastructure',
    'Sentry': 'Infrastructure',
    'Datadog': 'Infrastructure',
    'New Relic': 'Infrastructure',
    'Rollbar': 'Infrastructure',
    'Microsoft Teams': 'Communication',
    'Cisco Webex': 'Communication',
    'Discord': 'Communication',
    'Twilio': 'Communication',
    'Mailchimp': 'Marketing',
    'SendGrid': 'Marketing',
    'HubSpot': 'Marketing',
    'SEMrush': 'Marketing',
    'Ahrefs': 'Marketing',
    'Moz': 'Marketing',
    'Hootsuite': 'Marketing',
    'Buffer': 'Marketing',
    'Later': 'Marketing',
    'ConvertKit': 'Marketing',
    'Beehiiv': 'Marketing',
    'Substack': 'Marketing',
    'Medium Membership': 'Marketing',
    'LinkedIn Sales Navigator': 'Marketing',
    'Salesforce': 'Sales',
    'Intercom': 'Sales',
    'Zendesk': 'Sales',
    'Freshdesk': 'Sales',
    'Stripe': 'Infrastructure',
    'Square': 'Infrastructure',
    'PayPal': 'Infrastructure',
}

# ─── Core Analysis Functions ──────────────────────────────────────────────────


def categorize_transaction(transaction: dict) -> Optional[dict]:
    """
    Analyze a single bank transaction to identify if it's a subscription.

    Args:
        transaction: dict with at least 'description' (str), 'amount' (float),
                     'date' (str or datetime)

    Returns:
        dict with subscription info if matched, None otherwise.
        {
            'type': 'subscription',
            'name': 'Spotify',
            'category': 'Entertainment',
            'amount': 9.99,
            'date': '2026-01-07',
            'pattern_matched': 'spotify.com'
        }
    """
    description = transaction.get('description', '').lower()
    amount = transaction.get('amount', 0)
    date = transaction.get('date')

    if isinstance(date, datetime):
        date = date.strftime('%Y-%m-%d')

    for pattern, name in SUBSCRIPTION_PATTERNS.items():
        if pattern in description:
            return {
                'type': 'subscription',
                'name': name,
                'category': CATEGORY_MAP.get(name, 'Other'),
                'amount': amount,
                'date': date,
                'pattern_matched': pattern
            }

    return None


def get_monthly_totals(
    transactions: list,
    month: Optional[int] = None,
    year: Optional[int] = None
) -> dict:
    """
    Calculate total subscription spend by month, broken down by category.

    Args:
        transactions: List of transaction dicts
        month: Filter to specific month (1-12), None for all months
        year: Filter to specific year, None for all years

    Returns:
        {
            'total': 245.50,
            'by_category': {
                'Entertainment': 25.99,
                'Productivity': 45.00,
                'Infrastructure': 174.51
            },
            'by_subscription': {
                'Spotify': 9.99,
                'Notion': 15.00,
                'AWS': 149.58
            },
            'transaction_count': 12,
            'month': 1,
            'year': 2026
        }
    """
    totals = {
        'total': 0.0,
        'by_category': {},
        'by_subscription': {},
        'transaction_count': 0,
        'month': month,
        'year': year
    }

    for txn in transactions:
        sub = categorize_transaction(txn)
        if sub is None:
            continue

        # Apply month/year filters
        if month and sub['date']:
            try:
                txn_month = int(sub['date'].split('-')[1])
                if txn_month != month:
                    continue
            except (IndexError, ValueError):
                pass

        if year and sub['date']:
            try:
                txn_year = int(sub['date'].split('-')[0])
                if txn_year != year:
                    continue
            except (IndexError, ValueError):
                pass

        totals['total'] += sub['amount']
        totals['transaction_count'] += 1

        cat = sub['category']
        totals['by_category'][cat] = totals['by_category'].get(cat, 0) + sub['amount']

        name = sub['name']
        totals['by_subscription'][name] = totals['by_subscription'].get(name, 0) + sub['amount']

    # Round all values
    totals['total'] = round(totals['total'], 2)
    totals['by_category'] = {k: round(v, 2) for k, v in totals['by_category'].items()}
    totals['by_subscription'] = {k: round(v, 2) for k, v in totals['by_subscription'].items()}

    return totals


def find_savings_opportunities(
    transactions: list,
    last_login_map: Optional[dict] = None,
    cost_increase_threshold: float = 0.20,
    duplicate_similarity_threshold: float = 0.7
) -> dict:
    """
    Analyze transactions to find cost optimization opportunities.

    From the hackathon PDF Business Handover section:
      - Flag subscriptions with no login in 30 days
      - Flag cost increases > 20%
      - Flag duplicate functionality

    Args:
        transactions: List of all subscription transactions
        last_login_map: Dict mapping subscription name to last login date.
                        e.g., {'Spotify': '2026-01-01', 'Notion': '2025-11-15'}
        cost_increase_threshold: Fractional increase to flag (default: 0.20)
        duplicate_similarity_threshold: Similarity score to consider duplicates

    Returns:
        {
            'unused_subscriptions': [...],
            'cost_increases': [...],
            'potential_duplicates': [...],
            'total_potential_savings': 45.99
        }
    """
    if last_login_map is None:
        last_login_map = {}

    # Aggregate monthly totals to detect cost trends
    monthly_data = {}  # {subscription_name: {month_key: amount}}
    for txn in transactions:
        sub = categorize_transaction(txn)
        if sub is None:
            continue

        name = sub['name']
        date = sub['date']
        if date:
            month_key = date[:7]  # YYYY-MM
        else:
            month_key = 'unknown'

        if name not in monthly_data:
            monthly_data[name] = {}
        monthly_data[name][month_key] = (
            monthly_data[name].get(month_key, 0) + sub['amount']
        )

    findings = {
        'unused_subscriptions': [],
        'cost_increases': [],
        'potential_duplicates': [],
        'total_potential_savings': 0.0
    }

    today = datetime.now()
    thirty_days_ago = today - timedelta(days=30)

    # ── Check for unused subscriptions (no login in 30+ days) ──
    for name, last_login_str in last_login_map.items():
        if not last_login_str:
            continue
        try:
            last_login = datetime.strptime(last_login_str, '%Y-%m-%d')
            if last_login < thirty_days_ago:
                days_inactive = (today - last_login).days
                # Calculate monthly cost for this subscription
                monthly_cost = _get_avg_monthly_cost(monthly_data, name)
                findings['unused_subscriptions'].append({
                    'name': name,
                    'last_login': last_login_str,
                    'days_inactive': days_inactive,
                    'monthly_cost': monthly_cost,
                    'action': 'CANCEL'
                })
                findings['total_potential_savings'] += monthly_cost
        except (ValueError, TypeError):
            pass

    # ── Check for cost increases (> threshold) ──
    for name, months in monthly_data.items():
        sorted_months = sorted(months.keys())
        if len(sorted_months) >= 2:
            prev_amount = months[sorted_months[-2]]
            curr_amount = months[sorted_months[-1]]
            if prev_amount > 0:
                change_pct = (curr_amount - prev_amount) / prev_amount
                if change_pct > cost_increase_threshold:
                    findings['cost_increases'].append({
                        'name': name,
                        'previous_month': sorted_months[-2],
                        'previous_amount': round(prev_amount, 2),
                        'current_month': sorted_months[-1],
                        'current_amount': round(curr_amount, 2),
                        'increase_pct': round(change_pct * 100, 1),
                        'action': 'INVESTIGATE'
                    })

    # ── Check for duplicate functionality ──
    # Heuristic: group subscriptions by category
    category_subs = {}
    for name in monthly_data.keys():
        cat = CATEGORY_MAP.get(name, 'Other')
        if cat not in category_subs:
            category_subs[cat] = []
        category_subs[cat].append({
            'name': name,
            'avg_monthly': round(_get_avg_monthly_cost(monthly_data, name), 2)
        })

    for cat, subs in category_subs.items():
        if len(subs) > 1 and cat in ('Productivity', 'Communication', 'Infrastructure'):
            findings['potential_duplicates'].append({
                'category': cat,
                'subscriptions': subs,
                'note': f'{len(subs)} subscriptions in same category — review overlap'
            })

    findings['total_potential_savings'] = round(findings['total_potential_savings'], 2)
    return findings


def generate_audit_summary(
    transactions: list,
    last_login_map: Optional[dict] = None,
    month: Optional[int] = None,
    year: Optional[int] = None
) -> str:
    """
    Generate a text-based audit summary for the CEO Briefing.

    Args:
        transactions: List of all bank transactions
        last_login_map: Optional dict of last login dates per subscription
        month: Month to filter (1-12), None = current month
        year: Year to filter, None = current year

    Returns:
        Multi-line string summary ready for inclusion in CEO Briefing
    """
    if month is None:
        month = datetime.now().month
    if year is None:
        year = datetime.now().year

    totals = get_monthly_totals(transactions, month=month, year=year)
    savings = find_savings_opportunities(
        transactions, last_login_map=last_login_map
    )

    lines = [
        f"## Subscription Audit — {month}/{year}",
        "",
        f"**Total Subscription Spend:** ${totals['total']:.2f}/month",
        f"**Subscriptions Found:** {totals['transaction_count']}",
        "",
        "### Spend by Category",
    ]

    for cat, amount in sorted(totals['by_category'].items(), key=lambda x: -x[1]):
        lines.append(f"- **{cat}:** ${amount:.2f}")

    lines.extend(["", "### Subscriptions Breakdown"])
    for name, amount in sorted(totals['by_subscription'].items(), key=lambda x: -x[1]):
        lines.append(f"- {name}: ${amount:.2f}")

    if savings['unused_subscriptions']:
        lines.extend(["", "### ⚠️ Unused Subscriptions (Cancel Candidates)"])
        for s in savings['unused_subscriptions']:
            lines.append(
                f"- **{s['name']}**: ${s['monthly_cost']:.2f}/mo, "
                f"inactive {s['days_inactive']} days"
            )

    if savings['cost_increases']:
        lines.extend(["", "### 📈 Cost Increases (>20% MoM)"])
        for c in savings['cost_increases']:
            lines.append(
                f"- **{c['name']}**: ${c['current_amount']:.2f} vs "
                f"${c['previous_amount']:.2f} (+{c['increase_pct']}%)"
            )

    if savings['potential_duplicates']:
        lines.extend(["", "### 🔄 Potential Duplicates"])
        for d in savings['potential_duplicates']:
            sub_list = ", ".join(
                f"{s['name']} (${s['avg_monthly']})" for s in d['subscriptions']
            )
            lines.append(f"- **{d['category']}:** {sub_list}")

    lines.append("")
    lines.append(f"**Potential Monthly Savings:** ${savings['total_potential_savings']:.2f}")
    lines.append("")
    lines.append("---")
    lines.append("*Auto-generated by Financial Auditor skill*")

    return "\n".join(lines)


def _get_avg_monthly_cost(monthly_data: dict, name: str) -> float:
    """Helper: get average monthly cost for a subscription."""
    if name not in monthly_data or not monthly_data[name]:
        return 0.0
    amounts = list(monthly_data[name].values())
    return sum(amounts) / len(amounts)


# ─── CLI Self-Test ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Sample transaction data for testing
    sample_transactions = [
        {
            'description': 'SPOTIFY.COM/BILL    SUBSCRIPTION  ',
            'amount': 9.99,
            'date': '2026-01-07'
        },
        {
            'description': 'NOTION.SO           MONTHLY PLAN ',
            'amount': 15.00,
            'date': '2026-01-05'
        },
        {
            'description': 'AWS.AMAZON.COM      EC2 USAGE     ',
            'amount': 149.58,
            'date': '2026-01-10'
        },
        {
            'description': 'SLACK TECHNOLOGIES  BILLING       ',
            'amount': 8.75,
            'date': '2026-01-03'
        },
        {
            'description': 'NETFLIX.COM         SUBSCRIPTION  ',
            'amount': 15.49,
            'date': '2026-01-01'
        },
        {
            'description': 'GROCERY STORE #1234 PURCHASE      ',
            'amount': 85.30,
            'date': '2026-01-06'
        },
        {
            'description': 'SPOTIFY.COM/BILL    SUBSCRIPTION  ',
            'amount': 9.99,
            'date': '2025-12-07'
        },
        {
            'description': 'FRESHDESK.COM       BILLING       ',
            'amount': 49.00,
            'date': '2026-01-08'
        },
        {
            'description': 'FIGMA.COM           PRO PLAN      ',
            'amount': 75.00,
            'date': '2026-01-04'
        },
        {
            'description': 'SENTRY.IO           BILLING       ',
            'amount': 29.00,
            'date': '2026-01-09'
        },
    ]

    print("=" * 60)
    print("AUDIT LOGIC MODULE — SELF-TEST")
    print("=" * 60)

    # Test 1: Categorize transaction
    print("\n--- Test 1: Categorize Transaction ---")
    result = categorize_transaction(sample_transactions[0])
    assert result is not None
    assert result['name'] == 'Spotify'
    assert result['type'] == 'subscription'
    print(f"  ✓ '{sample_transactions[0]['description']}' → {result['name']} ({result['category']})")

    # Test 2: Non-subscription transaction
    print("\n--- Test 2: Non-Subscription Transaction ---")
    result = categorize_transaction(sample_transactions[5])
    assert result is None
    print(f"  ✓ '{sample_transactions[5]['description']}' → correctly identified as non-subscription")

    # Test 3: Monthly totals
    print("\n--- Test 3: Monthly Totals (Jan 2026) ---")
    totals = get_monthly_totals(sample_transactions, month=1, year=2026)
    assert totals['transaction_count'] == 7  # 7 of 10 are subscriptions in Jan
    assert totals['total'] > 0
    print(f"  ✓ Found {totals['transaction_count']} subscription transactions")
    print(f"  ✓ Total: ${totals['total']:.2f}/month")
    print(f"  ✓ Categories: {list(totals['by_category'].keys())}")
    print(f"  ✓ Subscriptions: {list(totals['by_subscription'].keys())}")

    # Test 4: Savings opportunities
    print("\n--- Test 4: Savings Opportunities ---")
    last_logins = {
        'Spotify': '2025-11-15',   # 54+ days ago (unused)
        'Notion': '2026-01-07',    # Recent (active)
        'Freshdesk': '2025-10-01', # 100+ days ago (unused)
    }
    savings = find_savings_opportunities(
        sample_transactions, last_login_map=last_logins
    )
    print(f"  ✓ Unused subscriptions: {len(savings['unused_subscriptions'])}")
    for s in savings['unused_subscriptions']:
        print(f"    - {s['name']}: ${s['monthly_cost']:.2f}/mo, inactive {s['days_inactive']}d")
    print(f"  ✓ Cost increases: {len(savings['cost_increases'])}")
    print(f"  ✓ Potential duplicates: {len(savings['potential_duplicates'])}")
    print(f"  ✓ Total potential savings: ${savings['total_potential_savings']:.2f}/mo")

    # Test 5: Generate audit summary text
    print("\n--- Test 5: Generated Audit Summary ---")
    summary = generate_audit_summary(sample_transactions, last_login_map=last_logins)
    print(summary)

    print("\n" + "=" * 60)
    print("✓ ALL AUDIT LOGIC TESTS PASSED")
    print("=" * 60)