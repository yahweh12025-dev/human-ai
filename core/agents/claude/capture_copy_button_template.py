#!/usr/bin/env python3
"""
capture_copy_button_template.py

Run this ONCE to capture a screenshot crop of Claude Desktop's copy button.
The saved image is used as the CV template for claude_agent_improved.py.

Usage:
    python3 capture_copy_button_template.py

Steps it guides you through:
    1. Opens Claude Desktop and gets a response showing on screen.
    2. Hover your mouse over the copy button (the clipboard icon that appears
       when you hover the bottom-right of a response bubble).
    3. Press ENTER in this terminal — it will screenshot and crop around
       your current cursor position.
    4. Saves the template to the correct path.
"""

import subprocess
import time
import os
import sys

try:
    import pyautogui
    import cv2
    import numpy as np
except ImportError:
    print("Install deps first: pip install pyautogui opencv-python --break-system-packages")
    sys.exit(1)

TEMPLATE_PATH = "/home/yahwehatwork/human-ai/core/agents/claude/templates/copy_button_template.png"
CROP_PADDING = 20  # px around cursor to crop as the template


def main():
    os.makedirs(os.path.dirname(TEMPLATE_PATH), exist_ok=True)

    print("=" * 60)
    print("Copy Button Template Capture")
    print("=" * 60)
    print()
    print("1. Open Claude Desktop and send a message so a response is visible.")
    print("2. Hover your mouse directly over the copy button icon")
    print("   (the clipboard icon in the bottom-right of the last response).")
    print("3. Come back here and press ENTER — don't move the mouse!")
    print()
    input("Press ENTER when your cursor is hovering over the copy button...")

    # Get current cursor position
    pos = pyautogui.position()
    x, y = pos.x, pos.y
    print(f"\n📍 Cursor position: ({x}, {y})")

    # Screenshot region around the cursor
    region_x = max(0, x - CROP_PADDING)
    region_y = max(0, y - CROP_PADDING)
    region_w = CROP_PADDING * 2
    region_h = CROP_PADDING * 2

    screenshot = pyautogui.screenshot(region=(region_x, region_y, region_w, region_h))
    img_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

    cv2.imwrite(TEMPLATE_PATH, img_cv)
    print(f"✅ Template saved to: {TEMPLATE_PATH}")
    print(f"   Size: {img_cv.shape[1]}x{img_cv.shape[0]} px")

    # Also save a debug full-screen shot so you can verify
    debug_path = "/tmp/template_capture_fullscreen.png"
    full = pyautogui.screenshot()
    full_cv = cv2.cvtColor(np.array(full), cv2.COLOR_RGB2BGR)
    # Draw a red rectangle where we cropped
    cv2.rectangle(full_cv, (region_x, region_y),
                  (region_x + region_w, region_y + region_h), (0, 0, 255), 2)
    cv2.imwrite(debug_path, full_cv)
    print(f"   Full-screen debug shot (with red crop box): {debug_path}")
    print()
    print("You can now run claude_agent_improved.py — CV template matching is ready.")


if __name__ == "__main__":
    main()
