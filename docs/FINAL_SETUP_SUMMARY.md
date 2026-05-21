# Nstbrowser Agent Installation Summary

## ✅ Installation Complete

The Nstbrowser agent has been successfully installed on your Debian system with the following components:

### Binaries Installed:
- **Agent**: `/home/yahwehatwork/.local/bin/agent`
- **Nstcli**: `/home/yahwehatwork/.local/bin/nstcli`

### Configuration:
- **Config File**: `/home/yahwehatwork/.nst-agent/conf/config.yaml` (contains your authentication token)
- **Kernel & Fonts**: Downloaded to `/home/yahwehatwork/.nst-agent/download/`

### Environment Variables (added to ~/.bashrc):
```bash
export NST_AGENT_DIR="/home/yahwehatwork/.nst-agent"
export TOKEN="8be46d89-2ac7-45b2-acb2-33fc6866e581"
```

## 🚀 How to Use the Agent

### Method 1: Using the Helper Script (Recommended)
```bash
~/run_nst_agent.sh
```

### Method 2: Direct Execution
```bash
# First, ensure environment variables are loaded (in new terminals):
source ~/.bashrc

# Then run the agent:
agent
```

### Method 3: Manual Environment Variable Setting
```bash
NST_AGENT_DIR=/home/yahwehatwork/.nst-agent TOKEN=8be46d89-2ac7-45b2-acb2-33fc6866e581 agent
```

## 🔧 Testing the Installation

### Test Nstcli (should show token required - this means it's working):
```bash
source ~/.bashrc
nstcli info
# Expected output: "Agent is not running."
```

### Test Agent Startup:
```bash
source ~/.bashrc
timeout 5s agent
# Agent will start and timeout after 5 seconds - this is normal behavior
```

## 📝 Important Notes

1. **The agent runs as a service**: When you run `agent`, it will start and wait for connections from the Nstbrowser platform. No continuous output is expected - this is normal.

2. **To stop the agent**: Press `Ctrl+C` when it's running in the foreground.

3. **Environment variables**: The token must be provided as `TOKEN` (not `NST_TOKEN`) for the agent to recognize it.

4. **Persistent setup**: Your environment variables are already saved in `~/.bashrc` and will be available in new terminal sessions after running `source ~/.bashrc`.

## 🛠️ Troubleshooting

If you see "env TOKEN is required":
- Make sure you've sourced your bashrc: `source ~/.bashrc`
- Verify variables are set: `echo $NST_AGENT_DIR && echo $TOKEN`
- Or set them manually before running: `NST_AGENT_DIR=/home/yahwehatwork/.nst-agent TOKEN=your_token agent`

## 📁 File Locations

- Agent binary: `/home/yahwehatwork/.local/bin/agent`
- Nstcli binary: `/home/yahwehatwork/.local/bin/nstcli`
- Config file: `/home/yahwehatwork/.nst-agent/conf/config.yaml`
- Downloads: `/home/yahwehatwork/.nst-agent/download/`
- Helper script: `~/run_nst_agent.sh`

---

**Your Nstbrowser agent is now ready to use!** Simply run `~/run_nst_agent.sh` or `agent` (after sourcing bashrc) to start the service.
