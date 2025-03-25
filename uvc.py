from Foundation import *
from AVFoundation import *
from Quartz import *
import time
import objc

def list_cameras():
    """List all available cameras using AVFoundation"""
    print("Available Cameras:")
    print("-----------------")
    
    # Get all video devices - using the older API that's more compatible
    devices = AVCaptureDevice.devicesWithMediaType_(AVMediaTypeVideo)
    
    if not devices or len(devices) == 0:
        print("No cameras found.")
        return []
    
    camera_list = []
    
    for i, device in enumerate(devices):
        # Get device information
        name = device.localizedName()
        model_id = device.modelID() if hasattr(device, 'modelID') else "Unknown"
        manufacturer = "Unknown"
        if hasattr(device, 'manufacturer'):
            if device.manufacturer():
                manufacturer = device.manufacturer()
        
        print(f"{i+1}. {name}")
        print(f"   Model ID: {model_id}")
        print(f"   Unique ID: {device.uniqueID()}")
        
        # Check which properties are supported
        print(f"   Supported Properties:")
        
        supports = []
        
        if device.isExposureModeSupported_(AVCaptureExposureModeContinuousAutoExposure):
            supports.append("Auto Exposure")
        if device.isExposureModeSupported_(AVCaptureExposureModeCustom):
            supports.append("Manual Exposure")
        if device.isWhiteBalanceModeSupported_(AVCaptureWhiteBalanceModeContinuousAutoWhiteBalance):
            supports.append("Auto White Balance")
        if device.isWhiteBalanceModeSupported_(AVCaptureWhiteBalanceModeCustom):
            supports.append("Manual White Balance")
        if device.isFocusModeSupported_(AVCaptureFocusModeContinuousAutoFocus):
            supports.append("Auto Focus")
        if device.isFocusModeSupported_(AVCaptureFocusModeAutoFocus):
            supports.append("Single Auto Focus")
        if device.isFocusModeSupported_(AVCaptureFocusModeManual):
            supports.append("Manual Focus")
        
        if supports:
            print(f"     - {', '.join(supports)}")
        else:
            print("     - None detected")
        
        # Check for adjustable properties
        props = []
        
        if device.isAdjustingExposure():
            props.append("Exposure")
        if device.isAdjustingFocus():
            props.append("Focus")
        if device.isAdjustingWhiteBalance():
            props.append("White Balance")
        
        if props:
            print(f"   Currently Adjusting: {', '.join(props)}")
        
        print()
        
        camera_list.append(device)
    
    return camera_list

def control_camera(device):
    """Control camera properties using AVFoundation"""
    print(f"Controlling camera: {device.localizedName()}")
    print("--------------------------------")
    
    try:
        # Lock the device for configuration
        success, error = device.lockForConfiguration_(None)
        if not success:
            print(f"Could not lock device for configuration: {error}")
            return
        
        # Show current values
        print("Current Settings:")
        
        if device.isExposureModeSupported_(AVCaptureExposureModeContinuousAutoExposure):
            mode = "Auto" if device.exposureMode() == AVCaptureExposureModeContinuousAutoExposure else "Manual"
            print(f"- Exposure Mode: {mode}")
            
            if hasattr(device, 'exposureDuration'):
                duration = device.exposureDuration()
                # Handle CMTime structure
                seconds = duration.value / float(duration.timescale) if duration.timescale != 0 else 0
                print(f"- Exposure Duration: {seconds:.6f} seconds")
            
            if hasattr(device, 'ISO'):
                print(f"- ISO: {device.ISO()}")
        
        if device.isWhiteBalanceModeSupported_(AVCaptureWhiteBalanceModeContinuousAutoWhiteBalance):
            mode = "Auto" if device.whiteBalanceMode() == AVCaptureWhiteBalanceModeContinuousAutoWhiteBalance else "Manual"
            print(f"- White Balance Mode: {mode}")
            
            if hasattr(device, 'deviceWhiteBalanceGains'):
                gains = device.deviceWhiteBalanceGains()
                # AVCaptureWhiteBalanceGains is a struct, access may vary
                if hasattr(gains, 'redGain'):
                    print(f"- White Balance Gains: R={gains.redGain}, G={gains.greenGain}, B={gains.blueGain}")
        
        if device.isFocusModeSupported_(AVCaptureFocusModeContinuousAutoFocus):
            if device.focusMode() == AVCaptureFocusModeContinuousAutoFocus:
                mode = "Continuous Auto"
            elif device.focusMode() == AVCaptureFocusModeAutoFocus:
                mode = "Single Auto"
            else:
                mode = "Manual"
                
            print(f"- Focus Mode: {mode}")
            
            if hasattr(device, 'lensPosition'):
                print(f"- Focus Position: {device.lensPosition()}")
        
        print("\nControl Options:")
        print("1. Toggle Auto/Manual Exposure")
        print("2. Set ISO (Manual Exposure)")
        print("3. Set Exposure Duration (Manual Exposure)")
        print("4. Toggle Auto/Manual Focus")
        print("5. Set Focus Position (Manual Focus)")
        print("6. Toggle Auto/Manual White Balance")
        print("0. Exit")
        
        while True:
            choice = input("\nEnter option number (0 to exit): ")
            
            if choice == "0":
                break
            
            elif choice == "1":
                # Toggle exposure mode
                if device.isExposureModeSupported_(AVCaptureExposureModeContinuousAutoExposure) and \
                   device.isExposureModeSupported_(AVCaptureExposureModeCustom):
                    if device.exposureMode() == AVCaptureExposureModeContinuousAutoExposure:
                        print("Switching to Manual Exposure")
                        device.setExposureMode_(AVCaptureExposureModeCustom)
                    else:
                        print("Switching to Auto Exposure")
                        device.setExposureMode_(AVCaptureExposureModeContinuousAutoExposure)
                else:
                    print("Camera does not support toggling exposure mode")
            
            elif choice == "2":
                # Set ISO
                if device.exposureMode() == AVCaptureExposureModeCustom:
                    if hasattr(device.activeFormat(), 'minISO') and hasattr(device.activeFormat(), 'maxISO'):
                        min_iso = device.activeFormat().minISO()
                        max_iso = device.activeFormat().maxISO()
                        current_iso = device.ISO()
                        
                        print(f"Current ISO: {current_iso}")
                        print(f"Valid range: {min_iso} - {max_iso}")
                        
                        try:
                            new_iso = float(input("Enter new ISO value: "))
                            if min_iso <= new_iso <= max_iso:
                                # Use the correct method name
                                device.setExposureModeCustomWithDuration_ISO_completionHandler_(
                                    device.exposureDuration(),
                                    new_iso,
                                    None
                                )
                                print(f"ISO set to {new_iso}")
                            else:
                                print(f"ISO must be between {min_iso} and {max_iso}")
                        except ValueError:
                            print("Invalid input. Please enter a number.")
                    else:
                        print("Camera does not support ISO adjustment")
                else:
                    print("Camera must be in Manual Exposure mode first")
            
            elif choice == "3":
                # Set exposure duration
                if device.exposureMode() == AVCaptureExposureModeCustom:
                    if hasattr(device.activeFormat(), 'minExposureDuration') and hasattr(device.activeFormat(), 'maxExposureDuration'):
                        min_duration = device.activeFormat().minExposureDuration()
                        max_duration = device.activeFormat().maxExposureDuration()
                        current = device.exposureDuration()
                        
                        # Handle CMTime structure
                        min_seconds = min_duration.value / float(min_duration.timescale) if min_duration.timescale != 0 else 0
                        max_seconds = max_duration.value / float(max_duration.timescale) if max_duration.timescale != 0 else 0
                        current_seconds = current.value / float(current.timescale) if current.timescale != 0 else 0
                        
                        print(f"Current Exposure: {current_seconds:.6f} seconds")
                        print(f"Valid range: {min_seconds:.6f} - {max_seconds:.6f} seconds")
                        
                        try:
                            new_seconds = float(input("Enter new exposure duration in seconds: "))
                            if min_seconds <= new_seconds <= max_seconds:
                                # Convert to CMTime
                                timescale = 1000000  # Use microsecond precision
                                value = int(new_seconds * timescale)
                                new_duration = CMTimeMake(value, timescale)
                                
                                device.setExposureModeCustomWithDuration_ISO_completionHandler_(
                                    new_duration,
                                    device.ISO(),
                                    None
                                )
                                print(f"Exposure duration set to {new_seconds:.6f} seconds")
                            else:
                                print(f"Duration must be between {min_seconds:.6f} and {max_seconds:.6f} seconds")
                        except ValueError:
                            print("Invalid input. Please enter a number.")
                    else:
                        print("Camera does not support exposure duration adjustment")
                else:
                    print("Camera must be in Manual Exposure mode first")
            
            elif choice == "4":
                # Toggle focus mode
                if device.isFocusModeSupported_(AVCaptureFocusModeContinuousAutoFocus) and \
                   device.isFocusModeSupported_(AVCaptureFocusModeManual):
                    if device.focusMode() == AVCaptureFocusModeContinuousAutoFocus:
                        print("Switching to Manual Focus")
                        device.setFocusMode_(AVCaptureFocusModeManual)
                    else:
                        print("Switching to Auto Focus")
                        device.setFocusMode_(AVCaptureFocusModeContinuousAutoFocus)
                else:
                    print("Camera does not support toggling focus mode")
            
            elif choice == "5":
                # Set focus position
                if device.focusMode() == AVCaptureFocusModeManual:
                    current = device.lensPosition()
                    print(f"Current Focus Position: {current}")
                    print("Valid range: 0.0 (far) - 1.0 (near)")
                    
                    try:
                        new_position = float(input("Enter new focus position (0.0-1.0): "))
                        if 0.0 <= new_position <= 1.0:
                            device.setFocusModeLockedWithLensPosition_completionHandler_(
                                new_position, 
                                None
                            )
                            print(f"Focus position set to {new_position}")
                        else:
                            print("Position must be between 0.0 and 1.0")
                    except ValueError:
                        print("Invalid input. Please enter a number.")
                else:
                    print("Camera must be in Manual Focus mode first")
            
            elif choice == "6":
                # Toggle white balance mode
                if device.isWhiteBalanceModeSupported_(AVCaptureWhiteBalanceModeContinuousAutoWhiteBalance) and \
                   device.isWhiteBalanceModeSupported_(AVCaptureWhiteBalanceModeCustom):
                    if device.whiteBalanceMode() == AVCaptureWhiteBalanceModeContinuousAutoWhiteBalance:
                        print("Switching to Manual White Balance")
                        device.setWhiteBalanceMode_(AVCaptureWhiteBalanceModeCustom)
                    else:
                        print("Switching to Auto White Balance")
                        device.setWhiteBalanceMode_(AVCaptureWhiteBalanceModeContinuousAutoWhiteBalance)
                else:
                    print("Camera does not support toggling white balance mode")
            
            else:
                print("Invalid option")
    
    except Exception as e:
        print(f"Error controlling camera: {e}")
    
    finally:
        # Unlock device
        device.unlockForConfiguration()

def main():
    print("macOS Camera Control with AVFoundation")
    print("=====================================")
    
    # List available cameras
    cameras = list_cameras()
    
    if not cameras:
        print("No cameras available.")
        return
    
    # Select camera
    selected_camera = cameras[0]
    
    if len(cameras) > 1:
        try:
            choice = int(input("\nSelect camera (number): ")) - 1
            if 0 <= choice < len(cameras):
                selected_camera = cameras[choice]
            else:
                print("Invalid selection. Using the first camera.")
        except ValueError:
            print("Invalid input. Using the first camera.")
    
    # Control camera
    control_camera(selected_camera)
    
    print("\nCamera control session ended.")

if __name__ == "__main__":
    main()