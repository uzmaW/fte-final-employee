"""
FastAPI server for AI Employee watchers and webhooks.
Handles Gmail polling, WhatsApp webhooks, and filesystem monitoring.
"""

import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import asyncio
from datetime import datetime
from typing import Dict, Any

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_settings
from watchers.gmail_watcher import GmailWatcher
from watchers.whatsapp_watcher import WhatsAppWatcher
from watchers.filesystem_watcher import FilesystemWatcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="AI Employee",
    description="Digital FTE with email, messaging, and task management",
    version="1.0.0"
)

# Settings
settings = get_settings()

# Initialize watchers
gmail_watcher = GmailWatcher() if settings.enable_gmail_watcher else None
whatsapp_watcher = WhatsAppWatcher(app) if settings.enable_whatsapp_watcher else None
filesystem_watcher = FilesystemWatcher() if settings.enable_orchestrator else None

# Background tasks
async def polling_loop():
    """Background task for polling watchers."""
    if not gmail_watcher:
        return
    
    logger.info("Starting polling loop")
    
    try:
        while True:
            # Run Gmail watcher
            count = gmail_watcher.run_once()
            if count > 0:
                logger.info(f"Processed {count} emails")
            
            # Sleep before next poll
            await asyncio.sleep(10)
    
    except asyncio.CancelledError:
        logger.info("Polling loop cancelled")
    except Exception as e:
        logger.error(f"Polling loop error: {e}", exc_info=True)


# FastAPI routes

@app.on_event("startup")
async def startup_event():
    """Handle startup."""
    logger.info("AI Employee server starting")
    
    # Start filesystem watcher
    if filesystem_watcher:
        logger.info("Starting filesystem watcher")
        filesystem_watcher.start_monitoring()
    
    # Start polling loop if Gmail enabled
    if gmail_watcher:
        logger.info("Starting Gmail polling loop")
        asyncio.create_task(polling_loop())


@app.on_event("shutdown")
async def shutdown_event():
    """Handle shutdown."""
    logger.info("AI Employee server shutting down")
    
    # Stop filesystem watcher
    if filesystem_watcher:
        logger.info("Stopping filesystem watcher")
        filesystem_watcher.stop_monitoring()


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "AI Employee",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "watchers": {}
    }
    
    if gmail_watcher:
        status["watchers"]["gmail"] = gmail_watcher.get_status()
    
    if whatsapp_watcher:
        status["watchers"]["whatsapp"] = whatsapp_watcher.get_status()
    
    if filesystem_watcher:
        status["watchers"]["filesystem"] = filesystem_watcher.get_status()
    
    return status


@app.get("/status")
async def get_status():
    """Get detailed system status."""
    status = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "watchers": {},
        "settings": {
            "gmail_enabled": settings.enable_gmail_watcher,
            "whatsapp_enabled": settings.enable_whatsapp_watcher,
            "filesystem_enabled": settings.enable_orchestrator,
        }
    }
    
    if gmail_watcher:
        status["watchers"]["gmail"] = gmail_watcher.get_status()
    
    if whatsapp_watcher:
        status["watchers"]["whatsapp"] = whatsapp_watcher.get_status()
        status["watchers"]["whatsapp"]["queued_messages"] = len(whatsapp_watcher.message_queue)
    
    if filesystem_watcher:
        status["watchers"]["filesystem"] = filesystem_watcher.get_status()
        pending = filesystem_watcher.get_pending_approvals()
        approved = filesystem_watcher.get_approved_actions()
        status["watchers"]["filesystem"]["pending_approvals"] = pending["count"]
        status["watchers"]["filesystem"]["approved_actions"] = approved["count"]
    
    return status


@app.post("/webhooks/whatsapp")
async def whatsapp_webhook(request: Request):
    """
    WhatsApp webhook endpoint for Twilio.
    
    This endpoint receives incoming WhatsApp messages from Twilio
    and queues them for processing.
    """
    if not whatsapp_watcher:
        raise HTTPException(status_code=503, detail="WhatsApp watcher disabled")
    
    try:
        # Validate signature
        if not await whatsapp_watcher.validate_twilio_request(request):
            logger.warning("Invalid Twilio signature for WhatsApp webhook")
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Parse message
        message_data = await whatsapp_watcher.parse_webhook_data(request)
        
        # Queue for processing
        whatsapp_watcher.message_queue.append(message_data)
        logger.info(f"Queued WhatsApp message from {message_data.get('from')}")
        
        return {"status": "ok", "message_sid": message_data.get('message_sid')}
    
    except Exception as e:
        logger.error(f"WhatsApp webhook error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/watchers/gmail/status")
async def gmail_status():
    """Get Gmail watcher status."""
    if not gmail_watcher:
        raise HTTPException(status_code=503, detail="Gmail watcher disabled")
    
    return gmail_watcher.get_status()


@app.get("/watchers/whatsapp/status")
async def whatsapp_status():
    """Get WhatsApp watcher status."""
    if not whatsapp_watcher:
        raise HTTPException(status_code=503, detail="WhatsApp watcher disabled")
    
    status = whatsapp_watcher.get_status()
    status["queued_messages"] = len(whatsapp_watcher.message_queue)
    return status


@app.get("/watchers/filesystem/status")
async def filesystem_status():
    """Get filesystem watcher status."""
    if not filesystem_watcher:
        raise HTTPException(status_code=503, detail="Filesystem watcher disabled")
    
    status = filesystem_watcher.get_status()
    pending = filesystem_watcher.get_pending_approvals()
    approved = filesystem_watcher.get_approved_actions()
    
    status["pending_approvals"] = pending["count"]
    status["approved_actions"] = approved["count"]
    
    return status


@app.post("/watchers/gmail/poll")
async def gmail_poll():
    """Manually trigger Gmail polling."""
    if not gmail_watcher:
        raise HTTPException(status_code=503, detail="Gmail watcher disabled")
    
    try:
        count = gmail_watcher.run_once()
        return {
            "status": "ok",
            "emails_processed": count,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        logger.error(f"Error polling Gmail: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/watchers/whatsapp/process")
async def whatsapp_process():
    """Manually trigger WhatsApp message processing."""
    if not whatsapp_watcher:
        raise HTTPException(status_code=503, detail="WhatsApp watcher disabled")
    
    try:
        if not whatsapp_watcher.message_queue:
            return {
                "status": "ok",
                "messages_processed": 0,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        
        count = whatsapp_watcher.run_once()
        return {
            "status": "ok",
            "messages_processed": count,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        logger.error(f"Error processing WhatsApp messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/watchers/filesystem/pending")
async def filesystem_pending():
    """Get pending approvals."""
    if not filesystem_watcher:
        raise HTTPException(status_code=503, detail="Filesystem watcher disabled")
    
    return filesystem_watcher.get_pending_approvals()


@app.get("/watchers/filesystem/approved")
async def filesystem_approved():
    """Get approved actions waiting for execution."""
    if not filesystem_watcher:
        raise HTTPException(status_code=503, detail="Filesystem watcher disabled")
    
    return filesystem_watcher.get_approved_actions()


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting AI Employee server")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
