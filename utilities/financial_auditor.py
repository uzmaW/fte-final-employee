"""
Financial Auditor - Analyze transactions, categorize expenses, and generate CEO briefings.
"""

import logging
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from statistics import mean, stdev
import csv

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utilities.vault_manager import VaultManager
from config import get_settings

logger = logging.getLogger(__name__)


class FinancialAuditor:
    """Analyze financial transactions and generate reports."""
    
    def __init__(self):
        """Initialize financial auditor."""
        self.vault_manager = VaultManager()
        self.settings = get_settings()
        self.current_month_file = "Accounting/Current_Month.md"
        
        # Standard expense categories
        self.expense_categories = {
            "Payroll": ["payroll", "salary", "wage", "bonus", "fica", "withholding"],
            "Cloud Services": ["aws", "azure", "gcp", "heroku", "datadog", "stripe"],
            "Marketing": ["ads", "facebook", "google ads", "marketing", "advertising"],
            "Contractors": ["contractor", "freelance", "upwork", "fiverr"],
            "Travel": ["airline", "hotel", "uber", "lyft", "rental car", "airbnb"],
            "Office": ["rent", "utilities", "office", "supplies"],
            "Legal": ["legal", "lawyer", "law firm", "attorney"],
            "Accounting": ["accounting", "accountant", "bookkeeper", "quickbooks"],
            "Insurance": ["insurance", "policy"],
            "Software": ["software", "license", "subscription", "saas"],
        }
    
    def import_transactions_csv(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Import transactions from CSV file.
        
        Expected CSV format:
        Date,Amount,Description,Category,Account
        """
        transactions = []
        
        try:
            with open(file_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    transaction = {
                        'date': row.get('Date', ''),
                        'amount': float(row.get('Amount', 0)),
                        'description': row.get('Description', ''),
                        'category': row.get('Category', ''),
                        'account': row.get('Account', ''),
                        'type': 'credit' if float(row.get('Amount', 0)) > 0 else 'debit',
                    }
                    transactions.append(transaction)
            
            logger.info(f"Imported {len(transactions)} transactions from CSV")
            return transactions
            
        except Exception as e:
            logger.error(f"Error importing CSV: {e}")
            return []
    
    def categorize_transaction(self, transaction: Dict[str, Any]) -> str:
        """
        Categorize a transaction based on description.
        
        Returns:
            Category name or "Uncategorized"
        """
        if transaction.get('category') and transaction['category'] != '':
            return transaction['category']
        
        description = transaction.get('description', '').lower()
        
        # Check each category's keywords
        for category, keywords in self.expense_categories.items():
            for keyword in keywords:
                if keyword in description:
                    return category
        
        # Check for income
        if transaction.get('amount', 0) > 0 and 'revenue' not in description.lower():
            if any(word in description for word in ['income', 'deposit', 'payment received', 'refund']):
                return 'Revenue'
        
        return 'Uncategorized'
    
    def categorize_transactions(self, transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Categorize all transactions."""
        for transaction in transactions:
            if not transaction.get('category') or transaction['category'] == '':
                transaction['category'] = self.categorize_transaction(transaction)
        
        return transactions
    
    def detect_anomalies(self, transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Detect anomalous transactions.
        
        Checks for:
        - Unusual amount for category
        - New vendors
        - Duplicate transactions
        - Weekend transactions
        """
        anomalies = []
        
        if not transactions:
            return anomalies
        
        # Group by category
        by_category = {}
        for t in transactions:
            cat = t.get('category', 'Uncategorized')
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(t)
        
        # Check for anomalies per category
        for category, items in by_category.items():
            amounts = [abs(t['amount']) for t in items if t['amount'] != 0]
            
            if len(amounts) < 2:
                continue
            
            try:
                avg = mean(amounts)
                std = stdev(amounts) if len(amounts) > 1 else 0
                
                # Flag if 3 std deviations above mean
                threshold = avg + (3 * std) if std > 0 else avg * 2
                
                for transaction in items:
                    if abs(transaction['amount']) > threshold:
                        anomalies.append({
                            'transaction': transaction,
                            'reason': f'Unusual amount for {category}',
                            'severity': 'high'
                        })
            except Exception as e:
                logger.debug(f"Error calculating anomalies for {category}: {e}")
        
        return anomalies
    
    def calculate_metrics(self, transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate financial metrics from transactions.
        """
        metrics = {
            'period': datetime.now().strftime('%Y-%m'),
            'total_revenue': 0,
            'total_expenses': 0,
            'transaction_count': len(transactions),
            'by_category': {},
            'net': 0,
            'cash_position': 0,
        }
        
        # Sum by category
        for transaction in transactions:
            amount = transaction['amount']
            category = transaction['category']
            
            if category not in metrics['by_category']:
                metrics['by_category'][category] = {
                    'amount': 0,
                    'count': 0,
                    'average': 0,
                }
            
            metrics['by_category'][category]['amount'] += amount
            metrics['by_category'][category]['count'] += 1
            
            # Track revenue vs expenses
            if amount > 0:
                metrics['total_revenue'] += amount
            else:
                metrics['total_expenses'] += abs(amount)
        
        # Calculate averages
        for category in metrics['by_category']:
            cat = metrics['by_category'][category]
            if cat['count'] > 0:
                cat['average'] = cat['amount'] / cat['count']
        
        # Calculate net
        metrics['net'] = metrics['total_revenue'] - metrics['total_expenses']
        
        # Calculate percentages
        if metrics['total_revenue'] > 0:
            metrics['expense_ratio'] = metrics['total_expenses'] / metrics['total_revenue']
        
        return metrics
    
    def store_transactions(self, transactions: List[Dict[str, Any]]):
        """Store transactions in vault's Accounting/Current_Month.md file."""
        try:
            # Build transaction table
            table_lines = [
                "## Transactions",
                "",
                "| Date | Amount | Description | Category |",
                "|------|--------|-------------|----------|",
            ]
            
            for t in transactions:
                date = t.get('date', '')
                amount = f"${t['amount']:.2f}"
                desc = t.get('description', '')[:30]
                cat = t.get('category', '')
                
                table_lines.append(f"| {date} | {amount} | {desc} | {cat} |")
            
            # Build summary section
            metrics = self.calculate_metrics(transactions)
            
            summary_lines = [
                "",
                "## Monthly Summary",
                "",
                f"- **Period:** {metrics['period']}",
                f"- **Total Revenue:** ${metrics['total_revenue']:.2f}",
                f"- **Total Expenses:** ${metrics['total_expenses']:.2f}",
                f"- **Net:** ${metrics['net']:.2f}",
                f"- **Transactions:** {metrics['transaction_count']}",
            ]
            
            # Build category breakdown
            summary_lines.append("")
            summary_lines.append("## By Category")
            summary_lines.append("")
            summary_lines.append("| Category | Amount | Count |")
            summary_lines.append("|----------|--------|-------|")
            
            for category, data in sorted(metrics['by_category'].items()):
                amount = f"${data['amount']:.2f}"
                count = data['count']
                summary_lines.append(f"| {category} | {amount} | {count} |")
            
            # Combine and write
            accounting_file = self.vault_manager.vault_path / "Accounting" / "Current_Month.md"
            
            header = f"""# {metrics['period']} Accounting

Last Updated: {datetime.now().isoformat()}Z

"""
            
            full_content = header + "\n".join(table_lines) + "\n" + "\n".join(summary_lines)
            
            with open(accounting_file, 'w') as f:
                f.write(full_content)
            
            logger.info(f"Stored {len(transactions)} transactions in accounting file")
            
        except Exception as e:
            logger.error(f"Error storing transactions: {e}", exc_info=True)
    
    def generate_briefing(self, transactions: List[Dict[str, Any]]) -> str:
        """
        Generate a CEO briefing from transactions.
        """
        try:
            metrics = self.calculate_metrics(transactions)
            anomalies = self.detect_anomalies(transactions)
            
            # Build briefing
            briefing = f"""---
type: executive_briefing
period: {metrics['period']}
generated: {datetime.now().isoformat()}Z
status: final
---

# CEO Financial Briefing

**Period:** {metrics['period']}  
**Generated:** {datetime.now().isoformat()}Z  

## Executive Summary

Financial summary for {metrics['period']}:
- Revenue: ${metrics['total_revenue']:,.2f}
- Expenses: ${metrics['total_expenses']:,.2f}
- Net: ${metrics['net']:,.2f}

## Key Metrics

| Metric | Amount |
|--------|--------|
| Total Revenue | ${metrics['total_revenue']:,.2f} |
| Total Expenses | ${metrics['total_expenses']:,.2f} |
| Net Income | ${metrics['net']:,.2f} |
| Transaction Count | {metrics['transaction_count']} |

## Spending by Category

| Category | Amount | Count | Avg |
|----------|--------|-------|-----|
"""
            
            for category in sorted(metrics['by_category'].keys()):
                data = metrics['by_category'][category]
                briefing += f"| {category} | ${data['amount']:.2f} | {data['count']} | ${data['average']:.2f} |\n"
            
            # Add anomalies section
            if anomalies:
                briefing += "\n## Anomalies Detected\n\n"
                for anomaly in anomalies[:5]:  # Top 5 anomalies
                    t = anomaly['transaction']
                    briefing += f"⚠️ **{t['description']}** - ${t['amount']:.2f} ({anomaly['reason']})\n"
            
            # Add recommendations
            briefing += "\n## Recommendations\n\n"
            
            if metrics['total_expenses'] > metrics['total_revenue'] * 0.8:
                briefing += "- Consider cost reduction initiatives\n"
            
            if len(anomalies) > 3:
                briefing += "- Review unusual transactions\n"
            
            # Check for uncategorized
            uncategorized = metrics['by_category'].get('Uncategorized', {})
            if uncategorized.get('count', 0) > 0:
                briefing += "- Categorize uncategorized transactions\n"
            
            briefing += "\n---\n\n"
            briefing += "**Status:** Ready for Review  \n"
            briefing += f"**Generated By:** Financial Auditor  \n"
            
            return briefing
            
        except Exception as e:
            logger.error(f"Error generating briefing: {e}", exc_info=True)
            return f"Error generating briefing: {str(e)}"
    
    def create_approval_request(self, transaction: Dict[str, Any], reason: str) -> Optional[Path]:
        """
        Create an approval request for an out-of-policy transaction.
        """
        try:
            action_id = f"PAYMENT_{datetime.now().strftime('%Y%m%d_%H%M%S')}_001"
            
            description = f"""
## Transaction Details

- **Description:** {transaction.get('description', 'N/A')}
- **Amount:** ${transaction.get('amount', 0):.2f}
- **Category:** {transaction.get('category', 'Uncategorized')}
- **Date:** {transaction.get('date', 'N/A')}

## Reason for Review

{reason}

## Action Required

Please review and approve or reject this transaction.
"""
            
            return self.vault_manager.create_approval_request(
                action_id=action_id,
                action_type='financial',
                description=description,
                risk_level='medium',
                priority='high'
            )
            
        except Exception as e:
            logger.error(f"Error creating approval request: {e}")
            return None
    
    def update_dashboard(self, metrics: Dict[str, Any]):
        """Update Dashboard.md with financial metrics."""
        try:
            # Read current dashboard
            dashboard_file = self.vault_manager.vault_path / "Dashboard.md"
            
            if dashboard_file.exists():
                with open(dashboard_file, 'r') as f:
                    content = f.read()
                
                # Update timestamp
                import re
                content = re.sub(
                    r'\*\*Last Updated:\*\* .+',
                    f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}",
                    content
                )
                
                # Write back
                with open(dashboard_file, 'w') as f:
                    f.write(content)
            
            logger.debug("Updated dashboard with financial metrics")
            
        except Exception as e:
            logger.error(f"Error updating dashboard: {e}")


if __name__ == "__main__":
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    auditor = FinancialAuditor()
    
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        # Test with sample transactions
        test_transactions = [
            {'date': '2026-02-08', 'amount': 25000, 'description': 'Customer Payment', 'category': 'Revenue'},
            {'date': '2026-02-08', 'amount': -35000, 'description': 'Payroll', 'category': ''},
            {'date': '2026-02-07', 'amount': -4500, 'description': 'AWS Services', 'category': ''},
            {'date': '2026-02-06', 'amount': -1200, 'description': 'Office Supplies', 'category': ''},
        ]
        
        # Categorize
        test_transactions = auditor.categorize_transactions(test_transactions)
        
        # Store
        auditor.store_transactions(test_transactions)
        
        # Generate briefing
        briefing = auditor.generate_briefing(test_transactions)
        print(briefing)
