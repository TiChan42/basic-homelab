# Basic Homelab

Dieses Repository enthält Ansible-Playbooks und Scripts zur Einrichtung und Verwaltung eines grundlegenden Homelabs auf einem Proxmox Server.

## Struktur

- `ansible-playbooks/`: Enthält Ansible-Playbooks für verschiedene Aufgaben
  - `vars.example.yml`: Beispiel-Variablen-Datei
  - `vars.yml`: Aktuelle Variablen-Datei
  - `general/`: Allgemeine Playbooks für NFS-Mounting und Auto-Deployment
  - `services/`: Playbooks für spezifische Services
- `scripts/`: Hilfsscripts
  - `install-necessary-apt-packages.sh`: Script zur Installation notwendiger APT-Pakete
  - `run-all-playbooks.sh`: Script zum Ausführen aller Playbooks

## Proxmox Setup Struktur

Um eine saubere und wartbare Umgebung zu gewährleisten, empfehlen wir folgende Dateisystem-Struktur auf dem Proxmox-Host:

- `/var/lib/vz/`: Standardverzeichnis für VMs und Container
  - `images/`: VM-Images
  - `private/`: Private Daten der VMs
  - `template/`: Templates

- `/mnt/backups/`: Zentrales Backup-Verzeichnis
  - Mountet auf NAS für einfaches Synchronisieren
  - Enthält alle Backups von VMs, Containern und Konfigurationen

- `/mnt/nfs/`: NFS-Mounts für persistente Speicherung

Alle Backups sollten in `/mnt/backups/` abgelegt werden, um das Syncen mit dem NAS zu erleichtern. Verwende die Ansible-Playbooks in `general/` zum Mounten des NAS.

## Installation

1. Klone dieses Repository:
   ```
   git clone <repository-url>
   cd basic-homelab
   ```

2. Bearbeite die Variablen in `ansible-playbooks/vars.yml` basierend auf `vars.example.yml`.

3. Führe das Installationsscript aus:
   ```
   ./scripts/install-necessary-apt-packages.sh
   ```

## Verwendung

Um alle Playbooks auszuführen:
```
./scripts/run-all-playbooks.sh
```

Einzelne Playbooks können mit `ansible-playbook` ausgeführt werden, z.B.:
```
ansible-playbook ansible-playbooks/general/check-mount-nfs.yml
```

## Voraussetzungen

- Ansible installiert
- Zugriff auf die Zielhosts
- SSH-Schlüssel konfiguriert

## Lizenz

[Hier Lizenz angeben, falls vorhanden]