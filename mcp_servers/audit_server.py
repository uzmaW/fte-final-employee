"""
Audit MCP Server - Financial analysis and anomaly detection.
"""

import logging
from typing import Dict, List, Any
from datetime import datetime
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_settings
from utilities.vault_manager import VaultManager
from utilities.financial_auditor import FinancialAuditor

logger = logging.getLogger(__name__)


class AuditServer:
    """Financial audit operations."""

    def __init__(self):
        self.settings = get_settings()
        self.vault_manager = VaultManager()
        self.auditor = FinancialAuditor()
        logger.info("✅ Audit Server initialized")

    def analyze_transactions(self, transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze transactions for anomalies and categorize."""
        try:
            categorized = self.auditor.categorize_transactions(transactions)
            anomalies = self.auditor.detect_anomalies(categorized)
            metrics = self.auditor.calculate_metrics(categorized)

            return {
                'success': True,
                'categorized_count': len(categorized),
                'anomalies_detected': len(anomalies),
                'anomalies': anomalies[:10],  # Return top 10
                'metrics': metrics,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error analyzing transactions: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def generate_ceo_briefing(self, period_start: str, period_end: str) -> Dict[str, Any]:
        """Generate CEO briefing for period."""
        try:
            briefing = self.auditor.generate_ceo_briefing(period_start, period_end)

            return {
                'success': True,
                'briefing': briefing,
                'period_start': period_start,
                'period_end': period_end,
                'generated_at': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error generating briefing: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def find_cost_savings(self, transactions: List[Dict]) -> Dict[str, Any]:
        """Find cost-saving opportunities."""
        try:
            savings = self.auditor._find_cost_savings(transactions)

            return {
                'success': True,
                'opportunities': savings.get('cost_optimization', []),
                'total_potential_savings': savings.get('total_potential_savings', 0),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error finding cost savings: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }


if __name__ == "__main__":
    audit = AuditServer()
    print("✅ Audit server ready")