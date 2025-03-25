import usb.core
import usb.util
import array
import time
import sys

def find_anker_camera():
    """Find the Anker PowerConf C200 camera specifically"""
    # Common Anker vendor ID
    anker_vid = 0x2516  # This is a common Anker vendor ID
    
    # First try with the known Anker vendor ID
    print(f"Looking for Anker camera with vendor ID 0x{anker_vid:04x}...")
    devices = list(usb.core.find(find_all=True, idVendor=anker_vid))
    
    if devices:
        for device in devices:
            try:
                product = usb.util.get_string(device, device.iProduct)
                if "PowerConf C200" in product or "Anker" in product:
                    print(f"Found Anker PowerConf C200: {product}")
                    return device
            except:
                pass
        
        # If we found Anker devices but none matched, return the first one
        print(f"Found an Anker device (might be PowerConf C200): VID=0x{devices[0].idVendor:04x}, PID=0x{devices[0].idProduct:04x}")
        return devices[0]
    
    # If no Anker VID found, search all USB devices for "Anker" or "PowerConf" in the product name
    print("Searching all USB devices for Anker camera...")
    all_devices = usb.core.find(find_all=True)
    
    for device in all_devices:
        try:
            product = usb.util.get_string(device, device.iProduct)
            if product and ("PowerConf" in product or "Anker" in product or "C200" in product):
                print(f"Found Anker camera: {product}")
                print(f"VID=0x{device.idVendor:04x}, PID=0x{device.idProduct:04x}")
                return device
        except:
            pass
    
    # If still not found, search for camera class devices (might be Anker but we can't read the name)
    print("Looking for any video class device (may be Anker camera)...")
    for device in all_devices:
        try:
            for cfg in device:
                for intf in cfg:
                    if intf.bInterfaceClass == 14:  # Video class
                        print(f"Found a Video device (might be Anker): VID=0x{device.idVendor:04x}, PID=0x{device.idProduct:04x}")
                        return device
        except:
            pass
    
    return None

def find_video_control_interface(device):
    """Find the Video Control interface in the device"""
    try:
        # Get active configuration
        cfg = device.get_active_configuration()
        
        # Find video control interface
        for i in range(cfg.bNumInterfaces):
            try:
                intf = cfg[(i, 0)]
                if intf.bInterfaceClass == 14 and intf.bInterfaceSubClass == 1:  # Video, Control
                    print(f"Found Video Control interface: {i}")
                    return intf
            except Exception as e:
                print(f"Error checking interface {i}: {e}")
    except Exception as e:
        print(f"Error getting configuration: {e}")
        
        # Alternative method - iterate through all interfaces
        try:
            for cfg in device:
                for intf in cfg:
                    if intf.bInterfaceClass == 14 and intf.bInterfaceSubClass == 1:  # Video, Control
                        print(f"Found Video Control interface through alternative method")
                        return intf
        except Exception as e2:
            print(f"Alternative method also failed: {e2}")
    
    # If we can't find the right interface, return a mock interface for the first one
    class MockInterface:
        def __init__(self):
            self.bInterfaceNumber = 0
    
    print("Warning: Couldn't find Video Control interface, using interface 0")
    return MockInterface()

def test_uvc_controls(device, interface):
    """Test UVC controls for the Anker PowerConf C200"""
    # Default terminal and unit IDs (typical for most UVC cameras)
    camera_terminal_id = 1
    processing_unit_id = 2
    
    # Get interface number
    interface_number = getattr(interface, 'bInterfaceNumber', 0)
    
    # List of controls to test - specific to Anker PowerConf C200
    # Based on common UVC controls that webcams typically support
    controls = [
        {"name": "Brightness", "unit": processing_unit_id, "selector": 0x02, "length": 2},
        {"name": "Contrast", "unit": processing_unit_id, "selector": 0x03, "length": 2},
        {"name": "Saturation", "unit": processing_unit_id, "selector": 0x07, "length": 2},
        {"name": "Sharpness", "unit": processing_unit_id, "selector": 0x08, "length": 2},
        {"name": "White Balance", "unit": processing_unit_id, "selector": 0x0A, "length": 2},
        {"name": "Auto White Balance", "unit": processing_unit_id, "selector": 0x11, "length": 1},
        {"name": "Auto Exposure Mode", "unit": camera_terminal_id, "selector": 0x02, "length": 1},
        {"name": "Exposure Time", "unit": camera_terminal_id, "selector": 0x04, "length": 4},
        {"name": "Focus", "unit": camera_terminal_id, "selector": 0x06, "length": 2},
        {"name": "Auto Focus", "unit": camera_terminal_id, "selector": 0x12, "length": 1},
        {"name": "Zoom", "unit": camera_terminal_id, "selector": 0x0A, "length": 2}
    ]
    
    successful_controls = []
    
    print("\nTesting UVC controls for Anker PowerConf C200:")
    print("----------------------------------------------")
    
    for control in controls:
        try:
            print(f"Testing {control['name']}...")
            
            # GET_CUR request
            bmRequestType = 0xA1  # Direction: IN, Type: Class, Recipient: Interface
            bRequest = 0x81      # GET_CUR
            wValue = (control['selector'] << 8)  # Control selector in high byte
            wIndex = (control['unit'] << 8) | interface_number  # Unit ID in high byte, interface in low byte
            wLength = control['length']
            
            # Create a buffer for the response
            buffer = array.array('B', [0] * wLength)
            
            # Send control transfer with timeout
            result = device.ctrl_transfer(bmRequestType, bRequest, wValue, wIndex, buffer, timeout=1000)
            
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
                    set_result = device.ctrl_transfer(bmRequestType, bRequest, wValue, wIndex, data, timeout=1000)
                    
                    if set_result is not None:
                        print(f"  ✓ SET_CUR successful ({set_result})")
                        
                        # Wait a moment for the change to take effect
                        time.sleep(0.5)
                        
                        # Get the value again to see if it changed
                        result = device.ctrl_transfer(bmRequestType=0xA1, bRequest=0x81, 
                                                     wValue=wValue, wIndex=wIndex,
                                                     data_or_wLength=buffer, timeout=1000)
                        
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
        
        # Add a separator line
        print()
    
    # Summary of findings
    print("\nSUMMARY:")
    print("--------")
    print(f"Successfully read {len(successful_controls)} of {len(controls)} controls")
    
    if successful_controls:
        print("\nWorking controls for your Anker PowerConf C200:")
        for ctrl in successful_controls:
            print(f"- {ctrl['name']} (Unit: {ctrl['unit']}, Selector: 0x{ctrl['selector']:02x})")
    
    # Create a sample function to adjust a specific control
    if successful_controls:
        # Pick the first working control as an example
        sample_control = successful_controls[0]
        
        print("\nSample Python function to adjust", sample_control['name'])
        print("-" * 50)
        print(f"""
def set_{sample_control['name'].lower().replace(' ', '_')}(device, value):
    \"\"\"Set {sample_control['name']} to the specified value\"\"\"
    interface_number = {interface_number}  # Your camera's interface number
    unit_id = {sample_control['unit']}
    control_selector = 0x{sample_control['selector']:02x}
    
    # SET_CUR request
    bmRequestType = 0x21  # Direction: OUT, Type: Class, Recipient: Interface
    bRequest = 0x01      # SET_CUR
    wValue = (control_selector << 8)
    wIndex = (unit_id << 8) | interface_number
    
    # Prepare data buffer
    data = array.array('B', [0] * {sample_control['length']})
    """)
        
        if sample_control['length'] == 1:
            print("""    # For 1-byte control
    data[0] = value & 0xFF  # Ensure value is between 0-255
    """)
        elif sample_control['length'] == 2:
            print("""    # For 2-byte control
    data[0] = value & 0xFF           # Low byte
    data[1] = (value >> 8) & 0xFF    # High byte
    """)
        elif sample_control['length'] == 4:
            print("""    # For 4-byte control
    data[0] = value & 0xFF
    data[1] = (value >> 8) & 0xFF
    data[2] = (value >> 16) & 0xFF
    data[3] = (value >> 24) & 0xFF
    """)
        
        print("""    # Send control transfer
    result = device.ctrl_transfer(bmRequestType, bRequest, wValue, wIndex, data, timeout=1000)
    return result is not None
""")

def main():
    if not sys.platform.startswith('darwin'):
        print("This script is designed for macOS.")
        return
        
    print("Anker PowerConf C200 UVC Control Tool")
    print("====================================")
    
    # Find the Anker camera
    dev = find_anker_camera()
    
    if not dev:
        print("\nError: Could not find Anker PowerConf C200 camera.")
        print("Make sure the camera is connected and you're running with sudo.")
        return
    
    try:
        # Find the video control interface
        interface = find_video_control_interface(dev)
        
        # Test UVC controls
        test_uvc_controls(dev, interface)
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Release the device
        usb.util.dispose_resources(dev)
        print("\nDevice resources released.")

if __name__ == "__main__":
    main()