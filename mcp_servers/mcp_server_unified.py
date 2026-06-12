"""
Unified MCP Server exposing all integrations via HTTP/REST.
Designed for distributed deployment and horizontal scaling.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_servers.payment_server import PaymentServer
from mcp_servers.email_server import EmailServer
from mcp_servers.social_server import SocialServer
from mcp_servers.browser_server import BrowserServer
from mcp_servers.audit_server import AuditServer
from mcp_servers.odoo_server import OdooMCPServer
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Global server instances
servers: Dict[str, Any] = {
    'payment': None,
    'email': None,
    'social': None,
    'browser': None,
    'audit': None,
    'odoo': None
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize servers on startup."""
    logger.info("🚀 Starting MCP Server...")

    # Initialize all servers
    try:
        servers['payment'] = PaymentServer()
        servers['email'] = EmailServer()
        servers['social'] = SocialServer()
        servers['browser'] = BrowserServer()
        servers['audit'] = AuditServer()

        # Odoo is lazy-loaded (optional)
        try:
            servers['odoo'] = OdooMCPServer(
                url=settings.odoo_url,
                db=settings.odoo_db,
                username=settings.odoo_user,
                password=settings.odoo_password
            )
            logger.info("✅ Odoo server initialized")
        except Exception as e:
            logger.warning(f"⚠️ Odoo server failed: {e}")
            servers['odoo'] = None

        logger.info("✅ All MCP servers initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize servers: {e}")
        raise

    yield  # App runs here

    logger.info("🛑 Shutting down MCP Server...")


app = FastAPI(title="AI Employee MCP Server", version="1.0", lifespan=lifespan)

# CORS middleware for agents
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# HEALTH & STATUS ENDPOINTS
# ============================================================================

@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Check health of all MCP servers."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "servers": {
            "payment": "ready" if servers['payment'] else "error",
            "email": "ready" if servers['email'] else "error",
            "social": "ready" if servers['social'] else "error",
            "browser": "ready" if servers['browser'] else "error",
            "audit": "ready" if servers['audit'] else "error",
            "odoo": "connected" if servers['odoo'] and servers['odoo'].authenticated else "not_initialized",
        }
    }


@app.get("/status")
async def status() -> Dict[str, Any]:
    """Get detailed status of all services."""
    status_dict = {
        "timestamp": datetime.utcnow().isoformat(),
        "services": {}
    }

    if servers['odoo']:
        try:
            status_dict['services']['odoo'] = servers['odoo'].health_check()
        except Exception as e:
            status_dict['services']['odoo'] = {"status": "error", "error": str(e)}

    return status_dict


# ============================================================================
# PAYMENT ENDPOINTS (/api/payment/*)
# ============================================================================

@app.post("/api/payment/process")
async def process_payment(
    amount: float,
    recipient: str,
    description: str = "",
    approval_id: Optional[str] = None
) -> Dict[str, Any]:
    """Process a payment with optional approval check."""
    if not servers['payment']:
        raise HTTPException(status_code=503, detail="Payment server not available")

    return servers['payment'].process_payment(
        amount=amount,
        recipient=recipient,
        description=description,
        approval_id=approval_id
    )


@app.post("/api/payment/refund")
async def refund_payment(
    transaction_id: str,
    reason: str = "Refund requested"
) -> Dict[str, Any]:
    """Refund a payment."""
    if not servers['payment']:
        raise HTTPException(status_code=503, detail="Payment server not available")

    return servers['payment'].refund_payment(transaction_id, reason)


@app.get("/api/payment/status/{transaction_id}")
async def get_transaction_status(transaction_id: str) -> Dict[str, Any]:
    """Get payment transaction status."""
    if not servers['payment']:
        raise HTTPException(status_code=503, detail="Payment server not available")

    return servers['payment'].get_transaction_status(transaction_id)


# ============================================================================
# EMAIL ENDPOINTS (/api/email/*)
# ============================================================================

@app.post("/api/email/send")
async def send_email(
    to: str,
    subject: str,
    body: str,
    html: bool = False,
    cc: Optional[list] = None,
    bcc: Optional[list] = None
) -> Dict[str, Any]:
    """Send an email."""
    if not servers['email']:
        raise HTTPException(status_code=503, detail="Email server not available")

    return servers['email'].send_email(
        to=to,
        subject=subject,
        body=body,
        html=html,
        cc=cc,
        bcc=bcc
    )


@app.post("/api/email/send-reply")
async def send_reply(
    to: str,
    subject: str,
    body: str
) -> Dict[str, Any]:
    """Send a reply email."""
    if not servers['email']:
        raise HTTPException(status_code=503, detail="Email server not available")

    return servers['email'].send_reply(to=to, subject=subject, body=body)


@app.post("/api/email/notify")
async def send_notification(
    to: str,
    title: str,
    message: str
) -> Dict[str, Any]:
    """Send a notification email."""
    if not servers['email']:
        raise HTTPException(status_code=503, detail="Email server not available")

    return servers['email'].send_notification(to=to, title=title, message=message)


# ============================================================================
# SOCIAL MEDIA ENDPOINTS (/api/social/*)
# ============================================================================

@app.post("/api/social/post-twitter")
async def post_twitter(text: str, media_urls: Optional[list] = None) -> Dict[str, Any]:
    """Post a tweet."""
    if not servers['social']:
        raise HTTPException(status_code=503, detail="Social server not available")

    return servers['social'].post_to_twitter(text=text, media_urls=media_urls)


@app.post("/api/social/post-linkedin")
async def post_linkedin(
    text: str,
    article_url: Optional[str] = None,
    image_url: Optional[str] = None
) -> Dict[str, Any]:
    """Post to LinkedIn."""
    if not servers['social']:
        raise HTTPException(status_code=503, detail="Social server not available")

    return servers['social'].post_to_linkedin(
        text=text,
        article_url=article_url,
        image_url=image_url
    )


@app.post("/api/social/schedule-post")
async def schedule_social_post(
    platform: str,
    text: str,
    scheduled_time: str
) -> Dict[str, Any]:
    """Schedule a social media post."""
    if not servers['social']:
        raise HTTPException(status_code=503, detail="Social server not available")

    return servers['social'].schedule_post(
        platform=platform,
        text=text,
        scheduled_time=scheduled_time
    )


@app.get("/api/social/engagement/{post_id}")
async def get_engagement(post_id: str) -> Dict[str, Any]:
    """Get engagement metrics for a post."""
    if not servers['social']:
        raise HTTPException(status_code=503, detail="Social server not available")

    return servers['social'].get_engagement(post_id)


# ============================================================================
# ODOO ENDPOINTS (/api/odoo/*)
# ============================================================================

@app.post("/api/odoo/invoice/create")
async def create_odoo_invoice(
    partner_id: int,
    invoice_lines: list,
    journal_id: int = 1,
    reference: str = ""
) -> Dict[str, Any]:
    """Create an invoice in Odoo."""
    if not servers['odoo']:
        raise HTTPException(status_code=503, detail="Odoo server not available")

    return servers['odoo'].create_invoice(
        partner_id=partner_id,
        invoice_lines=invoice_lines,
        journal_id=journal_id,
        reference=reference
    )


@app.get("/api/odoo/invoices")
async def get_odoo_invoices(partner_id: Optional[int] = None, limit: int = 50) -> Dict[str, Any]:
    """Get invoices from Odoo."""
    if not servers['odoo']:
        raise HTTPException(status_code=503, detail="Odoo server not available")

    return servers['odoo'].get_invoices(partner_id=partner_id, limit=limit)


@app.get("/api/odoo/partners")
async def get_odoo_partners(limit: int = 100) -> Dict[str, Any]:
    """Get partners from Odoo."""
    if not servers['odoo']:
        raise HTTPException(status_code=503, detail="Odoo server not available")

    return servers['odoo'].get_partners(limit=limit)


@app.get("/api/odoo/accounts")
async def get_odoo_accounts(limit: int = 100) -> Dict[str, Any]:
    """Get chart of accounts from Odoo."""
    if not servers['odoo']:
        raise HTTPException(status_code=503, detail="Odoo server not available")

    return servers['odoo'].get_accounts(limit=limit)


@app.post("/api/odoo/journal-entry")
async def post_odoo_journal_entry(
    journal_id: int,
    lines: list,
    reference: str = ""
) -> Dict[str, Any]:
    """Post a journal entry in Odoo."""
    if not servers['odoo']:
        raise HTTPException(status_code=503, detail="Odoo server not available")

    return servers['odoo'].post_journal_entry(
        journal_id=journal_id,
        lines=lines,
        reference=reference
    )


@app.post("/api/odoo/payment/reconcile")
async def reconcile_odoo_payment(
    invoice_id: int,
    payment_amount: float,
    payment_date: Optional[str] = None
) -> Dict[str, Any]:
    """Reconcile a payment in Odoo."""
    if not servers['odoo']:
        raise HTTPException(status_code=503, detail="Odoo server not available")

    return servers['odoo'].reconcile_payment(
        invoice_id=invoice_id,
        payment_amount=payment_amount,
        payment_date=payment_date
    )


@app.get("/api/odoo/report/{report_type}")
async def get_odoo_report(report_type: str) -> Dict[str, Any]:
    """Get financial report from Odoo."""
    if not servers['odoo']:
        raise HTTPException(status_code=503, detail="Odoo server not available")

    return servers['odoo'].get_financial_report(report_type=report_type)


# ============================================================================
# AUDIT ENDPOINTS (/api/audit/*)
# ============================================================================

@app.post("/api/audit/analyze-transactions")
async def analyze_transactions(transactions: list) -> Dict[str, Any]:
    """Analyze transactions for anomalies."""
    if not servers['audit']:
        raise HTTPException(status_code=503, detail="Audit server not available")

    return servers['audit'].analyze_transactions(transactions)


@app.post("/api/audit/briefing")
async def generate_audit_briefing(
    period_start: str,
    period_end: str
) -> Dict[str, Any]:
    """Generate financial audit briefing."""
    if not servers['audit']:
        raise HTTPException(status_code=503, detail="Audit server not available")

    return servers['audit'].generate_ceo_briefing(period_start, period_end)


@app.post("/api/audit/cost-savings")
async def find_cost_savings(transactions: list) -> Dict[str, Any]:
    """Find cost-saving opportunities."""
    if not servers['audit']:
        raise HTTPException(status_code=503, detail="Audit server not available")

    return servers['audit'].find_cost_savings(transactions)


# ============================================================================
# BROWSER ENDPOINTS (/api/browser/*)
# ============================================================================

@app.post("/api/browser/navigate")
async def browser_navigate(url: str) -> Dict[str, Any]:
    """Navigate to URL."""
    if not servers['browser']:
        raise HTTPException(status_code=503, detail="Browser server not available")

    return await servers['browser'].navigate_to(url)


@app.post("/api/browser/fill-form")
async def browser_fill_form(
    fields: Dict[str, str],
    submit_button: Optional[str] = None
) -> Dict[str, Any]:
    """Fill form on current page."""
    if not servers['browser']:
        raise HTTPException(status_code=503, detail="Browser server not available")

    return await servers['browser'].fill_form(fields, submit_button)


@app.post("/api/browser/click")
async def browser_click(selector: str) -> Dict[str, Any]:
    """Click element on page."""
    if not servers['browser']:
        raise HTTPException(status_code=503, detail="Browser server not available")

    return await servers['browser'].click_element(selector)


@app.post("/api/browser/screenshot")
async def browser_screenshot(path: str) -> Dict[str, Any]:
    """Take screenshot."""
    if not servers['browser']:
        raise HTTPException(status_code=503, detail="Browser server not available")

    return await servers['browser'].take_screenshot(path)


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return {
        "error": str(exc),
        "timestamp": datetime.utcnow().isoformat(),
        "path": request.url.path
    }


if __name__ == "__main__":
    import uvicorn

    logger.info("=" * 60)
    logger.info("AI Employee MCP Server Starting")
    logger.info("=" * 60)

    uvicorn.run(
        "mcp_servers.mcp_server_unified:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )