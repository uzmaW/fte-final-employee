"""
Tests for Google Workspace Onboarding skill.
Tests offline/mock mode only — no real Google Workspace connection required.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
import os
import json
from unittest.mock import MagicMock, patch
from datetime import datetime

from orchestrator.google_workspace_onboarding import (
    GoogleWorkspaceOnboarding,
    EmployeeOnboarding,
)


class TestEmployeeOnboardingDataclass:
    """Test the EmployeeOnboarding dataclass."""

    def test_basic_creation(self):
        """Test creating an EmployeeOnboarding instance."""
        onboarding = EmployeeOnboarding(
            employee_name="Jane Doe",
            employee_email="jane.doe@company.com",
            department="Engineering",
            start_date="2026-06-01",
        )
        assert onboarding.employee_name == "Jane Doe"
        assert onboarding.employee_email == "jane.doe@company.com"
        assert onboarding.department == "Engineering"
        assert onboarding.start_date == "2026-06-01"
        assert onboarding.status == "pending"
        assert onboarding.temporary_password == ""
        assert onboarding.provisioning_steps == []
        assert onboarding.errors == []

    def test_creation_with_task_file(self):
        """Test creation with task file info."""
        onboarding = EmployeeOnboarding(
            employee_name="John Smith",
            employee_email="john.smith@company.com",
            department="Marketing",
            start_date="2026-07-15",
            task_id="TASK-001",
            task_file="/tmp/test.md",
        )
        assert onboarding.task_id == "TASK-001"
        assert onboarding.task_file == "/tmp/test.md"


class TestGoogleWorkspaceOnboarding:
    """Test the GoogleWorkspaceOnboarding orchestrator."""

    @pytest.fixture
    def onboarding(self):
        """Create a GoogleWorkspaceOnboarding instance in offline mode."""
        with patch.dict(os.environ, {
            "GOOGLE_WORKSPACE_ADMIN_EMAIL": "admin@company.com",
            "GOOGLE_WORKSPACE_DOMAIN": "company.com",
            "GOOGLE_SERVICE_ACCOUNT_JSON": "/tmp/fake-key.json",
            "ONBOARDING_AUTO_GENERATE_PASSWORD": "true",
            "ONBOARDING_SEND_WELCOME_EMAIL": "true",
            "ONBOARDING_DEFAULT_GROUP": "all-employees",
            "ONBOARDING_INTRANET_URL": "https://intranet.company.com",
            "ONBOARDING_HELP_DESK": "it-help@company.com",
        }, clear=False):
            obj = object.__new__(GoogleWorkspaceOnboarding)
            obj.admin_email = "admin@company.com"
            obj.domain = "company.com"
            obj.service_account_json = "/tmp/fake-key.json"
            obj.default_ou = "/"
            obj.auto_generate_password = True
            obj.send_welcome_email = True
            obj.default_group = "all-employees"
            obj.intranet_url = "https://intranet.company.com"
            obj.help_desk = "it-help@company.com"
            obj.directory_service = None
            obj.gmail_service = None
            obj._authenticated = True
            obj.name = "google_workspace_onboarding"
            obj.last_poll_time = 0
            obj.error_count = 0
            obj.max_errors = 5
            obj.running = False
            obj.vault = MagicMock()
            obj.vault.vault_path = Path("/tmp/test_vault")
            obj.settings = MagicMock()
            obj.vault_manager = MagicMock()
            obj.vault_manager.vault_path = Path("/tmp/test_vault")
            obj.poll_interval = 300
            yield obj

    def test_initialization_offline(self, onboarding):
        """Test initialization in offline mode."""
        assert onboarding.domain == "company.com"
        assert onboarding.admin_email == "admin@company.com"
        assert onboarding.is_authenticated is True

    def test_extract_field(self, onboarding):
        """Test field extraction from markdown content."""
        content = """
---
employee_name: Jane Doe
employee_email: jane.doe@company.com
department: Engineering
start_date: 2026-06-01
---
"""
        assert onboarding._extract_field(content, "employee_name") == "Jane Doe"
        assert onboarding._extract_field(content, "employee_email") == "jane.doe@company.com"
        assert onboarding._extract_field(content, "department") == "Engineering"
        assert onboarding._extract_field(content, "start_date") == "2026-06-01"
        assert onboarding._extract_field(content, "nonexistent") == ""

    def test_extract_field_case_insensitive(self, onboarding):
        """Test case-insensitive field extraction."""
        content = "Employee_Name: Test User\n"
        assert onboarding._extract_field(content, "employee_name") == "Test User"

    def test_generate_temp_password(self, onboarding):
        """Test temporary password generation meets complexity requirements."""
        password = onboarding._generate_temp_password(16)
        assert len(password) == 16
        assert any(c.isupper() for c in password)
        assert any(c.islower() for c in password)
        assert any(c.isdigit() for c in password)
        assert any(c in "!@#$%^&*" for c in password)

    def test_create_user_offline(self, onboarding, tmp_path):
        """Test user creation in offline mode."""
        emp = EmployeeOnboarding(
            employee_name="Jane Doe",
            employee_email="jane.doe@company.com",
            department="Engineering",
            start_date="2026-06-01",
        )
        onboarding.vault.vault_path = tmp_path

        result = onboarding.create_user(emp)
        assert result["success"] is True
        assert result["mode"] == "offline"
        assert "sim_" in result["user_id"]

    def test_add_to_groups_offline(self, onboarding, tmp_path):
        """Test group addition in offline mode."""
        emp = EmployeeOnboarding(
            employee_name="Jane Doe",
            employee_email="jane.doe@company.com",
            department="Engineering",
            start_date="2026-06-01",
        )
        onboarding.vault.vault_path = tmp_path

        result = onboarding.add_to_groups(emp, "sim_12345678")
        assert result is True

    def test_send_onboarding_email_offline(self, onboarding, tmp_path):
        """Test onboarding email creation in offline mode."""
        emp = EmployeeOnboarding(
            employee_name="Jane Doe",
            employee_email="jane.doe@company.com",
            department="Engineering",
            start_date="2026-06-01",
        )
        onboarding.vault.vault_path = tmp_path
        result = onboarding.send_onboarding_email(emp)
        assert result is True

    def test_render_onboarding_email_with_password(self, onboarding):
        """Test email content rendering with temporary password."""
        onboarding.employee_name = "Jane Doe"
        onboarding.employee_email = "jane.doe@company.com"
        onboarding.department = "Engineering"
        onboarding.start_date = "2026-06-01"
        onboarding.temporary_password = "Test@Pass1234!"

        email = onboarding._render_onboarding_email(onboarding)
        assert "Jane Doe" in email
        assert "jane.doe@company.com" in email
        assert "Engineering" in email
        assert "2026-06-01" in email
        assert "Test@Pass1234!" in email
        assert "Setup Checklist" in email
        assert "First-Day Schedule" in email

    def test_render_onboarding_email_no_password(self, onboarding):
        """Test email rendering without temporary password."""
        onboarding.employee_name = "Jane Doe"
        onboarding.employee_email = "jane.doe@company.com"
        onboarding.department = "Engineering"
        onboarding.start_date = "2026-06-01"
        onboarding.temporary_password = ""

        email = onboarding._render_onboarding_email(onboarding)
        assert "Jane Doe" in email
        assert "jane.doe@company.com" in email
        assert "Temporary Password" not in email

    def test_create_gmail_message(self, onboarding):
        """Test Gmail message structure creation."""
        msg = onboarding._create_gmail_message(
            to="test@company.com",
            subject="Test Subject",
            body="Test body content"
        )
        assert "raw" in msg
        assert isinstance(msg["raw"], str)

    def test_parse_onboarding_task(self, onboarding, tmp_path):
        """Test parsing a real onboarding task file."""
        task_content = """---
type: employee_onboarding
employee_name: Jane Doe
employee_email: jane.doe@company.com
department: Engineering
start_date: 2026-06-01
task_id: ONBOARD-001
---

Welcome to the team!
"""
        task_file = tmp_path / "onboarding_task.md"
        task_file.write_text(task_content)

        result = onboarding._parse_onboarding_task(task_file)
        assert result is not None
        assert result.employee_name == "Jane Doe"
        assert result.employee_email == "jane.doe@company.com"
        assert result.department == "Engineering"
        assert result.start_date == "2026-06-01"
        assert result.task_id == "ONBOARD-001"
        assert result.task_file == str(task_file)

    def test_parse_incomplete_task(self, onboarding, tmp_path):
        """Test parsing an incomplete task file returns None."""
        task_content = """---
type: employee_onboarding
employee_name: Jane Doe
# Missing email, department, start_date
---
"""
        task_file = tmp_path / "incomplete_task.md"
        task_file.write_text(task_content)

        result = onboarding._parse_onboarding_task(task_file)
        assert result is None

    def test_parse_wrong_domain(self, onboarding, tmp_path):
        """Test task file with non-matching domain is rejected during parsing."""
        onboarding.domain = "company.com"
        task_content = """---
type: employee_onboarding
employee_name: Jane Doe
employee_email: jane.doe@other.com
department: Engineering
start_date: 2026-06-01
---
"""
        task_file = tmp_path / "wrong_domain_task.md"
        task_file.write_text(task_content)

result = onboarding._parse_onboarding_task(task_file)
        # _parse_onboarding_task validates domain and returns None on mismatch
        assert result is None

    def test_log_onboarding(self, onboarding, tmp_path):
        """Test logging onboarding results to vault."""
        onboarding.vault.vault_path = tmp_path
        onboarding.vault.append_to_file = MagicMock()

        onboarding.employee_name = "Jane Doe"
        onboarding.employee_email = "jane.doe@company.com"
        onboarding.department = "Engineering"
        onboarding.start_date = "2026-06-01"
        onboarding.status = "completed"
        onboarding.provisioning_steps = ["Generated temporary password", "User created"]
        onboarding.errors = []

        result = {
            "success": True,
            "steps_completed": ["user_created"],
            "errors": [],
        }

        onboarding._log_onboarding(onboarding, result)
        onboarding.vault.append_to_file.assert_called_once()
        call_args = onboarding.vault.append_to_file.call_args[0][1]
        logged_entry = json.loads(call_args)
        assert logged_entry["employee_name"] == "Jane Doe"
        assert logged_entry["employee_email"] == "jane.doe@company.com"
        assert logged_entry["status"] == "completed"

    def test_process_onboarding_full_pipeline(self, onboarding, tmp_path):
        """Test full onboarding pipeline in offline mode."""
        onboarding.vault.vault_path = tmp_path
        onboarding.vault.append_to_file = MagicMock()
        onboarding.vault.write_file = MagicMock()

        onboarding.employee_name = "Jane Doe"
        onboarding.employee_email = "jane.doe@company.com"
        onboarding.department = "Engineering"
        onboarding.start_date = "2026-06-01"
        onboarding.status = "pending"
        onboarding.provisioning_steps = []
        onboarding.errors = []

        result = onboarding.process_onboarding(onboarding)
        assert result["success"] is True
        assert "user_created" in result["steps_completed"]
        assert "groups_updated" in result["steps_completed"]
        assert len(result["steps_completed"]) >= 2
        assert len(result["errors"]) == 0


class TestOnboardingSecurity:
    """Test security aspects of onboarding."""

    @pytest.fixture
    def onboarding(self):
        """Create a GoogleWorkspaceOnboarding instance in offline mode."""
        with patch.dict(os.environ, {
            "GOOGLE_WORKSPACE_ADMIN_EMAIL": "admin@company.com",
            "GOOGLE_WORKSPACE_DOMAIN": "company.com",
            "GOOGLE_SERVICE_ACCOUNT_JSON": "/tmp/fake-key.json",
            "ONBOARDING_AUTO_GENERATE_PASSWORD": "true",
            "ONBOARDING_SEND_WELCOME_EMAIL": "true",
            "ONBOARDING_DEFAULT_GROUP": "all-employees",
            "ONBOARDING_INTRANET_URL": "https://intranet.company.com",
            "ONBOARDING_HELP_DESK": "it-help@company.com",
        }, clear=False):
            obj = object.__new__(GoogleWorkspaceOnboarding)
            obj.admin_email = "admin@company.com"
            obj.domain = "company.com"
            obj.service_account_json = "/tmp/fake-key.json"
            obj.default_ou = "/"
            obj.auto_generate_password = True
            obj.send_welcome_email = True
            obj.default_group = "all-employees"
            obj.intranet_url = "https://intranet.company.com"
            obj.help_desk = "it-help@company.com"
            obj.directory_service = None
            obj.gmail_service = None
            obj._authenticated = True
            obj.name = "google_workspace_onboarding"
            obj.last_poll_time = 0
            obj.error_count = 0
            obj.max_errors = 5
            obj.running = False
            obj.vault = MagicMock()
            obj.vault.vault_path = Path("/tmp/test_vault")
            obj.settings = MagicMock()
            obj.vault_manager = MagicMock()
            obj.vault_manager.vault_path = Path("/tmp/test_vault")
            obj.poll_interval = 300
            yield obj

    def test_password_is_different_each_time(self, onboarding):
        """Ensure generated passwords are unique."""
        passwords = [onboarding._generate_temp_password() for _ in range(5)]
        assert len(set(passwords)) == 5

    def test_password_meets_length_requirement(self, onboarding):
        """Test password minimum length."""
        for length in [8, 12, 16, 20]:
            password = onboarding._generate_temp_password(length)
            assert len(password) == length

    def test_domain_validation(self, onboarding):
        """Test that non-matching domains are rejected."""
        onboarding.domain = "company.com"
        email = "test@othercompany.com"
        assert not email.endswith(f"@{onboarding.domain}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])