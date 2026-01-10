#!/bin/bash
# File: initial-setup/autoinstall_proxmox.sh
# This script runs in the Proxmox installer environment.

SOURCE_DIR=$(dirname "$0")
if [[ -f "$SOURCE_DIR/.env" ]]; then
    source "$SOURCE_DIR/.env"
fi

# Fallback or mapping
WIFI_SSID="${WIFI_SSID}"
WIFI_PSK="${WIFI_PASSWORD}" # Mapped from .env
USE_WIFI="no"
if [[ "$PREFER_WIFI_CONNECTION" == "true" ]]; then
    USE_WIFI="yes"
fi
ROOT_PASSWORD="${ROOT_PASSWORD}"

echo "=== Automated Proxmox Installation Script ==="

# 1. Configure network (Wi-Fi or DHCP on LAN)
if [[ "$USE_WIFI" == "yes" && -n "$WIFI_SSID" ]]; then
    echo "[*] Setting up Wi-Fi connection for installer..."
    if ! command -v iwconfig &>/dev/null; then
        apt-get update && apt-get install -y wireless-tools wpasupplicant
    fi
    # Bring up Wi-Fi interface (assuming wlan0)
    WIFI_IFACE="wlan0"
    # Create wpa_supplicant config
    cat > /etc/wpa_supplicant.conf <<EOF
network={
    ssid="${WIFI_SSID}"
    scan_ssid=1
    key_mgmt=WPA-PSK
    psk="${WIFI_PSK}"
}
EOF
    chmod 600 /etc/wpa_supplicant.conf
    wpa_supplicant -B -i "$WIFI_IFACE" -c /etc/wpa_supplicant.conf
    # Obtain IP via DHCP
    dhclient "$WIFI_IFACE"
    echo "Wi-Fi configured, checking connectivity..."
    ping -c 3 download.proxmox.com && echo "Network OK" || echo "Network check failed, continuing anyway."
else
    echo "[*] Using wired network (assuming DHCP on eth0)..."
    dhclient -1 eth0 || true
fi

# 2. Identify the primary disk to install to
DISK=""
# Prefer NVMe drive if present, else use first SATA
if [[ -b /dev/nvme0n1 ]]; then
    DISK="/dev/nvme0n1"
elif [[ -b /dev/sda ]]; then
    DISK="/dev/sda"
else
    # Try detecting largest disk if multiple
    DISK=$(lsblk -dn -o NAME,SIZE | sort -k2 -hr | head -1 | awk '{print "/dev/"$1}')
fi
if [[ -z "$DISK" ]]; then
    echo "ERROR: No disk found for installation."
    exit 1
fi
echo "[*] Target install disk: $DISK"

# 3. Partition the disk (UEFI + root)
echo "[*] Partitioning disk $DISK ..."
parted -s "$DISK" mklabel gpt
parted -s "$DISK" mkpart primary fat32 1MiB 512MiB
parted -s "$DISK" set 1 esp on
parted -s "$DISK" mkpart primary ext4 512MiB 100%
EFI_PART="${DISK}1"
ROOT_PART="${DISK}2"
# Format partitions
mkfs.vfat -F32 "$EFI_PART"
mkfs.ext4 -F "$ROOT_PART" -L pve-root

# 4. Mount and bootstrap a minimal Debian system
mount "$ROOT_PART" /mnt || { echo "Mount failed"; exit 1; }
mkdir -p /mnt/boot/efi
mount "$EFI_PART" /mnt/boot/efi
echo "[*] Installing minimal Debian base..."
apt-get update
# Install debootstrap if not present
if ! command -v debootstrap &>/dev/null; then
    apt-get install -y debootstrap
fi
debootstrap --include=openssh-server,gnupg bookworm /mnt http://deb.debian.org/debian/
# Note: Using Debian 12 (bookworm) since Proxmox VE 8.x/9.x is based on it.

# 5. Configure the new system (chroot) - sources and network
echo "deb http://download.proxmox.com/debian/pve bookworm pve-no-subscription" > /mnt/etc/apt/sources.list.d/pve.list
# Add Proxmox repository key
chroot /mnt bash -c "apt-get update && apt-get install -y wget gnupg"
chroot /mnt bash -c "wget -qO- https://enterprise.proxmox.com/debian/proxmox-release-bookworm.gpg | gpg --dearmor > /etc/apt/trusted.gpg.d/proxmox.gpg"
# Set hostname
echo "proxmox" > /mnt/etc/hostname
# Basic hosts file
echo "127.0.0.1 localhost proxmox" > /mnt/etc/hosts

# Localization (Timezone, Locale, Keyboard)
if [[ -n "$TIMEZONE" ]]; then
    echo "[*] Setting timezone to $TIMEZONE"
    echo "$TIMEZONE" > /mnt/etc/timezone
    chroot /mnt ln -sf "/usr/share/zoneinfo/$TIMEZONE" /etc/localtime
fi

if [[ -n "$LOCALE" ]]; then
    echo "[*] Setting locale to $LOCALE"
    # Enable locale in locale.gen
    sed -i "s/^# $LOCALE/$LOCALE/" /mnt/etc/locale.gen
    chroot /mnt locale-gen
    echo "LANG=$LOCALE" > /mnt/etc/default/locale
fi

if [[ -n "$KEYMAP" ]]; then
    echo "[*] Setting keyboard layout to $KEYMAP"
    # Basic console setup
    if [[ ! -f /mnt/etc/default/keyboard ]]; then
        echo "XKBLAYOUT=\"$KEYMAP\"" > /mnt/etc/default/keyboard
    else
        sed -i "s/XKBLAYOUT=.*/XKBLAYOUT=\"$KEYMAP\"/" /mnt/etc/default/keyboard
    fi
fi

# Networking in installed system
if [[ "$USE_WIFI" == "yes" && -n "$WIFI_SSID" ]]; then
    echo "[*] Configuring Wi-Fi for installed system..."
    chroot /mnt apt-get install -y wireless-tools wpasupplicant
    # create wpa_supplicant config
    cat > /mnt/etc/wpa_supplicant/wlan0.conf <<EONET
network={
    ssid="${WIFI_SSID}"
    scan_ssid=1
    key_mgmt=WPA-PSK
    psk="${WIFI_PSK}"
}
EONET
    chmod 600 /mnt/etc/wpa_supplicant/wlan0.conf
    # Setup /etc/network/interfaces for wlan0
    cat >> /mnt/etc/network/interfaces <<EONET

allow-hotplug wlan0
iface wlan0 inet dhcp
    wpa-conf /etc/wpa_supplicant/wlan0.conf
EONET
fi

# 6. Set root password
echo "root:$ROOT_PASSWORD" | chroot /mnt chpasswd

# 7. Install Proxmox VE packages
echo "[*] Installing Proxmox VE packages (this may take a while)..."
chroot /mnt apt-get update
# Prevent interactive prompts (e.g., for postfix)
chroot /mnt bash -c "DEBIAN_FRONTEND=noninteractive apt-get install -y proxmox-ve postfix open-iscsi"

# 8. Setup auto-run of post-install configuration on first boot
echo "[*] Setting up initial configuration script to run on first boot..."

# Copy the entire homelab repo if present
if [[ -d "$SOURCE_DIR/homelab-setup" ]]; then
    echo "[*] Copying homelab repository to target system..."
    cp -r "$SOURCE_DIR/homelab-setup" /mnt/root/homelab-setup
    
    # Ensure config.yml is in place if Ansible expects it elsewhere or as backup
    if [[ -f "/mnt/root/homelab-setup/config.yml" ]]; then
         cp "/mnt/root/homelab-setup/config.yml" /mnt/root/config.yml
    fi
fi

# Copy the init-install script into the new system (prefer from repo, then root fallback)
if [[ -f "/mnt/root/homelab-setup/initial-setup/init-install.sh" ]]; then
    cp "/mnt/root/homelab-setup/initial-setup/init-install.sh" /mnt/root/init-install.sh
elif [[ -f "$SOURCE_DIR/init-install.sh" ]]; then
    cp "$SOURCE_DIR/init-install.sh" /mnt/root/init-install.sh
fi
chmod +x /mnt/root/init-install.sh

# Persist config.yml to the new system (for Ansible)
if [[ -f "$SOURCE_DIR/config.yml" ]]; then
    cp "$SOURCE_DIR/config.yml" /mnt/root/config.yml
fi
# (Optional) Persist .env if debugging is needed, but config.yml is the source of truth now

# Create systemd service to run init-install.sh
cat > /mnt/etc/systemd/system/initial-setup.service <<'EOSVC'
[Unit]
Description=Initial Homelab Setup Service
After=network-online.target

[Service]
Type=oneshot
ExecStart=/root/init-install.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOSVC
# Enable the service
chroot /mnt systemctl enable initial-setup.service

# 9. Finalize installation: install GRUB and reboot
echo "[*] Installing GRUB bootloader..."
chroot /mnt apt-get install -y grub-efi-amd64
chroot /mnt grub-install "$DISK"
chroot /mnt update-grub

echo "Installation complete. Cleaning up..."
umount /mnt/boot/efi && umount /mnt
echo "[*] Rebooting into the new Proxmox system. Remove the USB installer now."
sleep 5
reboot -f
