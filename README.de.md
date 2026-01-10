# Basic Homelab - Automatisiertes Proxmox Setup

Dieses Repository bietet eine komplette **Infrastructure-as-Code (IaC)** Lösung, um einen "Basic Homelab" Server auf Proxmox VE Basis einzurichten. Es automatisiert den gesamten Prozess, von der Erstellung eines benutzerdefinierten Installationsmediums (USB-Stick) über die Betriebssysteminstallation bis hin zur Konfiguration der Dienste (Home Assistant, MQTT, etc.) mittels Ansible.

## 🚀 Funktionsweise

Das System arbeitet in drei Hauptphasen:

1.  **Vorbereitung (Lokaler Computer):** Ein Python-Skript lädt die neueste Proxmox ISO herunter, flasht sie auf einen USB-Stick und "injiziert" deine Konfiguration (`config.yml`) sowie die Setup-Skripte direkt in das Installationsmedium.
2.  **Installation (Server-Hardware):** Du bootest den Server vom USB-Stick. Ein Auto-Installations-Skript partitioniert die Festplatte, installiert ein minimales Debian/Proxmox-System und speichert dieses Repository dauerhaft auf der Festplatte.
3.  **Konfiguration (Erster Start):** Beim ersten Neustart installiert das System automatisch Ansible und führt Playbooks aus, um deine definierten Dienste (LXC-Container, VMs) und den Speicher einzurichten.

## 📋 Voraussetzungen

*   **Lokaler Computer:** macOS oder Linux.
*   **Python 3:** Erforderlich zum Ausführen des Installer-Generators.
*   **USB-Stick:** Mindestens 4 GB. **Warnung: Alle Daten auf dem Stick werden gelöscht.**
*   **Ziel-Server:** Ein dedizierter Rechner (Mini-PC, Server), verbunden über Ethernet (empfohlen) oder WLAN.

## 🛠️ Anleitung

### 1. Konfiguration vorbereiten
Klone das Repository und bereite deine Konfiguration vor:

```bash
git clone <repository-url>
cd basic-homelab
cp config.yml.example config.yml
```

Bearbeite `config.yml` nach deinen Wünschen:
*   Setze Root-/Admin-Passwörter.
*   Wähle Zeitzone und Sprache.
*   Konfiguriere Netzwerkeinstellungen (WLAN oder Ethernet).
*   Aktiviere/Deaktiviere bestimmte Dienste (Home Assistant, MQTT, etc.).

### 2. Installations-USB erstellen
Stecke deinen USB-Stick ein und führe das Generator-Skript aus (erfordert Root-Rechte für direkten Disk-Zugriff):

```bash
sudo python3 etcher-scripts/create_proxmox_installer.py
```

Folge den Anweisungen im Terminal:
*   Das Skript lädt die Proxmox ISO herunter.
*   Wähle dein USB-Laufwerk aus.
*   Warte, bis der Flash-Vorgang und die Konfigurations-Injektion abgeschlossen sind.

### 3. Installation auf dem Server
1.  Stecke den USB-Stick in deinen Ziel-Server.
2.  Boote den Server und wähle den USB-Stick im BIOS/Boot-Menü aus.
3.  Das Installationsskript (`initial-setup/autoinstall_proxmox.sh`) beginnt die Arbeit.
4.  Nach Abschluss startet das System neu.

### 4. Nach der Installation
Nach dem Neustart kannst du den Fortschritt mittels `tail -f /var/log/syslog` oder durch Prüfen des `initial-setup.service` überwachen.

Sobald der Vorgang abgeschlossen ist, sind deine Dienste (wie Home Assistant) unter den konfigurierten IPs/Hostnames erreichbar.

## 📂 Dateistruktur auf dem Server

Nach der Installation ist die Dateistruktur auf dem **Proxmox Host** für einfache Wartung organisiert:

```text
/
├── root/
│   ├── config.yml                # Deine ursprüngliche Konfiguration
│   └── homelab-setup/            # Kopie dieses Repos für Wartung/Updates
│       ├── maintenance/
│       └── ...
│
├── home/
│   └── [admin-user]/
│       └── homelab-data -> /var/lib/homelab-data  # Symlink für einfachen Zugriff
│
├── var/
│   └── lib/
│       └── homelab-data/         # ZENTRALER SPEICHER FÜR CONTAINER-DATEN
│           ├── mqtt/
│           ├── zigbee2mqtt/
│           └── ...
│
└── backup/
    └── homelab/                  # Lokale Backups
```

**Kernkonzept:** Dienste (LXC/VMs) speichern ihre persistenten Daten nicht *in* sich selbst (in der virtuellen Disk), sondern nutzen "Bind Mounts", um Ordner von `/var/lib/homelab-data` des Hosts einzubinden. Das macht Backups des gesamten Systems extrem einfach, da nur dieser eine Ordner gesichert werden muss.

## 🔄 Wartung

Skripte für die Wartung befinden sich in `maintenance/`:
*   **Backups:** `./maintenance/backups/backup.sh` (Läuft automatisch via Cronjob).
*   **Updates:** `./maintenance/updates/update_system.sh`.

## 📄 Lizenz

[MIT](LICENSE)
