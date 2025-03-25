from Foundation import *
from AVFoundation import *
from Cocoa import *
import time
import os

def take_photo():
    """Capture a photo from the camera and save it to the desktop with detailed error reporting"""
    try:
        print("Simple macOS Camera Photo Capture")
        print("================================")
        
        # Get desktop path
        home_dir = os.path.expanduser("~")
        desktop_path = os.path.join(home_dir, "Desktop")
        photo_path = os.path.join(desktop_path, f"camera_photo_{int(time.time())}.jpg")
        
        print(f"Will save photo to: {photo_path}")
        
        # List all cameras
        print("\nLooking for cameras...")
        devices = AVCaptureDevice.devicesWithMediaType_(AVMediaTypeVideo)
        
        if not devices or len(devices) == 0:
            print("Error: No cameras found")
            return
        
        # Use the first camera
        camera = devices[0]
        print(f"Using camera: {camera.localizedName()}")
        
        # Create capture session
        print("Setting up capture session...")
        session = AVCaptureSession.alloc().init()
        session.beginConfiguration()
        
        # Add device input
        print("Adding camera input...")
        success, error = AVCaptureDeviceInput.deviceInputWithDevice_error_(camera, None)
        if not success:
            print(f"Error creating device input: {error}")
            return
        
        device_input = success
        if session.canAddInput_(device_input):
            session.addInput_(device_input)
        else:
            print("Error: Cannot add device input to session")
            return
        
        # Add still image output
        print("Adding image output...")
        still_output = AVCaptureStillImageOutput.alloc().init()
        still_output.setOutputSettings_({AVVideoCodecKey: AVVideoCodecJPEG})
        
        if session.canAddOutput_(still_output):
            session.addOutput_(still_output)
        else:
            print("Error: Cannot add still image output to session")
            return
        
        # Commit configuration and start the session
        session.commitConfiguration()
        print("Starting camera session...")
        session.startRunning()
        
        # Wait a moment for the camera to initialize
        print("Warming up camera...")
        time.sleep(2)
        
        # Get the connection
        print("Preparing to capture...")
        connection = still_output.connectionWithMediaType_(AVMediaTypeVideo)
        if not connection:
            print("Error: No valid connection for video output")
            return
        
        # Capture the image
        print("Taking photo...")
        
        # Use a semaphore to wait for the capture to complete
        capture_complete = NSCondition.alloc().init()
        capture_success = [False]  # Use a list so it can be modified in the completion handler
        
        def completion_handler(sampleBuffer, error):
            try:
                if error:
                    print(f"Error capturing image: {error}")
                    capture_complete.lock()
                    capture_complete.signal()
                    capture_complete.unlock()
                    return
                
                print("Processing captured image...")
                
                # Convert CMSampleBuffer to image
                imageBuffer = CMSampleBufferGetImageBuffer(sampleBuffer)
                ciImage = CIImage.imageWithCVPixelBuffer_(imageBuffer)
                context = CIContext.contextWithOptions_(None)
                cgImage = context.createCGImage_fromRect_(ciImage, ciImage.extent())
                
                # Create NSImage
                image = NSImage.alloc().initWithCGImage_size_(cgImage, NSZeroSize)
                
                # Save to file
                image_data = image.TIFFRepresentation()
                bitmap_rep = NSBitmapImageRep.imageRepWithData_(image_data)
                jpeg_data = bitmap_rep.representationUsingType_properties_(NSJPEGFileType, None)
                
                print(f"Saving image to: {photo_path}")
                result = jpeg_data.writeToFile_atomically_(photo_path, True)
                
                if result:
                    print("✓ Photo saved successfully!")
                    print(f"Photo location: {photo_path}")
                    capture_success[0] = True
                else:
                    print("✗ Failed to save photo")
                    
                # Alternative saving method if the first one fails
                if not result:
                    print("Trying alternative save method...")
                    try:
                        with open(photo_path, 'wb') as f:
                            f.write(jpeg_data.bytes().tobytes())
                        print("✓ Photo saved with alternative method!")
                        capture_success[0] = True
                    except Exception as e:
                        print(f"✗ Alternative save also failed: {e}")
                
                # Signal that we're done
                capture_complete.lock()
                capture_complete.signal()
                capture_complete.unlock()
                
            except Exception as e:
                print(f"Error in completion handler: {e}")
                capture_complete.lock()
                capture_complete.signal()
                capture_complete.unlock()
        
        # Start the capture
        still_output.captureStillImageAsynchronouslyFromConnection_completionHandler_(
            connection, completion_handler)
        
        # Wait for the capture to complete
        print("Waiting for capture to complete...")
        capture_complete.lock()
        capture_complete.wait()
        capture_complete.unlock()
        
        # Stop the session
        print("Stopping camera session...")
        session.stopRunning()
        
        if capture_success[0]:
            print("\nPhoto captured and saved successfully!")
            print(f"Look for the file at: {photo_path}")
            # For easier access in Terminal, also print the file URL
            file_url = NSURL.fileURLWithPath_(photo_path)
            print(f"File URL: {file_url.absoluteString()}")
            
            # Try to open the file with the default application
            try:
                NSWorkspace.sharedWorkspace().openFile_(photo_path)
                print("Opening the photo with your default image viewer...")
            except:
                print("Could not open the photo automatically.")
        else:
            print("\nFailed to capture or save the photo.")
            print("Check if your macOS settings allow Python or Terminal to access the camera and Desktop folder.")
            
    except Exception as e:
        print(f"Error in take_photo function: {e}")

if __name__ == "__main__":
    take_photo()