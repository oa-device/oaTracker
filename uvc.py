from Foundation import *
from AVFoundation import *
import time
import objc

def list_cameras():
    """List all available cameras"""
    print("Available Cameras:")
    print("-----------------")
    
    # Get all video devices
    devices = AVCaptureDevice.devicesWithMediaType_(AVMediaTypeVideo)
    
    if not devices or len(devices) == 0:
        print("No cameras found.")
        return []
    
    camera_list = []
    
    for i, device in enumerate(devices):
        # Get device information
        name = device.localizedName()
        model_id = "Unknown"
        if hasattr(device, 'modelID'):
            model_id = device.modelID()
        
        unique_id = device.uniqueID()
        
        print(f"{i+1}. {name}")
        print(f"   Model ID: {model_id}")
        print(f"   Unique ID: {unique_id}")
        
        # Check supported features in a safer way
        features = []
        
        # Focus
        if hasattr(device, 'isFocusModeSupported_'):
            # Mode 0 = Locked, 1 = Auto, 2 = Continuous Auto
            if device.isFocusModeSupported_(0):
                features.append("Manual Focus")
            if device.isFocusModeSupported_(1):
                features.append("Auto Focus")
            if device.isFocusModeSupported_(2):
                features.append("Continuous Auto Focus")
        
        # Exposure
        if hasattr(device, 'isExposureModeSupported_'):
            # Mode 0 = Locked, 1 = Auto, 2 = Continuous Auto, 3 = Custom
            if device.isExposureModeSupported_(0):
                features.append("Locked Exposure")
            if device.isExposureModeSupported_(3):
                features.append("Manual Exposure")
            if device.isExposureModeSupported_(2):
                features.append("Auto Exposure")
        
        if features:
            print(f"   Supported Features: {', '.join(features)}")
        else:
            print("   No detectable features")
        
        print()
        camera_list.append(device)
    
    return camera_list

def control_camera(device):
    """Control camera properties"""
    print(f"\nControlling camera: {device.localizedName()}")
    print("--------------------------------")
    
    # Try to get current settings
    try:
        # Lock device configuration
        success, error = device.lockForConfiguration_(None)
        if not success:
            print(f"Could not lock device for configuration: {error}")
            return
        
        # Get current settings
        print("Current Settings:")
        
        # Focus
        if hasattr(device, 'focusMode'):
            focus_mode = device.focusMode()
            mode_str = "Unknown"
            if focus_mode == 0:
                mode_str = "Locked"
            elif focus_mode == 1:
                mode_str = "Auto"
            elif focus_mode == 2:
                mode_str = "Continuous Auto"
            print(f"- Focus Mode: {mode_str}")
            
            if hasattr(device, 'lensPosition'):
                position = device.lensPosition()
                print(f"- Focus Position: {position:.2f} (0=far, 1=near)")
        
        # Exposure
        if hasattr(device, 'exposureMode'):
            exposure_mode = device.exposureMode()
            mode_str = "Unknown"
            if exposure_mode == 0:
                mode_str = "Locked"
            elif exposure_mode == 1:
                mode_str = "Auto"
            elif exposure_mode == 2:
                mode_str = "Continuous Auto"
            elif exposure_mode == 3:
                mode_str = "Custom"
            print(f"- Exposure Mode: {mode_str}")
            
            if hasattr(device, 'ISO'):
                iso = device.ISO()
                print(f"- ISO: {iso}")
        
        # Options menu
        print("\nControl Options:")
        print("1. Toggle Auto/Manual Focus")
        print("2. Set Focus Position")
        print("3. Toggle Auto/Manual Exposure")
        print("4. Set ISO")
        print("0. Exit")
        
        while True:
            choice = input("\nEnter option (0-4): ")
            
            if choice == "0":
                break
                
            elif choice == "1":
                # Toggle focus mode
                if hasattr(device, 'focusMode') and hasattr(device, 'setFocusMode_'):
                    current_mode = device.focusMode()
                    
                    if current_mode == 2:  # Continuous Auto
                        print("Switching to Manual Focus")
                        device.setFocusMode_(0)  # Locked
                    else:
                        print("Switching to Auto Focus")
                        device.setFocusMode_(2)  # Continuous Auto
                else:
                    print("Focus mode control not supported")
            
            elif choice == "2":
                # Set focus position
                if hasattr(device, 'setFocusModeLockedWithLensPosition_completionHandler_'):
                    try:
                        position = float(input("Enter focus position (0.0-1.0): "))
                        if 0 <= position <= 1:
                            # Set focus mode to locked and set position
                            device.setFocusModeLockedWithLensPosition_completionHandler_(
                                position, None)
                            print(f"Focus position set to {position:.2f}")
                        else:
                            print("Position must be between 0 and 1")
                    except ValueError:
                        print("Invalid input, must be a number")
                else:
                    print("Focus position control not supported")
            
            elif choice == "3":
                # Toggle exposure mode
                if hasattr(device, 'exposureMode') and hasattr(device, 'setExposureMode_'):
                    current_mode = device.exposureMode()
                    
                    if current_mode == 2:  # Continuous Auto
                        print("Switching to Manual Exposure")
                        device.setExposureMode_(3)  # Custom
                    else:
                        print("Switching to Auto Exposure")
                        device.setExposureMode_(2)  # Continuous Auto
                else:
                    print("Exposure mode control not supported")
            
            elif choice == "4":
                # Set ISO
                if hasattr(device, 'setExposureModeCustomWithDuration_ISO_completionHandler_'):
                    # Try to get valid ISO range
                    min_iso = 50
                    max_iso = 1600
                    
                    if hasattr(device.activeFormat(), 'minISO') and hasattr(device.activeFormat(), 'maxISO'):
                        min_iso = device.activeFormat().minISO()
                        max_iso = device.activeFormat().maxISO()
                    
                    current_iso = device.ISO()
                    print(f"Current ISO: {current_iso}")
                    print(f"Valid range: {min_iso} - {max_iso}")
                    
                    try:
                        new_iso = float(input(f"Enter new ISO value ({min_iso}-{max_iso}): "))
                        if min_iso <= new_iso <= max_iso:
                            # Keep current exposure duration
                            device.setExposureModeCustomWithDuration_ISO_completionHandler_(
                                device.exposureDuration(), new_iso, None)
                            print(f"ISO set to {new_iso}")
                        else:
                            print(f"ISO must be between {min_iso} and {max_iso}")
                    except ValueError:
                        print("Invalid input, must be a number")
                else:
                    print("ISO control not supported")
            
            else:
                print("Invalid option")
    
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        # Unlock device
        if hasattr(device, 'unlockForConfiguration'):
            device.unlockForConfiguration()

def main():
    print("Simple macOS Camera Control")
    print("==========================")
    
    # List cameras
    cameras = list_cameras()
    
    if not cameras:
        return
    
    # Select camera
    selected = cameras[0]
    
    if len(cameras) > 1:
        try:
            choice = int(input("\nSelect camera number: ")) - 1
            if 0 <= choice < len(cameras):
                selected = cameras[choice]
            else:
                print("Invalid selection, using first camera")
        except ValueError:
            print("Invalid input, using first camera")
    
    # Control camera
    control_camera(selected)
    
    print("\nCamera control ended")

if __name__ == "__main__":
    main()