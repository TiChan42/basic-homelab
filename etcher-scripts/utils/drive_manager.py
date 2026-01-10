"""
Drive Selection Manager
======================

Provides utilities to list, select, and eject external storage devices.
Supports both macOS (diskutil) and Linux (lsblk).
"""

import platform
import json
import sys

# Import system_commands safely for both package and direct execution
try:
    from . import system_commands
except ImportError:
    import system_commands

def _get_drives_macos():
    """Helper to list drives on macOS using diskutil."""
    drives = []
    try:
        # 1. Run diskutil to list external physical disks
        txt_out = system_commands.run_command(["diskutil", "list", "external", "physical"])
        
        # 2. Parse output
        for line in txt_out.split('\n'):
            if line.startswith("/dev/disk"):
                parts = line.split()
                dev = parts[0]
                drives.append({'device': dev, 'description': line})
    except Exception as e:
        print(f"Error listing macOS drives: {e}")
    return drives

def _get_drives_linux():
    """Helper to list drives on Linux using lsblk."""
    drives = []
    try:
        # 1. Run lsblk for JSON output
        output = system_commands.run_command(["lsblk", "-J", "-o", "NAME,SIZE,TYPE,TRAN,MODEL"])
        data = json.loads(output)
        
        # 2. Parse JSON
        for dev in data.get('blockdevices', []):
            # Filter for USB or Disk types
            if dev.get('tran') == 'usb' or dev.get('type') == 'disk': 
                name = f"/dev/{dev['name']}"
                model = dev.get('model', 'Unknown')
                size = dev.get('size', '')
                desc = f"{name} ({size}) {model}"
                drives.append({'device': name, 'description': desc})
    except Exception as e:
        print(f"Error listing Linux drives: {e}")
    return drives

def get_removable_drives():
    """
    Returns a cross-platform list of removable drives.
    
    Returns:
        list[dict]: List of {'device': str, 'description': str}
    """
    system = platform.system()
    
    if system == "Darwin":
        return _get_drives_macos()
    elif system == "Linux":
        return _get_drives_linux()
    else:
        print(f"Drive listing not supported on {system}")
        return []

def select_drive():
    """
    Interactively prompts the user to select a drive from the list.
    
    Returns:
        str or None: The selected device path (e.g. /dev/sdb) or None if aborted.
    """
    print("Scanning for drives...")
    drives = get_removable_drives()
    
    if not drives:
        print("No removable drives found.")
        return None

    # Print selection menu
    print("\nAvailable Drives:")
    for i, d in enumerate(drives):
        print(f"[{i+1}] {d['description']}")

    # Get user input
    choice = input("\nSelect drive number (or 'q' to quit): ")
    if choice.lower() == 'q':
        sys.exit(0)
    
    try:
        idx = int(choice) - 1
        if idx < 0 or idx >= len(drives):
            raise ValueError
        return drives[idx]['device']
    except ValueError:
        print("Invalid selection.")
        return None

def eject_drive(device):
    """
    Safely ejects (unmounts/powers off) the specified drive.
    
    Args:
        device (str): Device path to eject.
    """
    system = platform.system()
    print(f"Ejecting {device}...")
    
    if system == "Darwin":
        system_commands.run_command(["diskutil", "eject", device])
    elif system == "Linux":
        try:
            system_commands.run_command(["sudo", "eject", device])
        except Exception:
             print("Could not eject automatically. You may remove the drive safely if the activity light stopped.")
