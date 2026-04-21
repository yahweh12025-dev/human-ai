#!/bin/bash
# GUI Self-Healing Script for XRDP/XFCE
# Purpose: Clean up corrupted session states and reset XFCE environment

echo "🚀 Starting GUI Self-Healing Process..."

# 1. Kill any orphaned XFCE/XRDP processes for the current user
echo "🧹 Cleaning up orphaned processes..."
pkill -u $(whoami) xfce4-session || true
pkill -u $(whoami) xfwm4 || true
pkill -u $(whoami) xfce4-panel || true

# 2. Clear corrupted session and cache files
echo "🗑️ Clearing session and cache files..."
rm -rf ~/.cache/sessions/*
rm -rf ~/.cache/xfce4/*
rm -rf ~/.config/xfce4/cache/*

# 3. Ensure .xsession is correctly configured for XRDP
echo "📝 Verifying .xsession configuration..."
cat << 'EOF' > ~/.xsession
#!/bin/bash
export XDG_SESSION_TYPE=x11
export XDG_CURRENT_DESKTOP=XFCE
export GNOME_SHELL_SESSION_MODE=ubuntu
# Prevent the light-locker error
unset XDG_SESSION_PATH
startxfce4
EOF
chmod +x ~/.xsession

# 4. Restart XRDP to apply changes
echo "🔄 Restarting XRDP service..."
sudo systemctl restart xrdp

echo "✅ GUI Environment has been reset successfully!"
echo "You may need to reconnect your RDP session."
