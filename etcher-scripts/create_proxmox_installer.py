import os
import sys
import platform

# Configuration
script_dir = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(script_dir, "downloads")
ISO_NAME = "proxmox-ve_latest.iso"

try:
    from utils import validate_config
    from utils import check_dependencies
    from utils import iso_manager
    from utils import drive_manager
    from utils import flash_manager
    from utils import config_injector
except ImportError as e:
    print(f"Error importing helper modules: {e}")
    print(f"Ensure that the 'utils' directory exists in {script_dir} and contains an __init__.py and the required python files.")
    sys.exit(1)

def main():
    if platform.system() not in ["Darwin", "Linux"]:
        print("This script currently supports macOS and Linux.")
        sys.exit(1)

    # 1. Check Dependencies
    print("\n--- Step 1: Dependencies ---")
    if not check_dependencies.verify_dependencies():
        sys.exit(1)

    # 2. Validate Config
    print("--- Step 2: Validation ---")
    if not validate_config.validate_config("config.yml"):
        sys.exit(1)

    # 3. ISO Setup
    print("\n--- Step 3: ISO Download ---")
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)
    
    iso_url = iso_manager.get_latest_iso_url()
    iso_path = os.path.join(DOWNLOAD_DIR, ISO_NAME)
    iso_manager.download_file(iso_url, iso_path)

    # 4. Drive Selection
    print("\n--- Step 4: Select USB Drive ---")
    target_drive = drive_manager.select_drive()
    if not target_drive:
        sys.exit(1)

    print(f"\nWARNING: ALL DATA ON {target_drive} WILL BE ERASED!")
    if input("Type 'YES' to continue: ") != "YES":
        print("Aborted.")
        sys.exit(1)

    # 5. Flash
    print(f"\n--- Step 5: Flashing {ISO_NAME} to {target_drive} ---")
    flash_manager.flash_drive(iso_path, target_drive)

    # 6. Post-Config
    print("\n--- Step 6: Injecting Configuration ---")
    config_injector.mount_efi_and_copy(target_drive)

    # 7. Finalize
    print("\n--- Step 7: Finalizing & Ejecting ---")
    drive_manager.eject_drive(target_drive)
    
    print("\n" + "="*50)
    print("SUCCESS! The Installer USB is ready.")
    print("="*50)
    print("\nNext Steps:")
    print("1. Remove the USB drive.")
    print("2. Insert it into your target machine.")
    print("3. Boot the machine from USB (F6/F11/F12 during BIOS POST).")
    print("4. The installation will start automatically and configure itself.")
    print("5. Once finished, the system will reboot into Proxmox VE.")
    print("\nHappy Homelabbing!")

if __name__ == "__main__":
    if not os.path.exists("config.yml.example"):
        print("Error: Please run this script from the root of the repository.")
        sys.exit(1)
        
    try:
        main()
    except KeyboardInterrupt:
        print("\nAborted by user.")
        sys.exit(1)
