import usb.core
import usb.util
import time
import array
import platform
import subprocess
from enum import Enum

class UVCRequest(Enum):
    SET_CUR = 0x01
    GET_CUR = 0x81
    GET_MIN = 0x82
    GET_MAX = 0x83
    GET_RES = 0x84
    GET_INFO = 0x86
    GET_DEF = 0x87

class UVCControl(Enum):
    # Processing Unit Controls
    BRIGHTNESS = 0x02
    CONTRAST = 0x03
    HUE = 0x06
    SATURATION = 0x07
    SHARPNESS = 0x08
    GAMMA = 0x09
    WHITE_BALANCE_TEMPERATURE = 0x0A
    WHITE_BALANCE_COMPONENT = 0x0B
    BACKLIGHT_COMPENSATION = 0x0C
    GAIN = 0x0D
    POWER_LINE_FREQUENCY = 0x0E
    AUTO_HUE = 0x10
    AUTO_WHITE_BALANCE_TEMPERATURE = 0x11
    AUTO_WHITE_BALANCE_COMPONENT = 0x12
    DIGITAL_MULTIPLIER = 0x14
    DIGITAL_MULTIPLIER_LIMIT = 0x15
    ANALOG_VIDEO_STANDARD = 0x16
    ANALOG_VIDEO_LOCK_STATUS = 0x17
    # Camera Terminal Controls
    SCANNING_MODE = 0x01
    AUTO_EXPOSURE_MODE = 0x02
    AUTO_EXPOSURE_PRIORITY = 0x03
    EXPOSURE_TIME_ABSOLUTE = 0x04
    EXPOSURE_TIME_RELATIVE = 0x05
    FOCUS_ABSOLUTE = 0x06
    FOCUS_RELATIVE = 0x07
    IRIS_ABSOLUTE = 0x08
    IRIS_RELATIVE = 0x09
    ZOOM_ABSOLUTE = 0x0A
    ZOOM_RELATIVE = 0x0B
    PAN_ABSOLUTE = 0x0C
    PAN_RELATIVE = 0x0D
    ROLL_ABSOLUTE = 0x0E
    ROLL_RELATIVE = 0x0F
    TILT_ABSOLUTE = 0x10
    TILT_RELATIVE = 0x11
    FOCUS_AUTO = 0x12
    PRIVACY = 0x13

class UVCInterface:
    def __init__(self, vendor_id=None, product_id=None):
        """
        Initialize a connection to a UVC device.
        
        Args:
            vendor_id: The USB vendor ID (optional)
            product_id: The USB product ID (optional)
        """
        self.is_macos = platform.system() == 'Darwin'
        
        # For macOS on M1, try to identify UVC devices first
        if self.is_macos and not (vendor_id and product_id):
            try:
                # Use system_profiler to get USB device information
                cmd = ['system_profiler', 'SPUSBDataType', '-json']
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                import json
                usb_info = json.loads(result.stdout)
                
                # Find webcams/UVC devices in the USB tree
                webcams = []
                
                def traverse_usb_tree(node):
                    if isinstance(node, list):
                        for item in node:
                            traverse_usb_tree(item)
                    elif isinstance(node, dict):
                        # Look for camera-related keywords or UVC in the product name
                        if '_name' in node and any(keyword in node['_name'].lower() 
                                                for keyword in ['camera', 'webcam', 'facetime', 'uvc']):
                            if 'vendor_id' in node and 'product_id' in node:
                                try:
                                    vid = int(node['vendor_id'].replace('0x', ''), 16)
                                    pid = int(node['product_id'].replace('0x', ''), 16)
                                    webcams.append((vid, pid))
                                except ValueError:
                                    pass
                        
                        for key, value in node.items():
                            if isinstance(value, (list, dict)):
                                traverse_usb_tree(value)
                
                traverse_usb_tree(usb_info.get('SPUSBDataType', []))
                
                if webcams and not (vendor_id and product_id):
                    print(f"Found potential camera devices: {webcams}")
                    vendor_id, product_id = webcams[0]  # Use the first found camera
                    print(f"Using device with VID=0x{vendor_id:04x}, PID=0x{product_id:04x}")
            
            except Exception as e:
                print(f"Failed to enumerate webcams using system_profiler: {e}")
                # Continue with regular enumeration
        
        # Find a UVC device
        if vendor_id and product_id:
            self.dev = usb.core.find(idVendor=vendor_id, idProduct=product_id)
        else:
            # Try to find any UVC device
            self.dev = usb.core.find(find_all=True)
            if self.dev:
                # First pass: check for proper UVC devices 
                uvc_dev = next((d for d in self.dev if d.bDeviceClass == 239 and 
                               any(c.bInterfaceClass == 14 and c.bInterfaceSubClass in (1, 2) 
                                   for c in d for c in d.configurations())), None)
                
                # Second pass: look for common webcam vendors if no UVC device was found
                if not uvc_dev:
                    common_webcam_vendors = [0x046d, 0x0ac8, 0x041e, 0x0c45, 0x13d3, 0x05a9]  # Logitech, Apple, etc.
                    self.dev = next((d for d in self.dev if d.idVendor in common_webcam_vendors), None)
                else:
                    self.dev = uvc_dev
        
        if self.dev is None:
            raise ValueError("UVC device not found")
        
        # Detach kernel driver if active (not necessary on macOS)
        if not self.is_macos:
            try:
                if self.dev.is_kernel_driver_active(0):
                    self.dev.detach_kernel_driver(0)
            except Exception as e:
                print(f"Warning: {e}")
        else:
            # On macOS, we need to use IOKit to communicate with the camera
            # For now, we'll just print a message about this limitation
            print("Note: On macOS, direct USB control of cameras may be limited due to system protections.")
        
        # Set the active configuration
        self.dev.set_configuration()
        
        # Find the video control interface
        cfg = self.dev.get_active_configuration()
        self.vc_interface = None
        
        for interface in cfg:
            if interface.bInterfaceClass == 14 and interface.bInterfaceSubClass == 1:  # Video, Control
                self.vc_interface = interface
                break
        
        if not self.vc_interface:
            raise ValueError("Video Control interface not found")
        
        # Find camera terminal and processing unit
        self.camera_terminal_id = None
        self.processing_unit_id = None
        
        for descriptor in self.vc_interface.extra_descriptors:
            if len(descriptor) > 3:
                descriptor_type = descriptor[1]
                descriptor_subtype = descriptor[2]
                if descriptor_type == 0x24:  # CS_INTERFACE
                    if descriptor_subtype == 0x02:  # VC_INPUT_TERMINAL
                        if descriptor[4] == 0x01:  # ITT_CAMERA
                            self.camera_terminal_id = descriptor[3]
                    elif descriptor_subtype == 0x05:  # VC_PROCESSING_UNIT
                        self.processing_unit_id = descriptor[3]
        
        if not self.camera_terminal_id:
            self.camera_terminal_id = 1  # Default if not found
        
        if not self.processing_unit_id:
            self.processing_unit_id = 2  # Default if not found
    
    def _control_transfer(self, request_type, request, value, index, data_or_wLength):
        """Wrapper for control_transfer with error handling."""
        try:
            return self.dev.ctrl_transfer(request_type, request, value, index, data_or_wLength)
        except usb.core.USBError as e:
            print(f"USB Error: {e}")
            return None
    
    def get_control(self, unit_id, control, request_type=UVCRequest.GET_CUR, length=2):
        """
        Send a UVC GET control request.
        
        Args:
            unit_id: The unit ID (camera terminal or processing unit)
            control: The control selector from UVCControl
            request_type: The request type from UVCRequest
            length: Length of data to read
            
        Returns:
            The value read from the device
        """
        if isinstance(control, UVCControl):
            control = control.value
        
        if isinstance(request_type, UVCRequest):
            request_type = request_type.value
        
        # UVC control requests are always to the interface
        bmRequestType = 0xA1  # Direction: IN, Type: Class, Recipient: Interface
        
        # CS (control selector) in the high byte, entity ID in the low byte
        wValue = (control << 8) | 0x00
        
        # Interface number in the low byte, entity ID in the high byte
        wIndex = (unit_id << 8) | self.vc_interface.bInterfaceNumber
        
        # Create buffer for the response
        buffer = array.array('B', [0] * length)
        
        # Send the control transfer
        result = self._control_transfer(bmRequestType, request_type, wValue, wIndex, buffer)
        
        if result is None or len(result) == 0:
            return None
        
        # Convert the result based on length
        if length == 1:
            return result[0]
        elif length == 2:
            return result[0] | (result[1] << 8)
        elif length == 4:
            return result[0] | (result[1] << 8) | (result[2] << 16) | (result[3] << 24)
        else:
            return result
    
    def set_control(self, unit_id, control, value, length=2):
        """
        Send a UVC SET_CUR control request.
        
        Args:
            unit_id: The unit ID (camera terminal or processing unit)
            control: The control selector from UVCControl
            value: The value to set
            length: Length of data to write
            
        Returns:
            True if successful, False otherwise
        """
        if isinstance(control, UVCControl):
            control = control.value
        
        # UVC control requests are always to the interface
        bmRequestType = 0x21  # Direction: OUT, Type: Class, Recipient: Interface
        
        # CS (control selector) in the high byte, entity ID in the low byte
        wValue = (control << 8) | 0x00
        
        # Interface number in the low byte, entity ID in the high byte
        wIndex = (unit_id << 8) | self.vc_interface.bInterfaceNumber
        
        # Create the data buffer
        buffer = array.array('B')
        
        if length == 1:
            buffer.append(value & 0xFF)
        elif length == 2:
            buffer.append(value & 0xFF)
            buffer.append((value >> 8) & 0xFF)
        elif length == 4:
            buffer.append(value & 0xFF)
            buffer.append((value >> 8) & 0xFF)
            buffer.append((value >> 16) & 0xFF)
            buffer.append((value >> 24) & 0xFF)
        else:
            return False
        
        # Send the control transfer
        result = self._control_transfer(bmRequestType, UVCRequest.SET_CUR.value, wValue, wIndex, buffer)
        
        return result is not None
    
    # Convenience methods for common camera controls
    
    def get_brightness(self):
        """Get the current brightness value."""
        return self.get_control(self.processing_unit_id, UVCControl.BRIGHTNESS)
    
    def set_brightness(self, value):
        """Set the brightness value."""
        return self.set_control(self.processing_unit_id, UVCControl.BRIGHTNESS, value)
    
    def get_contrast(self):
        """Get the current contrast value."""
        return self.get_control(self.processing_unit_id, UVCControl.CONTRAST)
    
    def set_contrast(self, value):
        """Set the contrast value."""
        return self.set_control(self.processing_unit_id, UVCControl.CONTRAST, value)
    
    def get_focus(self):
        """Get the current focus value."""
        return self.get_control(self.camera_terminal_id, UVCControl.FOCUS_ABSOLUTE)
    
    def set_focus(self, value):
        """Set the focus value."""
        return self.set_control(self.camera_terminal_id, UVCControl.FOCUS_ABSOLUTE, value)
    
    def get_exposure(self):
        """Get the current exposure value."""
        return self.get_control(self.camera_terminal_id, UVCControl.EXPOSURE_TIME_ABSOLUTE, length=4)
    
    def set_exposure(self, value):
        """Set the exposure value."""
        return self.set_control(self.camera_terminal_id, UVCControl.EXPOSURE_TIME_ABSOLUTE, value, length=4)
    
    def get_auto_focus(self):
        """Get the auto focus state (1 for enabled, 0 for disabled)."""
        return self.get_control(self.camera_terminal_id, UVCControl.FOCUS_AUTO, length=1)
    
    def set_auto_focus(self, enabled):
        """Enable or disable auto focus."""
        return self.set_control(self.camera_terminal_id, UVCControl.FOCUS_AUTO, 1 if enabled else 0, length=1)
    
    def get_auto_exposure(self):
        """Get the auto exposure mode."""
        return self.get_control(self.camera_terminal_id, UVCControl.AUTO_EXPOSURE_MODE, length=1)
    
    def set_auto_exposure(self, mode):
        """Set the auto exposure mode (1 for manual, 2 for auto, 4 for shutter priority, 8 for aperture priority)."""
        return self.set_control(self.camera_terminal_id, UVCControl.AUTO_EXPOSURE_MODE, mode, length=1)
    
    def close(self):
        """Release the USB device."""
        usb.util.dispose_resources(self.dev)


# Alternative for macOS: using AVFoundation via PyObjC
def get_macos_cameras():
    """
    Get a list of cameras on macOS using AVFoundation.
    This requires PyObjC to be installed: pip install pyobjc-framework-AVFoundation
    
    Returns:
        A list of available camera devices
    """
    try:
        # Import PyObjC frameworks
        from AVFoundation import AVCaptureDevice
        from Foundation import NSObject
        
        # Get all video devices
        devices = AVCaptureDevice.devicesWithMediaType_('vide')
        
        camera_list = []
        for device in devices:
            camera_list.append({
                'name': device.localizedName(),
                'model_id': device.modelID(),
                'unique_id': device.uniqueID(),
                'manufacturer': device.manufacturer() if hasattr(device, 'manufacturer') else 'Unknown'
            })
        
        return camera_list
    except ImportError:
        print("PyObjC and AVFoundation frameworks not installed.")
        print("Install with: pip install pyobjc-framework-AVFoundation")
        return []
    except Exception as e:
        print(f"Error getting macOS cameras: {e}")
        return []


# Example usage
if __name__ == "__main__":
    try:
        # For macOS, list available webcams first
        if platform.system() == 'Darwin':
            print("Scanning for webcams on macOS...")
            try:
                cmd = ['system_profiler', 'SPUSBDataType']
                result = subprocess.run(cmd, capture_output=True, text=True)
                output_lines = result.stdout.split('\n')
                
                in_camera_section = False
                camera_info = []
                
                for line in output_lines:
                    if 'Camera' in line or 'FaceTime' in line or 'Webcam' in line:
                        in_camera_section = True
                        camera_info.append(line.strip())
                    elif in_camera_section and line.strip() and not line.startswith(' ' * 10):
                        in_camera_section = False
                    elif in_camera_section and line.strip():
                        camera_info.append(line.strip())
                
                if camera_info:
                    print("Found camera device(s):")
                    for info in camera_info:
                        print(f"  {info}")
                    print("\nYou can use these identifiers to initialize UVCInterface with specific vendor_id and product_id")
                else:
                    print("No camera devices found in system_profiler output")
            except Exception as e:
                print(f"Error scanning for cameras: {e}")
        
        # Connect to a UVC device
        # Common camera vendor IDs:
        # - 0x046d: Logitech
        # - 0x05ac: Apple
        # - 0x045e: Microsoft
        # - 0x0c45: Microdia (many generic webcams)
        
        # On macOS you likely need to specify the IDs explicitly
        # For example:
        # uvc = UVCInterface(vendor_id=0x05ac, product_id=0x8514)  # FaceTime HD Camera
        
        print("Attempting to connect to UVC device...")
        uvc = UVCInterface()
        
        if uvc.dev is None:
            print("No UVC device found. Please specify vendor_id and product_id.")
            print("Example: uvc = UVCInterface(vendor_id=0x05ac, product_id=0x8514)")
            exit(1)
        
        print(f"Connected to device: {uvc.dev.idVendor:04x}:{uvc.dev.idProduct:04x}")
        
        # Try getting camera info - this may fail on macOS
        try:
            brightness = uvc.get_brightness()
            print(f"Current brightness: {brightness}")
            
            contrast = uvc.get_contrast()
            print(f"Current contrast: {contrast}")
            
            # Set new values (may not work on macOS)
            success = uvc.set_brightness(128)
            print(f"Set brightness: {'Success' if success else 'Failed'}")
            
            success = uvc.set_contrast(128)
            print(f"Set contrast: {'Success' if success else 'Failed'}")
            
            # Auto focus control
            auto_focus = uvc.get_auto_focus()
            print(f"Auto focus: {'Enabled' if auto_focus else 'Disabled'}")
            
            # Try to set auto focus
            success = uvc.set_auto_focus(False)
            print(f"Disable auto focus: {'Success' if success else 'Failed'}")
        except Exception as e:
            print(f"Error accessing camera controls: {e}")
            print("This is expected on macOS due to its restrictive camera access policies.")
            print("On macOS, consider using alternative approaches like AVFoundation bindings.")
        
        # Close the connection
        uvc.close()
        
    except Exception as e:
        print(f"Error: {e}")