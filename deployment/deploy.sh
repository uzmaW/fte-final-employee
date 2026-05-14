#!/bin/bash
# AI Employee - Automated Deployment Script
# One-command deployment with Playwright automation
# Usage: bash deploy.sh [--interactive|--automated]

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_MIN_VERSION="3.10"
DEPLOYMENT_MODE="${1:-interactive}"

# Functions
print_header() {
    echo -e "\n${CYAN}========================================${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check Python version
check_python() {
    print_header "Checking Python Version"
    
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 not found. Please install Python $PYTHON_MIN_VERSION or higher."
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    print_info "Found Python $PYTHON_VERSION"
    
    # Check minimum version (basic check)
    if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"; then
        print_error "Python $PYTHON_MIN_VERSION or higher required"
        exit 1
    fi
    
    print_success "Python version OK"
}

# Setup virtual environment
setup_venv() {
    print_header "Setting Up Virtual Environment"
    
    if [ ! -d "$PROJECT_ROOT/venv" ]; then
        print_info "Creating virtual environment..."
        python3 -m venv "$PROJECT_ROOT/venv"
        print_success "Virtual environment created"
    else
        print_info "Virtual environment already exists"
    fi
    
    # Activate
    source "$PROJECT_ROOT/venv/bin/activate"
    print_success "Virtual environment activated"
}

# Install dependencies
install_dependencies() {
    print_header "Installing Dependencies"
    
    print_info "Upgrading pip..."
    pip install --quiet --upgrade pip
    
    print_info "Installing Python packages..."
    pip install --quiet -r "$PROJECT_ROOT/requirements.txt"
    
    print_info "Installing Playwright browsers..."
    python3 -m playwright install chromium
    
    print_success "All dependencies installed"
}

# Check Node.js
check_nodejs() {
    print_header "Checking Node.js"
    
    if ! command -v node &> /dev/null; then
        print_warning "Node.js not found. PM2 will be skipped."
        print_info "Install Node.js from: https://nodejs.org/"
        return 1
    fi
    
    NODE_VERSION=$(node -v)
    print_info "Found Node.js $NODE_VERSION"
    print_success "Node.js OK"
    return 0
}

# Install PM2
install_pm2() {
    print_header "Installing PM2"
    
    if command -v pm2 &> /dev/null; then
        print_info "PM2 already installed"
        return 0
    fi
    
    print_info "Installing PM2 globally..."
    npm install -g pm2 --silent
    print_success "PM2 installed"
}

# Run deployment automation
run_deployment() {
    print_header "Running Automated Deployment"
    
    # Set deployment mode
    if [ "$DEPLOYMENT_MODE" = "--automated" ]; then
        print_info "Running in automated mode (using environment variables)"
        export DEPLOY_MODE=automated
    else
        print_info "Running in interactive mode (will prompt for credentials)"
        export DEPLOY_MODE=interactive
    fi
    
    # Run deployment script
    cd "$PROJECT_ROOT"
    python3 deployment_automation.py
    
    if [ $? -eq 0 ]; then
        print_success "Deployment completed successfully"
    else
        print_error "Deployment failed"
        exit 1
    fi
}

# Post-deployment instructions
post_deployment() {
    print_header "Post-Deployment Setup"
    
    print_info "To setup automated backups:"
    echo -e "${CYAN}  bash setup_cron_backups.sh${NC}"
    
    print_info "To monitor the system:"
    echo -e "${CYAN}  pm2 logs${NC}"
    echo -e "${CYAN}  pm2 monit${NC}"
    
    print_info "To view status:"
    echo -e "${CYAN}  pm2 status${NC}"
    
    print_info "Dashboard available at:"
    echo -e "${CYAN}  AI_Employee_Vault/MONITORING_DASHBOARD.md${NC}"
}

# Main execution
main() {
    echo -e "${CYAN}"
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║     AI Employee - Automated Deployment System                  ║"
    echo "║     Build your Digital FTE in minutes                         ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    # Pre-flight checks
    check_python
    setup_venv
    install_dependencies
    check_nodejs && install_pm2
    
    # Run deployment
    run_deployment
    
    # Post-deployment
    post_deployment
    
    print_header "Deployment Complete!"
    echo -e "${GREEN}🚀 Your AI Employee is ready to work!${NC}\n"
}

# Run main
main "$@"
