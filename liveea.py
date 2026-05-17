#!/usr/bin/env python3
"""liveea.py — delegates to scripts/ea/liveea.py (full automated launcher)"""
import subprocess, sys
from pathlib import Path
script = Path(__file__).parent / "scripts" / "ea" / "liveea.py"
sys.exit(subprocess.run([sys.executable, str(script)] + sys.argv[1:]).returncode)
