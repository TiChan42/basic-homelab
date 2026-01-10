"""
Drive Flashing Manager
=====================

Handles the low-level writing of ISO images to storage devices using 'dd'.
Ensures partitions are unmounted before writing and syncs data afterwards.
"""

import platform
import subprocess
import sys

# Import system_commands safely for both package and direct execution
try:
    from . import system_commands
except ImportError:
    import system_commands

def _unmount_target(device, system):
    """Unmounts the device before flashing."""
    print(f"Unmounting {device}...")
    
    if system == "Darwin":
        system_commands.run_command(["diskutil", "unmountDisk", device])
        return device.replace("/dev/disk", "/dev/rdisk") # Use raw disk for speed
        
    elif system == "Linux":
        system_commands.run_command(f"umount {device}* || true", shell=True)
        return device
        
    return device

def _run_dd(iso_path, target, system):
    """Constructs and runs the dd command."""
    print(f"Writing ISO to {target} (this will take time)...")
    
    dd_cmd = ["sudo", "dd", f"if={iso_path}", f"of={target}", "bs=4m", "conv=sync"]
    
    if system == "Linux":
        dd_cmd.append("status=progress")
        subprocess.run(dd_cmd, check=True)
    else:
        print("  (Running in background, please compare activity LED on drive if available)")
        subprocess.run(dd_cmd, check=True)

def flash_drive(iso_path, device):
    """
    Flashes the ISO to the device using dd.
    
    Args:
        iso_path (str): Path to source ISO.
        device (str): Target device path (e.g. /dev/sdb).
    """
    system = platform.system()
    
    if system not in ["Darwin", "Linux"]:
        print("Flashing not supported on this OS in this script yet.")
        sys.exit(1)

    try:
        # 1. Prepare/Unmount
        target = _unmount_target(device, system)

        # 2. Write Data
        _run_dd(iso_path, target, system)
            
        # 3. Finalize
        print("Syncing...")
        system_commands.run_command(["sudo", "sync"])
        
    except subprocess.CalledProcessError:
        print("Error during flashing.")
        sys.exit(1)
