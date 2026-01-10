#!/bin/bash
# File: initial-setup/backup.sh
# Description: Collects and syncs backup data for homelab services.

# Load Environment Configuration
# Now using yq (installed with jq usually OR python) to parse YAML config
SCRIPT_DIR="$(dirname "$(realpath "$0")")"
CONFIG_FILE="$SCRIPT_DIR/../config.yml"

if [[ ! -f "$CONFIG_FILE" ]]; then
    # Fallback to old behavior if config not found (shouldn't happen)
    exit 0
fi

# Need python to parse yaml if yq is missing
has_config=$(python3 -c "import yaml; print(1)" 2>/dev/null)
if [[ -z "$has_config" ]]; then
    echo "Python3 with PyYAML required for backup script."
    # Try to install python3-yaml if missing (Debian)
    apt-get install -y python3-yaml || true
fi

# Check if backups are enabled
# We look for connections list length > 0
BACKUP_ENABLED=$(python3 -c "
import yaml, sys
try:
    with open('$CONFIG_FILE') as f:
        c = yaml.safe_load(f)
    conns = c.get('backup', {}).get('connections', [])
    print('yes' if conns and len(conns) > 0 else 'no')
except:
    print('no')
")

if [[ "$BACKUP_ENABLED" != "yes" ]]; then
    echo "Backup connections empty or not configured. Skipping backup."
    exit 0
fi

# Ensure rclone is configured for targets
# Simple check: If connection is defined but rclone config is missing it, standard setup might fail.
# For this basic setup, we assume rclone is configured OR we use a simple local target if specified.
# (Advanced dynamic rclone config creation from JSON would be implemented here)

# Get Service IDs from config.yml by looking up the NAME in Proxmox
# We don't read IDs from config anymore, we look for running containers/VMs with the configured Name.

# Helper function to get name from config
get_name() {
    python3 -c "import yaml; print(yaml.safe_load(open('$CONFIG_FILE')).get('services', {}).get('$1', {}).get('name', ''))" 2>/dev/null
}

# Helper to resolve Name -> ID (VM or CT)
resolve_id() {
    local name="$1"
    if [[ -z "$name" ]]; then echo ""; return; fi
    
    # Try VM (qm)
    local vmid=$(qm list 2>/dev/null | grep -F " $name " | awk '{print $1}')
    if [[ -n "$vmid" ]]; then echo "$vmid"; return; fi
    
    # Try CT (pct)
    local ctid=$(pct list 2>/dev/null | grep -F " $name " | awk '{print $1}')
    if [[ -n "$ctid" ]]; then echo "$ctid"; return; fi
}

HA_NAME=$(get_name "home_assistant")
HA_VMID=$(resolve_id "$HA_NAME")

Z2M_NAME=$(get_name "zigbee2mqtt")
Z2M_CTID=$(resolve_id "$Z2M_NAME")

NR_NAME=$(get_name "nodered")
NR_CTID=$(resolve_id "$NR_NAME")

N8N_NAME=$(get_name "n8n")
N8N_CTID=$(resolve_id "$N8N_NAME")

GF_NAME=$(get_name "grafana")
GF_CTID=$(resolve_id "$GF_NAME")


BACKUP_ROOT="/backup/homelab"
DATE=$(date +%F)
mkdir -p "$BACKUP_ROOT"

echo "==== Homelab Backup $(date) ===="

# 1. Home Assistant snapshots
HA_BACKUP_DIR="$BACKUP_ROOT/homeassistant"
mkdir -p "$HA_BACKUP_DIR"
echo "[*] Backing up Home Assistant snapshots (VM $HA_VMID)..."
# HAOS stores backups here internally
HA_SNAPSHOT_PATH="/root/config/backups"   
# Copy latest snapshot from HA VM (using qm guest exec if possible)
if [[ -n "$HA_VMID" ]]; then
    qm guest exec $HA_VMID -- ls $HA_SNAPSHOT_PATH || echo "HA snapshot path not accessible"
fi
# (In practice, one might use the HA CLI or an SMB share to get backups. This is a placeholder.)

# 2. Zigbee2MQTT data
Z2M_BACKUP_DIR="$BACKUP_ROOT/zigbee2mqtt"
mkdir -p "$Z2M_BACKUP_DIR"
echo "[*] Backing up Zigbee2MQTT data (CT $Z2M_CTID)..."
if [[ -n "$Z2M_CTID" ]]; then
    pct exec $Z2M_CTID -- tar -czf /tmp/z2m_backup.tgz -C /opt/zigbee2mqtt/data configuration.yaml database.db
    pct pull $Z2M_CTID /tmp/z2m_backup.tgz "$Z2M_BACKUP_DIR/z2m_$DATE.tgz"
    pct exec $Z2M_CTID -- rm /tmp/z2m_backup.tgz
fi

# 3. Node-RED flows
NR_BACKUP_DIR="$BACKUP_ROOT/nodered"
mkdir -p "$NR_BACKUP_DIR"
echo "[*] Backing up Node-RED flows (CT $NR_CTID)..."
if [[ -n "$NR_CTID" ]]; then
    pct pull $NR_CTID /root/.node-red/flows.json "$NR_BACKUP_DIR/flows_$DATE.json"
    pct pull $NR_CTID /root/.node-red/flows_cred.json "$NR_BACKUP_DIR/flows_cred_$DATE.json"
fi

# 4. n8n workflows (SQLite DB or via export)
N8N_BACKUP_DIR="$BACKUP_ROOT/n8n"
mkdir -p "$N8N_BACKUP_DIR"
echo "[*] Backing up n8n data (CT $N8N_CTID)..."
if [[ -n "$N8N_CTID" ]]; then
    pct pull $N8N_CTID /var/lib/n8n/.n8n/database.sqlite "$N8N_BACKUP_DIR/n8n_$DATE.sqlite" 2>/dev/null || echo "No SQLite DB found - maybe using different DB."
fi

# 5. Grafana (if used)
GF_BACKUP_DIR="$BACKUP_ROOT/grafana"
mkdir -p "$GF_BACKUP_DIR"
echo "[*] Backing up Grafana database (CT $GF_CTID)..."
if [[ -n "$GF_CTID" ]]; then
    pct pull $GF_CTID /var/lib/grafana/grafana.db "$GF_BACKUP_DIR/grafana_$DATE.db" 2>/dev/null || echo "No Grafana DB found or container not present."
fi

# 6. Sync backups to external storage using rclone (if configured)
# Requires rclone remote configured in /root/.config/rclone/rclone.conf
echo "[*] Syncing backups to remote storage (if configured)..."
# Example: sync to NAS or cloud
if grep -q '\[nas\]' /root/.config/rclone/rclone.conf; then
    rclone sync "$BACKUP_ROOT" nas:homelab_backup
fi
if grep -q '\[gdrive\]' /root/.config/rclone/rclone.conf; then
    rclone sync "$BACKUP_ROOT" gdrive:homelab_backup
fi

echo "==== Backup completed ===="
