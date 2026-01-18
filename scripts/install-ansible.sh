#!/usr/bin/env bash
set -euo pipefail

# Proxmox Ansible Installer for Debian
# Usage:
#   bash install-ansible.sh

if [[ "${EUID}" -ne 0 ]]; then
  echo "Please run as root (e.g., in the Proxmox shell you are usually root)."
  exit 1
fi

echo "==> Debian/Proxmox detected? (Info)"
cat /etc/os-release | sed -n '1,6p' || true
echo

echo "==> apt update"
apt-get update -y

echo "==> Installing base packages"
apt-get install -y --no-install-recommends \
  ca-certificates curl gnupg lsb-release \
  python3 python3-venv python3-pip

echo "==> Installing Ansible via apt"
apt-get install -y ansible

echo
echo "==> Versions"
ansible --version || true
python3 --version || true

echo
echo "Done. Ansible is installed."
