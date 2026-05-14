#!/bin/bash

# Test runner script for AI Employee system
# Run this to execute all tests with proper configuration

set -e

echo "======================================================================"
echo "AI Employee System - Test Suite"
echo "======================================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    exit 1
fi

echo -e "${YELLOW}Python version:${NC}"
python3 --version

# Check if pytest is available
if ! python3 -m pytest --version &> /dev/null; then
    echo -e "${YELLOW}Installing pytest and dependencies...${NC}"
    pip install -q pytest pytest-asyncio pytest-playwright pyyaml pydantic python-dotenv
fi

echo ""
echo -e "${YELLOW}Running unit tests (test_vault_operations.py)...${NC}"
python3 -m pytest tests/test_vault_operations.py -v --tb=short

echo ""
echo -e "${YELLOW}Running browser integration tests (test_vault_browser.py)...${NC}"
python3 -m pytest tests/test_vault_browser.py -v --tb=short

echo ""
echo -e "${YELLOW}Running Playwright integration tests (test_playwright_integration.py)...${NC}"
python3 -m pytest tests/test_playwright_integration.py -v --tb=short

echo ""
echo -e "${GREEN}All tests completed!${NC}"
echo ""
echo -e "${YELLOW}To run specific test:${NC}"
echo "  python3 -m pytest tests/test_vault_operations.py::TestVaultReading::test_read_task_file_with_frontmatter -v"
echo ""
echo -e "${YELLOW}To run with coverage:${NC}"
echo "  pip install pytest-cov"
echo "  python3 -m pytest tests/ --cov --cov-report=html"
echo ""
