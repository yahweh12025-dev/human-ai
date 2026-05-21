#!/usr/bin/env python3
"""
Full Sync Script - Syncs project state to Obsidian vault and Google Drive backup.
Runs all sync operations: tasks, docs, configs, and state.
"""

import os
import json
import shutil
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path("/home/yahwehatwork/human-ai")
OBSIDIAN_VAULT = Path("/home/yahwehatwork/obsidian-vault")
GDRIVE_BACKUP = Path("/home/yahwehatwork/gdrive/backups")


def sync_to_obsidian():
    """Sync key project state to Obsidian vault"""
    print("📒 Syncing to Obsidian vault...")

    # Sync unified tasks
    src_tasks = PROJECT_ROOT / "unified_tasks.json"
    dst_tasks = OBSIDIAN_VAULT / "HumanAI" / "state" / "unified_tasks.json"
    dst_tasks.parent.mkdir(parents=True, exist_ok=True)
    if src_tasks.exists():
        shutil.copy2(src_tasks, dst_tasks)
        print(f"  ✅ unified_tasks.json → Obsidian")

    # Sync roadmap
    src_roadmap = PROJECT_ROOT / "docs" / "ROADMAP.md"
    dst_roadmap = OBSIDIAN_VAULT / "HumanAI" / "docs" / "ROADMAP.md"
    dst_roadmap.parent.mkdir(parents=True, exist_ok=True)
    if src_roadmap.exists():
        shutil.copy2(src_roadmap, dst_roadmap)
        print(f"  ✅ ROADMAP.md → Obsidian")

    # Sync integration status
    src_integ = PROJECT_ROOT / "data" / "data" / "logs" / "integration_verification.json"
    dst_integ = OBSIDIAN_VAULT / "HumanAI" / "state" / "integrations.json"
    if src_integ.exists():
        shutil.copy2(src_integ, dst_integ)
        print(f"  ✅ integrations.json → Obsidian")

    # Sync key docs
    docs_to_sync = [
        "docs/social_media_agent_architecture.md",
        "docs/strategy_improvement_analysis.md",
        "CLAUDE.md",
        "README.md",
    ]
    for doc in docs_to_sync:
        src = PROJECT_ROOT / doc
        dst = OBSIDIAN_VAULT / "HumanAI" / doc
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.exists():
            shutil.copy2(src, dst)
            print(f"  ✅ {doc} → Obsidian")

    # Sync system state snapshot
    state = {
        "last_sync": datetime.now().isoformat(),
        "project_root": str(PROJECT_ROOT),
        "agents": ["OpenClaw", "Hermes", "OpenCode", "Pi.dev", "FreqTrade", "EA", "SocialMedia"],
        "active_services": ["OpenRouter", "Groq", "Telegram", "Binance Testnet"],
    }
    state_file = OBSIDIAN_VAULT / "HumanAI" / "state" / "system_state.json"
    with open(state_file, 'w') as f:
        json.dump(state, f, indent=2)
    print(f"  ✅ system_state.json → Obsidian")


def sync_to_gdrive():
    """Sync critical data to Google Drive backup"""
    print("\n☁️  Syncing to Google Drive backup...")

    backup_dir = GDRIVE_BACKUP / f"human_ai_{datetime.now().strftime('%Y%m%d')}"
    backup_dir.mkdir(parents=True, exist_ok=True)

    # Backup configs (no secrets)
    configs_dir = backup_dir / "configs"
    configs_dir.mkdir(exist_ok=True)

    config_files = [
        "core/config/dify_graphify_config.json",
        "core/config/agent_config.yaml",
        "config/social_cron.yaml",
        "unified_tasks.json",
    ]
    for cfg in config_files:
        src = PROJECT_ROOT / cfg
        if src.exists():
            shutil.copy2(src, configs_dir / src.name)
            print(f"  ✅ {cfg} → GDrive")

    # Backup docs
    docs_dir = backup_dir / "docs"
    docs_dir.mkdir(exist_ok=True)
    for doc in (PROJECT_ROOT / "docs").glob("*.md"):
        shutil.copy2(doc, docs_dir / doc.name)
    print(f"  ✅ docs/ → GDrive")

    # Backup trading results
    trading_dir = backup_dir / "trading"
    trading_dir.mkdir(exist_ok=True)
    bt_dir = PROJECT_ROOT / "validation" / "freqtrade_backtests"
    if bt_dir.exists():
        for bt in bt_dir.glob("*.json"):
            shutil.copy2(bt, trading_dir / bt.name)
        print(f"  ✅ backtest results → GDrive")

    # Backup EA data
    ea_data = PROJECT_ROOT / "EA" / "data"
    if ea_data.exists():
        ea_backup = backup_dir / "EA_data"
        ea_backup.mkdir(exist_ok=True)
        for f in ea_data.glob("*"):
            if f.is_file():
                shutil.copy2(f, ea_backup / f.name)
        print(f"  ✅ EA data → GDrive")


def sync_obsidian_memory():
    """Sync Obsidian memory entries back to project"""
    print("\n🧠 Syncing Obsidian memory → project...")

    memory_src = OBSIDIAN_VAULT / "Memory"
    memory_dst = PROJECT_ROOT / "data" / "obsidian" / "System_State"
    memory_dst.mkdir(parents=True, exist_ok=True)

    if memory_src.exists():
        for md_file in memory_src.glob("*.md"):
            shutil.copy2(md_file, memory_dst / md_file.name)
        print(f"  ✅ {len(list(memory_src.glob('*.md')))} memory files synced")


def main():
    print("=" * 60)
    print(f"Full Sync - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    sync_to_obsidian()
    sync_to_gdrive()
    sync_obsidian_memory()

    print(f"\n{'=' * 60}")
    print("✅ Full sync complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
