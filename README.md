# Basic Homelab - Automated Proxmox Setup

This repository provides a complete **Infrastructure-as-Code (IaC)** solution to set up a "Basic Homelab" server based on Proxmox VE. It automates the entire process, from creating a custom installation medium (USB stick) to the OS installation and the configuration of services (Home Assistant, MQTT, etc.) using Ansible.

## 🚀 How it Works

The system operates in three main phases:

1.  **Preparation (Local Machine):** A Python script downloads the latest Proxmox ISO, flashes it to a USB stick, and injects your configuration (`config.yml`) and setup scripts directly into the installation medium.
2.  **Installation (Server Hardware):** You boot the server from the USB stick. An auto-install script partitions the drive, installs a minimal Debian/Proxmox system, and persists this repository to the hard drive.
3.  **Configuration (First Boot):** Upon the first reboot, the system automatically installs Ansible and runs playbooks to set up your defined services (LXC containers, VMs) and storage.

## 📋 Prerequisites

*   **Local Machine:** macOS or Linux (Windows specific support is currently experimental/not fully implemented).
*   **Python 3:** Required to run the installer generator.
*   **USB Stick:** At least 4GB. **Warning: All data on the stick will be erased.**
*   **Target Server:** A dedicated machine (Mini-PC, Server) connected to the internet via Ethernet (recommended) or Wi-Fi.

## 🛠️ Usage Guide

### 1. Setup Configuration
Clone the repository and prepare your configuration:

```bash
git clone <repository-url>
cd basic-homelab
cp config.yml.example config.yml
```

Edit `config.yml` to set your preferences:
*   Define root/admin passwords.
*   Set timezone and locale.
*   Configure network settings (Wifi or Ethernet).
*   Enable/Disable specific services (Home Assistant, MQTT, etc.).

### 2. Create Installer USB
Insert your USB stick and run the generator script (requires root privileges for direct disk access):

```bash
sudo python3 etcher-scripts/create_proxmox_installer.py
```

Follow the interactive prompts:
*   The script will download the Proxmox ISO.
*   Select your USB drive.
*   Wait for flashing and configuration injection to complete.

### 3. Install on Server
1.  Insert the USB stick into your target server.
2.  Boot the server and select the USB drive in the BIOS/Boot Menu.
3.  The installation script (`initial-setup/autoinstall_proxmox.sh`) effectively takes over. *Note: Depending on the bootloader configuration, you might need to trigger the partition script manually or select the automated entry.*
4.  Once finished, the system will reboot.

### 4. Post-Installation
After the reboot, run `tail -f /var/log/syslog` or checking the status of `initial-setup.service` to monitor the Ansible provisioning process.

Once complete, your services (like Home Assistant) will be accessible via their configured IPs/Hostnames.

## 📂 Server Directory Structure

After installation, the file structure on the **Proxmox Host** is organized for easy maintenance:

```text
/
├── root/
│   ├── config.yml                # Your original configuration
│   └── homelab-setup/            # Copy of this repo for maintenance/updates
│       ├── maintenance/
│       └── ...
│
├── home/
│   └── [admin-user]/
│       └── homelab-data -> /var/lib/homelab-data  # Symlink for easy access
│
├── var/
│   └── lib/
│       └── homelab-data/         # CENTRAL STORAGE FOR CONTAINER DATA
│           ├── mqtt/
│           ├── zigbee2mqtt/
│           └── ...
│
└── backup/
    └── homelab/                  # Local backups
```

**Key Concept:** Services (LXC/VMs) do not store persistent data inside their virtual disks. Instead, they "bind mount" folders from `/var/lib/homelab-data` on the host. This makes backing up the entire system as simple as backing up that one folder.

## 🔄 Maintenance

Scripts for maintenance are located in `maintenance/`:
*   **Backups:** `./maintenance/backups/backup.sh` (Runs via cronjob automatically).
*   **Updates:** `./maintenance/updates/update_system.sh`.

## 📄 License

[MIT](LICENSE)
