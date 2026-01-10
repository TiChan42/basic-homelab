#!/bin/bash
# Script to update Docker containers
# Assumes that docker-compose is used.

# TODO: Adjust path to Docker Compose files or pass as parameter
SERVICES_DIR="/opt/homelab/services"

echo "Starting Docker updates..."

if [ -d "$SERVICES_DIR" ]; then
    cd "$SERVICES_DIR"
    docker compose pull
    docker compose up -d
    docker image prune -f
else
    echo "Directory $SERVICES_DIR not found."
fi
