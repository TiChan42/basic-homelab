#!/bin/bash
# File: initial-setup/init-install.sh
# This script runs on first boot of the Proxmox host to configure VMs/containers and services.

set -e
echo "=== Proxmox Homelab Initial Setup ==="

# 1. Ensure required tools are installed
echo "[*] Installing Git and Ansible on Proxmox host..."
apt-get update
# Install git and ansible (ansible typically includes python3 and pyyaml)
apt-get install -y git ansible

# 2. Clone the homelab setup repository (if not already present)
REPO_URL="https://github.com/timogrethel/basic-homelab.git"
CLONE_DIR="/root/homelab-setup"

if [[ -d "$CLONE_DIR" ]]; then
    echo "[*] Local repository found at $CLONE_DIR. Using offline version."
    chown -R root:root "$CLONE_DIR"
else
    # Fallback to a default repo or error out if critical
    echo "[!] Local repository NOT found. This installation relies on the offline files."
    exit 1
fi

# Restore config.yml if present from install process
if [[ -f "/root/config.yml" ]]; then
    echo "[*] Restoring config.yml configuration..."
    mv /root/config.yml "$CLONE_DIR/config.yml"
fi

cd "$CLONE_DIR/initial-setup" || { echo "Repo clone failed or path not found."; exit 1; }

# 3. Load configuration variables
# No need to parse manually, pass config.yml to Ansible

# 4. Run Ansible playbooks to set up services
echo "[*] Running Ansible playbooks for VM and container setup..."

# Pass config.yml as extra vars (Ansible will read YAML file automatically with @)
if [[ -f "../config.yml" ]]; then
    echo "  > With configuration from config.yml"
    ansible-playbook -i "localhost," -c local ansible/site.yml --extra-vars "@../config.yml"
else
    echo "WARNING: ../config.yml not found! Using defaults."
    ansible-playbook -i "localhost," -c local ansible/site.yml
fi


# 5. Set up backup cron job if backup script and rclone are configured
if [[ -f "./backup.sh" ]]; then
    echo "[*] Installing rclone for backup..."
    apt-get install -y rclone
    echo "[*] Setting up daily backup cron job..."
    # (Ensure backup script is executable)
    chmod +x ./backup.sh
    # Add cron entry (runs at 3:00 AM every day)
    CRONJOB="0 3 * * * root /root/homelab-setup/initial-setup/backup.sh >> /var/log/homelab_backup.log 2>&1"
    # Install cron job if not already present
    (crontab -l 2>/dev/null | grep -F "$CLONE_DIR/initial-setup/backup.sh") || echo "$CRONJOB" >> /etc/crontab
fi

# 6. Disable the initial setup service (so it doesn't run on every boot)
echo "[*] Disabling initial-setup systemd service..."
systemctl disable initial-setup.service || true

echo "=== Initial homelab setup complete! ==="
echo "You can now access the Proxmox web UI and the services installed."
