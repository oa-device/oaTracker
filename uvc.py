import usb.core
import usb.util
import array
import time
import sys
import subprocess
import json

def list_all_usb_devices():
    """List all USB devices connected to the system"""
    print("Listing all USB devices:")
    print("-------------------------")
    
    all_devices = list(usb.core.find(find_all=True))
    
    if not all_devices:
        print("No USB devices found. Are you running with sudo?")
        return []
    
    devices_info = []
    
    for i, device in enumerate(all_devices):
        try:
            vendor_id = device.idVendor
            product_id = device.idProduct
            
            # Try to get manufacturer and product strings
            manufacturer = "Unknown"
            product = "Unknown"
            
            try:
                if device.iManufacturer > 0:
                    manufacturer = usb.util.get_string(device, device.iManufacturer)
            except:
                pass
                
            try:
                if device.iProduct > 0:
                    product = usb.util.get_string(device, device.iProduct)
            except:
                pass
            
            # See if it might be a camera
            is_camera = False
            try:
                for cfg in device:
                    for intf in cfg:
                        if intf.bInterfaceClass == 14:  # Video class
                            is_camera = True
                            break
                    if is_camera:
                        break
            except:
                pass
            
            device_type = "Camera" if is_camera else "Other"
            
            print(f"{i+1}. {manufacturer} {product}")
            print(f"   VID: 0x{vendor_id:04x}, PID: 0x{product_id:04x}")
            print(f"   Type: {device_type}")
            print()
            
            devices_info.append({
                'index': i,
                'device': device,
                'manufacturer': manufacturer,
                'product': product,
                'vendor_id': vendor_id,
                'product_id': product_id,
                'is_camera': is_camera
            })
            
        except Exception as e:
            print(f"{i+1}. Error accessing device: {e}")
            print()
    
    return devices_info

def find_video_control_interface(device):
    """Find the Video Control interface in any USB device"""
    print(f"Looking for Video Control interface...")
    
    video_interfaces = []
    
    try:
        # Get all configurations
        for config_index in range(device.bNumConfigurations):
            try:
                cfg = device[config_index]
                print(f"  Checking configuration {config_index}...")
                
                # Find all interfaces
                for intf_index in range(cfg.bNumInterfaces):
                    try:
                        for alt_setting in range(10):  # Try a few alternate settings
                            try:
                                intf = cfg[(intf_index, alt_setting)]
                                
                                # Check if this is a Video interface
                                if intf.bInterfaceClass == 14:  # Video class
                                    interface_type = "Unknown"
                                    if intf.bInterfaceSubClass == 1:
                                        interface_type = "Control"
                                    elif intf.bInterfaceSubClass == 2:
                                        interface_type = "Streaming"
                                    
                                    print(f"  ✓ Found Video {interface_type} interface: {intf_index}, alt setting: {alt_setting}")
                                    
                                    if intf.bInterfaceSubClass == 1:  # Video Control
                                        video_interfaces.append({
                                            'interface': intf,
                                            'index': intf_index,
                                            'alt_setting': alt_setting
                                        })
                            except:
                                # No more alternate settings
                                break
                    except Exception as e:
                        print(f"  Error checking interface {intf_index}: {e}")
            except Exception as e:
                print(f"  Error checking configuration {config_index}: {e}")
    except Exception as e:
        print(f"  Error iterating configurations: {e}")
    
    # Return the first Video Control interface found
    if video_interfaces:
        print(f"Found {len(video_interfaces)} Video Control interfaces")
        return video_interfaces[0]['interface']
    
    # If no interface found, create a mock interface with default values
    print("  No Video Control interface found. Using default values.")
    
    class MockInterface:
        def __init__(self):
            self.bInterfaceNumber = 0
    
    return MockInterface()

def test_uvc_controls(device, interface):
    """Test UVC controls for any camera"""
    # Default terminal and unit IDs (typical for most UVC cameras)
    camera_terminal_id = 1
    processing_unit_id = 2
    
    # Get interface number
    interface_number = getattr(interface, 'bInterfaceNumber', 0)
    print(f"Using interface number: {interface_number}")
    
    # Try different unit IDs if needed
    unit_ids_to_try = list(range(1, 8))  # Try unit IDs 1 through 7
    
    # List of common UVC controls to test
    common_controls = [
        {"name": "Brightness", "unit": processing_unit_id, "selector": 0x02, "length": 2},
        {"name": "Contrast", "unit": processing_unit_id, "selector": 0x03, "length": 2},
        {"name": "Hue", "unit": processing_unit_id, "selector": 0x06, "length": 2},
        {"name": "Saturation", "unit": processing_unit_id, "selector": 0x07, "length": 2},
        {"name": "Sharpness", "unit": processing_unit_id, "selector": 0x08, "length": 2},
        {"name": "Gamma", "unit": processing_unit_id, "selector": 0x09, "length": 2},
        {"name": "White Balance", "unit": processing_unit_id, "selector": 0x0A, "length": 2},
        {"name": "Gain", "unit": processing_unit_id, "selector": 0x0D, "length": 2},
        {"name": "Auto White Balance", "unit": processing_unit_id, "selector": 0x11, "length": 1},
        {"name": "Auto Exposure Mode", "unit": camera_terminal_id, "selector": 0x02, "length": 1},
        {"name": "Exposure Time", "unit": camera_terminal_id, "selector": 0x04, "length": 4},
        {"name": "Focus", "unit": camera_terminal_id, "selector": 0x06, "length": 2},
        {"name": "Auto Focus", "unit": camera_terminal_id, "selector": 0x12, "length": 1},
        {"name": "Zoom", "unit": camera_terminal_id, "selector": 0x0A, "length": 2}
    ]
    
    successful_controls = []
    unit_support = {}
    
    print("\nProbing for UVC controls support...")
    print("----------------------------------")
    
    # First, probe which unit IDs actually respond to anything
    for unit_id in unit_ids_to_try:
        unit_support[unit_id] = False
        
        print(f"Testing Unit ID {unit_id}...")
        
        # Test a few common controls with this unit ID
        test_controls = [
            {"name": "Generic Test 1", "selector": 0x02, "length": 1},  # Often brightness or auto exposure
            {"name": "Generic Test 2", "selector": 0x03, "length": 1},  # Often contrast
            {"name": "Generic Test 3", "selector": 0x01, "length": 1}   # Often scanning mode
        ]
        
        for ctrl in test_controls:
            try:
                # GET_CUR request
                bmRequestType = 0xA1  # Direction: IN, Type: Class, Recipient: Interface
                bRequest = 0x81      # GET_CUR
                wValue = (ctrl['selector'] << 8)
                wIndex = (unit_id << 8) | interface_number
                wLength = ctrl['length']
                
                # Create a buffer for the response
                buffer = array.array('B', [0] * wLength)
                
                # Send control transfer with short timeout
                result = device.ctrl_transfer(bmRequestType, bRequest, wValue, wIndex, buffer, timeout=100)
                
                if result:
                    print(f"  ✓ Unit ID {unit_id} responded to control 0x{ctrl['selector']:02x}")
                    unit_support[unit_id] = True
                    break
            except:
                pass
    
    # Update unit IDs based on what we found
    responding_units = [unit_id for unit_id, supported in unit_support.items() if supported]
    
    if responding_units:
        print(f"\nFound responding Unit IDs: {responding_units}")
        # Assign first two responding units to camera terminal and processing unit
        if len(responding_units) >= 2:
            camera_terminal_id = responding_units[0]
            processing_unit_id = responding_units[1]
        else:
            camera_terminal_id = responding_units[0]
            processing_unit_id = responding_units[0]
    else:
        print("\nNo units responded. Using default Unit IDs: 1, 2")
    
    print(f"Using Camera Terminal ID: {camera_terminal_id}")
    print(f"Using Processing Unit ID: {processing_unit_id}")
    
    # Update control list with detected unit IDs
    controls = []
    for ctrl in common_controls:
        if ctrl['unit'] == camera_terminal_id:
            controls.append(dict(ctrl, unit=camera_terminal_id))
        elif ctrl['unit'] == processing_unit_id:
            controls.append(dict(ctrl, unit=processing_unit_id))
    
    print("\nTesting UVC controls:")
    print("--------------------")
    
    for control in controls:
        try:
            print(f"Testing {control['name']} (Unit: {control['unit']}, Selector: 0x{control['selector']:02x})...")
            
            # GET_CUR request
            bmRequestType = 0xA1  # Direction: IN, Type: Class, Recipient: Interface
            bRequest = 0x81      # GET_CUR
            wValue = (control['selector'] << 8)  # Control selector in high byte
            wIndex = (control['unit'] << 8) | interface_number  # Unit ID in high byte, interface in low byte
            wLength = control['length']
            
            # Create a buffer for the response
            buffer = array.array('B', [0] * wLength)
            
            # Send control transfer with timeout
            result = device.ctrl_transfer(bmRequestType, bRequest, wValue, wIndex, buffer, timeout=500)
            
            if result:
                # Parse value based on length
                if wLength == 1:
                    value = result[0]
                elif wLength == 2:
                    value = result[0] | (result[1] << 8)
                elif wLength == 4:
                    value = result[0] | (result[1] << 8) | (result[2] << 16) | (result[3] << 24)
                else:
                    value = result
                
                print(f"  ✓ Success! Current {control['name']}: {value}")
                successful_controls.append(control)
                
                # Try SET_CUR for this control
                try:
                    print(f"  Testing SET_CUR for {control['name']}...")
                    
                    # SET_CUR request
                    bmRequestType = 0x21  # Direction: OUT, Type: Class, Recipient: Interface
                    bRequest = 0x01      # SET_CUR
                    
                    # Prepare test value and data
                    if wLength == 1:
                        # For boolean controls, toggle the current value
                        test_value = 0 if value > 0 else 1
                        data = array.array('B', [test_value])
                    elif wLength == 2:
                        # For 2-byte controls, use middle value
                        test_value = 128
                        data = array.array('B', [test_value & 0xFF, (test_value >> 8) & 0xFF])
                    elif wLength == 4:
                        # For 4-byte controls (like exposure), use a reasonable value
                        test_value = 1000
                        data = array.array('B', [
                            test_value & 0xFF, 
                            (test_value >> 8) & 0xFF,
                            (test_value >> 16) & 0xFF,
                            (test_value >> 24) & 0xFF
                        ])
                    
                    # Send SET_CUR control transfer
                    set_result = device.ctrl_transfer(bmRequestType, bRequest, wValue, wIndex, data, timeout=500)
                    
                    if set_result is not None:
                        print(f"  ✓ SET_CUR successful ({set_result})")
                        
                        # Wait a moment for the change to take effect
                        time.sleep(0.2)
                        
                        # Get the value again to see if it changed
                        result = device.ctrl_transfer(bmRequestType=0xA1, bRequest=0x81, 
                                                     wValue=wValue, wIndex=wIndex,
                                                     data_or_wLength=buffer, timeout=500)
                        
                        if result:
                            if wLength == 1:
                                new_value = result[0]
                            elif wLength == 2:
                                new_value = result[0] | (result[1] << 8)
                            elif wLength == 4:
                                new_value = result[0] | (result[1] << 8) | (result[2] << 16) | (result[3] << 24)
                            
                            if new_value != value:
                                print(f"  ✓ Value changed: {value} -> {new_value}")
                            else:
                                print(f"  ⚠ Value did not change (may be restricted or auto mode)")
                    else:
                        print(f"  ✗ SET_CUR failed")
                
                except Exception as e:
                    print(f"  ✗ Error setting value: {e}")
            else:
                print(f"  ✗ Failed to get value")
        
        except usb.core.USBError as e:
            if "timeout" in str(e).lower():
                print(f"  ✗ Timeout error: device did not respond")
            else:
                print(f"  ✗ USB Error: {e}")
        except Exception as e:
            print(f"  ✗ Error: {e}")
        
        # Add a separator line between controls
        print()
    
    # Summary of findings
    print("\nSUMMARY:")
    print("--------")
    print(f"Successfully read {len(successful_controls)} of {len(controls)} controls")
    
    if successful_controls:
        print("\nWorking controls for your camera:")
        for ctrl in successful_controls:
            print(f"- {ctrl['name']} (Unit: {ctrl['unit']}, Selector: 0x{ctrl['selector']:02x})")
        
        # Generate a simple UVC class based on working controls
        generate_uvc_class(device, interface, successful_controls)

def generate_uvc_class(device, interface, controls):
    """Generate a simple UVC class implementation based on working controls"""
    if not controls:
        return
    
    # Get device info
    try:
        vendor_id = device.idVendor
        product_id = device.idProduct
        interface_number = getattr(interface, 'bInterfaceNumber', 0)
    except:
        vendor_id = 0
        product_id = 0
        interface_number = 0
    
    print("\nUSB Camera UVC Implementation:")
    print("===============================")
    print("Here's a Python class to control your camera:")
    print()
    
    print("""
import usb.core
import usb.util
import array

class UVCCamera:
    def __init__(self, vendor_id=None, product_id=None):
        """Initialize the UVC camera connection"""
        if vendor_id and product_id:
            self.dev = usb.core.find(idVendor=vendor_id, idProduct=product_id)
        else:
            # Use the detected camera from our testing
            self.dev = usb.core.find(idVendor=0x{:04x}, idProduct=0x{:04x})
        
        if not self.dev:
            raise ValueError("Camera not found")
            
        # Configure the device
        try:
            if self.dev.is_kernel_driver_active(0):
                self.dev.detach_kernel_driver(0)
        except Exception as e:
            print(f"Warning: {e}")
            
        try:
            self.dev.set_configuration()
        except Exception as e:
            print(f"Warning: {e}")
            
        self.interface_number = {}
""".format(vendor_id, product_id, interface_number))
    
    # Add constants for units
    units_used = set()
    for control in controls:
        units_used.add(control["unit"])
    
    for unit in units_used:
        if any(c["unit"] == unit and c["name"] in ["Brightness", "Contrast", "Saturation"] for c in controls):
            print(f"        self.PROCESSING_UNIT_ID = {unit}")
        elif any(c["unit"] == unit and c["name"] in ["Auto Focus", "Focus", "Zoom"] for c in controls):
            print(f"        self.CAMERA_TERMINAL_ID = {unit}")
    
    # Add methods for each control
    print()
    
    # First define helper methods
    print("""    def _control_transfer(self, request_type, request, value, index, data_or_wLength):
        """Send a control transfer to the device."""
        try:
            return self.dev.ctrl_transfer(request_type, request, value, index, data_or_wLength, timeout=1000)
        except Exception as e:
            print(f"Control transfer error: {e}")
            return None
            
    def _get_control(self, unit_id, control_selector, length=1):
        """Send a GET_CUR control request."""
        bmRequestType = 0xA1  # Direction: IN, Type: Class, Recipient: Interface
        bRequest = 0x81      # GET_CUR
        wValue = (control_selector << 8)
        wIndex = (unit_id << 8) | self.interface_number
        
        # Create buffer for the response
        buffer = array.array('B', [0] * length)
        
        # Send control transfer
        result = self._control_transfer(bmRequestType, bRequest, wValue, wIndex, buffer)
        
        if not result:
            return None
            
        # Parse value based on length
        if length == 1:
            return result[0]
        elif length == 2:
            return result[0] | (result[1] << 8)
        elif length == 4:
            return result[0] | (result[1] << 8) | (result[2] << 16) | (result[3] << 24)
        else:
            return result
            
    def _set_control(self, unit_id, control_selector, value, length=1):
        """Send a SET_CUR control request."""
        bmRequestType = 0x21  # Direction: OUT, Type: Class, Recipient: Interface
        bRequest = 0x01      # SET_CUR
        wValue = (control_selector << 8)
        wIndex = (unit_id << 8) | self.interface_number
        
        # Create data buffer with the value
        data = array.array('B')
        
        if length == 1:
            data.append(value & 0xFF)
        elif length == 2:
            data.append(value & 0xFF)           # Low byte
            data.append((value >> 8) & 0xFF)    # High byte
        elif length == 4:
            data.append(value & 0xFF)
            data.append((value >> 8) & 0xFF)
            data.append((value >> 16) & 0xFF)
            data.append((value >> 24) & 0xFF)
        
        # Send control transfer
        result = self._control_transfer(bmRequestType, bRequest, wValue, wIndex, data)
        return result is not None
    """)
    
    # Define methods for specific controls
    print()
    
    # Find working controls and generate methods
    for control in controls:
        control_name = control["name"].lower().replace(" ", "_")
        unit_name = "PROCESSING_UNIT_ID" if control["unit"] in [2, 3] else "CAMERA_TERMINAL_ID"
        selector = control["selector"]
        length = control["length"]
        
        # Generate getter method
        print(f"    def get_{control_name}(self):")
        print(f"        \"\"\"Get current {control['name']} value.\"\"\"")
        print(f"        return self._get_control(self.{unit_name}, 0x{selector:02x}, {length})")
        print()
        
        # Generate setter method (except for ones with "auto" in the name)
        if "auto" not in control_name:
            print(f"    def set_{control_name}(self, value):")
            print(f"        \"\"\"Set {control['name']} value.\"\"\"")
            print(f"        return self._set_control(self.{unit_name}, 0x{selector:02x}, value, {length})")
        else:
            print(f"    def set_{control_name}(self, enabled):")
            print(f"        \"\"\"Enable or disable {control['name']}.\"\"\"")
            print(f"        return self._set_control(self.{unit_name}, 0x{selector:02x}, 1 if enabled else 0, {length})")
        print()
    
    # Add example usage
    print("""    def close(self):
        """Release the USB device."""
        usb.util.dispose_resources(self.dev)


# Example usage:
if __name__ == "__main__":
    try:
        # Connect to the camera
        camera = UVCCamera()
        
        # Print some info
        print("Camera connected successfully!")
""")
    
    # Add examples for the first few controls
    for i, control in enumerate(controls[:3]):
        control_name = control["name"].lower().replace(" ", "_")
        print(f"        value = camera.get_{control_name}()")
        print(f"        print(f\"{control['name']}: {value}\")")
        
        if "auto" not in control_name:
            print(f"        # Set to middle value (for demonstration)")
            if control["length"] == 1:
                print(f"        camera.set_{control_name}(1)")
            elif control["length"] == 2:
                print(f"        camera.set_{control_name}(128)")
            else:
                print(f"        camera.set_{control_name}(1000)")
        else:
            print(f"        # Toggle auto mode")
            print(f"        camera.set_{control_name}(not value)")
        
        print()
    
    print("""        # Close the connection
        camera.close()
        
    except Exception as e:
        print(f"Error: {e}")
    """)

def main():
    print("UVC Camera Control Tool for macOS")
    print("================================")
    print("This tool scans for any UVC cameras and tests which controls work.\n")
    
    # List all USB devices
    devices = list_all_usb_devices()
    
    if not devices:
        print("No USB devices found. Make sure you're running with sudo.")
        return
    
    # Select a device
    camera_devices = [d for d in devices if d['is_camera']]
    other_devices = [d for d in devices if not d['is_camera']]
    
    selected_device = None
    
    if camera_devices:
        print(f"\nFound {len(camera_devices)} potential camera devices.")
        selected_device = camera_devices[0]['device']
        
        if len(camera_devices) > 1:
            try:
                print("\nPlease select a camera:")
                for i, device in enumerate(camera_devices):
                    print(f"{i+1}. {device['manufacturer']} {device['product']}")
                
                choice = int(input("\nEnter number: ")) - 1
                if 0 <= choice < len(camera_devices):
                    selected_device = camera_devices[choice]['device']
                    print(f"Selected: {camera_devices[choice]['manufacturer']} {camera_devices[choice]['product']}")
                else:
                    print("Invalid selection. Using the first camera.")
            except:
                print("Invalid input. Using the first camera.")
    else:
        print("\nNo camera devices detected. Trying other USB devices...")
        if other_devices:
            selected_device = other_devices[0]['device']
            
            if len(other_devices) > 1:
                try:
                    print("\nPlease select a USB device to test:")
                    for i, device in enumerate(other_devices):
                        print(f"{i+1}. {device['manufacturer']} {device['product']}")
                    
                    choice = int(input("\nEnter number: ")) - 1
                    if 0 <= choice < len(other_devices):
                        selected_device = other_devices[choice]['device']
                        print(f"Selected: {other_devices[choice]['manufacturer']} {other_devices[choice]['product']}")
                    else:
                        print("Invalid selection. Using the first device.")
                except:
                    print("Invalid input. Using the first device.")
    
    if not selected_device:
        print("No suitable device found.")
        return
    
    try:
        # Find the video control interface
        interface = find_video_control_interface(selected_device)
        
        # Test UVC controls
        test_uvc_controls(selected_device, interface)
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Release the device
        try:
            usb.util.dispose_resources(selected_device)
            print("\nDevice resources released.")
        except:
            pass

if __name__ == "__main__":
    main()