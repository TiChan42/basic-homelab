# Basic Homelab

Ansible-basierte Automatisierung für ein Homelab auf Proxmox VE. Dieses Repository provisioniert und konfiguriert alle Services vollautomatisch – von der Container-/VM-Erstellung über die Service-Konfiguration bis hin zu automatisierten Backups auf ein NAS.

## Architektur

```
┌─────────────────────────────────────────────────────────────┐
│                      Proxmox VE Host                        │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  LXC: MQTT   │  │ LXC: Web-    │  │  VM: Home        │  │
│  │  Broker       │  │ server(s)    │  │  Assistant OS    │  │
│  │  (Mosquitto)  │  │ (Node.js)    │  │  (HAOS + Z2M)    │  │
│  │  :1883        │  │ :3003+       │  │  :8123           │  │
│  └──────┬───────┘  └──────────────┘  └────────┬─────────┘  │
│         │              MQTT Traffic            │            │
│         │◄─────────────────────────────────────┘            │
│         │         Zigbee USB Dongle ──► VM (Z2M Add-on)     │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  NFS Mount: /mnt/nas                                 │   │
│  │  ├── services/       (Service-Daten)                 │   │
│  │  └── backups/        (Backups + Ansible-Config)      │   │
│  │      ├── mqtt-broker/                                │   │
│  │      ├── homeassistant/                              │   │
│  │      └── ansible-config/all.yml                      │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                           │
                    NFS    │
                           ▼
                    ┌──────────────┐
                    │     NAS      │
                    └──────────────┘
```

## Enthaltene Services

| Service | Typ | Beschreibung |
|---|---|---|
| **MQTT Broker** | LXC | Eclipse Mosquitto mit Authentifizierung, Backup/Restore |
| **Home Assistant** | VM (HAOS) | Smart-Home-Zentrale mit Zigbee2MQTT, Matter, USB-Passthrough |
| **Webserver** | LXC | Node.js-Webserver(s) aus Git-Repos |

## Repository-Struktur

```
basic-homelab/
├── README.md
├── ansible-playbooks/
│   ├── ansible.cfg
│   ├── inventory/
│   │   ├── hosts.yml                   # Host-IPs, VMIDs, Gruppen
│   │   └── group_vars/
│   │       ├── all.yml                 # Zentrale Konfiguration (NICHT im Repo)
│   │       └── all.example.yml         # Vorlage zum Kopieren
│   ├── general/
│   │   ├── mount-persistent-storage.yml
│   │   ├── check-mount-nfs.yml
│   │   ├── setup-auto-deployment.yml
│   │   └── templates/
│   │       ├── check_nfs_mount.sh.j2
│   │       └── homelab_auto_deployment.sh.j2
│   └── services/
│       ├── webserver/
│       │   ├── main.yml
│       │   └── templates/
│       │       ├── netplan.yaml.j2
│       │       └── webserver.service.j2
│       ├── mqtt-broker/
│       │   ├── main.yml
│       │   └── templates/
│       │       ├── netplan.yaml.j2
│       │       ├── mosquitto.conf.j2
│       │       ├── mqtt_backup.sh.j2
│       │       ├── mqtt_restore.sh.j2
│       │       └── mqtt-restore.service.j2
│       └── homeassistant/
│           ├── main.yml
│           └── templates/
│               └── ha_backup.sh.j2
└── scripts/
    ├── install-necessary-apt-packages.sh
    ├── run-all-playbooks.sh
    └── restore-config-from-nas.sh
```

## Proxmox-Dateisystem

Die Playbooks erzeugen folgende Struktur auf dem Proxmox-Host:

```
/mnt/nas/                              # NFS-Mount (NAS)
├── services/                          # Persistente Service-Daten
└── backups/                           # Alle Backups
    ├── mqtt-broker/                   # Mosquitto Config + Persistence
    │   ├── mosquitto.conf
    │   ├── passwd
    │   ├── data/
    │   └── backup_meta.txt
    ├── homeassistant/                 # HA Backup-Archive
    │   └── <instance>/
    │       ├── ha_backup_latest.tar
    │       └── ha_backup_previous.tar
    └── ansible-config/                # Ansible all.yml Backup
        └── all.yml

/usr/local/bin/                        # Von Ansible deployte Scripts
├── homelab_auto_deployment.sh         # Git-Poll + Auto-Deploy
├── check_nfs_mount.sh                 # NFS Health Check
├── mqtt_backup.sh                     # MQTT Backup (im Container)
├── mqtt_restore.sh                    # MQTT Restore (im Container)
├── ha_backup.sh                       # HA Backup (auf Host)

/etc/ha_backup_refresh_token           # HA API Refresh Token (auto-generiert)
```

## Voraussetzungen

- **Proxmox VE** mit Netzwerkzugang
- **NAS** mit NFS-Export (z.B. Synology, TrueNAS, OpenMediaVault)
- **SSH-Schlüssel** auf dem Proxmox-Host (`/root/.ssh/id_rsa`)
- Optional: **Zigbee USB-Dongle** (z.B. Sonoff Zigbee 3.0)

## Installation

### 1. Pakete installieren

```bash
git clone https://github.com/TiChan42/basic-homelab.git
cd basic-homelab
./scripts/install-necessary-apt-packages.sh
```

### 2. Proxmox API-Token erstellen

In der Proxmox-Weboberfläche unter **Datacenter → Permissions → API Tokens**:

1. User: `root@pam`
2. Token ID: `ansible`
3. **Privilege Separation** deaktivieren
4. Token-Secret kopieren

### 3. Konfiguration anpassen

```bash
cp ansible-playbooks/inventory/group_vars/all.example.yml \
   ansible-playbooks/inventory/group_vars/all.yml
```

Die `all.yml` ist die **zentrale Konfigurationsdatei**. Alle mit `CHANGE THIS` markierten Werte müssen angepasst werden:

| Abschnitt | Was anpassen? |
|---|---|
| **Proxmox API** | `proxmox_api_token_secret` (aus Schritt 2) |
| **Netzwerk** | `network_gateway`, `network_dns`, `network_cidr` |
| **NAS** | `nas_ip`, `nas_nfs_export` |
| **MQTT** | `mqtt_default_user`, `mqtt_default_password` |
| **Home Assistant** | `ha_admin_user`, `ha_admin_password` |

Host-IPs und VMIDs werden in `hosts.yml` konfiguriert.

### 4. Alles ausführen

```bash
./scripts/run-all-playbooks.sh
```

Das Script führt in Reihenfolge aus:
1. **General Playbooks** – NFS-Mount, NFS-Health-Check, Auto-Deployment
2. **Service Playbooks** – Webserver, MQTT-Broker, Home Assistant
3. **Config-Backup** – Sichert `all.yml` automatisch auf das NAS

### 5. Einzelne Services ausführen

```bash
# Nur MQTT-Broker
ansible-playbook -i ansible-playbooks/inventory/hosts.yml \
  ansible-playbooks/services/mqtt-broker/main.yml

# Nur Home Assistant
ansible-playbook -i ansible-playbooks/inventory/hosts.yml \
  ansible-playbooks/services/homeassistant/main.yml

# Nur Webserver
ansible-playbook -i ansible-playbooks/inventory/hosts.yml \
  ansible-playbooks/services/webserver/main.yml
```

Tags erlauben es, nur bestimmte Phasen auszuführen:

```bash
# Nur Container/VM erstellen, nicht deployen
ansible-playbook ... mqtt-broker/main.yml --tags provision

# Nur Software deployen (Container muss existieren)
ansible-playbook ... mqtt-broker/main.yml --tags deploy
```

## Backup & Disaster Recovery

### Automatische Backups

| Service | Methode | Intervall | Ziel |
|---|---|---|---|
| **MQTT Broker** | Stop → rsync → Start (Cron) | Alle 4 Stunden | `/mnt/nas/backups/mqtt-broker/` |
| **Home Assistant** | HA API Full Backup (Cron) | Täglich 02:30 | `/mnt/nas/backups/homeassistant/` |
| **Ansible Config** | Kopie nach Playbook-Run | Bei jedem Run | `/mnt/nas/backups/ansible-config/` |

### MQTT Backup-Validierung

- Automatischer Restore-on-Boot via systemd wenn lokale Daten fehlen
- Backup umfasst: Config, Persistence-Daten, Passwort-Datei

### HA Backup-Validierung

Jedes HA-Backup wird vor dem Übernehmen validiert:

1. ✅ HTTP-Statuscode = 200
2. ✅ Dateigröße > 10 KB
3. ✅ Gültiges tar-Archiv (`tar -tf`)
4. ✅ Erst dann: altes Backup rotieren → neues übernehmen

Es gibt immer zwei Backups: `ha_backup_latest.tar` + `ha_backup_previous.tar`.

### Disaster Recovery (Neuinstallation)

Nach einer frischen Proxmox-Installation:

```bash
# 1. NAS manuell mounten
mkdir -p /mnt/nas
mount -t nfs <NAS_IP>:<EXPORT> /mnt/nas

# 2. Repo klonen
git clone https://github.com/TiChan42/basic-homelab.git
cd basic-homelab

# 3. Gespeicherte Konfiguration wiederherstellen
./scripts/restore-config-from-nas.sh

# 4. Alles neu aufsetzen
./scripts/install-necessary-apt-packages.sh
./scripts/run-all-playbooks.sh
```

## Auto-Deployment

Ein Cron-Job pollt das Git-Repository (Standard: täglich um 03:00) und führt bei Änderungen automatisch alle Playbooks aus. Zusätzlich wird nach jedem Proxmox-Reboot ein Deployment getriggert.

Konfigurierbar in `all.yml`:

```yaml
polling_minute: 0
polling_hour: 3
```

## Variablen-Architektur

```
all.yml (zentrale Defaults)          hosts.yml (host-spezifisch)
├── Proxmox API Credentials          ├── Host-IPs (ansible_host)
├── Netzwerk (CIDR, Gateway, DNS)    ├── VMIDs / Container-IDs
├── NAS (IP, Export, Mount)          ├── Service-spezifische Overrides
├── Proxmox Defaults (Template,     └── Gruppen-Defaults
│   Storage)                             (Memory, Cores, etc.)
├── MQTT Settings
├── HA Settings
└── Backup/Cron Intervalle
```

**Prinzipien:**
- **Single Source of Truth** – Jede IP steht nur in `hosts.yml` als `ansible_host`
- **Cross-Referencing** – Playbooks nutzen `hostvars['mqtt-broker']['ansible_host']`
- **Zentrale Defaults** – Netzwerk, NAS, Storage-Einstellungen in `all.yml`
- **Kein manueller Token** – HA Refresh-Token wird automatisch beim Setup erzeugt

## Lizenz

MIT