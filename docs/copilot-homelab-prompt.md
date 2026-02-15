# Copilot-Startanweisung: Homelab Infrastructure Verification & Fix

## Kontext

Du arbeitest an einem **Proxmox-basierten Homelab** mit Ansible-Automatisierung. Das Repository liegt lokal unter VS Code und wird auf einen Proxmox-Server deployed.

### Architektur

| Komponente | Typ | IP | ID | Ports |
|---|---|---|---|---|
| **Proxmox Host** | Bare Metal | 192.168.1.91 | – | SSH root@ |
| **Traefik** | LXC Container | 192.168.1.100 | 100 | 80, 443, 50100 (Dashboard) |
| **MQTT (Mosquitto)** | LXC Container | 192.168.1.101 | 101 | 1883 (TCP), 9001 (WS) |
| **Home Assistant** | KVM VM (HAOS) | 192.168.1.102 | 102 | 8123 |
| **Node-RED** | LXC Container | 192.168.1.103 | 103 | 1880 |
| **n8n** | LXC Container | 192.168.1.104 | 104 | 5678 |
| **Desktop-BG Webserver** | LXC Container | 192.168.1.105 | 105 | 3000 |

### Traefik Domain-Routing

Nur Services mit tatsächlichen Endpoints bekommen die entsprechenden Domains:

| Service | Frontend | API | WebSocket |
|---|---|---|---|
| Traefik | `traefik.home.local` | – | – |
| MQTT | – (TCP, kein HTTP) | – | – |
| Home Assistant | `ha.home.local` | `api.ha.home.local` | `socket.ha.home.local` |
| Node-RED | `nodered.home.local` | `api.nodered.home.local` | `socket.nodered.home.local` |
| n8n | `n8n.home.local` | `api.n8n.home.local` | `socket.n8n.home.local` |
| Desktop-BG | `desktop-bg.home.local` | – (statische Site) | – (statische Site) |

---

## Deployment-Workflow

**WICHTIG: Alle Änderungen NUR im lokalen Git-Repository machen, NIEMALS direkt auf dem Server.**

### Schritt-für-Schritt

```
1. Datei(en) lokal im Repo bearbeiten
2. git add -A && git commit -m "beschreibung" && git push
3. SSH zum Server und dort Repo aktualisieren + Playbook ausführen:
   ssh root@192.168.1.91 'cd /home/homelab/basic-homelab && git fetch origin && git reset --hard origin/main && cd ansible-playbooks && ansible-playbook <playbook-pfad>'
4. Ergebnis testen
```

### Playbook-Ausführung

Alle Playbooks müssen **innerhalb von `ansible-playbooks/`** ausgeführt werden (dort liegt `ansible.cfg`):

```bash
# Einzelnes Service-Playbook
cd ansible-playbooks && ansible-playbook services/100-traefik/main.yml

# Alle Playbooks
cd ansible-playbooks && bash ../scripts/run-all-playbooks.sh
```

### Verfügbare Playbooks

| Reihenfolge | Pfad | Beschreibung |
|---|---|---|
| 1 | `general/mount-persistent-storage.yml` | NAS-Mounts |
| 2 | `services/100-traefik/main.yml` | Traefik Reverse Proxy |
| 3 | `services/101-mqtt-broker/main.yml` | Mosquitto MQTT Broker |
| 4 | `services/102-homeassistant/main.yml` | Home Assistant OS VM |
| 5 | `services/103-nodered/main.yml` | Node-RED |
| 6 | `services/104-n8n/main.yml` | n8n Workflow Automation |
| 7 | `services/105-webserver/main.yml` | Statischer Webserver |
| 8 | `general/setup-auto-deployment.yml` | Auto-Deployment Cron |
| 9 | `general/check-mount-nfs.yml` | NFS-Mount-Check Cron |

---

## Relevante Dateien

### Inventar & Konfiguration
- `ansible-playbooks/inventory/hosts.yml` – Alle Hosts mit IPs, Ports, Traefik-Domains
- `ansible-playbooks/inventory/group_vars/all.yml` – Globale Variablen (Credentials, Netzwerk, etc.)
- `ansible-playbooks/inventory/group_vars/all.example.yml` – Dokumentation der Variablen

### Traefik
- `ansible-playbooks/services/100-traefik/templates/services.yml.j2` – Dynamische Routing-Config (generiert aus Inventar)
- `ansible-playbooks/services/100-traefik/templates/traefik.yml.j2` – Statische Traefik-Config
- `ansible-playbooks/services/100-traefik/tasks/provision_container.yml` – LXC-Erstellung + DNS + Port-Forwarding
- `ansible-playbooks/services/100-traefik/tasks/configure_traefik.yml` – Config-Deployment

### Home Assistant Besonderheiten
- HAOS ist eine VM (kein LXC), kein SSH-Zugang
- Zugriff auf HAOS-Dateisystem: `qm guest exec 102 -- <command>`
- configuration.yaml liegt unter: `/mnt/data/supervisor/homeassistant/configuration.yaml`
- API-Kommunikation über WebSocket-Helper: `files/ha_supervisor_api.py`
- HA CLI: `qm guest exec 102 -- /bin/sh -c "ha core restart"`
- Reverse-Proxy-Konfiguration: `tasks/configure_reverse_proxy.yml` (trusted_proxies für Traefik)

---

## Vorgehensweise für Prüfung & Fixes

### 1. Analyse
- Alle relevanten Dateien lesen (Templates, Tasks, Inventar)
- Deployed-Zustand auf dem Server prüfen (z.B. `pct exec 100 -- cat /etc/traefik/dynamic/services.yml`)
- Live-Tests mit curl vom Proxmox-Host aus

### 2. Connectivity-Test-Template

```bash
ssh root@192.168.1.91 '
# Frontend-Domains
for d in traefik.home.local ha.home.local nodered.home.local n8n.home.local desktop-bg.home.local; do
  code=$(curl -sk -o /dev/null -w "%{http_code}" --max-time 5 https://$d)
  echo "  $d → $code"
done
# API-Domains
for d in api.ha.home.local api.nodered.home.local api.n8n.home.local; do
  code=$(curl -sk -o /dev/null -w "%{http_code}" --max-time 5 https://$d)
  echo "  $d → $code"
done
# WebSocket-Domains
for d in socket.ha.home.local socket.nodered.home.local socket.n8n.home.local; do
  code=$(curl -sk -o /dev/null -w "%{http_code}" --max-time 5 https://$d)
  echo "  $d → $code"
done
# HTTP→HTTPS Redirect
for d in ha.home.local api.ha.home.local; do
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://$d)
  echo "  http://$d → $code (301=OK)"
done
'
```

### 3. Fix-Workflow
1. Problem identifizieren (Logs, curl-Tests, Config-Vergleich)
2. **Nur im lokalen Repo** bearbeiten
3. Commit + Push
4. Server: `git fetch && git reset --hard origin/main`
5. Playbook ausführen
6. Ergebnis testen
7. Bei Fehler → iterieren (zurück zu Schritt 1)

### 4. Bekannte Fallstricke

- **Jinja2 Backticks**: `regex_replace` mit Backticks in Jinja2 funktioniert nicht → direkte String-Konkatenation verwenden (`"Host(\`" ~ domain ~ "\`)"`)
- **Ansible Template Pre-Evaluation**: Jinja2-Expressions in `loop`-Items werden für ALLE Items evaluiert, auch wenn `when` sie überspringt → sichere Defaults mit `| default({})` verwenden
- **jmespath nicht installiert**: `json_query` Filter geht nicht → stattdessen reines Jinja2 mit `| from_json`
- **HA 400 Bad Request über Reverse Proxy**: `trusted_proxies` in HA's `configuration.yaml` fehlt
- **sniStrict: true ohne Zertifikate**: TLS-Handshake schlägt fehl → nur mit gültigen Zertifikaten verwenden
- **DNS /etc/hosts Duplikate**: `lineinfile` regexp muss `\s*$` am Ende haben, um Trailing-Whitespace zu matchen

---

## Erwartete HTTP-Statuscodes

| Endpoint | Erwarteter Code | Bedeutung |
|---|---|---|
| Frontend-Domain | 200 | Service erreichbar |
| Traefik Dashboard | 301 | Redirect zum Dashboard-Port |
| API-Domain | 200 oder 401 | 401 = Auth erforderlich (API existiert) |
| WebSocket-Domain | 200 oder 400 | 400 = Braucht WS-Upgrade-Header |
| HTTP (Port 80) | 301 | Redirect zu HTTPS |
| Nicht-konfigurierte Domain | 000 oder 404 | Korrekt nicht geroutet |
