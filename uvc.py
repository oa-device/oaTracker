import usb.core
import usb.util
import time
import array
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
        # Find a UVC device
        if vendor_id and product_id:
            self.dev = usb.core.find(idVendor=vendor_id, idProduct=product_id)
        else:
            # Try to find any UVC device - this is a simplification
            # In a real implementation, you'd need to check the device class/subclass
            self.dev = usb.core.find(find_all=True)
            print(self.dev)
            # Filter for UVC devices (class 14, subclass 1 or 2)
            self.dev = next((d for d in self.dev if d.bDeviceClass == 239 and 
                             any(c.bInterfaceClass == 14 and c.bInterfaceSubClass in (1, 2) 
                                 for c in d for c in d.configurations())), None)
        
        if self.dev is None:
            raise ValueError("UVC device not found")
        
        # Detach kernel driver if active
        try:
            if self.dev.is_kernel_driver_active(0):
                self.dev.detach_kernel_driver(0)
        except Exception as e:
            print(f"Warning: {e}")
        
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


# Example usage
if __name__ == "__main__":
    try:
        # Connect to a UVC device (you can specify vendor_id and product_id)
        # For example: uvc = UVCInterface(vendor_id=0x046d, product_id=0x082d)  # Logitech C270
        uvc = UVCInterface()
        
        # Get current values
        brightness = uvc.get_brightness()
        contrast = uvc.get_contrast()
        
        print(f"Current brightness: {brightness}")
        print(f"Current contrast: {contrast}")
        
        # Set new values
        uvc.set_brightness(128)  # Set to middle value
        uvc.set_contrast(128)    # Set to middle value
        
        # Auto focus control
        auto_focus = uvc.get_auto_focus()
        print(f"Auto focus: {'Enabled' if auto_focus else 'Disabled'}")
        
        # Disable auto focus and set manual focus
        uvc.set_auto_focus(False)
        uvc.set_focus(100)  # Set to some value
        
        # Close the connection
        uvc.close()
        
    except Exception as e:
        print(f"Error: {e}")