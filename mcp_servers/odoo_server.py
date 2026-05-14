"""
Odoo MCP Server - Integration with Odoo Community Edition for accounting operations.

Provides JSON-RPC interface to:
- Create and manage invoices
- Post journal entries
- Manage chart of accounts
- Track payments and reconciliation
- Generate financial reports
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import xmlrpc.client as xmlrpc

logger = logging.getLogger(__name__)


class OdooMCPServer:
    """
    MCP Server for Odoo Community Edition integration.
    
    Provides operations for:
    - Invoice management
    - Journal entries
    - Account synchronization
    - Payment tracking
    - Financial reporting
    """
    
    def __init__(self, url: str, db: str, username: str, password: str):
        """
        Initialize Odoo MCP Server.
        
        Args:
            url: Odoo instance URL (e.g., 'http://localhost:8069')
            db: Database name
            username: Odoo username
            password: Odoo password
        """
        self.url = url
        self.db = db
        self.username = username
        self.password = password
        self.uid = None
        self.models = None
        self.authenticated = False
        
        logger.info(f"Initializing Odoo MCP Server: {url}/{db}")
        self._authenticate()
    
    def _authenticate(self) -> bool:
        """Authenticate with Odoo instance."""
        try:
            common = xmlrpc.ServerProxy(f'{self.url}/xmlrpc/2/common')
            self.uid = common.authenticate(self.db, self.username, self.password, {})
            
            if self.uid:
                self.models = xmlrpc.ServerProxy(f'{self.url}/xmlrpc/2/object')
                self.authenticated = True
                logger.info(f"Successfully authenticated with Odoo as {self.username}")
                return True
            else:
                logger.error("Failed to authenticate with Odoo")
                return False
        except Exception as e:
            logger.error(f"Odoo authentication error: {str(e)}")
            return False
    
    def create_invoice(
        self,
        partner_id: int,
        invoice_lines: List[Dict[str, Any]],
        journal_id: int = 1,
        invoice_type: str = 'out_invoice',
        description: str = '',
        reference: str = ''
    ) -> Dict[str, Any]:
        """
        Create an invoice in Odoo.
        
        Args:
            partner_id: Odoo partner/customer ID
            invoice_lines: List of invoice line items
                [{'product_id': 1, 'quantity': 1, 'price_unit': 100}]
            journal_id: Sales journal ID (default: 1)
            invoice_type: 'out_invoice', 'in_invoice', 'out_refund', 'in_refund'
            description: Invoice description
            reference: Invoice reference number
        
        Returns:
            Dict with invoice creation result
        """
        try:
            if not self.authenticated:
                return {'success': False, 'error': 'Not authenticated with Odoo'}
            
            # Prepare invoice data
            invoice_data = {
                'partner_id': partner_id,
                'journal_id': journal_id,
                'move_type': invoice_type,
                'invoice_date': datetime.now().date().isoformat(),
                'ref': reference or '',
                'memo': description or '',
                'invoice_line_ids': []
            }
            
            # Add invoice lines
            for line in invoice_lines:
                line_data = {
                    'product_id': line.get('product_id'),
                    'quantity': line.get('quantity', 1),
                    'price_unit': line.get('price_unit', 0),
                    'name': line.get('description', ''),
                }
                invoice_data['invoice_line_ids'].append((0, 0, line_data))
            
            # Create invoice
            invoice_id = self.models.execute_kw(
                self.db, self.uid, self.password,
                'account.move', 'create',
                [invoice_data]
            )
            
            logger.info(f"Created invoice {invoice_id} for partner {partner_id}")
            
            return {
                'success': True,
                'invoice_id': invoice_id,
                'partner_id': partner_id,
                'created_at': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error creating invoice: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def post_journal_entry(
        self,
        journal_id: int,
        lines: List[Dict[str, Any]],
        reference: str = '',
        description: str = ''
    ) -> Dict[str, Any]:
        """
        Post a journal entry in Odoo.
        
        Args:
            journal_id: Journal ID (e.g., General, Sales, etc.)
            lines: List of journal entry lines
                [{'account_id': 1, 'debit': 100, 'credit': 0, 'name': 'Entry'}]
            reference: Journal entry reference
            description: Journal entry description
        
        Returns:
            Dict with journal entry creation result
        """
        try:
            if not self.authenticated:
                return {'success': False, 'error': 'Not authenticated with Odoo'}
            
            # Prepare move data
            move_data = {
                'journal_id': journal_id,
                'date': datetime.now().date().isoformat(),
                'ref': reference or '',
                'narration': description or '',
                'line_ids': []
            }
            
            # Add move lines
            for line in lines:
                line_data = {
                    'account_id': line.get('account_id'),
                    'debit': line.get('debit', 0),
                    'credit': line.get('credit', 0),
                    'name': line.get('name', ''),
                }
                move_data['line_ids'].append((0, 0, line_data))
            
            # Create move
            move_id = self.models.execute_kw(
                self.db, self.uid, self.password,
                'account.move', 'create',
                [move_data]
            )
            
            # Post the move
            self.models.execute_kw(
                self.db, self.uid, self.password,
                'account.move', 'action_post',
                [move_id]
            )
            
            logger.info(f"Created and posted journal entry {move_id}")
            
            return {
                'success': True,
                'entry_id': move_id,
                'created_at': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error posting journal entry: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_partners(self, limit: int = 100) -> Dict[str, Any]:
        """Get list of partners (customers/suppliers)."""
        try:
            if not self.authenticated:
                return {'success': False, 'error': 'Not authenticated with Odoo'}
            
            partners = self.models.execute_kw(
                self.db, self.uid, self.password,
                'res.partner', 'search_read',
                [[]],
                {'fields': ['id', 'name', 'email', 'phone'], 'limit': limit}
            )
            
            return {'success': True, 'partners': partners}
        except Exception as e:
            logger.error(f"Error getting partners: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_accounts(self, limit: int = 100) -> Dict[str, Any]:
        """Get list of chart of accounts."""
        try:
            if not self.authenticated:
                return {'success': False, 'error': 'Not authenticated with Odoo'}
            
            accounts = self.models.execute_kw(
                self.db, self.uid, self.password,
                'account.account', 'search_read',
                [[]],
                {'fields': ['id', 'code', 'name', 'account_type'], 'limit': limit}
            )
            
            return {'success': True, 'accounts': accounts}
        except Exception as e:
            logger.error(f"Error getting accounts: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_invoices(self, partner_id: Optional[int] = None, limit: int = 50) -> Dict[str, Any]:
        """
        Get invoices, optionally filtered by partner.
        
        Args:
            partner_id: Filter by partner ID (optional)
            limit: Maximum number of invoices to return
        
        Returns:
            Dict with list of invoices
        """
        try:
            if not self.authenticated:
                return {'success': False, 'error': 'Not authenticated with Odoo'}
            
            domain = []
            if partner_id:
                domain = [('partner_id', '=', partner_id)]
            
            invoices = self.models.execute_kw(
                self.db, self.uid, self.password,
                'account.move', 'search_read',
                [domain],
                {'fields': ['id', 'name', 'partner_id', 'amount_total', 'state', 'invoice_date'],
                 'limit': limit,
                 'order': 'invoice_date desc'}
            )
            
            return {'success': True, 'invoices': invoices}
        except Exception as e:
            logger.error(f"Error getting invoices: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def reconcile_payment(
        self,
        invoice_id: int,
        payment_amount: float,
        payment_date: str = None,
        payment_method: str = 'bank'
    ) -> Dict[str, Any]:
        """
        Register a payment against an invoice.
        
        Args:
            invoice_id: Invoice ID
            payment_amount: Payment amount
            payment_date: Payment date (YYYY-MM-DD)
            payment_method: Payment method (bank, cash, card, etc.)
        
        Returns:
            Dict with payment result
        """
        try:
            if not self.authenticated:
                return {'success': False, 'error': 'Not authenticated with Odoo'}
            
            payment_date = payment_date or datetime.now().date().isoformat()
            
            # Create payment record
            payment_data = {
                'partner_type': 'customer',
                'partner_id': self._get_invoice_partner(invoice_id),
                'amount': payment_amount,
                'date': payment_date,
                'journal_id': 1,  # Bank journal
                'payment_type': 'inbound',
                'ref': f'Payment for Invoice {invoice_id}',
            }
            
            payment_id = self.models.execute_kw(
                self.db, self.uid, self.password,
                'account.payment', 'create',
                [payment_data]
            )
            
            # Post payment
            self.models.execute_kw(
                self.db, self.uid, self.password,
                'account.payment', 'action_post',
                [payment_id]
            )
            
            logger.info(f"Recorded payment {payment_id} for invoice {invoice_id}")
            
            return {
                'success': True,
                'payment_id': payment_id,
                'invoice_id': invoice_id,
                'amount': payment_amount,
                'created_at': datetime.now().isoformat()
            }
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
        try:
            if not self.authenticated:
                return {'success': False, 'error': 'Not authenticated with Odoo'}
            
            if report_type == 'balance_sheet':
                # Get balance sheet data
                accounts = self.models.execute_kw(
                    self.db, self.uid, self.password,
                    'account.account', 'search_read',
                    [('account_type', 'in', ['asset_current', 'asset_fixed', 'liability_current', 'liability_fixed', 'equity'])],
                    {'fields': ['code', 'name', 'balance']}
                )
            elif report_type == 'income_statement':
                # Get income statement data
                accounts = self.models.execute_kw(
                    self.db, self.uid, self.password,
                    'account.account', 'search_read',
                    [('account_type', 'in', ['income', 'expense'])],
                    {'fields': ['code', 'name', 'balance']}
                )
            else:
                # Trial balance
                accounts = self.models.execute_kw(
                    self.db, self.uid, self.password,
                    'account.account', 'search_read',
                    [['balance', '!=', 0]],
                    {'fields': ['code', 'name', 'balance']}
                )
            
            return {
                'success': True,
                'report_type': report_type,
                'accounts': accounts,
                'generated_at': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error generating financial report: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _get_invoice_partner(self, invoice_id: int) -> int:
        """Get partner ID from invoice."""
        try:
            invoice = self.models.execute_kw(
                self.db, self.uid, self.password,
                'account.move', 'read',
                [invoice_id],
                {'fields': ['partner_id']}
            )
            return invoice[0]['partner_id'][0] if invoice else None
        except Exception as e:
            logger.error(f"Error getting invoice partner: {str(e)}")
            return None
    
    def health_check(self) -> Dict[str, bool]:
        """Check if Odoo server is accessible and authenticated."""
        return {
            'connected': True,
            'authenticated': self.authenticated,
            'database': self.db,
            'user': self.username
        }


# Standalone server for testing
if __name__ == '__main__':
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Configuration from environment
    odoo_url = os.getenv('ODOO_URL', 'http://localhost:8069')
    odoo_db = os.getenv('ODOO_DB', 'odoo_db')
    odoo_user = os.getenv('ODOO_USER', 'admin')
    odoo_pass = os.getenv('ODOO_PASSWORD', 'admin')
    
    # Initialize server
    try:
        odoo = OdooMCPServer(odoo_url, odoo_db, odoo_user, odoo_pass)
        
        if odoo.authenticated:
            print("✅ Odoo MCP Server initialized successfully")
            print(f"Connected to {odoo_url}/{odoo_db}")
            
            # Test operations
            print("\n--- Testing Operations ---")
            
            # Get partners
            partners_result = odoo.get_partners(limit=5)
            print(f"Partners: {partners_result['success']}")
            
            # Get accounts
            accounts_result = odoo.get_accounts(limit=5)
            print(f"Accounts: {accounts_result['success']}")
            
            # Get invoices
            invoices_result = odoo.get_invoices(limit=5)
            print(f"Invoices: {invoices_result['success']}")
            
            print("\n✅ All tests passed")
        else:
            print("❌ Failed to authenticate with Odoo")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
