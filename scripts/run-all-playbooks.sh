#!/bin/bash

# Script to run all Ansible playbooks: first general, then services.
# After all playbooks succeed, backs up all.yml to the NAS so it can be
# restored after a fresh install.
#
# Usage: ./run-all-playbooks.sh [ansible_dir]

set -euo pipefail

if [ -n "${1:-}" ]; then
    ANSIBLE_DIR="$1"
else
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    ANSIBLE_DIR="$SCRIPT_DIR/../ansible-playbooks"
fi

ANSIBLE_DIR="$(cd "$ANSIBLE_DIR" && pwd)"
ALL_YML="$ANSIBLE_DIR/inventory/group_vars/all.yml"

# ==============================================================================
# Helper: Read nas_mount from all.yml (plain YAML value, no Jinja2)
# ==============================================================================
get_nas_mount() {
    grep -E '^nas_mount:' "$ALL_YML" \
        | head -1 \
        | sed 's/^nas_mount:[[:space:]]*//' \
        | sed 's/^["'\'']//' \
        | sed 's/["'\'']\s*$//' \
        | sed 's/[[:space:]]*#.*//'
}

# ==============================================================================
# Run general playbooks
# ==============================================================================
echo "=========================================="
echo " Running general playbooks..."
echo "=========================================="
for playbook in "$ANSIBLE_DIR/general"/*.yml; do
    if [ -f "$playbook" ]; then
        echo "▶ Running $playbook"
        ansible-playbook -v -i "${ANSIBLE_DIR}/inventory/hosts.yml" "$playbook"
    fi
done

# ==============================================================================
# Run services playbooks
# ==============================================================================
echo "=========================================="
echo " Running services playbooks..."
echo "=========================================="
for playbook in "$ANSIBLE_DIR/services"/*/main.yml; do
    if [ -f "$playbook" ]; then
        echo "▶ Running $playbook"
        ansible-playbook -v -i "${ANSIBLE_DIR}/inventory/hosts.yml" "$playbook"
    fi
done

# ==============================================================================
# Backup Ansible config to NAS
# ==============================================================================
echo "=========================================="
echo " Backing up Ansible config to NAS..."
echo "=========================================="

NAS_MOUNT="$(get_nas_mount)"
CONFIG_BACKUP_DIR="$NAS_MOUNT/backups/ansible-config"

if [ -z "$NAS_MOUNT" ]; then
    echo "WARNING: Could not read nas_mount from $ALL_YML – skipping config backup."
    exit 0
fi

if ! mountpoint -q "$NAS_MOUNT" 2>/dev/null; then
    echo "WARNING: NAS not mounted at $NAS_MOUNT – skipping config backup."
    exit 0
fi

mkdir -p "$CONFIG_BACKUP_DIR"

# Copy config file (overwrite if changed)
cp -f "$ALL_YML" "$CONFIG_BACKUP_DIR/all.yml"

echo "✔ all.yml backed up to: $CONFIG_BACKUP_DIR/"

echo "=========================================="
echo " All playbooks executed successfully."
echo "=========================================="