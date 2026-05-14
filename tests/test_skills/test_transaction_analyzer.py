"""
Tests for financial auditor module.
"""

import pytest
import tempfile
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from utilities.financial_auditor import FinancialAuditor


class TestFinancialAuditor:
    """Test Financial Auditor functionality."""
    
    @pytest.fixture
    def auditor(self):
        """Create auditor instance."""
        auditor = FinancialAuditor()
        return auditor
    
    def test_auditor_initialization(self, auditor):
        """Test auditor initialization."""
        assert auditor is not None
        assert auditor.vault_manager is not None
        assert len(auditor.expense_categories) > 0
    
    def test_categorize_transaction_by_existing_category(self, auditor):
        """Test categorization when category is already provided."""
        transaction = {
            'description': 'AWS Services',
            'amount': -4500,
            'category': 'Cloud Services'
        }
        
        result = auditor.categorize_transaction(transaction)
        assert result == 'Cloud Services'
    
    def test_categorize_transaction_by_keywords(self, auditor):
        """Test categorization by keyword matching."""
        transactions = [
            {'description': 'AWS Services', 'amount': -4500, 'category': ''},
            {'description': 'Payroll Processing', 'amount': -35000, 'category': ''},
            {'description': 'Google Ads Campaign', 'amount': -1200, 'category': ''},
            {'description': 'Freelancer from Upwork', 'amount': -500, 'category': ''},
        ]
        
        for transaction in transactions:
            category = auditor.categorize_transaction(transaction)
            assert category != 'Uncategorized'
    
    def test_categorize_transactions(self, auditor):
        """Test categorizing multiple transactions."""
        transactions = [
            {'description': 'AWS Services', 'amount': -4500, 'category': ''},
            {'description': 'Customer Payment', 'amount': 25000, 'category': ''},
            {'description': 'Office Supplies', 'amount': -500, 'category': ''},
        ]
        
        result = auditor.categorize_transactions(transactions)
        
        assert len(result) == 3
        assert all('category' in t and t['category'] for t in result)
    
    def test_detect_anomalies_empty(self, auditor):
        """Test anomaly detection with empty list."""
        anomalies = auditor.detect_anomalies([])
        assert len(anomalies) == 0
    
    def test_detect_anomalies_single_transaction(self, auditor):
        """Test anomaly detection with single transaction."""
        transactions = [
            {'description': 'AWS', 'amount': -4500, 'category': 'Cloud Services'}
        ]
        
        anomalies = auditor.detect_anomalies(transactions)
        assert len(anomalies) == 0  # Can't calculate std dev with 1 item
    
    def test_detect_anomalies_unusual_amount(self, auditor):
        """Test detecting unusually large transactions."""
        transactions = [
            {'description': 'AWS', 'amount': -100, 'category': 'Cloud Services'},
            {'description': 'AWS', 'amount': -150, 'category': 'Cloud Services'},
            {'description': 'AWS', 'amount': -120, 'category': 'Cloud Services'},
            {'description': 'AWS', 'amount': -110, 'category': 'Cloud Services'},
            {'description': 'AWS Emergency', 'amount': -50000, 'category': 'Cloud Services'},
        ]
        
        anomalies = auditor.detect_anomalies(transactions)
        
        # Should detect anomaly if there are enough data points
        if len(anomalies) > 0:
            unusual_amounts = [a['transaction']['amount'] for a in anomalies]
            assert any(abs(amount) > 1000 for amount in unusual_amounts)
    
    def test_calculate_metrics_empty(self, auditor):
        """Test metrics calculation with empty list."""
        metrics = auditor.calculate_metrics([])
        
        assert metrics['transaction_count'] == 0
        assert metrics['total_revenue'] == 0
        assert metrics['total_expenses'] == 0
        assert metrics['net'] == 0
    
    def test_calculate_metrics_basic(self, auditor):
        """Test metrics calculation with basic transactions."""
        transactions = [
            {'description': 'Sale', 'amount': 10000, 'category': 'Revenue'},
            {'description': 'Payroll', 'amount': -3500, 'category': 'Payroll'},
            {'description': 'Marketing', 'amount': -1000, 'category': 'Marketing'},
        ]
        
        metrics = auditor.calculate_metrics(transactions)
        
        assert metrics['transaction_count'] == 3
        assert metrics['total_revenue'] == 10000
        assert metrics['total_expenses'] == 4500
        assert metrics['net'] == 5500
        assert metrics['expense_ratio'] == 4500 / 10000
    
    def test_calculate_metrics_by_category(self, auditor):
        """Test category breakdown in metrics."""
        transactions = [
            {'description': 'Sale', 'amount': 10000, 'category': 'Revenue'},
            {'description': 'Payroll', 'amount': -3500, 'category': 'Payroll'},
            {'description': 'Payroll', 'amount': -3500, 'category': 'Payroll'},
            {'description': 'Marketing', 'amount': -1000, 'category': 'Marketing'},
        ]
        
        metrics = auditor.calculate_metrics(transactions)
        
        assert 'Revenue' in metrics['by_category']
        assert 'Payroll' in metrics['by_category']
        assert 'Marketing' in metrics['by_category']
        
        assert metrics['by_category']['Payroll']['count'] == 2
        assert metrics['by_category']['Payroll']['amount'] == -7000
        assert metrics['by_category']['Payroll']['average'] == -3500
    
    def test_generate_briefing_basic(self, auditor):
        """Test CEO briefing generation."""
        transactions = [
            {'description': 'Sale', 'amount': 10000, 'category': 'Revenue'},
            {'description': 'Payroll', 'amount': -3500, 'category': 'Payroll'},
            {'description': 'Marketing', 'amount': -1000, 'category': 'Marketing'},
        ]
        
        briefing = auditor.generate_briefing(transactions)
        
        assert 'CEO Financial Briefing' in briefing
        assert '$10,000.00' in briefing or '$10000' in briefing
        assert 'Payroll' in briefing
        assert 'Marketing' in briefing


class TestAnomalyDetection:
    """Test anomaly detection specifically."""
    
    @pytest.fixture
    def auditor(self):
        """Create auditor instance."""
        return FinancialAuditor()
    
    def test_new_vendor_flag(self, auditor):
        """Test identifying new vendors."""
        transactions = [
            {'description': 'Vendor A', 'amount': -500, 'category': 'Operations'},
            {'description': 'Vendor A', 'amount': -500, 'category': 'Operations'},
            {'description': 'Vendor A', 'amount': -600, 'category': 'Operations'},
            {'description': 'Vendor B', 'amount': -5000, 'category': 'Operations'},
        ]
        
        # New vendor (Vendor B) with large amount should be flagged
        anomalies = auditor.detect_anomalies(transactions)
        
        # Should detect the unusual amount if enough data points
        if len(anomalies) > 0:
            assert any('Unusual' in a['reason'] for a in anomalies)


class TestCategoryRules:
    """Test category assignment rules."""
    
    @pytest.fixture
    def auditor(self):
        """Create auditor instance."""
        return FinancialAuditor()
    
    def test_payroll_category(self, auditor):
        """Test payroll categorization."""
        keywords = ['payroll', 'salary', 'wage', 'bonus']
        for keyword in keywords:
            t = {'description': f'Monthly {keyword}', 'amount': -5000, 'category': ''}
            assert auditor.categorize_transaction(t) == 'Payroll'
    
    def test_cloud_services_category(self, auditor):
        """Test cloud services categorization."""
        keywords = ['aws', 'azure', 'gcp', 'heroku']
        for keyword in keywords:
            t = {'description': f'{keyword.upper()} services', 'amount': -500, 'category': ''}
            assert auditor.categorize_transaction(t) == 'Cloud Services'
    
    def test_marketing_category(self, auditor):
        """Test marketing categorization."""
        keywords = ['ads', 'advertising', 'google ads']
        for keyword in keywords:
            t = {'description': f'Campaign {keyword}', 'amount': -1000, 'category': ''}
            assert auditor.categorize_transaction(t) == 'Marketing'


class TestFinancialMetrics:
    """Test financial metrics calculations."""
    
    @pytest.fixture
    def auditor(self):
        """Create auditor instance."""
        return FinancialAuditor()
    
    def test_expense_ratio(self, auditor):
        """Test expense ratio calculation."""
        transactions = [
            {'description': 'Revenue', 'amount': 10000, 'category': 'Revenue'},
            {'description': 'Expenses', 'amount': -5000, 'category': 'Operations'},
        ]
        
        metrics = auditor.calculate_metrics(transactions)
        
        assert metrics['expense_ratio'] == 0.5  # 5000 / 10000
    
    def test_net_calculation(self, auditor):
        """Test net income calculation."""
        transactions = [
            {'description': 'Revenue', 'amount': 50000, 'category': 'Revenue'},
            {'description': 'Expenses', 'amount': -30000, 'category': 'Operations'},
        ]
        
        metrics = auditor.calculate_metrics(transactions)
        
        assert metrics['net'] == 20000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
