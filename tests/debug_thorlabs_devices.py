import clr
from pathlib import Path

try:
    # Load DLLs
    dll_path = Path(__file__).parent.parent / "Thorlabs_DLL"
    clr.AddReference(str(dll_path / "Thorlabs.MotionControl.DeviceManagerCLI.dll"))
    clr.AddReference(str(dll_path / "Thorlabs.MotionControl.PolarizerCLI.dll"))
    from Thorlabs.MotionControl.DeviceManagerCLI import DeviceManagerCLI
    from Thorlabs.MotionControl.PolarizerCLI import Polarizer
    
    print("✓ DLLs loaded successfully")
    
    # Build device list
    print("Building device list...")
    DeviceManagerCLI.BuildDeviceList()
    
    # Get all available devices
    device_list = DeviceManagerCLI.GetDeviceList()
    print(f"Found {len(device_list)} devices:")
    
    for i, device in enumerate(device_list):
        print(f"  Device {i}: {device}")
    
    # Get polarizer devices specifically
    polarizer_list = DeviceManagerCLI.GetDeviceList(Polarizer.DevicePrefix)
    print(f"\nFound {len(polarizer_list)} polarizer devices:")
    
    for i, device in enumerate(polarizer_list):
        print(f"  Polarizer {i}: {device}")
        
    # Check if the serial number from your config exists
    target_serial = "38000001"  # From your main SOA_TESTING.py
    test_serial = "38487984"    # From the test file
    
    print(f"\nChecking for target serial numbers:")
    print(f"  Main config serial ({target_serial}): {'FOUND' if target_serial in device_list else 'NOT FOUND'}")
    print(f"  Test file serial ({test_serial}): {'FOUND' if test_serial in device_list else 'NOT FOUND'}")
    
    if len(polarizer_list) > 0:
        print(f"\nRecommendation: Use serial number '{polarizer_list[0]}' in your test")
    else:
        print("\nNo polarizer devices found. Check USB connections!")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()