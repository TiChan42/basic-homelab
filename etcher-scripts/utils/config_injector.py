"""
Configuration Injector
=====================

Handles the post-flash configuration injection.
Mounts the EFI partition of the created installer media and places
necessary scripts and configuration files into it.
"""

import os
import shutil
import time
import platform
import subprocess
import sys
import tempfile

try:
    from . import system_commands
    from . import env_generator
except ImportError:
    import system_commands
    import env_generator

MOUNT_POINT = "/tmp/pve-efi-mount"

def _prepare_mount_point():
    """Cleans and creates the temporary mount point."""
    if os.path.exists(MOUNT_POINT):
        # Allow removing as root in case previous run left it owned by root
        system_commands.run_command(["sudo", "rm", "-rf", MOUNT_POINT])
    
    os.makedirs(MOUNT_POINT, exist_ok=True)

def _find_efi_partition_macos(device):
    """Identifies the EFI partition slice on macOS."""
    system_commands.run_command(["diskutil", "unmountDisk", device], check=False)
    output = system_commands.run_command(["diskutil", "list", device])
    
    for line in output.split('\n'):
        if "EFI" in line:
                parts = line.split()
                for p in parts:
                    if p.startswith(os.path.basename(device)):
                        return f"/dev/{p}"
    return f"{device}s1" # Default fallback

def _find_efi_partition_linux(device):
    """Identifies the EFI partition on Linux (usually partition 2 for Proxmox ISOs)."""
    system_commands.run_command(["sudo", "partprobe", device], check=False)
    time.sleep(2)
    return f"{device}2" 

def _mount_partition(device, system):
    """Finds and mounts the EFI partition."""
    print("Searching for EFI partition...")
    time.sleep(2) # Wait for system to settle

    partition = ""
    if system == "Darwin":
        partition = _find_efi_partition_macos(device)
        print(f"Mounting {partition} on {MOUNT_POINT}...")
        system_commands.run_command(["sudo", "mount", "-t", "msdos", partition, MOUNT_POINT])
        
    elif system == "Linux":
        partition = _find_efi_partition_linux(device)
        # Try mounting partition 2, fallback to 1 
        res = subprocess.run(["sudo", "mount", partition, MOUNT_POINT], capture_output=True)
        if res.returncode != 0:
             partition = f"{device}1"
             system_commands.run_command(["sudo", "mount", partition, MOUNT_POINT])

def _copy_files(config_path):
    """Copies the repo to the mount point using sudo."""
    print("Copying configuration scripts and repository...")
    
    repo_root = os.getcwd() 
    
    # 1. Copy repository to the stick
    # Create a dedicated directory to keep the root clean
    dest_repo_dir = os.path.join(MOUNT_POINT, "homelab-setup")
    system_commands.run_command(["sudo", "mkdir", "-p", dest_repo_dir])

    # Exclusion list for files/folders to skip
    excludes = [
        "etcher-scripts", # Contains huge downloads/ISOs -> IMPORTANT: Exclude
        ".git", 
        ".github",
        ".venv", 
        ".vscode", 
        "__pycache__",
        ".DS_Store"
    ]

    print(f"  -> Transferring repository content to {dest_repo_dir}...")
    
    # Iterate through root directory and copy non-excluded items
    for item in os.listdir(repo_root):
        if item in excludes:
            continue
            
        src = os.path.join(repo_root, item)
        dst = os.path.join(dest_repo_dir, item)
        
        # Copy directories recursively, files directly
        if os.path.isdir(src):
            system_commands.run_command(["sudo", "cp", "-r", src, dst])
        else:
            system_commands.run_command(["sudo", "cp", src, dst])

    # 2. Place boot/entry point files in root
    # Script must be in root for the Proxmox installer hook to find it
    print("  -> Placing bootstrap files in EFI root...")
    
    bootstrap_files = [
        ("initial-setup/autoinstall_proxmox.sh", "autoinstall_proxmox.sh"),
        ("initial-setup/autoinstall.service", "autoinstall.service")
    ]
    
    for src_rel, dest_name in bootstrap_files:
        src_path = os.path.join(repo_root, src_rel)
        dest_path = os.path.join(MOUNT_POINT, dest_name)
        
        if os.path.exists(src_path):
            system_commands.run_command(["sudo", "cp", src_path, dest_path])
        else:
            print(f"     Warning: {src_rel} not found!")

    # 2. Generate and Copy .env (also in root for easy script access)
    print("Generating .env configuration...")
    try:
        env_content = env_generator.generate_env_content(config_path)
        
        # Use tempfile instead of pipe for cleaner handling
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
            tmp.write(env_content)
            tmp.write("\n")
            tmp_path = tmp.name
        
        print("  -> .env")
        system_commands.run_command(["sudo", "cp", tmp_path, os.path.join(MOUNT_POINT, ".env")])
        os.remove(tmp_path)
        
    except Exception as e:
        print(f"Error generating .env file: {e}")

    # 3. Set Permissions (Best effort for FAT32)
    print("Setting permissions...")
    system_commands.run_command(["sudo", "chmod", "+x", os.path.join(MOUNT_POINT, "autoinstall_proxmox.sh")], check=False)


def mount_efi_and_copy(device, config_path="config.yml"):
    """
    Orchestrates the injection process.
    
    Args:
        device (str): The target device path.
        config_path (str): Path to local config.yml.
    """
    system = platform.system()
    
    try:
        # 1. Prepare
        _prepare_mount_point()
        
        # 2. Mount
        _mount_partition(device, system)
        
        # 3. Copy
        _copy_files(config_path)
        
    except Exception as e:
        print(f"Error during configuration injection: {e}")
        
    finally:
        # 4. Clean up / Unmount
        print("Unmounting...")
        if os.path.exists(MOUNT_POINT):
            subprocess.run(["sudo", "umount", MOUNT_POINT], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
