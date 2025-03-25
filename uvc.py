import usb.core
import usb.util
import array
import time
import sys

def list_all_usb_devices():
    """List all USB devices"""
    print("Listing USB devices:")
    print("-------------------")
    
    devices = list(usb.core.find(find_all=True))
    
    if not devices:
        print("No USB devices found. Try running with sudo.")
        return []
    
    devices_info = []
    
    for i, device in enumerate(devices):
        try:
            vid = device.idVendor
            pid = device.idProduct
            
            # Get strings if possible
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
            
            # Check if it might be a camera
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
            print(f"   VID: 0x{vid:04x}, PID: 0x{pid:04x}")
            print(f"   Type: {device_type}")
            print()
            
            devices_info.append({
                'index': i,
                'device': device,
                'manufacturer': manufacturer,
                'product': product,
                'vendor_id': vid,
                'product_id': pid,
                'is_camera': is_camera
            })
            
        except Exception as e:
            print(f"{i+1}. Error: {e}")
            print()
    
    return devices_info

def find_video_interfaces(device):
    """Find video interfaces in the device"""
    print(f"Looking for video interfaces...")
    
    video_interfaces = []
    
    try:
        # Get all configurations
        for cfg_idx in range(device.bNumConfigurations):
            try:
                cfg = device[cfg_idx]
                
                # Find all interfaces
                for intf_idx in range(cfg.bNumInterfaces):
                    try:
                        for alt in range(3):  # Try a few alternate settings
                            try:
                                intf = cfg[(intf_idx, alt)]
                                
                                # Check if this is a Video interface
                                if intf.bInterfaceClass == 14:  # Video class
                                    if_type = "Control" if intf.bInterfaceSubClass == 1 else "Streaming"
                                    print(f"  Found Video {if_type} interface: {intf_idx}")
                                    
                                    video_interfaces.append({
                                        'interface': intf,
                                        'index': intf_idx,
                                        'type': if_type
                                    })
                            except:
                                break
                    except:
                        pass
            except:
                pass
    except:
        pass
    
    return video_interfaces

def test_uvc_controls(device, interfaces):
    """Test UVC controls on the device"""
    # Find control interface
    control_interface = None
    interface_number = 0
    
    for intf in interfaces:
        if intf['type'] == 'Control':
            control_interface = intf['interface']
            interface_number = intf['index']
            break
    
    if not control_interface:
        print("No Video Control interface found.")
        if interfaces:
            print("Using first video interface instead.")
            control_interface = interfaces[0]['interface']
            interface_number = interfaces[0]['index']
        else:
            print("Using default interface 0.")
            interface_number = 0
    
    # Default UVC unit IDs
    camera_id = 1
    processing_id = 2
    
    # Find which unit IDs respond
    print("\nProbing for unit IDs...")
    
    # Set up control lists
    common_controls = [
        {"name": "Brightness", "unit": processing_id, "selector": 0x02, "length": 2},
        {"name": "Contrast", "unit": processing_id, "selector": 0x03, "length": 2},
        {"name": "Hue", "unit": processing_id, "selector": 0x06, "length": 2},
        {"name": "Saturation", "unit": processing_id, "selector": 0x07, "length": 2},
        {"name": "Sharpness", "unit": processing_id, "selector": 0x08, "length": 2},
        {"name": "Auto White Balance", "unit": processing_id, "selector": 0x11, "length": 1},
        {"name": "Auto Exposure", "unit": camera_id, "selector": 0x02, "length": 1},
        {"name": "Exposure Time", "unit": camera_id, "selector": 0x04, "length": 4},
        {"name": "Focus", "unit": camera_id, "selector": 0x06, "length": 2},
        {"name": "Auto Focus", "unit": camera_id, "selector": 0x12, "length": 1},
        {"name": "Zoom", "unit": camera_id, "selector": 0x0A, "length": 2}
    ]
    
    # Test controls
    print("\nTesting UVC controls:")
    print("--------------------")
    
    working_controls = []
    unit_tested = set()
    
    for control in common_controls:
        unit_id = control['unit']
        if unit_id in unit_tested:
            continue
            
        # Test one control for this unit to see if it responds
        print(f"Testing unit ID {unit_id}...")
        
        try:
            # GET_CUR request
            bmRequestType = 0xA1  # Direction: IN, Type: Class, Recipient: Interface
            bRequest = 0x81       # GET_CUR
            wValue = (control['selector'] << 8)
            wIndex = (unit_id << 8) | interface_number
            wLength = 1  # Short test
            
            buffer = array.array('B', [0] * wLength)
            
            result = device.ctrl_transfer(bmRequestType, bRequest, wValue, wIndex, buffer, timeout=300)
            
            if result:
                print(f"  Unit ID {unit_id} responded!")
                unit_tested.add(unit_id)
            else:
                print(f"  Unit ID {unit_id} did not respond")
        except:
            print(f"  Unit ID {unit_id} error")
    
    # Now test all controls
    for control in common_controls:
        try:
            name = control['name']
            unit = control['unit']
            selector = control['selector']
            length = control['length']
            
            print(f"Testing {name}...")
            
            # GET_CUR request
            bmRequestType = 0xA1
            bRequest = 0x81
            wValue = (selector << 8)
            wIndex = (unit << 8) | interface_number
            wLength = length
            
            buffer = array.array('B', [0] * wLength)
            
            result = device.ctrl_transfer(bmRequestType, bRequest, wValue, wIndex, buffer, timeout=500)
            
            if result:
                # Get value
                if length == 1:
                    value = result[0]
                elif length == 2:
                    value = result[0] | (result[1] << 8)
                elif length == 4:
                    value = result[0] | (result[1] << 8) | (result[2] << 16) | (result[3] << 24)
                else:
                    value = result
                
                print(f"  ✓ Success! Value: {value}")
                
                # Try setting value
                try:
                    print(f"  Testing SET_CUR...")
                    
                    bmRequestType = 0x21
                    bRequest = 0x01
                    
                    # Test value
                    if length == 1:
                        test_value = 0 if value > 0 else 1
                        data = array.array('B', [test_value])
                    elif length == 2:
                        test_value = 128
                        data = array.array('B', [test_value & 0xFF, (test_value >> 8) & 0xFF])
                    elif length == 4:
                        test_value = 1000
                        data = array.array('B', [
                            test_value & 0xFF, 
                            (test_value >> 8) & 0xFF,
                            (test_value >> 16) & 0xFF,
                            (test_value >> 24) & 0xFF
                        ])
                    
                    # Send control
                    result = device.ctrl_transfer(bmRequestType, bRequest, wValue, wIndex, data, timeout=500)
                    
                    if result is not None:
                        print(f"  ✓ Set value successful")
                        # Read again to verify change
                        time.sleep(0.2)
                        device.ctrl_transfer(0xA1, 0x81, wValue, wIndex, buffer, timeout=500)
                        print(f"  New value read back: {buffer[0] if length == 1 else 'complex value'}")
                    else:
                        print(f"  ✗ Set value failed")
                
                except Exception as e:
                    print(f"  ✗ Error setting: {e}")
                
                working_controls.append(control)
            else:
                print(f"  ✗ Failed")
        
        except Exception as e:
            print(f"  ✗ Error: {e}")
        
        print()
    
    # Print results
    print("\nRESULTS:")
    print("--------")
    
    if working_controls:
        print(f"Found {len(working_controls)} working controls:")
        for ctrl in working_controls:
            print(f"- {ctrl['name']} (Unit: {ctrl['unit']}, Selector: 0x{ctrl['selector']:02x})")
        
        # Generate sample code
        print("\nSample code to control this camera:")
        print("----------------------------------")
        print("import usb.core")
        print("import usb.util")
        print("import array")
        print("")
        print("class UVCCamera:")
        print("    def __init__(self):")
        print(f"        self.dev = usb.core.find(idVendor=0x{device.idVendor:04x}, idProduct=0x{device.idProduct:04x})")
        print("        if not self.dev:")
        print("            raise ValueError(\"Camera not found\")")
        print(f"        self.interface = {interface_number}")
        
        for unit in set(c['unit'] for c in working_controls):
            print(f"        self.UNIT_{unit} = {unit}")
        
        print("")
        print("    def _get_control(self, unit, selector, length):")
        print("        bmRequestType = 0xA1")
        print("        bRequest = 0x81")
        print("        wValue = (selector << 8)")
        print("        wIndex = (unit << 8) | self.interface")
        print("        buffer = array.array('B', [0] * length)")
        print("        result = self.dev.ctrl_transfer(bmRequestType, bRequest, wValue, wIndex, buffer)")
        print("        if not result:")
        print("            return None")
        print("        if length == 1:")
        print("            return result[0]")
        print("        elif length == 2:")
        print("            return result[0] | (result[1] << 8)")
        print("        else:")
        print("            return result")
        print("")
        
        print("    def _set_control(self, unit, selector, value, length):")
        print("        bmRequestType = 0x21")
        print("        bRequest = 0x01")
        print("        wValue = (selector << 8)")
        print("        wIndex = (unit << 8) | self.interface")
        print("        data = array.array('B')")
        print("        if length == 1:")
        print("            data.append(value)")
        print("        elif length == 2:")
        print("            data.append(value & 0xFF)")
        print("            data.append((value >> 8) & 0xFF)")
        print("        # Add more length handlers as needed")
        print("        return self.dev.ctrl_transfer(bmRequestType, bRequest, wValue, wIndex, data)")
        print("")
        
        # Add method for each control
        for ctrl in working_controls[:3]:  # First few controls as examples
            name = ctrl['name'].lower().replace(' ', '_')
            unit = ctrl['unit']
            selector = ctrl['selector']
            length = ctrl['length']
            
            print(f"    def get_{name}(self):")
            print(f"        return self._get_control(self.UNIT_{unit}, 0x{selector:02x}, {length})")
            print("")
            
            print(f"    def set_{name}(self, value):")
            print(f"        return self._set_control(self.UNIT_{unit}, 0x{selector:02x}, value, {length})")
            print("")
    else:
        print("No working UVC controls found on this device.")

def main():
    print("UVC Camera Tool")
    print("===============")
    
    # List devices
    devices = list_all_usb_devices()
    
    if not devices:
        return
    
    # Get cameras first
    cameras = [d for d in devices if d['is_camera']]
    other_devices = [d for d in devices if not d['is_camera']]
    
    if cameras:
        device_list = cameras
        print(f"\nFound {len(cameras)} camera devices")
    else:
        device_list = other_devices
        print("\nNo cameras found, showing other USB devices")
    
    # Select device
    if not device_list:
        print("No suitable devices found")
        return
    
    selected_device = device_list[0]['device']
    
    if len(device_list) > 1:
        try:
            print("\nSelect device:")
            for i, d in enumerate(device_list):
                print(f"{i+1}. {d['manufacturer']} {d['product']}")
            
            choice = input("\nEnter number [1]: ") or "1"
            choice = int(choice) - 1
            
            if 0 <= choice < len(device_list):
                selected_device = device_list[choice]['device']
            else:
                print("Invalid choice, using first device")
        except:
            print("Invalid input, using first device")
    
    print(f"\nUsing device: {usb.util.get_string(selected_device, selected_device.iProduct)}")
    
    try:
        # Find video interfaces
        interfaces = find_video_interfaces(selected_device)
        
        if not interfaces:
            print("No video interfaces found. Device may not be a UVC camera.")
            print("Continuing with tests anyway...")
        
        # Test UVC controls
        test_uvc_controls(selected_device, interfaces)
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Release device
        usb.util.dispose_resources(selected_device)

if __name__ == "__main__":
    main()