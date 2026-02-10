#!/bin/bash

# ==============================================================================
# Restore Ansible config (all.yml) from NAS backup.
#
# This script reads the NAS mount path from the EXISTING all.yml (if present)
# or falls back to the default /mnt/nas. It then copies the backed-up all.yml
# back into the Ansible inventory directory.
#
# Use Case:
#   After a fresh Proxmox install, clone the repo, mount the NAS manually,
#   then run this script to restore your personalized configuration.
#
# Usage:
#   ./restore-config-from-nas.sh [ansible_dir]
#
# Manual NAS mount (if mount-persistent-storage.yml hasn't run yet):
#   mount -t nfs <NAS_IP>:<EXPORT> /mnt/nas
# ==============================================================================

set -euo pipefail

if [ -n "${1:-}" ]; then
    ANSIBLE_DIR="$1"
else
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    ANSIBLE_DIR="$SCRIPT_DIR/../ansible-playbooks"
fi

ANSIBLE_DIR="$(cd "$ANSIBLE_DIR" && pwd)"
ALL_YML="$ANSIBLE_DIR/inventory/group_vars/all.yml"

DEFAULT_NAS_MOUNT="/mnt/nas"

# ==============================================================================
# Helper: Read nas_mount from all.yml (if it exists)
# ==============================================================================
get_nas_mount() {
    if [ -f "$ALL_YML" ]; then
        local val
        val=$(grep -E '^nas_mount:' "$ALL_YML" \
            | head -1 \
            | sed 's/^nas_mount:[[:space:]]*//' \
            | sed 's/^["'\'']//' \
            | sed 's/["'\'']\s*$//' \
            | sed 's/[[:space:]]*#.*//')
        if [ -n "$val" ]; then
            echo "$val"
            return
        fi
    fi
    echo "$DEFAULT_NAS_MOUNT"
}

# ==============================================================================
# Main
# ==============================================================================
NAS_MOUNT="$(get_nas_mount)"
CONFIG_BACKUP_DIR="$NAS_MOUNT/backups/ansible-config"

echo "=========================================="
echo " Restore Ansible Config from NAS"
echo "=========================================="
echo "  NAS mount:    $NAS_MOUNT"
echo "  Backup dir:   $CONFIG_BACKUP_DIR"
echo "  Target dir:   $ANSIBLE_DIR/inventory/"
echo ""

# Verify NAS is mounted
if ! mountpoint -q "$NAS_MOUNT" 2>/dev/null; then
    echo "ERROR: NAS is not mounted at $NAS_MOUNT"
    echo ""
    echo "Mount it manually first, e.g.:"
    echo "  mount -t nfs <NAS_IP>:<EXPORT> $NAS_MOUNT"
    echo ""
    echo "Or run the mount playbook first:"
    echo "  ansible-playbook -i $ANSIBLE_DIR/inventory/hosts.yml $ANSIBLE_DIR/general/mount-persistent-storage.yml"
    exit 1
fi

# Verify backup exists
if [ ! -d "$CONFIG_BACKUP_DIR" ]; then
    echo "ERROR: No config backup found at $CONFIG_BACKUP_DIR"
    echo "  Has run-all-playbooks.sh ever completed successfully?"
    exit 1
fi

SRC="$CONFIG_BACKUP_DIR/all.yml"

if [ ! -f "$SRC" ]; then
    echo "ERROR: all.yml not found in backup at $SRC"
    exit 1
fi

# Check if target already exists and differs
if [ -f "$ALL_YML" ]; then
    if cmp -s "$SRC" "$ALL_YML"; then
        echo "  ✔ all.yml is already up to date – nothing to do."
        exit 0
    fi

    # Create a timestamped backup of the current file before overwriting
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_NAME="${ALL_YML}.pre-restore.${TIMESTAMP}"
    cp -f "$ALL_YML" "$BACKUP_NAME"
    echo "  ⚠ all.yml differs – existing file backed up to:"
    echo "    $(basename "$BACKUP_NAME")"
fi

cp -f "$SRC" "$ALL_YML"

echo ""
echo "=========================================="
echo " ✔ all.yml restored successfully."
echo "=========================================="
