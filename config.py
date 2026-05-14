"""
Configuration management for AI Employee system.
Loads settings from environment variables with sensible defaults.
"""

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from pathlib import Path
import os
from typing import Optional

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Paths
    vault_path: Path = Field(default=Path("AI_Employee_Vault"), description="Path to Obsidian vault")
    skills_path: Path = Field(default=Path(".claude/skills"), description="Path to skills directory")
    logs_dir: Path = Field(default=Path("AI_Employee_Vault/Logs"), description="Path to logs directory")
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)")
    log_to_file: bool = Field(default=True, description="Whether to log to file")
    
    # Timezone
    timezone: str = Field(default="UTC", description="System timezone")
    
    # Gmail API
    gmail_client_id: Optional[str] = Field(default=None, description="Gmail OAuth client ID")
    gmail_client_secret: Optional[str] = Field(default=None, description="Gmail OAuth client secret")
    gmail_refresh_token: Optional[str] = Field(default=None, description="Gmail refresh token")
    gmail_poll_interval: int = Field(default=300, description="Gmail poll interval in seconds")
    
    # WhatsApp (Twilio)
    twilio_account_sid: Optional[str] = Field(default=None, description="Twilio account SID")
    twilio_auth_token: Optional[str] = Field(default=None, description="Twilio auth token")
    twilio_phone_number: Optional[str] = Field(default=None, description="Twilio phone number")
    whatsapp_poll_interval: int = Field(default=60, description="WhatsApp poll interval in seconds")
    
    # Stripe
    stripe_api_key: Optional[str] = Field(default=None, description="Stripe API key")
    stripe_signing_secret: Optional[str] = Field(default=None, description="Stripe webhook signing secret")
    
    # System
    watchdog_check_interval: int = Field(default=30, description="Watchdog check interval in seconds")
    max_retries: int = Field(default=3, description="Max retries for transient errors")
    retry_backoff: float = Field(default=1.0, description="Backoff multiplier for retries")
    
    # Feature flags
    enable_gmail_watcher: bool = Field(default=False, description="Enable Gmail watcher")
    enable_whatsapp_watcher: bool = Field(default=False, description="Enable WhatsApp watcher")
    enable_orchestrator: bool = Field(default=False, description="Enable orchestrator")
    enable_watchdog: bool = Field(default=False, description="Enable watchdog")
    
    # Testing
    test_mode: bool = Field(default=False, description="Whether running in test mode")

    # Odoo
    odoo_url: str = Field(default="http://localhost:8069", description="Odoo instance URL")
    odoo_db: str = Field(default="odoo_db", description="Odoo database name")
    odoo_user: str = Field(default="admin", description="Odoo username")
    odoo_password: str = Field(default="admin", description="Odoo password")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

def get_settings() -> Settings:
    """Get application settings singleton."""
    return Settings()

# Create vault directories if they don't exist
def ensure_vault_structure():
    """Create vault directory structure if it doesn't exist."""
    settings = get_settings()
    vault_path = settings.vault_path
    
    required_dirs = [
        vault_path / "Needs_Action",
        vault_path / "In_Progress",
        vault_path / "In_Progress/claude",
        vault_path / "Plans",
        vault_path / "Done",
        vault_path / "Pending_Approval",
        vault_path / "Approved",
        vault_path / "Rejected",
        vault_path / "Logs",
        vault_path / "Accounting",
        vault_path / ".obsidian",
    ]
    
    for dir_path in required_dirs:
        dir_path.mkdir(parents=True, exist_ok=True)

if __name__ == "__main__":
    settings = get_settings()
    print("Configuration loaded:")
    print(f"  Vault Path: {settings.vault_path}")
    print(f"  Skills Path: {settings.skills_path}")
    print(f"  Log Level: {settings.log_level}")
    print(f"  Timezone: {settings.timezone}")
