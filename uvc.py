import usb.core
import usb.util
import array
import sys

# Your specific camera details from the error message
CAMERA_VID = 0x291a  # Vendor ID from your output
CAMERA_PID = 0x3369  # Product ID from your output

def test_direct_controls():
    """Test UVC controls directly on your specific camera"""
    print(f"Looking for camera with VID=0x{CAMERA_VID:04x}, PID=0x{CAMERA_PID:04x}...")
    
    # Find your camera directly
    dev = usb.core.find(idVendor=CAMERA_VID, idProduct=CAMERA_PID)
    
    if not dev:
        print("Camera not found. Make sure it's connected and you're running with sudo.")
        return
    
    print("Camera found!")
    
    # Try to set configuration (may fail, that's ok)
    try:
        dev.set_configuration()
    except:
        pass
    
    # Common UVC interface numbers
    interfaces_to_try = [0, 1, 2, 3]
    
    # Common UVC unit IDs
    camera_terminal_ids = [1, 2, 3]     # Camera Terminal is usually 1
    processing_unit_ids = [2, 3, 4, 5]  # Processing Unit is usually 2
    
    # Common UVC controls to test
    controls = [
        {"name": "Brightness", "selector": 0x02, "length": 2},
        {"name": "Contrast", "selector": 0x03, "length": 2},
        {"name": "Saturation", "selector": 0x07, "length": 2},
        {"name": "Sharpness", "selector": 0x08, "length": 2},
        {"name": "Auto White Balance", "selector": 0x11, "length": 1},
        {"name": "Auto Exposure", "selector": 0x02, "length": 1},
        {"name": "Focus", "selector": 0x06, "length": 2},
        {"name": "Auto Focus", "selector": 0x12, "length": 1},
        {"name": "Zoom", "selector": 0x0A, "length": 2},
    ]
    
    # Test each combination
    successful_controls = []
    
    for interface_num in interfaces_to_try:
        print(f"\nTrying interface {interface_num}...")
        
        # Test processing unit controls (brightness, contrast, etc.)
        for unit_id in processing_unit_ids:
            print(f"  Testing Processing Unit ID {unit_id}...")
            
            # Try each control
            for control in controls:
                try:
                    print(f"    Testing {control['name']}...")
                    
                    # GET_CUR request
                    bmRequestType = 0xA1  # Direction: IN, Type: Class, Recipient: Interface
                    bRequest = 0x81       # GET_CUR
                    wValue = (control['selector'] << 8)
                    wIndex = (unit_id << 8) | interface_num
                    wLength = control['length']
                    
                    buffer = array.array('B', [0] * wLength)
                    
                    # Send request with short timeout
                    result = dev.ctrl_transfer(bmRequestType, bRequest, wValue, wIndex, buffer, timeout=200)
                    
                    if result:
                        # Parse value
                        if wLength == 1:
                            value = result[0]
                        elif wLength == 2:
                            value = result[0] | (result[1] << 8)
                        else:
                            value = result
                        
                        print(f"      ✓ Success! Current value: {value}")
                        
                        # Record success
                        successful_controls.append({
                            "name": control['name'],
                            "unit_id": unit_id,
                            "interface": interface_num,
                            "selector": control['selector'],
                            "length": control['length']
                        })
                    else:
                        print(f"      ✗ No data returned")
                
                except usb.core.USBError as e:
                    if "timeout" in str(e).lower():
                        print(f"      ✗ Timeout")
                    else:
                        print(f"      ✗ USB Error: {e}")
                except Exception as e:
                    print(f"      ✗ Error: {e}")
        
        # Test camera terminal controls (focus, zoom, etc.)
        for unit_id in camera_terminal_ids:
            print(f"  Testing Camera Terminal ID {unit_id}...")
            
            # Test only camera-related controls
            camera_controls = [c for c in controls if c['name'] in 
                              ["Auto Exposure", "Focus", "Auto Focus", "Zoom"]]
            
            for control in camera_controls:
                try:
                    print(f"    Testing {control['name']}...")
                    
                    # GET_CUR request
                    bmRequestType = 0xA1
                    bRequest = 0x81
                    wValue = (control['selector'] << 8)
                    wIndex = (unit_id << 8) | interface_num
                    wLength = control['length']
                    
                    buffer = array.array('B', [0] * wLength)
                    
                    # Send request with short timeout
                    result = dev.ctrl_transfer(bmRequestType, bRequest, wValue, wIndex, buffer, timeout=200)
                    
                    if result:
                        # Parse value
                        if wLength == 1:
                            value = result[0]
                        elif wLength == 2:
                            value = result[0] | (result[1] << 8)
                        else:
                            value = result
                        
                        print(f"      ✓ Success! Current value: {value}")
                        
                        # Record success
                        successful_controls.append({
                            "name": control['name'],
                            "unit_id": unit_id,
                            "interface": interface_num,
                            "selector": control['selector'],
                            "length": control['length']
                        })
                    else:
                        print(f"      ✗ No data returned")
                
                except usb.core.USBError as e:
                    if "timeout" in str(e).lower():
                        print(f"      ✗ Timeout")
                    else:
                        print(f"      ✗ USB Error: {e}")
                except Exception as e:
                    print(f"      ✗ Error: {e}")
    
    # Print results
    print("\n\nRESULTS:")
    print("========")
    
    if successful_controls:
        print(f"Found {len(successful_controls)} working controls:")
        
        # Group by interface/unit
        controls_by_interface = {}
        
        for ctrl in successful_controls:
            key = f"Interface {ctrl['interface']}, Unit {ctrl['unit_id']}"
            if key not in controls_by_interface:
                controls_by_interface[key] = []
            controls_by_interface[key].append(ctrl)
        
        for key, ctrls in controls_by_interface.items():
            print(f"\n{key}:")
            for ctrl in ctrls:
                print(f"  - {ctrl['name']} (Selector: 0x{ctrl['selector']:02x})")
        
        # Generate sample code for the interface with most controls
        best_interface = max(controls_by_interface.items(), key=lambda x: len(x[1]))
        interface_num = best_interface[1][0]['interface']
        
        print("\n\nSample Python code for your camera:")
        print("=================================")
        print("import usb.core")
        print("import usb.util")
        print("import array")
        print("")
        print("class UVCCamera:")
        print("    def __init__(self):")
        print(f"        self.dev = usb.core.find(idVendor=0x{CAMERA_VID:04x}, idProduct=0x{CAMERA_PID:04x})")
        print("        if not self.dev:")
        print("            raise ValueError(\"Camera not found\")")
        print(f"        self.interface = {interface_num}")
        print("")
        
        # Add unit constants
        units = set(ctrl['unit_id'] for ctrl in best_interface[1])
        for unit in units:
            print(f"        self.UNIT_{unit} = {unit}")
        
        print("")
        print("    def get_control(self, unit, selector, length):")
        print("        try:")
        print("            bmRequestType = 0xA1")
        print("            bRequest = 0x81")
        print("            wValue = (selector << 8)")
        print("            wIndex = (unit << 8) | self.interface")
        print("            buffer = array.array('B', [0] * length)")
        print("            ")
        print("            result = self.dev.ctrl_transfer(")
        print("                bmRequestType, bRequest, wValue, wIndex, buffer, timeout=1000)")
        print("            ")
        print("            if not result:")
        print("                return None")
        print("                ")
        print("            if length == 1:")
        print("                return result[0]")
        print("            elif length == 2:")
        print("                return result[0] | (result[1] << 8)")
        print("            else:")
        print("                return result")
        print("        except Exception as e:")
        print("            print(f\"Error reading control: {e}\")")
        print("            return None")
        print("")
        
        print("    def set_control(self, unit, selector, value, length):")
        print("        try:")
        print("            bmRequestType = 0x21")
        print("            bRequest = 0x01")
        print("            wValue = (selector << 8)")
        print("            wIndex = (unit << 8) | self.interface")
        print("            ")
        print("            data = array.array('B')")
        print("            if length == 1:")
        print("                data.append(value & 0xFF)")
        print("            elif length == 2:")
        print("                data.append(value & 0xFF)")
        print("                data.append((value >> 8) & 0xFF)")
        print("            elif length == 4:")
        print("                data.append(value & 0xFF)")
        print("                data.append((value >> 8) & 0xFF)")
        print("                data.append((value >> 16) & 0xFF)")
        print("                data.append((value >> 24) & 0xFF)")
        print("            ")
        print("            result = self.dev.ctrl_transfer(")
        print("                bmRequestType, bRequest, wValue, wIndex, data, timeout=1000)")
        print("            return result is not None")
        print("        except Exception as e:")
        print("            print(f\"Error setting control: {e}\")")
        print("            return False")
        print("")
        
        # Add control methods
        for ctrl in best_interface[1]:
            name = ctrl['name'].lower().replace(' ', '_')
            unit = ctrl['unit_id']
            selector = ctrl['selector']
            length = ctrl['length']
            
            print(f"    def get_{name}(self):")
            print(f"        return self.get_control(self.UNIT_{unit}, 0x{selector:02x}, {length})")
            print("")
            
            if name.startswith('auto'):
                print(f"    def set_{name}(self, enabled):")
                print(f"        return self.set_control(self.UNIT_{unit}, 0x{selector:02x}, 1 if enabled else 0, {length})")
            else:
                print(f"    def set_{name}(self, value):")
                print(f"        return self.set_control(self.UNIT_{unit}, 0x{selector:02x}, value, {length})")
            print("")
        
        print("    def close(self):")
        print("        usb.util.dispose_resources(self.dev)")
        print("")
        print("# Example usage")
        print("if __name__ == \"__main__\":")
        print("    try:")
        print("        camera = UVCCamera()")
        print("        print(\"Connected to camera!\")")
        print("")
        
        # Add example for first control
        if best_interface[1]:
            ctrl = best_interface[1][0]
            name = ctrl['name'].lower().replace(' ', '_')
            print(f"        value = camera.get_{name}()")
            print(f"        print(f\"{ctrl['name']}: {value}\")")
            print("")
            
            if name.startswith('auto'):
                print(f"        # Toggle auto mode")
                print(f"        camera.set_{name}(not value)")
            else:
                print(f"        # Set to middle value")
                print(f"        camera.set_{name}(128)")
            
            print("")
            print("        camera.close()")
            print("    except Exception as e:")
            print("        print(f\"Error: {e}\")")
    else:
        print("No working UVC controls found on this camera.")
        print("\nTry these troubleshooting steps:")
        print("1. Make sure you're running the script with sudo")
        print("2. Try using a different USB port")
        print("3. If on macOS, there may be system restrictions on camera access")

if __name__ == "__main__":
    test_direct_controls()