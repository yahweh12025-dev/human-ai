
import subprocess
import sys
import time

def sample_color():
    print("🚀 Color Sampler Started.")
    print("👉 Please hover your mouse over the 'Copy' icon in the Claude window.")
    print("👉 I will capture the color in 5 seconds...")
    
    time.sleep(5)
    
    try:
        # Get mouse position
        pos_output = subprocess.check_output("xdotool getmouselocation", shell=True, text=True)
        coords = pos_output.strip().split()
        x = int(coords[0].split(':')[1])
        y = int(coords[1].split(':')[1])
        
        print(f"📍 Mouse position captured: ({x}, {y})")
        
        # Use xwd to capture a 1x1 pixel dump and then use convert to make it a PNG
        # We'll use a more direct pipe to avoid temporary file issues
        cmd = f"xwd -root -geometry 1x1+{x}+{y} | convert - '{x}_{y}.png'"
        subprocess.run(cmd, shell=True, check=True)
        
        print(f"✅ Pixel captured to {x}_{y}.png")
        print("👉 Please tell me if you see a file in your directory, or describe the color.")
        
    except Exception as e:
        print(f"❌ Failed to sample color: {e}")
        print("Tip: Try running 'which convert' to ensure ImageMagick is installed.")

if __name__ == "__main__":
    sample_color()
