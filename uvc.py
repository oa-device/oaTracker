import Foundation
import AVFoundation
import Quartz
import time

def list_cameras():
    """List all available cameras using AVFoundation"""
    print("Available Cameras:")
    print("-----------------")
    
    # Get all video devices
    discovery_session = AVCaptureDeviceDiscoverySession.discoverySessionWithDeviceTypes_mediaType_position_(
        [AVCaptureDeviceTypeBuiltInWideAngleCamera, AVCaptureDeviceTypeExternalUnknown],
        AVMediaTypeVideo,
        AVCaptureDevicePositionUnspecified
    )
    
    devices = discovery_session.devices()
    
    if not devices or len(devices) == 0:
        print("No cameras found.")
        return []
    
    camera_list = []
    
    for i, device in enumerate(devices):
        # Get device information
        name = device.localizedName()
        model = device.modelID()
        manufacturer = "Apple" if device.manufacturer() is None else device.manufacturer()
        
        print(f"{i+1}. {name}")
        print(f"   Manufacturer: {manufacturer}")
        print(f"   Model: {model}")
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
        if device.isFocusModeSupported_(AVCaptureModeContinuousAutoFocus):
            supports.append("Auto Focus")
        if device.isFocusModeSupported_(AVCaptureModeAutoFocus):
            supports.append("Single Auto Focus")
        if device.isFocusModeSupported_(AVCaptureModeManual):
            supports.append("Manual Focus")
        
        print(f"     - {', '.join(supports)}")
        
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

def setup_camera_session(device):
    """Set up an AVCaptureSession for the selected camera"""
    # Create capture session
    session = AVCaptureSession.alloc().init()
    session.beginConfiguration()
    
    # Set session preset
    session.setSessionPreset_(AVCaptureSessionPresetHigh)
    
    # Add device input
    device_input = AVCaptureDeviceInput.deviceInputWithDevice_error_(device, None)[0]
    if not device_input:
        print("Error creating device input")
        return None
    
    if session.canAddInput_(device_input):
        session.addInput_(device_input)
    else:
        print("Could not add device input to session")
        return None
    
    # Add video output
    video_output = AVCaptureVideoDataOutput.alloc().init()
    
    if session.canAddOutput_(video_output):
        session.addOutput_(video_output)
    else:
        print("Could not add video output to session")
        return None
    
    # Commit configuration
    session.commitConfiguration()
    
    return {
        'session': session,
        'device': device,
        'device_input': device_input,
        'video_output': video_output
    }

def control_camera(device):
    """Control camera properties using AVFoundation"""
    print(f"Controlling camera: {device.localizedName()}")
    print("--------------------------------")
    
    try:
        # Lock the device for configuration
        if not device.lockForConfiguration_(None)[0]:
            print("Could not lock device for configuration")
            return
        
        # Show current values
        print("Current Settings:")
        
        if device.isExposureModeSupported_(AVCaptureExposureModeContinuousAutoExposure):
            mode = "Auto" if device.exposureMode() == AVCaptureExposureModeContinuousAutoExposure else "Manual"
            print(f"- Exposure Mode: {mode}")
            
            if hasattr(device, 'exposureDuration'):
                duration = device.exposureDuration()
                seconds = duration.seconds + (duration.timescale / float(duration.value))
                print(f"- Exposure Duration: {seconds:.6f} seconds")
            
            if hasattr(device, 'ISO'):
                print(f"- ISO: {device.ISO()}")
        
        if device.isWhiteBalanceModeSupported_(AVCaptureWhiteBalanceModeContinuousAutoWhiteBalance):
            mode = "Auto" if device.whiteBalanceMode() == AVCaptureWhiteBalanceModeContinuousAutoWhiteBalance else "Manual"
            print(f"- White Balance Mode: {mode}")
            
            if hasattr(device, 'deviceWhiteBalanceGains'):
                gains = device.deviceWhiteBalanceGains()
                print(f"- White Balance Gains: R={gains.redGain}, G={gains.greenGain}, B={gains.blueGain}")
        
        if device.isFocusModeSupported_(AVCaptureModeContinuousAutoFocus):
            if device.focusMode() == AVCaptureModeContinuousAutoFocus:
                mode = "Continuous Auto"
            elif device.focusMode() == AVCaptureModeAutoFocus:
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
                    min_iso = device.activeFormat().minISO()
                    max_iso = device.activeFormat().maxISO()
                    current_iso = device.ISO()
                    
                    print(f"Current ISO: {current_iso}")
                    print(f"Valid range: {min_iso} - {max_iso}")
                    
                    try:
                        new_iso = float(input("Enter new ISO value: "))
                        if min_iso <= new_iso <= max_iso:
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
                    print("Camera must be in Manual Exposure mode first")
            
            elif choice == "3":
                # Set exposure duration
                if device.exposureMode() == AVCaptureExposureModeCustom:
                    min_duration = device.activeFormat().minExposureDuration()
                    max_duration = device.activeFormat().maxExposureDuration()
                    current = device.exposureDuration()
                    
                    min_seconds = min_duration.value / float(min_duration.timescale)
                    max_seconds = max_duration.value / float(max_duration.timescale)
                    current_seconds = current.value / float(current.timescale)
                    
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
                    print("Camera must be in Manual Exposure mode first")
            
            elif choice == "4":
                # Toggle focus mode
                if device.isFocusModeSupported_(AVCaptureModeContinuousAutoFocus) and \
                   device.isFocusModeSupported_(AVCaptureModeManual):
                    if device.focusMode() == AVCaptureModeContinuousAutoFocus:
                        print("Switching to Manual Focus")
                        device.setFocusMode_(AVCaptureModeManual)
                    else:
                        print("Switching to Auto Focus")
                        device.setFocusMode_(AVCaptureModeContinuousAutoFocus)
                else:
                    print("Camera does not support toggling focus mode")
            
            elif choice == "5":
                # Set focus position
                if device.focusMode() == AVCaptureModeManual:
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