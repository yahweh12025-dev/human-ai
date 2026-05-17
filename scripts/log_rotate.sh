#!/bin/bash
"""
Log Rotation Engine
Rotates and compresses log files to prevent disk space exhaustion
"""

# Configuration
LOG_DIRS=(
    "/var/log"
    "./human-ai/logs"
    "./logs"
    "./human-ai/agents/*/logs"
    "./human-ai/data/logs"
)

RETENTION_DAYS=7
COMPRESS_AFTER_DAYS=1
MAX_SIZE_MB=100

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_message() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${timestamp} [${level}] ${message}"
}

log_info() {
    log_message "INFO" "$1"
}

log_warn() {
    log_message "WARN" "$1"
}

log_error() {
    log_message "ERROR" "$1"
}

rotate_log_file() {
    local logfile="$1"
    
    # Check if file exists
    if [[ ! -f "$logfile" ]]; then
        return 0
    fi
    
    # Get file size in MB
    local size_mb=$(du -m "$logfile" | cut -f1)
    
    # Check if file needs rotation due to size
    if [[ $size_mb -gt $MAX_SIZE_MB ]]; then
        log_warn "Large log file detected: $logfile (${size_mb}MB)"
    fi
    
    # Check if file is older than compression threshold
    local file_age_days=$(find "$logfile" -mtime +$COMPRESS_AFTER_DAYS -print 2>/dev/null)
    
    if [[ -n "$file_age_days" ]]; then
        # Compress the file if not already compressed
        if [[ "$logfile" != *.gz && "$logfile" != *.bz2 && "$logfile" != *.xz ]]; then
            log_info "Compressing old log file: $logfile"
            gzip "$logfile"
            return 0
        fi
    fi
    
    # Check if file needs rotation based on age
    local rotation_needed=false
    
    # Check if we have rotated files for this log
    local rotated_count=0
    for i in $(seq 1 $RETENTION_DAYS); do
        if [[ -f "${logfile}.${i}.gz" ]]; then
            ((rotated_count++))
        fi
    done
    
    # If we have enough rotated files, rotate
    if [[ $rotated_count -ge $RETENTION_DAYS ]]; then
        rotation_needed=true
    fi
    
    # Also rotate if file is older than retention period
    local old_file=$(find "$logfile" -mtime +$RETENTION_DAYS -print 2>/dev/null)
    if [[ -n "$old_file" ]]; then
        rotation_needed=true
    fi
    
    if [[ "$rotation_needed" = true ]]; then
        log_info "Rotating log file: $logfile"
        
        # Remove oldest rotation if we're at limit
        if [[ -f "${logfile}.${RETENTION_DAYS}.gz" ]]; then
            rm "${logfile}.${RETENTION_DAYS}.gz"
            log_info "Removed oldest rotation: ${logfile}.${RETENTION_DAYS}.gz"
        fi
        
        # Shift existing rotations
        for i in $(seq $((RETENTION_DAYS-1)) -1 1); do
            if [[ -f "${logfile}.${i}.gz" ]]; then
                local next=$((i+1))
                mv "${logfile}.${i}.gz" "${logfile}.${next}.gz"
                log_info "Rotated ${logfile}.${i}.gz -> ${logfile}.${next}.gz"
            fi
        done
        
        # Compress current file and move to .1.gz
        if [[ -f "$logfile" && ! "$logfile" = *.gz ]]; then
            gzip -c "$logfile" > "${logfile}.1.gz"
            # Truncate original file
            > "$logfile"
            log_info "Created rotation: ${logfile}.1.gz"
        fi
    fi
}

main() {
    log_info "Starting log rotation engine"
    
    # Process each log directory
    for log_dir in "${LOG_DIRS[@]}"; do
        # Expand wildcards in directory path
        expanded_dirs=$(eval echo "$log_dir")
        
        for dir in $expanded_dirs; do
            if [[ -d "$dir" ]]; then
                log_info "Processing directory: $dir"
                
                # Find all log files in directory
                while IFS= read -r -d '' logfile; do
                    rotate_log_file "$logfile"
                done < <(find "$dir" -type f \( -name "*.log" -o -name "*.out" -o -name "*.err" \) -print0 2>/dev/null)
            else
                log_warn "Directory does not exist: $dir"
            fi
        done
    done
    
    log_info "Log rotation engine completed"
}

# If script is executed directly, run main function
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi