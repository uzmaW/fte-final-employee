"""
Accounting Manager Skill - Manages Odoo accounting operations.

Integrates with Odoo Community Edition to:
- Create and manage invoices
- Post journal entries
- Reconcile payments
- Generate financial reports
- Sync financial data
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

from mcp_servers.odoo_server import OdooMCPServer
from utilities.vault_manager import VaultManager

logger = logging.getLogger(__name__)


class AccountingManager:
    """
    Manages accounting operations via Odoo MCP server.
    
    Provides high-level operations for:
    - Invoice creation and management
    - Journal entry posting
    - Payment reconciliation
    - Financial reporting
    - Account synchronization
    """
    
    # Account mapping for automatic categorization
    ACCOUNT_MAP = {
        'revenue': 4000,  # Sales revenue
        'cost_of_goods': 5000,  # Cost of goods sold
        'supplies': 6100,  # Office supplies
        'utilities': 6200,  # Utilities
        'rent': 6300,  # Rent expense
        'salaries': 6400,  # Salaries
        'advertising': 6500,  # Advertising
        'professional_fees': 6600,  # Professional services
        'equipment': 1500,  # Equipment assets
        'bank': 1010,  # Bank account
        'receivables': 1200,  # Accounts receivable
        'payables': 2100,  # Accounts payable
    }
    
    def __init__(self):
        """Initialize Accounting Manager with Odoo connection."""
        self.odoo_url = os.getenv('ODOO_URL', 'http://localhost:8069')
        self.odoo_db = os.getenv('ODOO_DB', 'odoo_db')
        self.odoo_user = os.getenv('ODOO_USER', 'admin')
        self.odoo_password = os.getenv('ODOO_PASSWORD', 'admin')
        
        # Initialize Odoo server
        try:
            self.odoo = OdooMCPServer(
                self.odoo_url,
                self.odoo_db,
                self.odoo_user,
                self.odoo_password
            )
            self.vault = VaultManager()
            logger.info("AccountingManager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize AccountingManager: {str(e)}")
            self.odoo = None
            self.vault = None
    
    def is_connected(self) -> bool:
        """Check if connected to Odoo."""
        return self.odoo and self.odoo.authenticated
    
    def create_invoice_from_transaction(
        self,
        transaction: Dict[str, Any],
        customer_name: str = None
    ) -> Dict[str, Any]:
        """
        Create an invoice in Odoo from a transaction record.
        
        Args:
            transaction: Transaction data
                {
                    'customer': 'Name',
                    'amount': 1500.00,
                    'description': 'Service description',
                    'date': '2026-02-08',
                    'reference': 'TXN-123'
                }
            customer_name: Override customer name
        
        Returns:
            Dict with invoice creation result
        """
        if not self.is_connected():
            return {'success': False, 'error': 'Not connected to Odoo'}
        
        try:
            # Get or create customer
            customer_name = customer_name or transaction.get('customer', 'Unknown')
            partner_id = self._get_or_create_partner(customer_name)
            
            if not partner_id:
                return {'success': False, 'error': f'Failed to create customer {customer_name}'}
            
            # Prepare invoice lines
            invoice_lines = [
                {
                    'product_id': 1,  # Generic service product
                    'quantity': 1,
                    'price_unit': transaction.get('amount', 0),
                    'description': transaction.get('description', 'Services rendered')
                }
            ]
            
            # Create invoice
            result = self.odoo.create_invoice(
                partner_id=partner_id,
                invoice_lines=invoice_lines,
                description=transaction.get('description', ''),
                reference=transaction.get('reference', '')
            )
            
            if result['success']:
                # Log in vault
                self._log_invoice(result['invoice_id'], transaction, partner_id)
                logger.info(f"Created invoice {result['invoice_id']} from transaction")
            
            return result
        except Exception as e:
            logger.error(f"Error creating invoice: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def post_expense(
        self,
        amount: float,
        category: str,
        description: str,
        date: str = None,
        vendor: str = ''
    ) -> Dict[str, Any]:
        """
        Post an expense as a journal entry in Odoo.
        
        Args:
            amount: Expense amount
            category: Expense category (supplies, utilities, rent, etc.)
            description: Expense description
            date: Expense date (YYYY-MM-DD)
            vendor: Vendor name
        
        Returns:
            Dict with journal entry creation result
        """
        if not self.is_connected():
            return {'success': False, 'error': 'Not connected to Odoo'}
        
        try:
            date = date or datetime.now().date().isoformat()
            
            # Get account ID for category
            expense_account_id = self.ACCOUNT_MAP.get(category, 6100)  # Default to supplies
            
            # Journal entry lines (debit expense, credit bank)
            lines = [
                {
                    'account_id': expense_account_id,
                    'debit': amount,
                    'credit': 0,
                    'name': description
                },
                {
                    'account_id': self.ACCOUNT_MAP['bank'],
                    'debit': 0,
                    'credit': amount,
                    'name': f'Payment: {description}'
                }
            ]
            
            # Post journal entry
            result = self.odoo.post_journal_entry(
                journal_id=2,  # General journal
                lines=lines,
                reference=f'{category.upper()}-{date}',
                description=f'{description} | {vendor}'
            )
            
            if result['success']:
                self._log_expense(result['entry_id'], amount, category, description)
                logger.info(f"Posted expense {category}: ${amount}")
            
            return result
        except Exception as e:
            logger.error(f"Error posting expense: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def post_revenue(
        self,
        amount: float,
        description: str,
        customer: str = '',
        date: str = None
    ) -> Dict[str, Any]:
        """
        Post revenue as a journal entry in Odoo.
        
        Args:
            amount: Revenue amount
            description: Revenue description
            customer: Customer name
            date: Transaction date
        
        Returns:
            Dict with journal entry creation result
        """
        if not self.is_connected():
            return {'success': False, 'error': 'Not connected to Odoo'}
        
        try:
            date = date or datetime.now().date().isoformat()
            
            # Journal entry lines (debit bank, credit revenue)
            lines = [
                {
                    'account_id': self.ACCOUNT_MAP['bank'],
                    'debit': amount,
                    'credit': 0,
                    'name': f'Revenue from {customer}'
                },
                {
                    'account_id': self.ACCOUNT_MAP['revenue'],
                    'debit': 0,
                    'credit': amount,
                    'name': description
                }
            ]
            
            # Post journal entry
            result = self.odoo.post_journal_entry(
                journal_id=2,  # General journal
                lines=lines,
                reference=f'REV-{date}',
                description=f'{description} | Customer: {customer}'
            )
            
            if result['success']:
                self._log_revenue(result['entry_id'], amount, description, customer)
                logger.info(f"Posted revenue: ${amount} from {customer}")
            
            return result
        except Exception as e:
            logger.error(f"Error posting revenue: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def reconcile_payment(
        self,
        invoice_id: int,
        payment_amount: float,
        payment_date: str = None,
        payment_method: str = 'bank'
    ) -> Dict[str, Any]:
        """
        Reconcile a payment against an invoice.
        
        Args:
            invoice_id: Odoo invoice ID
            payment_amount: Payment amount
            payment_date: Payment date
            payment_method: Payment method (bank, cash, card)
        
        Returns:
            Dict with payment result
        """
        if not self.is_connected():
            return {'success': False, 'error': 'Not connected to Odoo'}
        
        try:
            result = self.odoo.reconcile_payment(
                invoice_id=invoice_id,
                payment_amount=payment_amount,
                payment_date=payment_date,
                payment_method=payment_method
            )
            
            if result['success']:
                self._log_payment(result['payment_id'], invoice_id, payment_amount)
                logger.info(f"Reconciled payment {result['payment_id']} for invoice {invoice_id}")
            
            return result
        except Exception as e:
            logger.error(f"Error reconciling payment: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_financial_report(self, report_type: str = 'balance_sheet') -> Dict[str, Any]:
        """
        Get financial report from Odoo.
        
        Args:
            report_type: 'balance_sheet', 'income_statement', 'trial_balance'
        
        Returns:
            Dict with financial data
        """
        if not self.is_connected():
            return {'success': False, 'error': 'Not connected to Odoo'}
        
        try:
            result = self.odoo.get_financial_report(report_type)
            
            if result['success']:
                logger.info(f"Generated {report_type} report")
            
            return result
        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _get_or_create_partner(self, partner_name: str) -> Optional[int]:
        """Get existing partner or create new one."""
        try:
            # Try to find existing partner
            partners = self.odoo.models.execute_kw(
                self.odoo.db, self.odoo.uid, self.odoo.password,
                'res.partner', 'search',
                [[('name', '=', partner_name)]]
            )
            
            if partners:
                return partners[0]
            
            # Create new partner
            partner_id = self.odoo.models.execute_kw(
                self.odoo.db, self.odoo.uid, self.odoo.password,
                'res.partner', 'create',
                [{'name': partner_name}]
            )
            
            logger.info(f"Created new partner: {partner_name} (ID: {partner_id})")
            return partner_id
        except Exception as e:
            logger.error(f"Error getting/creating partner: {str(e)}")
            return None
    
    def _log_invoice(self, invoice_id: int, transaction: Dict, partner_id: int):
        """Log invoice creation to vault."""
        try:
            log_entry = {
                'type': 'invoice_created',
                'invoice_id': invoice_id,
                'partner_id': partner_id,
                'transaction': transaction,
                'timestamp': datetime.now().isoformat()
            }
            
            if self.vault:
                self.vault.append_to_file(
                    'AI_Employee_Vault/Logs/accounting.json',
                    json.dumps(log_entry)
                )
        except Exception as e:
            logger.warning(f"Failed to log invoice: {str(e)}")
    
    def _log_expense(self, entry_id: int, amount: float, category: str, description: str):
        """Log expense posting to vault."""
        try:
            log_entry = {
                'type': 'expense_posted',
                'entry_id': entry_id,
                'amount': amount,
                'category': category,
                'description': description,
                'timestamp': datetime.now().isoformat()
            }
            
            if self.vault:
                self.vault.append_to_file(
                    'AI_Employee_Vault/Logs/accounting.json',
                    json.dumps(log_entry)
                )
        except Exception as e:
            logger.warning(f"Failed to log expense: {str(e)}")
    
    def _log_revenue(self, entry_id: int, amount: float, description: str, customer: str):
        """Log revenue posting to vault."""
        try:
            log_entry = {
                'type': 'revenue_posted',
                'entry_id': entry_id,
                'amount': amount,
                'description': description,
                'customer': customer,
                'timestamp': datetime.now().isoformat()
            }
            
            if self.vault:
                self.vault.append_to_file(
                    'AI_Employee_Vault/Logs/accounting.json',
                    json.dumps(log_entry)
                )
        except Exception as e:
            logger.warning(f"Failed to log revenue: {str(e)}")
    
    def _log_payment(self, payment_id: int, invoice_id: int, amount: float):
        """Log payment reconciliation to vault."""
        try:
            log_entry = {
                'type': 'payment_reconciled',
                'payment_id': payment_id,
                'invoice_id': invoice_id,
                'amount': amount,
                'timestamp': datetime.now().isoformat()
            }
            
            if self.vault:
                self.vault.append_to_file(
                    'AI_Employee_Vault/Logs/accounting.json',
                    json.dumps(log_entry)
                )
        except Exception as e:
            logger.warning(f"Failed to log payment: {str(e)}")
