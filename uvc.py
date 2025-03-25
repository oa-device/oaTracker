from Foundation import *
from AVFoundation import *
from Cocoa import *
import time
import objc
import os
import datetime

class StillImageOutput(NSObject):
    """Helper class to handle photo capture callbacks"""
    def initWithPath_(self, save_path):
        self = objc.super(StillImageOutput, self).init()
        if self is None:
            return None
        self.save_path = save_path
        return self
    
    def captureOutput_didOutputSampleBuffer_fromConnection_(self, output, sample_buffer, connection):
        print("Captured photo!")
        # Convert CMSampleBuffer to image
        imageBuffer = CMSampleBufferGetImageBuffer(sample_buffer)
        ciImage = CIImage.imageWithCVPixelBuffer_(imageBuffer)
        context = CIContext.contextWithOptions_(None)
        cgImage = context.createCGImage_fromRect_(ciImage, ciImage.extent())
        
        # Create NSImage
        image = NSImage.alloc().initWithCGImage_size_(cgImage, NSZeroSize)
        
        # Save to file
        image_data = image.TIFFRepresentation()
        bitmap_rep = NSBitmapImageRep.imageRepWithData_(image_data)
        png_data = bitmap_rep.representationUsingType_properties_(NSPNGFileType, None)
        png_data.writeToFile_atomically_(self.save_path, True)
        print(f"Saved image to: {self.save_path}")

def capture_photo(session, file_path):
    """Capture a photo from the active session and save it to file_path"""
    print("Taking photo...")
    
    # Create a still image output
    still_output = AVCaptureStillImageOutput.alloc().init()
    still_output.setOutputSettings_({AVVideoCodecKey: AVVideoCodecJPEG})
    
    if session.canAddOutput_(still_output):
        session.addOutput_(still_output)
    else:
        print("Error: Cannot add still image output to session")
        return False
    
    # Get the connection
    connection = still_output.connectionWithMediaType_(AVMediaTypeVideo)
    if not connection:
        print("Error: No valid connection for video output")
        return False
    
    # Create delegate for handling the captured image
    delegate = StillImageOutput.alloc().initWithPath_(file_path)
    
    # Capture the image
    still_output.captureStillImageAsynchronouslyFromConnection_completionHandler_(
        connection,
        lambda sampleBuffer, error: delegate.captureOutput_didOutputSampleBuffer_fromConnection_(
            still_output, sampleBuffer, connection)
        if not error else print(f"Error capturing image: {error}")
    )
    
    # Wait a moment for the capture to complete
    time.sleep(1.5)
    
    # Remove the output
    session.removeOutput_(still_output)
    
    return True

def get_desktop_path():
    """Get the path to the user's desktop"""
    home_dir = os.path.expanduser("~")
    desktop_path = os.path.join(home_dir, "Desktop")
    return desktop_path

def control_anker_camera():
    """Control Anker PowerConf C200 camera with photo capture"""
    print("Anker PowerConf C200 Control Tool with Photo Capture")
    print("==================================================")
    
    # Find the Anker camera
    devices = AVCaptureDevice.devicesWithMediaType_(AVMediaTypeVideo)
    
    anker_camera = None
    for device in devices:
        if "Anker" in device.localizedName():
            anker_camera = device
            break
    
    if not anker_camera:
        print("Anker PowerConf C200 camera not found!")
        return
    
    print(f"Found camera: {anker_camera.localizedName()}")
    print(f"Model: {anker_camera.modelID()}")
    print(f"Unique ID: {anker_camera.uniqueID()}")
    
    # Set up capture session
    session = AVCaptureSession.alloc().init()
    session.beginConfiguration()
    
    # Set session quality
    session.setSessionPreset_(AVCaptureSessionPresetPhoto)
    
    # Add device input
    success, error = AVCaptureDeviceInput.deviceInputWithDevice_error_(anker_camera, None)
    if not success:
        print(f"Error creating device input: {error}")
        return
    
    device_input = success
    
    if session.canAddInput_(device_input):
        session.addInput_(device_input)
    else:
        print("Error: Cannot add device input to session")
        return
    
    # Commit configuration and start the session
    session.commitConfiguration()
    session.startRunning()
    
    print("Camera session started")
    
    # Take initial photo
    desktop_path = get_desktop_path()
    initial_photo_path = os.path.join(desktop_path, f"anker_initial_{int(time.time())}.png")
    capture_photo(session, initial_photo_path)
    
    # Try to lock for configuration
    success, error = anker_camera.lockForConfiguration_(None)
    if not success:
        print(f"Could not lock camera for configuration: {error}")
        session.stopRunning()
        return
    
    try:
        # Check supported features
        print("\nChecking camera capabilities...")
        
        # Check for zoom
        zoom_supported = False
        if hasattr(anker_camera, 'videoZoomFactor'):
            zoom_supported = True
            current_zoom = anker_camera.videoZoomFactor()
            print(f"Digital Zoom: Supported (Current: {current_zoom:.2f}x)")
            
            if hasattr(anker_camera, 'activeFormat') and hasattr(anker_camera.activeFormat(), 'videoMaxZoomFactor'):
                max_zoom = anker_camera.activeFormat().videoMaxZoomFactor()
                print(f"Max Zoom: {max_zoom:.2f}x")
            else:
                print("Max Zoom: Unknown")
        else:
            print("Digital Zoom: Not supported")
        
        # Check for pan/tilt
        pan_tilt_supported = False
        if hasattr(anker_camera, 'centerPoint'):
            pan_tilt_supported = True
            center = anker_camera.centerPoint()
            print(f"Pan/Tilt: Supported (Current: X={center.x:.2f}, Y={center.y:.2f})")
        else:
            print("Pan/Tilt: Not supported")
        
        # Check for focus
        focus_supported = False
        if hasattr(anker_camera, 'focusPointOfInterest'):
            focus_supported = True
            focus_point = anker_camera.focusPointOfInterest()
            print(f"Focus Point: Supported (Current: X={focus_point.x:.2f}, Y={focus_point.y:.2f})")
        else:
            print("Focus Point: Not supported")
        
        if hasattr(anker_camera, 'lensPosition'):
            print(f"Focus Position: Supported (Current: {anker_camera.lensPosition():.2f})")
        else:
            print("Focus Position: Not supported")
        
        # Menu options
        print("\nControl Options:")
        print("1. Set Digital Zoom")
        print("2. Set Pan/Tilt (Center Point)")
        print("3. Set Focus Position")
        print("4. Set Focus Point")
        print("5. Toggle Auto/Manual Focus")
        print("6. Take Photo Only")
        print("0. Exit")
        
        while True:
            choice = input("\nEnter option (0-6): ")
            
            if choice == "0":
                break
            
            elif choice == "1" and zoom_supported:
                try:
                    # Get max zoom
                    max_zoom = 5.0  # Default if we can't get actual max
                    if hasattr(anker_camera.activeFormat(), 'videoMaxZoomFactor'):
                        max_zoom = anker_camera.activeFormat().videoMaxZoomFactor()
                    
                    current_zoom = anker_camera.videoZoomFactor()
                    print(f"Current zoom: {current_zoom:.2f}x")
                    print(f"Valid range: 1.0 - {max_zoom:.2f}")
                    
                    # Get new zoom factor
                    new_zoom_str = input(f"Enter new zoom (1.0-{max_zoom:.2f}): ")
                    new_zoom = float(new_zoom_str.replace(',', '.'))  # Handle both comma and period as decimal
                    
                    if 1.0 <= new_zoom <= max_zoom:
                        anker_camera.setVideoZoomFactor_(new_zoom)
                        print(f"Zoom set to {new_zoom:.2f}x")
                        
                        # Capture a photo after zoom change
                        timestamp = int(time.time())
                        photo_path = os.path.join(desktop_path, f"anker_zoom_{new_zoom:.2f}_{timestamp}.png")
                        capture_photo(session, photo_path)
                    else:
                        print(f"Zoom must be between 1.0 and {max_zoom:.2f}")
                except ValueError:
                    print("Invalid input, must be a number")
                except Exception as e:
                    print(f"Error setting zoom: {e}")
            
            elif choice == "2" and pan_tilt_supported:
                try:
                    current = anker_camera.centerPoint()
                    print(f"Current center point: X={current.x:.2f}, Y={current.y:.2f}")
                    print("Valid range: 0.0 - 1.0 for both X and Y")
                    print("(0,0) = top-left, (1,1) = bottom-right")
                    
                    x_str = input("Enter X position (0.0-1.0): ")
                    y_str = input("Enter Y position (0.0-1.0): ")
                    
                    x = float(x_str.replace(',', '.'))
                    y = float(y_str.replace(',', '.'))
                    
                    if 0.0 <= x <= 1.0 and 0.0 <= y <= 1.0:
                        # Create an NSPoint
                        point = NSMakePoint(x, y)
                        anker_camera.setCenterPoint_(point)
                        print(f"Center point set to X={x:.2f}, Y={y:.2f}")
                        
                        # Capture a photo after pan/tilt change
                        timestamp = int(time.time())
                        photo_path = os.path.join(desktop_path, f"anker_pan_x{x:.2f}_y{y:.2f}_{timestamp}.png")
                        capture_photo(session, photo_path)
                    else:
                        print("Position values must be between 0.0 and 1.0")
                except ValueError:
                    print("Invalid input, must be a number")
                except Exception as e:
                    print(f"Error setting center point: {e}")
            
            elif choice == "3":
                if hasattr(anker_camera, 'lensPosition') and hasattr(anker_camera, 'setFocusModeLockedWithLensPosition_completionHandler_'):
                    try:
                        current = anker_camera.lensPosition()
                        print(f"Current focus position: {current:.2f}")
                        print("Valid range: 0.0 (far) - 1.0 (near)")
                        
                        pos_str = input("Enter focus position (0.0-1.0): ")
                        pos = float(pos_str.replace(',', '.'))
                        
                        if 0.0 <= pos <= 1.0:
                            # Set focus mode to locked and update position
                            anker_camera.setFocusModeLockedWithLensPosition_completionHandler_(pos, None)
                            print(f"Focus position set to {pos:.2f}")
                            
                            # Capture a photo after focus change
                            timestamp = int(time.time())
                            photo_path = os.path.join(desktop_path, f"anker_focus_pos{pos:.2f}_{timestamp}.png")
                            capture_photo(session, photo_path)
                        else:
                            print("Position must be between 0.0 and 1.0")
                    except ValueError:
                        print("Invalid input, must be a number")
                    except Exception as e:
                        print(f"Error setting focus position: {e}")
                else:
                    print("Focus position control not supported")
            
            elif choice == "4" and focus_supported:
                try:
                    current = anker_camera.focusPointOfInterest()
                    print(f"Current focus point: X={current.x:.2f}, Y={current.y:.2f}")
                    print("Valid range: 0.0 - 1.0 for both X and Y")
                    print("(0,0) = top-left, (1,1) = bottom-right")
                    
                    x_str = input("Enter X position (0.0-1.0): ")
                    y_str = input("Enter Y position (0.0-1.0): ")
                    
                    x = float(x_str.replace(',', '.'))
                    y = float(y_str.replace(',', '.'))
                    
                    if 0.0 <= x <= 1.0 and 0.0 <= y <= 1.0:
                        # Create an NSPoint
                        point = NSMakePoint(x, y)
                        
                        # Set focus mode to point of interest
                        if anker_camera.isFocusPointOfInterestSupported():
                            anker_camera.setFocusPointOfInterest_(point)
                            print(f"Focus point set to X={x:.2f}, Y={y:.2f}")
                            
                            # Capture a photo after focus point change
                            timestamp = int(time.time())
                            photo_path = os.path.join(desktop_path, f"anker_focus_pt_x{x:.2f}_y{y:.2f}_{timestamp}.png")
                            capture_photo(session, photo_path)
                        else:
                            print("Camera does not support focus point of interest")
                    else:
                        print("Position values must be between 0.0 and 1.0")
                except ValueError:
                    print("Invalid input, must be a number")
                except Exception as e:
                    print(f"Error setting focus point: {e}")
            
            elif choice == "5":
                if hasattr(anker_camera, 'focusMode') and hasattr(anker_camera, 'setFocusMode_'):
                    try:
                        current_mode = anker_camera.focusMode()
                        mode_str = "Unknown"
                        if current_mode == 0:
                            mode_str = "Locked"
                        elif current_mode == 1:
                            mode_str = "Auto"
                        elif current_mode == 2:
                            mode_str = "Continuous Auto"
                        
                        print(f"Current focus mode: {mode_str}")
                        
                        if current_mode == 2:  # If in auto mode
                            print("Switching to Manual Focus")
                            anker_camera.setFocusMode_(0)  # 0 = Locked
                            new_mode = "Manual"
                        else:  # If in manual or other mode
                            print("Switching to Auto Focus")
                            anker_camera.setFocusMode_(2)  # 2 = Continuous Auto
                            new_mode = "Auto"
                            
                        # Capture a photo after focus mode change
                        timestamp = int(time.time())
                        photo_path = os.path.join(desktop_path, f"anker_focus_mode_{new_mode}_{timestamp}.png")
                        capture_photo(session, photo_path)
                            
                    except Exception as e:
                        print(f"Error toggling focus mode: {e}")
                else:
                    print("Focus mode control not supported")
            
            elif choice == "6":
                # Just take a photo without changing any settings
                timestamp = int(time.time())
                photo_path = os.path.join(desktop_path, f"anker_photo_{timestamp}.png")
                capture_photo(session, photo_path)
            
            else:
                print("Invalid option or feature not supported")
    
    except Exception as e:
        print(f"Error controlling camera: {e}")
    
    finally:
        # Unlock configuration
        anker_camera.unlockForConfiguration()
        
        # Stop the session
        session.stopRunning()
        print("\nCamera session ended")

if __name__ == "__main__":
    control_anker_camera()