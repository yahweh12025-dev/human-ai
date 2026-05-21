#!/usr/bin/env bash
# ============================================================
# Human-AI Swarm — Comprehensive Fresh-Instance Bootstrap
# Version: 2.0.0
#
# Usage:
#   # On a fresh Linux instance (pipe-to-bash):
#   curl -s https://raw.githubusercontent.com/yahweh12025-dev/human-ai/main/scripts/install.sh | bash
#
#   # After cloning:
#   bash scripts/install.sh
#
# Idempotent: safe to re-run on an existing install.
# Tested on: Ubuntu 22.04 LTS, Debian 12
# ============================================================

set -euo pipefail

# ── Configuration ─────────────────────────────────────────────
REPO="https://github.com/yahweh12025-dev/human-ai.git"
INSTALL_DIR="$HOME/human-ai"
PYTHON_VERSION="3.11"
NODE_VERSION="20"
LOG="$HOME/install_human_ai.log"
NVM_DIR="$HOME/.nvm"
GSD_DIR="$HOME/.claude/get-shit-done"
GSD_REPO="https://github.com/get-shit-done/get-shit-done"
CLAUDE_SETTINGS="$HOME/.claude/settings.json"

# ── Helpers ───────────────────────────────────────────────────
log()  { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG"; }
info() { echo "[$(date '+%H:%M:%S')] [INFO] $*" | tee -a "$LOG"; }
warn() { echo "[$(date '+%H:%M:%S')] [WARN] $*" | tee -a "$LOG"; }
err()  { echo "[$(date '+%H:%M:%S')] [ERROR] $*" | tee -a "$LOG" >&2; exit 1; }

log "================================================================"
log "  Human-AI Swarm — Bootstrap Installer v2.0.0"
log "  $(date)"
log "  Log: $LOG"
log "================================================================"

# ── 1. System Packages ────────────────────────────────────────
# Covers: Python, git, build tools, rclone, multimedia, display, Wine, VNC
log ""
log "── STEP 1: System packages ──────────────────────────────────"
sudo apt-get update -qq

# Core build tools + Python
sudo apt-get install -y -qq \
    python${PYTHON_VERSION} python${PYTHON_VERSION}-venv python${PYTHON_VERSION}-dev \
    python3-pip build-essential libssl-dev libffi-dev libpq-dev \
    2>>"$LOG" || warn "Some Python/build packages may have failed"

# Version control + network tools
sudo apt-get install -y -qq \
    git curl wget unzip jq tmux htop \
    2>>"$LOG" || warn "Some utility packages may have failed"

# rclone (Google Drive sync)
if ! command -v rclone &>/dev/null; then
    log "  Installing rclone..."
    curl -s https://rclone.org/install.sh | sudo bash >>"$LOG" 2>&1 || \
        sudo apt-get install -y -qq rclone 2>>"$LOG" || warn "rclone install failed"
else
    info "  rclone already installed: $(rclone --version 2>/dev/null | head -1)"
fi

# TA-Lib (technical analysis C library — must come before pip install)
if ! python${PYTHON_VERSION} -c "import talib" 2>/dev/null; then
    log "  Installing TA-Lib C library..."
    sudo apt-get install -y -qq ta-lib 2>>"$LOG" || {
        # Fallback: build from source
        warn "  apt TA-Lib failed, building from source..."
        cd /tmp
        wget -q http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
        tar -xzf ta-lib-0.4.0-src.tar.gz
        cd ta-lib
        ./configure --prefix=/usr >/dev/null 2>>"$LOG"
        make -s 2>>"$LOG"
        sudo make install -s 2>>"$LOG"
        cd "$HOME"
        info "  TA-Lib built from source"
    }
fi

# Multimedia (ffmpeg for video production)
sudo apt-get install -y -qq ffmpeg 2>>"$LOG" || warn "ffmpeg install failed"

# Virtual display + window management (required for browser automation + Wine/MT5)
sudo apt-get install -y -qq \
    xvfb xdotool wmctrl x11vnc \
    2>>"$LOG" || warn "X11 packages install failed"

# Wine (for MetaTrader 5 on Linux)
if ! command -v wine &>/dev/null; then
    log "  Installing Wine for MetaTrader 5..."
    sudo dpkg --add-architecture i386 2>>"$LOG" || true
    sudo apt-get update -qq 2>>"$LOG" || true
    sudo apt-get install -y -qq wine wine32 wine64 2>>"$LOG" || warn "Wine install failed"
else
    info "  Wine already installed: $(wine --version 2>/dev/null)"
fi

log "  System packages done."

# ── 2. Clone or Update Repo ───────────────────────────────────
log ""
log "── STEP 2: Repository ───────────────────────────────────────"
if [ -d "$INSTALL_DIR/.git" ]; then
    info "  Repo exists at $INSTALL_DIR — pulling latest..."
    git -C "$INSTALL_DIR" pull --ff-only 2>>"$LOG" || warn "pull failed (repo may be dirty)"
else
    log "  Cloning repo to $INSTALL_DIR..."
    git clone "$REPO" "$INSTALL_DIR" 2>>"$LOG"
    log "  Clone complete."
fi

cd "$INSTALL_DIR"

# ── 3. Python Virtual Environment ─────────────────────────────
log ""
log "── STEP 3: Python virtual environment ───────────────────────"
if [ ! -d "$INSTALL_DIR/.venv" ]; then
    log "  Creating .venv with Python ${PYTHON_VERSION}..."
    python${PYTHON_VERSION} -m venv .venv
fi

source .venv/bin/activate
pip install --upgrade pip setuptools wheel -q 2>>"$LOG"

log "  Installing Python dependencies from requirements.txt..."
pip install -r requirements.txt -q 2>>"$LOG" || \
    warn "Some pip deps failed (check $LOG for details)"
log "  Python deps installed."

# ── 4. Node.js via nvm ────────────────────────────────────────
log ""
log "── STEP 4: Node.js (via nvm) ────────────────────────────────"
if [ ! -d "$NVM_DIR" ]; then
    log "  Installing nvm..."
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash >>"$LOG" 2>&1
fi

# Load nvm in current shell
export NVM_DIR="$NVM_DIR"
# shellcheck disable=SC1090
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"

if ! command -v node &>/dev/null || ! node --version | grep -q "v${NODE_VERSION}"; then
    log "  Installing Node.js ${NODE_VERSION}..."
    nvm install "$NODE_VERSION" >>"$LOG" 2>&1
    nvm use "$NODE_VERSION" >>"$LOG" 2>&1
    nvm alias default "$NODE_VERSION" >>"$LOG" 2>&1
else
    info "  Node.js already installed: $(node --version)"
fi

# ── 5. Claude Code CLI ────────────────────────────────────────
log ""
log "── STEP 5: Claude Code CLI ──────────────────────────────────"
if ! command -v claude &>/dev/null; then
    log "  Installing Claude Code CLI..."
    npm install -g @anthropic-ai/claude-code >>"$LOG" 2>&1 || \
        warn "Claude Code CLI install failed — run: npm install -g @anthropic-ai/claude-code"
else
    info "  Claude Code already installed: $(claude --version 2>/dev/null | head -1)"
fi

# ── 6. GSD SDK ────────────────────────────────────────────────
log ""
log "── STEP 6: GSD SDK (Get Shit Done) ──────────────────────────"
mkdir -p "$HOME/.claude"
if [ ! -d "$GSD_DIR/.git" ]; then
    log "  Cloning GSD SDK to $GSD_DIR..."
    git clone "$GSD_REPO" "$GSD_DIR" 2>>"$LOG" || \
        warn "GSD SDK clone failed — repo may be private; clone manually: git clone $GSD_REPO $GSD_DIR"
else
    log "  GSD SDK exists — pulling latest..."
    git -C "$GSD_DIR" pull --ff-only 2>>"$LOG" || warn "GSD SDK pull failed"
fi

# Install GSD SDK npm dependencies if present
if [ -f "$GSD_DIR/package.json" ]; then
    log "  Installing GSD SDK npm deps..."
    (cd "$GSD_DIR" && npm install --quiet >>"$LOG" 2>&1) || warn "GSD SDK npm install failed"
fi

# ── 7. rclone Google Drive Config ─────────────────────────────
log ""
log "── STEP 7: rclone Google Drive ──────────────────────────────"
if rclone listremotes 2>/dev/null | grep -q "gdrive:"; then
    info "  GDrive remote already configured."
else
    log ""
    log "  ╔══════════════════════════════════════════════════════════╗"
    log "  ║  Google Drive NOT configured.                           ║"
    log "  ║  Run these commands to configure:                       ║"
    log "  ║                                                         ║"
    log "  ║    rclone config                                        ║"
    log "  ║    > n  (new remote)                                    ║"
    log "  ║    > Name: gdrive                                       ║"
    log "  ║    > Type: drive  (Google Drive)                        ║"
    log "  ║    > Follow OAuth prompts                               ║"
    log "  ║                                                         ║"
    log "  ║  Then re-run this script to complete vault restore.     ║"
    log "  ╚══════════════════════════════════════════════════════════╝"
    log ""
fi

# ── 8. Mount GDrive ───────────────────────────────────────────
log ""
log "── STEP 8: Mount GDrive ─────────────────────────────────────"
if [ -f "$INSTALL_DIR/scripts/system/mount_gdrive.sh" ]; then
    if rclone listremotes 2>/dev/null | grep -q "gdrive:"; then
        log "  Mounting GDrive..."
        bash "$INSTALL_DIR/scripts/system/mount_gdrive.sh" 2>>"$LOG" || \
            warn "GDrive mount failed — check mount_gdrive.sh"
    else
        warn "  Skipping mount — GDrive not configured yet."
    fi
else
    warn "  scripts/system/mount_gdrive.sh not found — skipping mount."
fi

# ── 9. Restore Obsidian Vault from GDrive ─────────────────────
log ""
log "── STEP 9: Restore Obsidian vault ───────────────────────────"
if rclone listremotes 2>/dev/null | grep -q "gdrive:"; then
    log "  Syncing Obsidian vault from gdrive:backups/obsidian..."
    rclone sync "gdrive:backups/obsidian" "$INSTALL_DIR/data/obsidian" \
        --log-file="$LOG" --log-level INFO 2>>"$LOG" || \
        warn "Obsidian vault sync failed — vault may not exist in GDrive yet"
    info "  Obsidian vault synced to $INSTALL_DIR/data/obsidian"
else
    warn "  Skipping vault restore — GDrive not configured."
fi

# ── 10. Restore .env from GDrive ──────────────────────────────
log ""
log "── STEP 10: Restore .env ─────────────────────────────────────"
if rclone listremotes 2>/dev/null | grep -q "gdrive:"; then
    if [ ! -f "$INSTALL_DIR/.env" ]; then
        log "  Copying .env from gdrive:backups/env/.env..."
        rclone copy "gdrive:backups/env/.env" "$INSTALL_DIR" \
            2>>"$LOG" || warn ".env not found in GDrive — create one manually from .env.example"
        if [ -f "$INSTALL_DIR/.env" ]; then
            info "  .env restored from GDrive."
        else
            warn "  .env not found in GDrive backup. Create manually: cp .env.example .env && nano .env"
        fi
    else
        info "  .env already exists — skipping restore."
    fi
else
    if [ ! -f "$INSTALL_DIR/.env" ] && [ -f "$INSTALL_DIR/.env.example" ]; then
        log "  Creating .env from template..."
        cp "$INSTALL_DIR/.env.example" "$INSTALL_DIR/.env"
        warn "  .env created from template — edit API keys: nano $INSTALL_DIR/.env"
    fi
fi

# ── 11. Required Directories ──────────────────────────────────
log ""
log "── STEP 11: Directory structure ─────────────────────────────"
mkdir -p \
    "$INSTALL_DIR/data/logs" \
    "$INSTALL_DIR/data/obsidian" \
    "$INSTALL_DIR/data/feeds" \
    "$INSTALL_DIR/data/media_output" \
    "$INSTALL_DIR/data/tests" \
    "$INSTALL_DIR/data/logs/pow" \
    "$INSTALL_DIR/data/market_cache"
info "  Required directories ensured."

# ── 12. Docker + Postiz ───────────────────────────────────────
log ""
log "── STEP 12: Docker + Postiz ─────────────────────────────────"

# Install Docker if not present
if ! command -v docker &>/dev/null; then
    log "  Installing Docker..."
    curl -fsSL https://get.docker.com | sh >>"$LOG" 2>&1 || warn "Docker install failed"
    sudo usermod -aG docker "$USER" 2>>"$LOG" || true
    info "  Docker installed. NOTE: logout/login required for docker group to take effect."
else
    info "  Docker already installed: $(docker --version 2>/dev/null)"
fi

# Install docker-compose if not present
if ! command -v docker-compose &>/dev/null && ! docker compose version &>/dev/null 2>&1; then
    log "  Installing docker-compose..."
    sudo apt-get install -y -qq docker-compose-plugin 2>>"$LOG" || \
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
        -o /usr/local/bin/docker-compose 2>>"$LOG" && \
    sudo chmod +x /usr/local/bin/docker-compose 2>>"$LOG" || warn "docker-compose install failed"
else
    info "  docker-compose already installed."
fi

# Start Postiz
POSTIZ_DIR="$INSTALL_DIR/infrastructure/docker/postiz"
if [ -f "$POSTIZ_DIR/docker-compose.yml" ] || [ -f "$POSTIZ_DIR/docker-compose.yaml" ]; then
    log "  Starting Postiz (social media publishing)..."
    (cd "$POSTIZ_DIR" && docker-compose up -d 2>>"$LOG") || \
        warn "Postiz startup failed — check $POSTIZ_DIR and Docker status"
    info "  Postiz starting at http://localhost:4200"
else
    warn "  Postiz docker-compose not found at $POSTIZ_DIR — skipping."
fi

# ── 13. Cron Jobs ─────────────────────────────────────────────
log ""
log "── STEP 13: Cron jobs ───────────────────────────────────────"
CRON_FILE=$(mktemp)
crontab -l 2>/dev/null > "$CRON_FILE" || true

add_cron() {
    local entry="$1"
    local desc="${2:-}"
    if ! grep -qF "$entry" "$CRON_FILE"; then
        echo "$entry" >> "$CRON_FILE"
        log "  Added cron: ${desc:-$entry}"
    else
        info "  Cron already set: ${desc:-$entry}"
    fi
}

PYTHON="$INSTALL_DIR/.venv/bin/python3"

# GDrive mount on reboot
add_cron \
    "@reboot bash $INSTALL_DIR/scripts/system/mount_gdrive.sh >> /tmp/rclone-gdrive.log 2>&1" \
    "GDrive mount on reboot"

# Obsidian vault sync every 30 minutes
add_cron \
    "*/30 * * * * rclone sync $INSTALL_DIR/data/obsidian gdrive:backups/obsidian >> $INSTALL_DIR/data/logs/obsidian_sync.log 2>&1" \
    "Obsidian vault sync (every 30m)"

# Full sync (full_sync.py handles dify/graphify/etc) every 30 minutes
add_cron \
    "*/30 * * * * $PYTHON $INSTALL_DIR/scripts/sync/full_sync.py >> $INSTALL_DIR/data/logs/sync.log 2>&1" \
    "Full sync (every 30m)"

# Supabase backup every 6 hours
add_cron \
    "0 */6 * * * bash $INSTALL_DIR/scripts/backup_supabase_to_gdrive.sh >> $INSTALL_DIR/data/logs/backup.log 2>&1" \
    "Supabase backup (every 6h)"

# Cloud backup every hour (Firebase + GDrive)
add_cron \
    "5 * * * * $PYTHON $INSTALL_DIR/scripts/system/backup_to_cloud.py >> $INSTALL_DIR/data/logs/cloud_backup.log 2>&1" \
    "Cloud backup (hourly)"

crontab "$CRON_FILE"
rm -f "$CRON_FILE"
log "  Cron jobs configured."

# ── 14. Context7 MCP ──────────────────────────────────────────
log ""
log "── STEP 14: Context7 MCP ────────────────────────────────────"
mkdir -p "$HOME/.claude"

if [ -f "$CLAUDE_SETTINGS" ]; then
    # Merge Context7 into existing settings.json using jq
    if command -v jq &>/dev/null; then
        # Check if context7 already configured
        if jq -e '.mcpServers["context7"]' "$CLAUDE_SETTINGS" >/dev/null 2>&1; then
            info "  Context7 MCP already configured in $CLAUDE_SETTINGS"
        else
            log "  Adding Context7 MCP to existing $CLAUDE_SETTINGS..."
            TMPFILE=$(mktemp)
            jq '.mcpServers["context7"] = {
                "command": "npx",
                "args": ["-y", "@upstash/context7-mcp"]
            }' "$CLAUDE_SETTINGS" > "$TMPFILE" && mv "$TMPFILE" "$CLAUDE_SETTINGS"
            info "  Context7 MCP added."
        fi
    else
        warn "  jq not found — cannot merge Context7 into existing settings.json. Install jq and re-run."
    fi
else
    log "  Writing $CLAUDE_SETTINGS with Context7 MCP..."
    cat > "$CLAUDE_SETTINGS" << 'CLAUDE_SETTINGS_EOF'
{
  "mcpServers": {
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp"]
    }
  }
}
CLAUDE_SETTINGS_EOF
    info "  $CLAUDE_SETTINGS created with Context7 MCP."
fi

# ── 15. Verify Key Components ─────────────────────────────────
log ""
log "── STEP 15: Verification ────────────────────────────────────"

verify_ok() { log "  [OK]  $1"; }
verify_warn() { warn "  [!!]  $1"; }

command -v python${PYTHON_VERSION} &>/dev/null && verify_ok "Python ${PYTHON_VERSION}" || verify_warn "Python ${PYTHON_VERSION} missing"
[ -f "$INSTALL_DIR/.venv/bin/python3" ] && verify_ok ".venv active" || verify_warn ".venv missing"
command -v git &>/dev/null && verify_ok "git" || verify_warn "git missing"
command -v rclone &>/dev/null && verify_ok "rclone" || verify_warn "rclone missing"
command -v ffmpeg &>/dev/null && verify_ok "ffmpeg" || verify_warn "ffmpeg missing"
command -v docker &>/dev/null && verify_ok "docker" || verify_warn "docker missing"
command -v node &>/dev/null && verify_ok "node $(node --version 2>/dev/null)" || verify_warn "node missing"
command -v claude &>/dev/null && verify_ok "claude-code CLI" || verify_warn "claude-code CLI missing"
[ -d "$GSD_DIR" ] && verify_ok "GSD SDK at $GSD_DIR" || verify_warn "GSD SDK missing ($GSD_DIR)"
[ -f "$INSTALL_DIR/.env" ] && verify_ok ".env present" || verify_warn ".env missing — add API keys"

# ── Summary ───────────────────────────────────────────────────
log ""
log "================================================================"
log "  INSTALL COMPLETE — $(date)"
log "================================================================"
log ""
log "Next steps:"
log ""
log "  1. API keys (required for all agents):"
log "       nano $INSTALL_DIR/.env"
log ""
log "  2. Google Drive (if not already configured):"
log "       rclone config    # name remote 'gdrive'"
log "       bash $INSTALL_DIR/scripts/system/mount_gdrive.sh"
log ""
log "  3. Obsidian vault sync:"
log "       rclone sync gdrive:backups/obsidian $INSTALL_DIR/data/obsidian"
log ""
log "  4. Activate Python env:"
log "       source $INSTALL_DIR/.venv/bin/activate"
log ""
log "  5. Start the dashboard (Mission Control):"
log "       python3 $INSTALL_DIR/core/apps/dashboard/mission_control.py"
log "       # Access at http://localhost:10000"
log ""
log "  6. Start trading agents:"
log "       python3 $INSTALL_DIR/liveea.py           # EA v10.1 (XAUUSD/XAGUSD)"
log "       python3 $INSTALL_DIR/startbinance.py     # Binance Scalper v10"
log ""
log "  7. Start Automode (full swarm):"
log "       python3 $INSTALL_DIR/automode.py"
log ""
log "  8. Postiz (social media publishing):"
log "       # Already started via docker-compose (if configured)"
log "       # Access at http://localhost:4200"
log ""
log "Full install log: $LOG"
log "================================================================"
