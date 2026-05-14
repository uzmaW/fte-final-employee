#!/bin/bash
# AI Employee Vault Backup Script
# Backs up the Obsidian vault and logs
# Usage: ./scripts/backup_vault.sh
# Or schedule with cron: 0 2 * * * /path/to/scripts/backup_vault.sh

set -e

# ============================================================================
# CONFIGURATION
# ============================================================================

VAULT_PATH="AI_Employee_Vault"
BACKUP_DIR="backups"
BACKUP_RETENTION_DAYS=30
LOG_FILE="$BACKUP_DIR/backup.log"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="fte-vault-$TIMESTAMP"

# ============================================================================
# COLORS FOR OUTPUT
# ============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# FUNCTIONS
# ============================================================================

log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] ✅ $1${NC}" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ❌ $1${NC}" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] ⚠️  $1${NC}" | tee -a "$LOG_FILE"
}

# ============================================================================
# MAIN BACKUP LOGIC
# ============================================================================

main() {
    log "Starting vault backup..."
    
    # Create backup directory if it doesn't exist
    mkdir -p "$BACKUP_DIR"
    mkdir -p "$BACKUP_DIR/logs"
    
    # Check if vault exists
    if [ ! -d "$VAULT_PATH" ]; then
        log_error "Vault path not found: $VAULT_PATH"
        exit 1
    fi
    
    log "Vault size: $(du -sh "$VAULT_PATH" | cut -f1)"
    
    # Create backup tar.gz
    log "Creating backup: $BACKUP_NAME.tar.gz"
    
    if tar -czf "$BACKUP_DIR/$BACKUP_NAME.tar.gz" "$VAULT_PATH"; then
        BACKUP_SIZE=$(du -sh "$BACKUP_DIR/$BACKUP_NAME.tar.gz" | cut -f1)
        log_success "Backup created successfully (Size: $BACKUP_SIZE)"
    else
        log_error "Failed to create backup"
        exit 1
    fi
    
    # Create JSON metadata
    create_backup_metadata
    
    # Verify backup integrity
    verify_backup
    
    # Cleanup old backups
    cleanup_old_backups
    
    # Sync to cloud (if configured)
    sync_to_cloud
    
    log_success "Backup completed successfully!"
}

create_backup_metadata() {
    log "Creating backup metadata..."
    
    local metadata_file="$BACKUP_DIR/$BACKUP_NAME.json"
    
    cat > "$metadata_file" << EOF
{
  "backup_name": "$BACKUP_NAME",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "vault_path": "$VAULT_PATH",
  "backup_file": "$BACKUP_NAME.tar.gz",
  "backup_size": "$(du -sh "$BACKUP_DIR/$BACKUP_NAME.tar.gz" | cut -f1)",
  "vault_size": "$(du -sh "$VAULT_PATH" | cut -f1)",
  "file_count": $(find "$VAULT_PATH" -type f | wc -l),
  "hostname": "$(hostname)",
  "user": "$(whoami)",
  "backup_method": "tar-gzip",
  "compression": "gzip",
  "retention_days": $BACKUP_RETENTION_DAYS,
  "status": "completed"
}
EOF
    
    log "Metadata saved to: $metadata_file"
}

verify_backup() {
    log "Verifying backup integrity..."
    
    if tar -tzf "$BACKUP_DIR/$BACKUP_NAME.tar.gz" > /dev/null 2>&1; then
        log_success "Backup verification passed"
    else
        log_error "Backup verification failed - archive may be corrupted"
        exit 1
    fi
}

cleanup_old_backups() {
    log "Cleaning up old backups (keeping $BACKUP_RETENTION_DAYS days)..."
    
    local count=0
    while IFS= read -r old_backup; do
        log_warning "Removing old backup: $(basename $old_backup)"
        rm -f "$old_backup"
        rm -f "${old_backup%.tar.gz}.json"
        ((count++))
    done < <(find "$BACKUP_DIR" -name "fte-vault-*.tar.gz" -mtime +$BACKUP_RETENTION_DAYS)
    
    if [ $count -gt 0 ]; then
        log_success "Removed $count old backup(s)"
    fi
}

sync_to_cloud() {
    # Uncomment and configure for your cloud storage
    
    # AWS S3 Example:
    # if command -v aws &> /dev/null; then
    #     log "Syncing to S3..."
    #     aws s3 cp "$BACKUP_DIR/$BACKUP_NAME.tar.gz" s3://your-bucket/fte-backups/
    #     log_success "S3 sync completed"
    # fi
    
    # Google Cloud Example:
    # if command -v gsutil &> /dev/null; then
    #     log "Syncing to Google Cloud Storage..."
    #     gsutil cp "$BACKUP_DIR/$BACKUP_NAME.tar.gz" gs://your-bucket/fte-backups/
    #     log_success "GCS sync completed"
    # fi
    
    # Dropbox Example:
    # if command -v rclone &> /dev/null; then
    #     log "Syncing to Dropbox..."
    #     rclone copy "$BACKUP_DIR/$BACKUP_NAME.tar.gz" dropbox:/fte-backups/
    #     log_success "Dropbox sync completed"
    # fi
    
    log "Cloud sync skipped (not configured)"
}

# ============================================================================
# RUN MAIN FUNCTION
# ============================================================================

main
