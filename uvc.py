import usb.core
import usb.util
import array
import subprocess
import json
import time

def find_macos_cameras():
    """Find USB cameras on macOS using system_profiler"""
    try:
        cmd = ['system_profiler', 'SPUSBDataType', '-json']
        result = subprocess.run(cmd, capture_output=True, text=True)
        usb_info = json.loads(result.stdout)
        
        cameras = []
        
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
        return cameras
    
    except Exception as e:
        print(f"Error finding cameras: {e}")
        return []

def main():
    # Find cameras
    cameras = find_macos_cameras()
    
    if not cameras:
        print("No cameras found using system_profiler")
        return
    
    print("Found cameras:")
    for i, camera in enumerate(cameras):
        print(f"{i+1}. {camera['name']} (VID: 0x{camera['vendor_id']:04x}, PID: 0x{camera['product_id']:04x})")
    
    # Get camera selection
    selection = 0
    if len(cameras) > 1:
        try:
            selection = int(input("Select camera (number): ")) - 1
            if selection < 0 or selection >= len(cameras):
                print("Invalid selection")
                return
        except ValueError:
            print("Invalid input")
            return
    
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
            # Basic UVC control parameters
            bmRequestType = 0xA1  # Direction: IN, Type: Class, Recipient: Interface
            bRequest = 0x81      # GET_CUR
            wValue = (0x02 << 8) # Brightness control is 0x02
            wIndex = (processing_unit_id << 8) | interface_number
            wLength = 2
            
            # Create a buffer for the response
            buffer = array.array('B', [0] * wLength)
            
            # Send control transfer
            result = dev.ctrl_transfer(bmRequestType, bRequest, wValue, wIndex, buffer)
            
            if result:
                brightness = result[0] | (result[1] << 8) if len(result) > 1 else result[0]
                print(f"Current brightness: {brightness}")
                
                # Try setting brightness
                print("Setting brightness to 128...")
                
                bmRequestType = 0x21  # Direction: OUT, Type: Class, Recipient: Interface
                bRequest = 0x01      # SET_CUR
                
                # Create data buffer with new value
                data = array.array('B', [128, 0])
                
                result = dev.ctrl_transfer(bmRequestType, bRequest, wValue, wIndex, data)
                print(f"Set brightness result: {result}")
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