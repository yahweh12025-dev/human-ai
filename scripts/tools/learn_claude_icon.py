
import subprocess
import sys
import time
import os

def learn_icon():
    print("🚀 Claude Icon Learning Mode Started.")
    print("--------------------------------------")
    print("👉 Please hover your mouse over the 'Copy' icon in the Claude window.")
    print("👉 I will capture the icon in 5 seconds...")
    
    time.sleep(5)
    
    try:
        # 1. Get mouse position
        pos_output = subprocess.check_output("xdotool getmouselocation", shell=True, text=True)
        coords = pos_output.strip().split()
        x = int(coords[0].split(':')[1])
        y = int(coords[1].split(':')[1])
        
        print(f"📍 Mouse position: ({x}, {y})")
        
        # 2. Create target directory
        target_dir = "/home/yahwehatwork/human-ai/agents/freqtrade/user_data"
        os.makedirs(target_dir, exist_ok=True)
        template_path = os.path.join(target_dir, "claude_copy_icon_template.png")
        
        # 3. Capture a small 40x40 patch around the mouse
        # We use xwd and convert to create a small crop
        # xwd -root -geometry 40x40+x+y
        print(f"📸 Capturing icon template from {x}, {y}...")
        cmd = f"xwd -root -geometry 40x40+{x}+{y} | convert - '{template_path}'"
        subprocess.run(cmd, shell=True, check=True)
        
        print(f"✅ SUCCESS! Icon template saved to: {template_path}")
        print("🚀 You can now run the Claude agent. It will use this image to find the button!")

    except Exception as e:
        print(f"❌ Failed to learn icon: {e}")
        print("Tip: Ensure you have 'xdotool', 'xwd', and 'convert' installed.")

if __name__ == "__main__":
    learn_icon()
