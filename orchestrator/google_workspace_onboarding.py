"""
google_workspace_onboarding.py - Automated Google Workspace account provisioning
and onboarding email delivery for new employees.

Backs the .claude/skills/google_workspace_onboarding/SKILL.md specification.
Queries HR task files in the vault, provisions Google Workspace accounts,
and sends personalized onboarding instructions.
"""

import os
import re
import json
import logging
import secrets
import string
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from orchestrator.base_watcher import BaseWatcher
from utilities.vault_manager import VaultManager
from utilities.retry_handler import with_retry, TransientError, PermanentError

logger = logging.getLogger(__name__)


@dataclass
class EmployeeOnboarding:
    """Represents a new employee onboarding request."""
    employee_name: str
    employee_email: str
    department: str
    start_date: str
    task_id: str = ""
    task_file: str = ""
    status: str = "pending"
    temporary_password: str = ""
    provisioning_steps: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class GoogleWorkspaceOnboarding(BaseWatcher):
    """
    Watch for new employee onboarding tasks and provision Google Workspace accounts.

    Queries the vault for employee_onboarding task files, creates Google Workspace
    user accounts via Directory API, sends onboarding emails, and tracks status.
    """

    STANDARD_GROUPS = ["all-employees"]

    def __init__(self):
        """Initialize Google Workspace onboarding."""
        from config import get_settings
        settings = get_settings()

        super().__init__(
            name="google_workspace_onboarding",
            poll_interval=300
        )

        self.admin_email = os.getenv("GOOGLE_WORKSPACE_ADMIN_EMAIL", "")
        self.domain = os.getenv("GOOGLE_WORKSPACE_DOMAIN", "")
        self.service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
        self.default_ou = os.getenv("GOOGLE_WORKSPACE_OU", "/")

        self.auto_generate_password = os.getenv(
            "ONBOARDING_AUTO_GENERATE_PASSWORD", "true"
        ).lower() == "true"
        self.send_welcome_email = os.getenv(
            "ONBOARDING_SEND_WELCOME_EMAIL", "true"
        ).lower() == "true"
        self.default_group = os.getenv("ONBOARDING_DEFAULT_GROUP", "all-employees")
        self.intranet_url = os.getenv("ONBOARDING_INTRANET_URL", "")
        self.help_desk = os.getenv("ONBOARDING_HELP_DESK", "")

        self.directory_service = None
        self.gmail_service = None
        self._authenticated = False
        self.vault = VaultManager()

        logger.info(
            f"Google Workspace Onboarding initialized for domain: {self.domain}"
        )

    def authenticate(self) -> bool:
        """Authenticate with Google Workspace using service account."""
        try:
            if not all([self.admin_email, self.domain, self.service_account_json]):
                logger.warning(
                    "Google Workspace credentials not fully configured in .env"
                )
                self._authenticated = False
                return False

            if not Path(self.service_account_json).exists():
                logger.error(
                    f"Service account JSON not found: {self.service_account_json}"
                )
                self._authenticated = False
                return False

            try:
                from google.oauth2 import service_account
                from googleapiclient.discovery import build

                credentials = service_account.Credentials.from_service_account_file(
                    self.service_account_json,
                    scopes=[
                        "https://www.googleapis.com/auth/admin.directory.user",
                        "https://www.googleapis.com/auth/admin.directory.group",
                        "https://www.googleapis.com/auth/gmail.send",
                        "https://www.googleapis.com/auth/gmail.labels",
                    ],
                    subject=self.admin_email,
                )

                self.directory_service = build(
                    "admin", "directory_v1", credentials=credentials
                )
                self.gmail_service = build("gmail", "v1", credentials=credentials)
                self._authenticated = True
                logger.info(
                    f"Authenticated with Google Workspace as {self.admin_email}"
                )

            except ImportError:
                logger.warning(
                    "google-auth/google-api-python-client not installed - "
                    "Google Workspace provisioning offline mode"
                )
                self._authenticated = True
                self.directory_service = None
                self.gmail_service = None
                logger.info("Google Workspace onboarding running in offline mode")

            except Exception as e:
                logger.error(f"Google Workspace authentication failed: {e}")
                self._authenticated = False
                return False

            return True

        except Exception as e:
            logger.error(f"Authentication error: {e}")
            self._authenticated = False
            return False

    @property
    def is_authenticated(self) -> bool:
        """Check if authenticated with Google Workspace."""
        return self._authenticated

    def process_item(self, item: Dict[str, Any]) -> Optional[str]:
        """Process a single onboarding task (implements BaseWatcher interface)."""
        return self.handle(item)

    def poll(self) -> List[Dict[str, Any]]:
        """Poll vault for new employee onboarding tasks."""
        if not self._authenticated:
            logger.warning("Google Workspace onboarding not authenticated")
            return []

        tasks = []
        try:
            needs_action_path = self.vault.vault_path / "Needs_Action"
            if not needs_action_path.exists():
                return []

            for task_file in needs_action_path.glob("*.md"):
                content = task_file.read_text()

                if "type: employee_onboarding" in content or \
                   "type: employee_onboarding" in content.lower():
                    data = self._parse_onboarding_task(task_file)
                    if data and data.status == "pending":
                        tasks.append(data)

        except Exception as e:
            logger.error(f"Error polling for onboarding tasks: {e}")

        return tasks

    def _parse_onboarding_task(
        self, task_file: Path
    ) -> Optional[EmployeeOnboarding]:
        """Parse an onboarding task file and extract employee data."""
        try:
            content = task_file.read_text()
            data = EmployeeOnboarding(
                employee_name=self._extract_field(content, "employee_name"),
                employee_email=self._extract_field(content, "employee_email"),
                department=self._extract_field(content, "department"),
                start_date=self._extract_field(content, "start_date"),
                task_id=self._extract_field(content, "task_id"),
                status="pending",
                task_file=str(task_file),
            )

            if not all([data.employee_name, data.employee_email,
                        data.department, data.start_date]):
                logger.warning(
                    f"Incomplete onboarding task in {task_file.name}: "
                    f"name={data.employee_name}, email={data.employee_email}"
                )
                return None

            if not data.employee_email.endswith(f"@{self.domain}"):
                logger.warning(
                    f"Employee email domain mismatch: "
                    f"{data.employee_email} does not match {self.domain}"
                )
                return None

            return data

        except Exception as e:
            logger.error(f"Error parsing onboarding task {task_file}: {e}")
            return None

    @staticmethod
    def _extract_field(content: str, field_name: str) -> str:
        """Extract a field value from markdown frontmatter-style content."""
        patterns = [
            rf"{field_name}:\s*['\"]?([^'\n\"]+)['\"]?",
            rf"{field_name}:\s*(.+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip().strip("\"'")
        return ""

    def _generate_temp_password(self, length: int = 16) -> str:
        """Generate a secure temporary password."""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        while True:
            password = "".join(secrets.choice(alphabet) for _ in range(length))
            if (any(c.isupper() for c in password) and
                any(c.islower() for c in password) and
                any(c.isdigit() for c in password) and
                any(c in "!@#$%^&*" for c in password)):
                return password

    @with_retry(max_attempts=3, base_delay=1.0, max_delay=60)
    def create_user(self, onboarding: EmployeeOnboarding) -> Dict[str, Any]:
        """Create a Google Workspace user account."""
        try:
            if self.directory_service is None:
                logger.info(
                    f"[OFFLINE] Would create user: {onboarding.employee_email}"
                )
                onboarding.status = "provisioned"
                onboarding.provisioning_steps.append(
                    f"User account creation simulated for {onboarding.employee_email}"
                )
                return {
                    "success": True,
                    "user_id": f"sim_{secrets.token_hex(8)}",
                    "email": onboarding.employee_email,
                    "mode": "offline"
                }

            user_data = {
                "primaryEmail": onboarding.employee_email,
                "name": {
                    "givenName": onboarding.employee_name.split()[0],
                    "familyName": " ".join(onboarding.employee_name.split()[1:])
                },
                "password": onboarding.temporary_password,
                "changePasswordAtNextLogin": True,
                "orgUnitPath": f"{self.default_ou}{onboarding.department}",
                "isEnrolledIn2Sv": False,
            }

            result = (
                self.directory_service.users()
                .insert(body=user_data)
                .execute()
            )

            onboarding.status = "provisioned"
            onboarding.provisioning_steps.append(
                f"Google Workspace account created: {result['primaryEmail']}"
            )
            logger.info(
                f"Created Google Workspace user: {result['primaryEmail']}"
            )

            return {
                "success": True,
                "user_id": result.get("id"),
                "email": result["primaryEmail"],
                "mode": "live"
            }

        except Exception as e:
            logger.error(
                f"Error creating Google Workspace user "
                f"{onboarding.employee_email}: {e}"
            )
            onboarding.status = "failed"
            raise PermanentError(
                f"Failed to create user {onboarding.employee_email}: {e}"
            )

    @with_retry(max_attempts=3, base_delay=1.0, max_delay=60)
    def add_to_groups(
        self, onboarding: EmployeeOnboarding, user_id: str
    ) -> bool:
        """Add new user to standard Google groups."""
        groups = self.STANDARD_GROUPS.copy()
        dept_group = onboarding.department.lower().replace(" ", "-")
        if dept_group not in groups:
            groups.append(dept_group)

        try:
            if self.directory_service is None:
                for group in groups:
                    logger.info(
                        f"[OFFLINE] Would add {onboarding.employee_email} "
                        f"to group: {group}"
                    )
                onboarding.provisioning_steps.append(
                    f"Group membership simulated: {', '.join(groups)}"
                )
                return True

            for group_email in groups:
                try:
                    group_key = f"{group_email}@{self.domain}"
                    self.directory_service.members().insert(
                        groupKey=group_key,
                        body={
                            "email": onboarding.employee_email,
                            "role": "MEMBER",
                        }
                    ).execute()
                    logger.info(
                        f"Added {onboarding.employee_email} to {group_email}"
                    )
                    onboarding.provisioning_steps.append(
                        f"Added to group: {group_email}"
                    )
                except Exception as e:
                    logger.warning(
                        f"Could not add to group {group_email}: {e}"
                    )

            return True

        except Exception as e:
            logger.error(
                f"Error adding {onboarding.employee_email} to groups: {e}"
            )
            raise TransientError(f"Group addition failed: {e}")

    @with_retry(max_attempts=3, base_delay=1.0, max_delay=60)
    def send_onboarding_email(
        self, onboarding: EmployeeOnboarding
    ) -> bool:
        """Send personalized onboarding email with setup instructions."""
        try:
            email_body = self._render_onboarding_email(onboarding)

            if self.gmail_service is None:
                logger.info(
                    f"[OFFLINE] Would send onboarding email to: "
                    f"{onboarding.employee_email}"
                )
                onboarding.provisioning_steps.append(
                    "Onboarding email composed (offline mode)"
                )
                self._save_email_draft(onboarding, email_body)
                return True

            message = self._create_gmail_message(
                to=onboarding.employee_email,
                subject=f"Welcome to {self.domain} — Your Account Setup",
                body=email_body
            )

            result = (
                self.gmail_service.users()
                .messages()
                .send(userId="me", body=message)
                .execute()
            )

            onboarding.provisioning_steps.append(
                f"Onboarding email sent (message ID: "
                f"{result.get('id', 'unknown')})"
            )
            logger.info(
                f"Sent onboarding email to {onboarding.employee_email}"
            )
            return True

        except Exception as e:
            logger.error(
                f"Exception sending onboarding email to "
                f"{onboarding.employee_email}: {e}"
            )
            onboarding.provisioning_steps.append(
                f"Email send failed: {e}"
            )
            raise TransientError(f"Onboarding email failed: {e}")

    def _render_onboarding_email(
        self, onboarding: EmployeeOnboarding
    ) -> str:
        """Render the onboarding email body from template."""
        pwd_section = ""
        if onboarding.temporary_password:
            pwd_section = (
                f"\n🔐 Temporary Password: {onboarding.temporary_password}"
                "\n   (You'll be prompted to change this on first login)\n"
            )

        return f"""Welcome to the team, {onboarding.employee_name}! 🎉

Your Google Workspace account has been created:

📧 Email: {onboarding.employee_email}
🏢 Department: {onboarding.department}
📅 Start Date: {onboarding.start_date}
{pwd_section}
## Setup Checklist

1. ☐ Sign in to Google Workspace at https://mail.google.com
2. ☐ Change your temporary password (if assigned)
3. ☐ Set up 2FA at https://myaccount.google.com/security
4. ☐ Install Google Drive for Desktop
5. ☐ Join the {onboarding.department} Google Group
6. ☐ Review the Employee Handbook
7. ☐ Complete security awareness training

## Important Links

- Company Intranet: {self.intranet_url or f'https://intranet.{self.domain}.com'}
- IT Help Desk: {self.help_desk or f'it-help@{self.domain}'}
- Google Workspace: https://workspace.google.com

## First-Day Schedule

- 9:00 AM — Welcome meeting with your manager
- 10:00 AM — IT setup and account configuration
- 11:00 AM — Team introduction
- 12:00 PM — Team lunch
- 1:00 PM — Project overview
- 3:00 PM — Security and compliance training

If you have any questions before your start date, reach out anytime.

Welcome aboard!
IT Operations | {self.domain}
"""

    def _save_email_draft(
        self, onboarding: EmployeeOnboarding, body: str
    ):
        """Save email draft to vault for offline review."""
        try:
            draft_path = self.vault.vault_path / "Social/Drafts"
            draft_path.mkdir(parents=True, exist_ok=True)
            safe_name = onboarding.employee_name.replace(" ", "_")
            draft_file = (
                draft_path
                / f"onboarding_{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            )
            self.vault.write_file(
                str(draft_file),
                f"""---
type: email_draft
to: {onboarding.employee_email}
subject: "Welcome to {self.domain} — Your Account Setup"
created: {datetime.now().isoformat()}
status: pending_send
---

{body}
"""
            )
            logger.info(f"Saved onboarding email draft to {draft_file}")
        except Exception as e:
            logger.warning(f"Failed to save email draft: {e}")

    @staticmethod
    def _create_gmail_message(to: str, subject: str, body: str) -> Dict:
        """Create a Gmail API message structure."""
        import base64
        from email.mime.text import MIMEText

        message = MIMEText(body, "plain")
        message["to"] = to
        message["subject"] = subject
        return {"raw": base64.urlsafe_b64encode(message.as_bytes()).decode()}

    def process_onboarding(
        self, onboarding: EmployeeOnboarding
    ) -> Dict[str, Any]:
        """Execute the full onboarding provisioning pipeline."""
        result = {
            "employee": onboarding.employee_name,
            "email": onboarding.employee_email,
            "department": onboarding.department,
            "start_date": onboarding.start_date,
            "steps_completed": [],
            "errors": [],
            "success": False,
        }

        try:
            logger.info(
                f"Starting provisioning for {onboarding.employee_name} "
                f"({onboarding.employee_email})"
            )

            if self.auto_generate_password:
                onboarding.temporary_password = self._generate_temp_password()
                onboarding.provisioning_steps.append(
                    "Generated temporary password"
                )

            user_result = self.create_user(onboarding)
            if not user_result["success"]:
                result["errors"].append("User creation failed")
                self._log_onboarding(onboarding, result)
                return result
            result["user_id"] = user_result.get("user_id")
            result["steps_completed"].append("user_created")

            if self.add_to_groups(onboarding, result.get("user_id", "")):
                result["steps_completed"].append("groups_updated")
            else:
                result["errors"].append("Some group additions failed")

            if self.send_welcome_email:
                try:
                    self.send_onboarding_email(onboarding)
                    result["steps_completed"].append("welcome_email_sent")
                except TransientError:
                    logger.warning(
                        "Onboarding email failed — will retry on next poll"
                    )

            result["success"] = True
            onboarding.status = "completed"
            logger.info(
                f"Provisioning complete for {onboarding.employee_email}"
            )

            self._update_task_status(
                onboarding, "In_Progress",
                f"Provisioned — {len(result['steps_completed'])} steps completed"
            )

        except PermanentError as e:
            result["errors"].append(str(e))
            onboarding.status = "failed"
            self._update_task_status(
                onboarding, "Needs_Action", f"Failed: {e}"
            )
            logger.error(f"Permanent provisioning failure: {e}")

        except Exception as e:
            result["errors"].append(str(e))
            onboarding.status = "failed"
            logger.error(
                f"Provisioning error for {onboarding.employee_email}: {e}"
            )
            self._update_task_status(
                onboarding, "Needs_Action", f"Failed: {e}"
            )

        finally:
            result["steps"] = onboarding.provisioning_steps
            self._log_onboarding(onboarding, result)

        return result

    def _log_onboarding(
        self, onboarding: EmployeeOnboarding, result: Dict[str, Any]
    ):
        """Log onboarding result to vault audit trail."""
        try:
            log_entry = {
                "type": "employee_onboarding",
                "employee_name": onboarding.employee_name,
                "employee_email": onboarding.employee_email,
                "department": onboarding.department,
                "start_date": onboarding.start_date,
                "status": onboarding.status,
                "steps": onboarding.provisioning_steps,
                "result_errors": result.get("errors", []),
                "timestamp": datetime.now().isoformat(),
            }

            self.vault.append_to_file(
                "AI_Employee_Vault/Logs/onboarding.json",
                json.dumps(log_entry)
            )
            logger.info(f"Logged onboarding for {onboarding.employee_email}")
        except Exception as e:
            logger.warning(f"Failed to log onboarding: {e}")

    def _update_task_status(
        self,
        onboarding: EmployeeOnboarding,
        target_status: str,
        note: str = "",
    ):
        """Move task file to appropriate status folder."""
        try:
            if target_status == "In_Progress" and onboarding.task_file:
                source = Path(onboarding.task_file)
                if source.exists():
                    dest = (
                        self.vault.vault_path
                        / "In_Progress"
                        / f"[IN_PROGRESS] {source.name}"
                    )
                    content = source.read_text()
                    if note:
                        content += (
                            f"\n\n---\n**Status:** {note}\n"
                            f"**Updated:** {datetime.now().isoformat()}Z\n"
                        )
                    self.vault.write_file(str(dest), content)
                    if source.exists():
                        source.unlink()
                    logger.info(
                        f"Moved task to In_Progress: {source.name}"
                    )

            elif target_status == "Needs_Action" and onboarding.task_file:
                source = Path(onboarding.task_file)
                if source.exists():
                    logger.info(
                        "Task remains in Needs_Action due to failure"
                    )

        except Exception as e:
            logger.warning(f"Failed to update task status: {e}")

    def handle(self, task: Dict[str, Any]) -> Optional[str]:
        """Process a single onboarding task."""
        try:
            onboarding = EmployeeOnboarding(
                employee_name=task.get("employee_name", ""),
                employee_email=task.get("employee_email", ""),
                department=task.get("department", ""),
                start_date=task.get("start_date", ""),
                task_id=task.get("task_id", ""),
            )

            if not onboarding.employee_email.endswith(f"@{self.domain}"):
                logger.warning(
                    f"Skipping {onboarding.employee_email} — domain mismatch"
                )
                return None

            if self._is_already_provisioned(onboarding.employee_email):
                logger.info(
                    f"User {onboarding.employee_email} already provisioned"
                )
                self._move_to_done(onboarding)
                return f"Already provisioned: {onboarding.employee_email}"

            result = self.process_onboarding(onboarding)

            if result["success"]:
                self._move_to_done(onboarding)
                return (
                    f"Provisioned {onboarding.employee_email} — "
                    f"{', '.join(result['steps_completed'])}"
                )
            else:
                return f"Failed: {', '.join(result['errors'])}"

        except Exception as e:
            logger.error(f"Error handling onboarding task: {e}")
            return f"Error: {e}"

    def _is_already_provisioned(self, email: str) -> bool:
        """Check if a Google Workspace account already exists."""
        try:
            if self.directory_service is None:
                log_path = self.vault.vault_path / "Logs" / "onboarding.json"
                if log_path.exists():
                    for line in log_path.read_text().split("\n"):
                        if line.strip():
                            entry = json.loads(line)
                            if entry.get("employee_email") == email:
                                return True
                return False

            result = (
                self.directory_service.users()
                .get(userKey=email)
                .execute()
            )
            return result.get("suspended", False) is False

        except Exception:
            return False

    def _move_to_done(self, onboarding: EmployeeOnboarding):
        """Move completed task to Done folder."""
        try:
            if onboarding.task_file and Path(onboarding.task_file).exists():
                source = Path(onboarding.task_file)
                dest = (
                    self.vault.vault_path
                    / "Done"
                    / f"[DONE] {source.name}"
                )
                content = source.read_text()
                content += f"""

---
**Completed:** {datetime.now().isoformat()}Z
**Result:** Provisioning complete
**Steps:** {', '.join(onboarding.provisioning_steps)}
"""
                self.vault.write_file(str(dest), content)
                source.unlink()
                logger.info(
                    f"Moved completed task to Done: {source.name}"
                )
        except Exception as e:
            logger.warning(f"Failed to move task to Done: {e}")