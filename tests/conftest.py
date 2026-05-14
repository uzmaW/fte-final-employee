"""
Pytest configuration and shared fixtures for all tests.
"""

import pytest
import tempfile
from pathlib import Path
import sys
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging for tests
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

@pytest.fixture(scope="session")
def test_vault_root():
    """Create a temporary root directory for all tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)

@pytest.fixture
def sample_task_content():
    """Sample task content for testing."""
    return """---
type: email_task
priority: high
source: gmail
created: 2026-02-08T10:30:00Z
---

# Sample Task

**From:** sender@example.com
**Subject:** Important task

This is a sample task for testing purposes.

## Action Required
- [ ] Do something
- [ ] Verify result
"""

@pytest.fixture
def sample_approval_content():
    """Sample approval request content."""
    return """---
type: payment_approval
priority: high
created: 2026-02-08T10:30:00Z
action_id: ACTION_TEST_001
risk_level: medium
---

# Approval Request: Payment

**Amount:** $500
**Recipient:** vendor@example.com
**Purpose:** Invoice payment

Please review and approve or deny.
"""

def pytest_configure(config):
    """Configure pytest."""
    # Add custom markers
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "vault: mark test as vault operation test"
    )
    config.addinivalue_line(
        "markers", "browser: mark test as browser automation test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
