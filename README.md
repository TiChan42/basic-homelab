# Basic Homelab

Ansible-basierte Automatisierung für ein Homelab auf Proxmox VE. Dieses Repository provisioniert und konfiguriert alle Services vollautomatisch – von der Container-/VM-Erstellung über die Service-Konfiguration bis hin zu automatisierten Backups auf ein NAS.

## Architektur

```
                        ┌──────────────────────────┐
                        │        Client (Mac)       │
                        │  DNS: /etc/resolver/      │
                        │       home.lab → dnsmasq  │
                        │  CA: Homelab Root CA in   │
                        │      System Keychain      │
                        └────────────┬─────────────┘
                                     │  https://*.home.lab
                                     ▼
┌─────────────────────────────────────────────────────────────┐
│                      Proxmox VE Host                        │
│                      192.168.1.91                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  dnsmasq DNS Server                                  │   │
│  │  *.home.lab → 192.168.1.100 (Traefik)               │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  LXC 100: Traefik Reverse Proxy  (192.168.1.100)    │   │
│  │  ├── HTTPS :443 (TLS via self-signed Root CA)        │   │
│  │  ├── HTTP  :80  → redirect → HTTPS                  │   │
│  │  └── Dashboard :50100                                │   │
│  │  Wildcard cert: *.home.lab (5yr, signed by own CA)   │   │
│  └──────────────────────────────────────────────────────┘   │
│       │ Routes: ha. / nodered. / n8n. / desktop-bg.         │
│       ▼                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  LXC 101     │  │  LXC 103     │  │  VM 102          │  │
│  │  MQTT Broker  │  │  Node-RED    │  │  Home Assistant   │  │
│  │  (Mosquitto)  │  │  :1880       │  │  OS (HAOS)       │  │
│  │  :1883        │  ├──────────────┤  │  :8123           │  │
│  │               │  │  LXC 104     │  │  + Zigbee2MQTT   │  │
│  │               │  │  n8n :5678   │  │  + Matter Server │  │
│  └──────┬───────┘  ├──────────────┤  └────────┬─────────┘  │
│         │          │  LXC 105     │            │            │
│         │          │  Webserver   │   USB Dongle ──► Z2M   │
│         │◄─────────┤  :3000       │◄───────────┘   MQTT    │
│         │  MQTT    └──────────────┘                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  NFS Mount: /mnt/nas                                 │   │
│  │  ├── services/        (Persistente Service-Daten)    │   │
│  │  └── backups/         (Rotierte Backups)             │   │
│  │      ├── traefik/         CA-Zertifikate             │   │
│  │      ├── mqtt-broker/     Mosquitto-Daten            │   │
│  │      ├── homeassistant/   HA Full-Backups            │   │
│  │      ├── nodered/         Flows + Credentials        │   │
│  │      ├── n8n/             SQLite DB + Workflows      │   │
│  │      └── ansible-config/  all.yml                    │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                           │
                    NFS    │
                           ▼
                    ┌──────────────┐
                    │     NAS      │
                    │ 192.168.1.3  │
                    └──────────────┘
```

## Enthaltene Services

| Service | Typ | ID | IP | Domain | Beschreibung |
|---|---|---|---|---|---|
| **Traefik** | LXC | 100 | 192.168.1.100 | `traefik.home.lab` | Reverse Proxy, TLS-Terminierung, Dashboard |
| **MQTT Broker** | LXC | 101 | 192.168.1.101 | – | Eclipse Mosquitto mit Auth, Backup/Restore |
| **Home Assistant** | VM | 102 | 192.168.1.102 | `ha.home.lab` | Smart-Home mit Zigbee2MQTT, Matter, USB-Passthrough |
| **Node-RED** | LXC | 103 | 192.168.1.103 | `nodered.home.lab` | Flow-Automatisierung, MQTT + HA Integration |
| **n8n** | LXC | 104 | 192.168.1.104 | `n8n.home.lab` | Workflow-Automatisierung, Webhooks |
| **Desktop-BG** | LXC | 105 | 192.168.1.105 | `desktop-bg.home.lab` | Node.js Webserver aus Git-Repo |

## Repository-Struktur

```
basic-homelab/
├── README.md
├── ansible-playbooks/
│   ├── ansible.cfg
│   ├── inventory/
│   │   ├── hosts.yml                   # Host-IPs, VMIDs, Domains
│   │   └── group_vars/
│   │       ├── all.yml                 # Zentrale Konfiguration (NICHT im Repo)
│   │       └── all.example.yml         # Vorlage zum Kopieren
│   ├── general/
│   │   ├── mount-persistent-storage.yml
│   │   ├── check-mount-nfs.yml
│   │   ├── setup-auto-deployment.yml
│   │   └── templates/
│   └── services/
│       ├── 100-traefik/                # Reverse Proxy + TLS
│       │   ├── main.yml
│       │   ├── tasks/
│       │   │   ├── provision_container.yml
│       │   │   ├── configure_networking.yml
│       │   │   ├── install_traefik.yml
│       │   │   ├── generate_tls_certificates.yml
│       │   │   ├── configure_traefik.yml
│       │   │   └── verify_service.yml
│       │   └── templates/
│       ├── 101-mqtt-broker/            # MQTT mit Backup/Restore
│       ├── 102-homeassistant/          # HAOS VM mit API-Backup
│       ├── 103-nodered/                # Node-RED mit Backup/Restore
│       ├── 104-n8n/                    # n8n mit Backup/Restore
│       └── 105-webserver/              # Statische Webserver
└── scripts/
    ├── install-necessary-apt-packages.sh
    ├── run-all-playbooks.sh
    └── restore-config-from-nas.sh
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
| **Admin** | `admin_user`, `admin_password` (verwendet von allen Services) |
| **Traefik TLS** | `traefik_base_domain` (Standard: `home.lab`) |

Host-IPs, VMIDs und Domains werden in `hosts.yml` konfiguriert.

### 4. Alles ausführen

```bash
./scripts/run-all-playbooks.sh
```

Das Script führt in Reihenfolge aus:
1. **General Playbooks** – NFS-Mount, NFS-Health-Check, Auto-Deployment
2. **Service Playbooks** – Traefik, MQTT, Home Assistant, Node-RED, n8n, Webserver
3. **Config-Backup** – Sichert `all.yml` automatisch auf das NAS

### 5. Einzelne Services ausführen

```bash
# Nur Traefik (Reverse Proxy + TLS)
ansible-playbook services/100-traefik/main.yml

# Nur Home Assistant
ansible-playbook services/102-homeassistant/main.yml
```

Tags erlauben es, nur bestimmte Phasen auszuführen:

```bash
# Nur Container/VM erstellen, nicht deployen
ansible-playbook ... 100-traefik/main.yml --tags provision

# Nur Software deployen (Container muss existieren)
ansible-playbook ... 100-traefik/main.yml --tags deploy
```

## HTTPS / TLS

Alle Web-Services sind über `https://<service>.home.lab` erreichbar. Traefik terminiert TLS mit einem Wildcard-Zertifikat, das von einer eigenen Root CA signiert wird.

### Funktionsweise

1. **Root CA** wird beim ersten Traefik-Deployment generiert (gültig 10 Jahre)
2. **Wildcard-Zertifikat** `*.home.lab` wird von der CA signiert (gültig 5 Jahre)
3. **Fullchain** (Wildcard + CA) wird von Traefik ausgeliefert – Browser sehen die komplette Kette
4. CA wird automatisch auf NAS gesichert (`/mnt/nas/backups/traefik/ca.crt`)
5. Bei Container-Rebuild wird die CA vom NAS wiederhergestellt → Clients müssen die CA nur **einmal** vertrauen

### Client-Einrichtung

**macOS** (einmalig):
```bash
# CA-Zertifikat herunterladen
scp root@192.168.1.91:/mnt/nas/backups/traefik/ca.crt ~/Downloads/homelab-ca.crt

# Im System Keychain als vertrauenswürdig eintragen
sudo security add-trusted-cert -d -r trustRoot -p ssl -p basic \
  -k /Library/Keychains/System.keychain ~/Downloads/homelab-ca.crt

# DNS-Resolver: nur *.home.lab an Homelab-DNS routen
sudo mkdir -p /etc/resolver
echo "nameserver 192.168.1.91" | sudo tee /etc/resolver/home.lab
```

**iOS**:
1. CA-Zertifikat per AirDrop/E-Mail auf das Gerät übertragen
2. Einstellungen → Allgemein → VPN & Geräteverwaltung → Profil installieren
3. Einstellungen → Allgemein → Info → Zertifikatsvertrauenseinstellungen → aktivieren

**Linux**:
```bash
sudo cp ca.crt /usr/local/share/ca-certificates/homelab-ca.crt
sudo update-ca-certificates
```

### DNS-Auflösung

Ein **dnsmasq**-Server auf dem Proxmox-Host löst `*.home.lab` zu `192.168.1.100` (Traefik) auf. Clients müssen lediglich den Proxmox-Host als DNS-Server für die Domain `.home.lab` verwenden. Auf macOS geschieht dies über `/etc/resolver/home.lab`, auf anderen Systemen kann der Router-DNS auf `192.168.1.91` als sekundären DNS-Server konfiguriert werden.

## Backup & Disaster Recovery

### Automatische Backups

| Service | Methode | Intervall | Ziel |
|---|---|---|---|
| **Traefik CA** | Ansible kopiert auf NAS | Bei Deploy | `/mnt/nas/backups/traefik/` |
| **MQTT Broker** | Stop → tar.gz → Start (Cron) | Alle 4 Stunden | `/mnt/nas/backups/mqtt-broker/` |
| **Home Assistant** | HA API Full Backup (Cron) | Täglich 02:30 | `/mnt/nas/backups/homeassistant/` |
| **Node-RED** | Stop → tar.gz → Start (Cron) | Alle 4 Stunden | `/mnt/nas/backups/nodered/` |
| **n8n** | SQLite Export (Cron) | Alle 6 Stunden | `/mnt/nas/backups/n8n/` |
| **Ansible Config** | Kopie nach Playbook-Run | Bei jedem Run | `/mnt/nas/backups/ansible-config/` |

### Einheitliches Backup-Konzept

Alle Services verwenden dasselbe Validierungs- und Rotationskonzept:

1. ✅ Backup wird in eine **temporäre Datei** geschrieben
2. ✅ **Größenvalidierung** – Mindestgröße muss erreicht werden
3. ✅ **Integritätsprüfung** – tar-Archiv bzw. SQLite-Integrität
4. ✅ **Überschreibschutz** – leeres Backup überschreibt kein gutes (Größenvergleich, Inhaltscheck)
5. ✅ **Nummerierte Rotation** – `*.0` = neuestes, `*.N` = ältestes

### Restore-on-Boot

MQTT, Node-RED und n8n haben **systemd Oneshot-Services**, die beim Container-Start automatisch prüfen ob lokale Daten fehlen und bei Bedarf vom NAS wiederherstellen. Home Assistant wird über ein API-basiertes Restore-Script auf dem Proxmox-Host wiederhergestellt.

Schutzmechanismen:
- Leere Datenbanken/Dateien werden erkannt und durch NAS-Backup ersetzt
- Mehrere Backup-Generationen werden durchprobiert (0 → 1 → 2 → ...)
- Gleiche Validierungslogik wie beim Backup

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

Alle Services stellen sich automatisch aus den NAS-Backups wieder her. Die Traefik-CA wird ebenfalls vom NAS restauriert – bereits vertrauende Clients brauchen keine erneute Einrichtung.

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
├── NAS (IP, Export, Mount)          ├── Traefik-Domains (service_traefik)
├── Proxmox Defaults (Template,     └── Gruppen-Defaults
│   Storage)                             (Memory, Cores, etc.)
├── TLS / CA Settings
├── MQTT Settings
├── HA Settings
├── Node-RED Settings
├── n8n Settings
└── Backup/Cron Intervalle
```

**Prinzipien:**
- **Single Source of Truth** – Jede IP steht nur in `hosts.yml` als `ansible_host`
- **Cross-Referencing** – Playbooks nutzen `hostvars['mqtt-broker']['ansible_host']`
- **Zentrale Defaults** – Netzwerk, NAS, TLS, Storage-Einstellungen in `all.yml`
- **Kein manueller Token** – HA Refresh-Token wird automatisch beim Setup erzeugt
- **Automatische DNS-Records** – dnsmasq-Einträge werden aus `hosts.yml` generiert

## Lizenz

MIT
