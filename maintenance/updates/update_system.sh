#!/bin/bash
# Script for system updates (apt update/upgrade)
# Can be executed on the Proxmox host or in containers/VMs.

echo "Starting system updates..."
apt-get update && apt-get upgrade -y
echo "System updates completed."
