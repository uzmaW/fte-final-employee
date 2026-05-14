#!/bin/bash
# Setup Cron Jobs for Automated Backups and Maintenance
# Run this script once to configure cron jobs

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Setting up automated backup and maintenance tasks...${NC}\n"

# Get the full path to the project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_SCRIPT="$PROJECT_DIR/scripts/backup_vault.sh"

echo "Project directory: $PROJECT_DIR"
echo "Backup script: $BACKUP_SCRIPT"

# Check if script exists
if [ ! -f "$BACKUP_SCRIPT" ]; then
    echo -e "${RED}❌ Backup script not found: $BACKUP_SCRIPT${NC}"
    exit 1
fi

# Create backup directory if it doesn't exist
mkdir -p "$PROJECT_DIR/backups"
mkdir -p "$PROJECT_DIR/backups/logs"

echo -e "\n${YELLOW}Suggested Cron Jobs:${NC}"
echo ""
echo "1. Daily backup at 2 AM:"
echo "   0 2 * * * $BACKUP_SCRIPT"
echo ""
echo "2. Weekly health check on Mondays at 3 AM:"
echo "   0 3 * * 1 cd $PROJECT_DIR && python3 -m pytest tests/ -q"
echo ""
echo "3. Monthly credential rotation reminder (1st of month at 9 AM):"
echo "   0 9 1 * * echo 'Monthly credential rotation due' | mail -s 'AI Employee Maintenance' your-email@example.com"
echo ""
echo "4. Auto-restart of PM2 processes (every Sunday at 4 AM):"
echo "   0 4 * * 0 cd $PROJECT_DIR && pm2 restart all"
echo ""

read -p "Do you want to install these cron jobs? (y/n) " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Backup current crontab
    echo -e "${YELLOW}Backing up current crontab...${NC}"
    crontab -l > "$PROJECT_DIR/backups/crontab.backup" 2>/dev/null || true
    
    # Create temporary cron file
    CRON_FILE=$(mktemp)
    
    # Add existing cron jobs
    crontab -l >> "$CRON_FILE" 2>/dev/null || true
    
    # Add new cron jobs (if not already present)
    if ! grep -q "$BACKUP_SCRIPT" "$CRON_FILE"; then
        echo "" >> "$CRON_FILE"
        echo "# AI Employee Vault Backups (Daily at 2 AM)" >> "$CRON_FILE"
        echo "0 2 * * * $BACKUP_SCRIPT" >> "$CRON_FILE"
    fi
    
    if ! grep -q "pytest tests/" "$CRON_FILE"; then
        echo "" >> "$CRON_FILE"
        echo "# AI Employee Health Check (Weekly on Monday at 3 AM)" >> "$CRON_FILE"
        echo "0 3 * * 1 cd $PROJECT_DIR && python3 -m pytest tests/ -q" >> "$CRON_FILE"
    fi
    
    if ! grep -q "pm2 restart all" "$CRON_FILE"; then
        echo "" >> "$CRON_FILE"
        echo "# AI Employee Process Restart (Weekly on Sunday at 4 AM)" >> "$CRON_FILE"
        echo "0 4 * * 0 cd $PROJECT_DIR && pm2 restart all" >> "$CRON_FILE"
    fi
    
    # Install new crontab
    crontab "$CRON_FILE"
    rm "$CRON_FILE"
    
    echo -e "${GREEN}✅ Cron jobs installed successfully!${NC}"
    echo ""
    echo "View installed cron jobs with: crontab -l"
    echo "Edit cron jobs with: crontab -e"
    echo "Restore from backup with: crontab $PROJECT_DIR/backups/crontab.backup"
else
    echo -e "${YELLOW}Cron installation skipped.${NC}"
    echo "You can manually add the cron jobs at any time."
fi

echo -e "\n${GREEN}Done!${NC}"
