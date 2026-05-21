#!/usr/bin/env python3
"""stopea.py — Stop EA + close all MT5 positions. Run: python3 ~/human-ai/stopea.py"""
import subprocess, sys
from pathlib import Path
sys.exit(subprocess.run([sys.executable, str(Path(__file__).parent/"scripts"/"ea"/"stopea.py")] + sys.argv[1:]).returncode)
