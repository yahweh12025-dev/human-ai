
import subprocess
import sys

def sample_color():
    print("🚀 Color Sampler Started.")
    print("👉 Please hover your mouse over the 'Copy' icon in the Claude window.")
    print("👉 I will capture the color in 5 seconds...")
    
    import time
    time.sleep(5)
    
    # Get mouse position
    try:
        pos_output = subprocess.check_output("xdotool getmouselocation", shell=True, text=True)
        # xdotool getmouselocation output: x:123 y:456 screen:0
        coords = pos_output.strip().split()
        x = int(coords[0].split(':')[1])
        y = int(coords[1].split(':')[1])
        
        print(f"📍 Mouse position captured: ({x}, {y})")
        
        # Take a screenshot of that single pixel using xwd
        subprocess.run(f"xwd -root -geometry 1x1+{x}+{y} | convert - '{x}_{y}.png'", shell=True, check=True)
        print(f"✅ Pixel captured to {x}_{y}.png")
        print("👉 Please send me the contents of that file (or tell me the color if you can see it).")
        
    except Exception as e:
        print(f"❌ Failed to sample color: {e}")

if __name__ == "__main__":
    sample_color()
