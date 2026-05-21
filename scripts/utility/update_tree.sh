#!/bin/bash

# Script to update the repository tree view
cd /home/yahwehatwork

# Generate tree view excluding common directories and files that clutter the view
tree -L 3 \
  -I 'node_modules|.git|__pycache__|.browser-profile|.hermes|.cache|.config|.local|.npm|.npm-global|.nvm|.opencode|.openclaw|.mission-control|.pi|.ssh|.viminfo|.xauthority|.ICEauthority|.xsession|.xsession-errors|.bash_history|.bashrc|.profile|.inputrc|.gtkrc-2.0|.mozilla|.thunderbird|.libreoffice|.jupyter|.ipython|.python_history|.python_eggs|.subversion|.gem|.bundle|.rvm|.cargo|.rustup|.gradle|.m2|.sbt|.lein|.npmrc|.yarnrc|.yarn|.pnpm|.pnpm-store|.electron|.yarn-cache|.npm-debug.log|.yarn-debug.log.*|.pnpm-debug.log*|output|test_scripts|downloads|env_configs|error_logs|fre*|venv-*|.hermes|hermes_response.txt|FINAL_SETUP_SUMMARY.md|masterseed_py|run_nst_agent.sh|security_audit_summary.txt|agent-review|apps|backups|browsers|claude_sessions|conversation_logs|docs|human-ai|Obsidian|projects|pulseaudio-*|thinclient_drives|trading_strategies|workspace|*' \
  --charset=ascii \
  > /home/yahwehatwork/human-ai/repo_tree.txt

echo "Tree view updated at $(date)" >> /home/yahwehatwork/human-ai/tree_update.log