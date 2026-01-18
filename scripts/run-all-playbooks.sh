#!/bin/bash

# Script to run all Ansible playbooks: first general, then services
# Usage: ./run-all-playbooks.sh [ansible_dir]

if [ -n "$1" ]; then
    ANSIBLE_DIR="$1"
else
    SCRIPT_DIR="$(dirname "$0")"
    ANSIBLE_DIR="$SCRIPT_DIR/../ansible-playbooks"
fi

# Run general playbooks
for playbook in "$ANSIBLE_DIR/general"/*.yml; do
    if [ -f "$playbook" ]; then
        echo "Running $playbook"
        ansible-playbook "$playbook"
    fi
done

# Run services playbooks
for playbook in "$ANSIBLE_DIR/services"/*.yml; do
    if [ -f "$playbook" ]; then
        echo "Running $playbook"
        ansible-playbook "$playbook"
    fi
done

echo "All playbooks executed."