import usb.core
import usb.util
import array
import subprocess
import json
import time

def find_macos_cameras():
    """Find USB cameras on macOS using both system_profiler and direct USB enumeration"""
    cameras = []
    
    # First, try using pyusb to enumerate all USB devices
    try:
        print("Searching for USB devices...")
        all_devices = usb.core.find(find_all=True)
        
        if all_devices:
            # Common webcam vendor IDs
            webcam_vendors = {
                0x046d: "Logitech",
                0x05ac: "Apple",
                0x041e: "Creative",
                0x0c45: "Microdia",
                0x13d3: "IMC Networks / Integrated Camera",
                0x045e: "Microsoft",
                0x0bda: "Realtek",
                0x1871: "Aveo",
                0x0ac8: "Z-Star Microelectronics",
                0x0402: "ALi Corp"
            }
            
            for device in all_devices:
                try:
                    device_info = {}
                    vendor_id = device.idVendor
                    product_id = device.idProduct
                    
                    # Check if this is likely a camera
                    is_likely_camera = False
                    
                    # Check if it's a known webcam vendor
                    if vendor_id in webcam_vendors:
                        is_likely_camera = True
                        device_info["name"] = f"{webcam_vendors[vendor_id]} Camera"
                    else:
                        # Try to check device class
                        try:
                            if device.bDeviceClass == 239:  # Miscellaneous Device Class (often used for cameras)
                                is_likely_camera = True
                                device_info["name"] = "USB Camera"
                            else:
                                # Look at interfaces
                                for cfg in device:
                                    for intf in cfg:
                                        if intf.bInterfaceClass == 14:  # Video class
                                            is_likely_camera = True
                                            device_info["name"] = "USB Video Device"
                                            break
                                    if is_likely_camera:
                                        break
                        except:
                            pass
                    
                    if is_likely_camera:
                        try:
                            # Try to get a better name
                            try:
                                mfg = usb.util.get_string(device, device.iManufacturer)
                                product = usb.util.get_string(device, device.iProduct)
                                if mfg and product:
                                    device_info["name"] = f"{mfg} {product}"
                                elif product:
                                    device_info["name"] = product
                            except:
                                pass
                            
                            device_info["vendor_id"] = vendor_id
                            device_info["product_id"] = product_id
                            cameras.append(device_info)
                        except:
                            pass
                except Exception as e:
                    print(f"Error processing device: {e}")
    except Exception as e:
        print(f"Error during USB enumeration: {e}")
    
    # If we found cameras, return them
    if cameras:
        return cameras
    
    # As a fallback, try system_profiler
    try:
        print("No cameras found via USB enumeration, trying system_profiler...")
        cmd = ['system_profiler', 'SPUSBDataType', '-json']
        result = subprocess.run(cmd, capture_output=True, text=True)
        usb_info = json.loads(result.stdout)
        
        def traverse_usb_tree(node):
            if isinstance(node, list):
                for item in node:
                    traverse_usb_tree(item)
            elif isinstance(node, dict):
                # Look for camera-related keywords
                if '_name' in node and any(keyword in node['_name'].lower() 
                                        for keyword in ['camera', 'webcam', 'facetime', 'uvc']):
                    if 'vendor_id' in node and 'product_id' in node:
                        try:
                            vid = int(node['vendor_id'].replace('0x', ''), 16)
                            pid = int(node['product_id'].replace('0x', ''), 16)
                            cameras.append({
                                'name': node['_name'],
                                'vendor_id': vid,
                                'product_id': pid
                            })
                        except ValueError:
                            pass
                
                for key, value in node.items():
                    if isinstance(value, (list, dict)):
                        traverse_usb_tree(value)
        
        traverse_usb_tree(usb_info.get('SPUSBDataType', []))
    
    except Exception as e:
        print(f"Error with system_profiler: {e}")
    
    # If still no cameras found, add fallback options for common camera IDs
    if not cameras:
        print("No cameras found via automatic detection, adding common camera types...")
        cameras.extend([
            {'name': 'Apple FaceTime HD Camera', 'vendor_id': 0x05ac, 'product_id': 0x8514},
            {'name': 'Logitech Webcam C270', 'vendor_id': 0x046d, 'product_id': 0x082d},
            {'name': 'Generic USB Camera', 'vendor_id': 0x0c45, 'product_id': 0x6366}
        ])
    
    return cameras

def main():
    # Find cameras
    cameras = find_macos_cameras()
    
    if not cameras:
        print("No cameras found. This is highly unusual as we include fallbacks.")
        return
    
    print("\nAvailable cameras:")
    for i, camera in enumerate(cameras):
        print(f"{i+1}. {camera['name']} (VID: 0x{camera['vendor_id']:04x}, PID: 0x{camera['product_id']:04x})")
    
    # Get camera selection
    selection = 0
    if len(cameras) > 1:
        try:
            selection = int(input("\nSelect camera (number): ")) - 1
            if selection < 0 or selection >= len(cameras):
                print("Invalid selection, using the first camera")
                selection = 0
        except ValueError:
            print("Invalid input, using the first camera")
            selection = 0
    
    # Connect to the selected camera
    camera = cameras[selection]
    print(f"Connecting to {camera['name']}...")
    
    try:
        # Find the device
        dev = usb.core.find(idVendor=camera['vendor_id'], idProduct=camera['product_id'])
        
        if dev is None:
            print("Device not found. You may need to run this with sudo")
            return
        
        print(f"Device found: {dev}")
        
        # Try to get control interface
        interface = None
        
        try:
            # Get active configuration
            cfg = dev.get_active_configuration()
            
            # Find video control interface
            for i in range(cfg.bNumInterfaces):
                try:
                    intf = cfg[(i, 0)]
                    if intf.bInterfaceClass == 14 and intf.bInterfaceSubClass == 1:  # Video, Control
                        interface = intf
                        print(f"Found Video Control interface: {i}")
                        break
                except:
                    continue
        except Exception as e:
            print(f"Error getting configuration: {e}")
        
        # Set simple default values for control units
        camera_terminal_id = 1
        processing_unit_id = 2
        interface_number = getattr(interface, 'bInterfaceNumber', 0) if interface else 0
        
        # Try brightness control as an example
        print("Attempting to get brightness...")
        
        try:
            # Try common controls
        controls = [
            {"name": "Brightness", "unit": processing_unit_id, "selector": 0x02, "length": 2},
            {"name": "Contrast", "unit": processing_unit_id, "selector": 0x03, "length": 2},
            {"name": "Auto Focus", "unit": camera_terminal_id, "selector": 0x12, "length": 1},
            {"name": "Focus", "unit": camera_terminal_id, "selector": 0x06, "length": 2},
            {"name": "Auto Exposure", "unit": camera_terminal_id, "selector": 0x02, "length": 1},
            {"name": "Exposure Time", "unit": camera_terminal_id, "selector": 0x04, "length": 4},
            {"name": "Zoom", "unit": camera_terminal_id, "selector": 0x0A, "length": 2}
        ]
        
        print("\nAttempting to read camera controls...")
        successful_controls = 0
        
        for control in controls:
            try:
                print(f"\nTrying to get {control['name']}...")
                
                # UVC GET_CUR request
                bmRequestType = 0xA1  # Direction: IN, Type: Class, Recipient: Interface
                bRequest = 0x81      # GET_CUR
                wValue = (control['selector'] << 8)  # Control selector in high byte
                wIndex = (control['unit'] << 8) | interface_number
                wLength = control['length']
                
                # Create a buffer for the response
                buffer = array.array('B', [0] * wLength)
                
                # Send control transfer
                result = dev.ctrl_transfer(bmRequestType, bRequest, wValue, wIndex, buffer)
                
                if result:
                    if wLength == 1:
                        value = result[0]
                    elif wLength == 2:
                        value = result[0] | (result[1] << 8)
                    elif wLength == 4:
                        value = result[0] | (result[1] << 8) | (result[2] << 16) | (result[3] << 24)
                    else:
                        value = result
                    
                    print(f"✓ Success! Current {control['name']}: {value}")
                    successful_controls += 1
                    
                    # If we succeeded, try setting a value (only for non-boolean controls)
                    if control['length'] > 1:
                        print(f"  Setting {control['name']} to a test value...")
                        
                        # UVC SET_CUR request
                        bmRequestType = 0x21  # Direction: OUT, Type: Class, Recipient: Interface
                        bRequest = 0x01      # SET_CUR
                        
                        # Create data buffer with test value
                        if control['length'] == 2:
                            test_value = 128  # Middle value for most 2-byte controls
                            data = array.array('B', [test_value & 0xFF, (test_value >> 8) & 0xFF])
                        elif control['length'] == 4:
                            test_value = 1000  # Reasonable value for 4-byte controls
                            data = array.array('B', [
                                test_value & 0xFF, 
                                (test_value >> 8) & 0xFF,
                                (test_value >> 16) & 0xFF,
                                (test_value >> 24) & 0xFF
                            ])
                        
                        result = dev.ctrl_transfer(bmRequestType, bRequest, wValue, wIndex, data)
                        if result is not None:
                            print(f"  ✓ Value set successfully! ({result})")
                        else:
                            print(f"  ✗ Failed to set value")
                else:
                    print(f"✗ Failed to get {control['name']}")
            
            except usb.core.USBError as e:
                print(f"✗ USB Error for {control['name']}: {e}")
            except Exception as e:
                print(f"✗ Error for {control['name']}: {e}")
        
        print(f"\nSummary: Successfully accessed {successful_controls} out of {len(controls)} controls")
            else:
                print("Failed to get brightness")
        
        except usb.core.USBError as e:
            print(f"USB Error: {e}")
            if "Access denied" in str(e) or "Permission denied" in str(e):
                print("You may need to run this script with sudo")
            elif "No such device" in str(e):
                print("Device disconnected or not responding")
        
        finally:
            # Release the device
            usb.util.dispose_resources(dev)
    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()