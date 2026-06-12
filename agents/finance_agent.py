"""
Finance Agent - Handles payment processing, invoice tracking, reconciliation.
"""

import logging
import re
from typing import Dict, List, Any, Optional
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.base_agent_http import BaseAgentHTTP

logger = logging.getLogger(__name__)


class FinanceAgent(BaseAgentHTTP):
    """
    Finance agent for payment processing and financial transactions.

    Responsibilities:
    - Process approved payments
    - Track payment status
    - Reconcile invoices
    - Generate transaction reports
    """

    def __init__(self, mcp_url: str = "http://localhost:8000", poll_interval: int = 60):
        super().__init__(
            name="finance-agent",
            mcp_url=mcp_url,
            poll_interval=poll_interval
        )

    def poll(self) -> List[Dict[str, Any]]:
        """
        Poll vault for financial tasks.

        Looks for:
        - PAYMENT_* files in Needs_Action/
        - INVOICE_* files in Needs_Action/
        """
        items = []

        try:
            needs_action = self.vault_manager.vault_path / "Needs_Action"
            if not needs_action.exists():
                return items

            # Find payment-related tasks
            for task_file in needs_action.glob("PAYMENT_*.md"):
                items.append({
                    'id': task_file.stem,
                    'type': 'payment',
                    'file': task_file
                })

            # Find invoice-related tasks
            for task_file in needs_action.glob("INVOICE_*.md"):
                items.append({
                    'id': task_file.stem,
                    'type': 'invoice',
                    'file': task_file
                })

            logger.debug(f"Found {len(items)} financial tasks")
            return items

        except Exception as e:
            logger.error(f"Error polling for financial tasks: {e}")
            return []

    def process_item(self, item: Dict[str, Any]) -> Optional[str]:
        """Process payment or invoice task."""
        try:
            task_file = item['file']
            task_type = item.get('type', 'unknown')

            if task_type == 'payment':
                return self._process_payment(task_file)
            elif task_type == 'invoice':
                return self._process_invoice(task_file)
            else:
                logger.warning(f"Unknown task type: {task_type}")
                return None

        except Exception as e:
            logger.error(f"Error processing financial task: {e}")
            return None

    def _process_payment(self, task_file: Path) -> Optional[str]:
        """Process a payment task."""
        try:
            content = task_file.read_text()

            # Extract payment details using regex
            amount_match = re.search(r'\$?([\d,]+\.?\d{0,2})', content)
            recipient_match = re.search(r'recipient:?\s*(.+?)(?:\n|$)', content, re.IGNORECASE)
            approval_match = re.search(r'approval_id:?\s*(\w+)', content, re.IGNORECASE)

            if not (amount_match and recipient_match):
                logger.warning(f"Could not extract payment details from {task_file.name}")
                return None

            amount = float(amount_match.group(1).replace(',', ''))
            recipient = recipient_match.group(1).strip()
            approval_id = approval_match.group(1) if approval_match else None

            logger.info(f"Processing payment: ${amount} to {recipient}")

            # Call MCP payment server
            result = self._mcp_call(
                "POST",
                "/api/payment/process",
                amount=amount,
                recipient=recipient,
                description=f"Payment from {task_file.stem}",
                approval_id=approval_id
            )

            if result.get('status') == 'success':
                # Move task to Done
                self.vault_manager.move_task_to_done(
                    task_file,
                    result=f"payment_processed_{result.get('transaction_id', '')}"
                )
                logger.info(f"✅ Payment processed: {result.get('transaction_id')}")
                return str(task_file)
            else:
                logger.error(f"Payment failed: {result.get('error')}")
                return None

        except Exception as e:
            logger.error(f"Error processing payment: {e}")
            return None

    def _process_invoice(self, task_file: Path) -> Optional[str]:
        """Process an invoice task."""
        try:
            content = task_file.read_text()

            # Extract invoice details
            partner_match = re.search(r'partner_id:?\s*(\d+)', content, re.IGNORECASE)
            amount_match = re.search(r'amount:?\s*\$?([\d,]+\.?\d{0,2})', content, re.IGNORECASE)

            if not (partner_match and amount_match):
                logger.warning(f"Could not extract invoice details from {task_file.name}")
                return None

            partner_id = int(partner_match.group(1))
            amount = float(amount_match.group(1).replace(',', ''))

            logger.info(f"Creating invoice for partner {partner_id}: ${amount}")

            # Call Odoo MCP to create invoice
            result = self._mcp_call(
                "POST",
                "/api/odoo/invoice/create",
                partner_id=partner_id,
                invoice_lines=[{
                    'product_id': 1,
                    'quantity': 1,
                    'price_unit': amount,
                    'description': task_file.stem
                }]
            )

            if result.get('success'):
                self.vault_manager.move_task_to_done(
                    task_file,
                    result=f"invoice_created_{result.get('invoice_id', '')}"
                )
                logger.info(f"✅ Invoice created: {result.get('invoice_id')}")
                return str(task_file)
            else:
                logger.error(f"Invoice creation failed: {result.get('error')}")
                return None

        except Exception as e:
            logger.error(f"Error processing invoice: {e}")
            return None


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)

    agent = FinanceAgent()
    agent.run_once()