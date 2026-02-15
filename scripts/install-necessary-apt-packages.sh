#!/usr/bin/env bash
set -euo pipefail

# Necessary APT Software Installer for Debian
# Usage:
#   bash install-necessary-apt-software.sh

# List of packages to install
PACKAGES=(
  ca-certificates
  curl
  gnupg
  lsb-release
  python3
  python3-venv
  python3-pip
  ansible
)

# Python packages needed by Ansible filters (e.g. password_hash)
PIP_PACKAGES=(
  passlib
  bcrypt
)

if [[ "${EUID}" -ne 0 ]]; then
  echo "Please run as root (e.g., in the Proxmox shell you are usually root)."
  exit 1
fi

echo "==> Debian/Proxmox detected? (Info)"
cat /etc/os-release | sed -n '1,6p' || true
echo

echo "==> apt update"
apt-get update -y

echo "==> Installing necessary packages"
for pkg in "${PACKAGES[@]}"; do
  echo "==> Installing $pkg"
  apt-get install -y --no-install-recommends "$pkg"
done

echo
echo "==> Installing Python packages via pip"
for pkg in "${PIP_PACKAGES[@]}"; do
  echo "==> pip install $pkg"
  pip3 install --break-system-packages "$pkg"
done

echo
echo "==> Versions"
for pkg in "${PACKAGES[@]}"; do
  echo "==> $pkg version"
  $pkg --version || true
done

echo
echo "Done. All necessary software is installed."
