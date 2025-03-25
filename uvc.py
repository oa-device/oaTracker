#!/usr/bin/env python3
import os
import subprocess
import time
import shutil

def take_photo_with_imagesnap():
    """Use the imagesnap command-line tool to capture a photo"""
    print("macOS ImageSnap Camera Capture")
    print("=============================")
    
    # Check if imagesnap is installed
    if not shutil.which("imagesnap"):
        print("ImageSnap not found. Installing with Homebrew...")
        try:
            # Try to install with Homebrew
            subprocess.run(["brew", "install", "imagesnap"], check=True)
            print("ImageSnap installed successfully")
        except subprocess.CalledProcessError:
            print("Failed to install ImageSnap with Homebrew")
            print("Please install it manually: brew install imagesnap")
            return
        except FileNotFoundError:
            print("Homebrew not found. Please install ImageSnap manually:")
            print("1. Install Homebrew from https://brew.sh/")
            print("2. Run: brew install imagesnap")
            return
    
    # Create output directory on desktop
    home_dir = os.path.expanduser("~")
    desktop_path = os.path.join(home_dir, "Desktop")
    photo_path = os.path.join(desktop_path, f"camera_photo_{int(time.time())}.jpg")
    
    print(f"Taking photo using ImageSnap...")
    print(f"Will save to: {photo_path}")
    
    # Run imagesnap to capture a photo
    try:
        # List available cameras
        print("\nAvailable cameras:")
        list_result = subprocess.run(["imagesnap", "-l"], 
                                   capture_output=True, text=True, check=True)
        print(list_result.stdout)
        
        # Take the photo
        print("\nTaking photo...")
        capture_result = subprocess.run(["imagesnap", "-w", "2", photo_path], 
                                      capture_output=True, text=True, check=False)
        
        if capture_result.returncode == 0:
            print("✓ Photo captured successfully!")
            print(f"Photo saved to: {photo_path}")
            
            # Check if the file exists and has a non-zero size
            if os.path.exists(photo_path) and os.path.getsize(photo_path) > 0:
                print(f"✓ Verified: File exists and contains data ({os.path.getsize(photo_path)} bytes)")
                
                # Try to open the photo with the default application
                print("Opening the photo...")
                subprocess.run(["open", photo_path], check=False)
            else:
                print("✗ Error: File doesn't exist or is empty")
        else:
            print(f"✗ Error capturing photo: {capture_result.stderr}")
    
    except subprocess.CalledProcessError as e:
        print(f"✗ Command failed: {e}")
        if e.stderr:
            print(f"Error output: {e.stderr}")
    except Exception as e:
        print(f"✗ Error: {str(e)}")

if __name__ == "__main__":
    take_photo_with_imagesnap()