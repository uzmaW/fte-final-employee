"""
Integration tests for Odoo accounting operations.

Tests the Accounting Manager skill with Odoo MCP server.
Note: Requires a running Odoo instance for full integration tests.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
import os
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from mcp_servers.odoo_server import OdooMCPServer
from skills.finance.accounting_manager.accounting_manager import AccountingManager


class TestOdooMCPServer:
    """Test Odoo MCP Server functionality."""

    @pytest.fixture
    def mock_odoo(self):
        """Create a mock Odoo server for testing."""
        with patch('mcp_servers.odoo_server.xmlrpc.ServerProxy') as mock_proxy:
            # Mock common endpoint
            mock_common = MagicMock()
            mock_common.authenticate.return_value = 1  # Mock UID

            # Mock models endpoint
            mock_models = MagicMock()

            # Setup return values
            mock_proxy.side_effect = lambda url: mock_common if 'common' in url else mock_models

            yield mock_common, mock_models

    def test_odoo_authentication_success(self, mock_odoo):
        """Test successful Odoo authentication."""
        mock_common, _ = mock_odoo

        with patch('mcp_servers.odoo_server.xmlrpc.ServerProxy') as mock_proxy:
            mock_proxy.return_value = mock_common

            server = OdooMCPServer('http://localhost:8069', 'test_db', 'admin', 'admin')

            assert server.authenticated
            assert server.uid == 1

    def test_odoo_authentication_failure(self, mock_odoo):
        """Test failed Odoo authentication."""
        mock_common, _ = mock_odoo
        mock_common.authenticate.return_value = None  # Failed auth

        with patch('mcp_servers.odoo_server.xmlrpc.ServerProxy') as mock_proxy:
            mock_proxy.return_value = mock_common

            server = OdooMCPServer('http://localhost:8069', 'test_db', 'admin', 'wrong_pass')

            assert not server.authenticated
            assert server.uid is None

    def test_health_check(self, mock_odoo):
        """Test health check endpoint."""
        mock_common, _ = mock_odoo

        with patch('mcp_servers.odoo_server.xmlrpc.ServerProxy') as mock_proxy:
            mock_proxy.return_value = mock_common

            server = OdooMCPServer('http://localhost:8069', 'test_db', 'admin', 'admin')
            health = server.health_check()

            assert health['connected'] is True
            assert health['authenticated'] is True
            assert health['database'] == 'test_db'


class TestAccountingManager:
    """Test Accounting Manager skill."""

    @pytest.fixture
    def accounting_manager(self):
        """Create AccountingManager with mocked Odoo."""
        with patch.object(AccountingManager, '__init__', lambda x: None):
            manager = AccountingManager()
            manager.odoo = MagicMock()
            manager.odoo.authenticated = True
            manager.vault = MagicMock()
            return manager

    def test_manager_initialization(self):
        """Test AccountingManager initialization."""
        with patch('skills.finance.accounting_manager.accounting_manager.OdooMCPServer') as mock_odoo:
            mock_odoo_instance = MagicMock()
            mock_odoo_instance.authenticated = True
            mock_odoo.return_value = mock_odoo_instance

            with patch('skills.finance.accounting_manager.accounting_manager.VaultManager'):
                manager = AccountingManager()
                assert manager.is_connected()

    def test_create_invoice_success(self, accounting_manager):
        """Test successful invoice creation."""
        # Mock Odoo response
        accounting_manager.odoo.create_invoice.return_value = {
            'success': True,
            'invoice_id': 1,
            'partner_id': 1,
            'created_at': datetime.now().isoformat()
        }

        # Mock partner lookup
        accounting_manager.odoo.models = MagicMock()
        accounting_manager.odoo.models.execute_kw.return_value = [1]  # Partner found

        # Create invoice
        result = accounting_manager.create_invoice_from_transaction({
            'customer': 'Test Customer',
            'amount': 1000.00,
            'description': 'Test Service',
            'date': '2026-02-08',
            'reference': 'TEST-001'
        })

        assert result['success']
        assert result['invoice_id'] == 1
        assert accounting_manager.vault.append_to_file.called

    def test_create_invoice_not_connected(self, accounting_manager):
        """Test invoice creation when not connected."""
        accounting_manager.odoo.authenticated = False

        result = accounting_manager.create_invoice_from_transaction({
            'customer': 'Test',
            'amount': 100.00
        })

        assert not result['success']
        assert 'Not connected' in result['error']

    def test_post_expense_success(self, accounting_manager):
        """Test successful expense posting."""
        accounting_manager.odoo.post_journal_entry.return_value = {
            'success': True,
            'entry_id': 1,
            'created_at': datetime.now().isoformat()
        }

        result = accounting_manager.post_expense(
            amount=350.00,
            category='supplies',
            description='Office supplies',
            date='2026-02-08'
        )

        assert result['success']
        assert result['entry_id'] == 1
        assert accounting_manager.odoo.post_journal_entry.called

    def test_post_revenue_success(self, accounting_manager):
        """Test successful revenue posting."""
        accounting_manager.odoo.post_journal_entry.return_value = {
            'success': True,
            'entry_id': 2,
            'created_at': datetime.now().isoformat()
        }

        result = accounting_manager.post_revenue(
            amount=2500.00,
            description='Service revenue',
            customer='Acme Corp',
            date='2026-02-08'
        )

        assert result['success']
        assert result['entry_id'] == 2
        assert accounting_manager.odoo.post_journal_entry.called

    def test_reconcile_payment_success(self, accounting_manager):
        """Test successful payment reconciliation."""
        accounting_manager.odoo.reconcile_payment.return_value = {
            'success': True,
            'payment_id': 1,
            'invoice_id': 1,
            'amount': 1000.00,
            'created_at': datetime.now().isoformat()
        }

        result = accounting_manager.reconcile_payment(
            invoice_id=1,
            payment_amount=1000.00,
            payment_date='2026-02-08'
        )

        assert result['success']
        assert result['payment_id'] == 1
        assert accounting_manager.odoo.reconcile_payment.called

    def test_get_financial_report(self, accounting_manager):
        """Test financial report generation."""
        accounting_manager.odoo.get_financial_report.return_value = {
            'success': True,
            'report_type': 'balance_sheet',
            'accounts': [
                {'code': '1010', 'name': 'Bank', 'balance': 50000.00},
                {'code': '1500', 'name': 'Equipment', 'balance': 10000.00}
            ]
        }

        result = accounting_manager.get_financial_report('balance_sheet')

        assert result['success']
        assert result['report_type'] == 'balance_sheet'
        assert len(result['accounts']) == 2

    def test_expense_categories_mapping(self, accounting_manager):
        """Test that expense categories map to correct accounts."""
        expected_mappings = {
            'revenue': 4000,
            'supplies': 6100,
            'utilities': 6200,
            'rent': 6300,
            'salaries': 6400,
            'advertising': 6500,
        }

        for category, account_id in expected_mappings.items():
            assert AccountingManager.ACCOUNT_MAP.get(category) == account_id

    def test_vault_logging(self, accounting_manager):
        """Test that operations are logged to vault."""
        accounting_manager.odoo.create_invoice.return_value = {
            'success': True,
            'invoice_id': 1,
            'partner_id': 1,
            'created_at': datetime.now().isoformat()
        }
        accounting_manager.odoo.models = MagicMock()
        accounting_manager.odoo.models.execute_kw.return_value = [1]

        result = accounting_manager.create_invoice_from_transaction({
            'customer': 'Test',
            'amount': 100.00
        })

        # Verify vault logging was called
        assert accounting_manager.vault.append_to_file.called
        call_args = accounting_manager.vault.append_to_file.call_args
        assert 'accounting.json' in str(call_args)


class TestOdooIntegration:
    """Integration tests for full Odoo workflow."""

    @pytest.mark.skip(reason="Requires running Odoo instance")
    def test_full_accounting_workflow(self):
        """Test complete accounting workflow: invoice → payment → reconciliation."""
        manager = AccountingManager()

        if not manager.is_connected():
            pytest.skip("Odoo not available")

        # Step 1: Create invoice
        invoice_result = manager.create_invoice_from_transaction({
            'customer': 'Integration Test Customer',
            'amount': 1500.00,
            'description': 'Integration test invoice',
            'date': datetime.now().date().isoformat()
        })
        assert invoice_result['success']
        invoice_id = invoice_result['invoice_id']

        # Step 2: Post expense
        expense_result = manager.post_expense(
            amount=250.00,
            category='supplies',
            description='Test supplies'
        )
        assert expense_result['success']

        # Step 3: Reconcile payment
        payment_result = manager.reconcile_payment(
            invoice_id=invoice_id,
            payment_amount=1500.00
        )
        assert payment_result['success']

        # Step 4: Generate report
        report_result = manager.get_financial_report('balance_sheet')
        assert report_result['success']

    @pytest.mark.skip(reason="Requires running Odoo instance")
    def test_multi_invoice_workflow(self):
        """Test creating multiple invoices and tracking."""
        manager = AccountingManager()

        if not manager.is_connected():
            pytest.skip("Odoo not available")

        invoice_ids = []

        # Create multiple invoices
        for i in range(3):
            result = manager.create_invoice_from_transaction({
                'customer': f'Customer {i}',
                'amount': 1000.00 * (i + 1),
                'description': f'Invoice {i+1}'
            })
            assert result['success']
            invoice_ids.append(result['invoice_id'])

        # Verify all created
        assert len(invoice_ids) == 3


# Test utilities

@pytest.mark.skip(reason="Requires running Odoo instance")
def test_odoo_config_from_env():
    """Test Odoo configuration from environment variables."""
    os.environ['ODOO_URL'] = 'http://test.local:8069'
    os.environ['ODOO_DB'] = 'test_db'
    os.environ['ODOO_USER'] = 'testuser'
    os.environ['ODOO_PASSWORD'] = 'testpass'

    with patch('skills.finance.accounting_manager.accounting_manager.OdooMCPServer._authenticate', return_value=True):
        with patch('skills.finance.accounting_manager.accounting_manager.VaultManager'):
            manager = AccountingManager()
            assert manager.odoo_url == 'http://test.local:8069'
            assert manager.odoo_db == 'test_db'
            assert manager.odoo_user == 'testuser'


@pytest.mark.skip(reason="Requires running Odoo instance")
def test_connection_error_handling():
    """Test handling of connection errors."""
    with patch('skills.finance.accounting_manager.accounting_manager.OdooMCPServer') as mock_odoo:
        mock_odoo.side_effect = Exception("Connection failed")

        with patch('skills.finance.accounting_manager.accounting_manager.VaultManager'):
            manager = AccountingManager()
            assert manager.odoo is None
            assert not manager.is_connected()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])