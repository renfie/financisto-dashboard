# Caddy, HTTPS und Reverse-Proxy-Anbindung

**Sprache / Language:** [English](CADDY.en.md) | **Deutsch**

Das Financisto-Dashboard bringt **Caddy als eigenen Docker-Compose-Dienst** mit. Caddy stellt HTTPS für den lokalen Zugriff bereit, leitet autorisierte Anfragen an die Python-Webanwendung weiter und bewahrt die lokal ausgestellten Zertifikate über Updates hinweg auf. Caddy muss nicht zusätzlich installiert werden.

## Netzwerkaufbau

```text
Browser im LAN ── HTTPS (Host-Port standardmäßig 8443) ── Caddy ── dashboard:8000
                                                               (privates Docker-Netz)

Optionaler Internetzugriff:
Internet-Browser ── HTTPS + öffentliches Zertifikat ── Nginx Proxy Manager
                                      └── internes HTTPS ── Caddy ── dashboard:8000
```

Das Dashboard selbst benötigt keinen öffentlich freigegebenen HTTP-Port. Über `HTTPS_BIND_IP` und `HTTPS_PORT` wird festgelegt, an welcher Hostadresse der Caddy-Dienst HTTPS veröffentlicht. Standardmäßig wäre dies `0.0.0.0:8443`; für produktive Installationen ist eine Beschränkung auf die erforderliche LAN-/Loopback-Adresse empfehlenswert.

## Zertifikate und die interne Caddy-CA

Die enthaltene [Caddyfile](../Caddyfile) nutzt `tls internal`. Caddy stellt seine TLS-Zertifikate damit über eine **eigene lokale Zertifizierungsstelle** aus. Sie sind nicht automatisch bei öffentlichen Browsern als vertrauenswürdig hinterlegt.

Beim direkten HTTPS-Zugriff aus dem LAN muss das lokale Caddy-Stammzertifikat auf den vertrauenswürdigen Geräten korrekt importiert werden. Die zugehörigen Zertifikate und Schlüssel werden im eingebundenen Verzeichnis `caddy/data/` aufbewahrt und dürfen beim Update **nicht gelöscht oder ersetzt** werden. Das Stammzertifikat sollte nur aus einer verifizierten eigenen Installation übernommen werden.

Für öffentliche Erreichbarkeit über **Nginx Proxy Manager (NPM)** sollte NPM nach außen ein öffentlich vertrauenswürdiges TLS-Zertifikat, beispielsweise von Let's Encrypt, bereitstellen. Die Verbindung NPM → Caddy ist ein davon getrennter HTTPS-Abschnitt, für den die private Caddy-CA und passende Host-/SNI-Einstellungen berücksichtigt werden müssen.

## Wichtige Einstellungen in .env

Bei der Neuinstallation werden diese Werte mit dem Installer konfiguriert. Das folgende Beispiel verwendet **ausdrücklich keine realen Serveradressen**:

```dotenv
SITE_HOST=finance.example.org
SITE_ADDRESSES=https://finance.example.org
HTTPS_BIND_IP=192.0.2.10
HTTPS_PORT=8443
TRUSTED_PROXY_IPS=127.0.0.1/32
```

- `SITE_HOST`: primärer HTTPS-Hostname und Standard-SNI in Caddy.
- `SITE_ADDRESSES`: komma-getrennte HTTPS-Adressen und zusätzliche gültige Hostnamen.
- `HTTPS_BIND_IP` und `HTTPS_PORT`: lokale Bind-Adresse und veröffentlichter HTTPS-Port.
- `TRUSTED_PROXY_IPS`: IP-Adresse bzw. eng begrenztes Netz des tatsächlich vorgeschalteten Reverse-Proxys; keinesfalls pauschal `0.0.0.0/0` vertrauen. Die Einstellung beeinflusst die korrekte Erkennung von Client-IP-Adressen.

Eine konfigurierte `.env` mit echten Hosts oder Zugangsdaten gehört **nicht** ins öffentliche GitHub-Repository.

## PC-IP-Freigaben und optionaler Internetzugriff

Die Anwendung unterstützt IP-Freigaben sowie einen separat aktivierbaren öffentlichen Zugriffsmodus. Der Internetzugriff sollte erst nach Einrichtung von HTTPS, 2FA, Benutzerkonten, vertrauenswürdigen Proxy-IP-Adressen und passenden Firewallregeln aktiviert werden.

Bei aktuellen Versionen wird der öffentliche Zugriff in der Weboberfläche durch den Administrator gesteuert. Der ältere `.env`-Wert `PUBLIC_ACCESS` dient nur der Initialisierung beziehungsweise der Abwärtskompatibilität; die aktuelle Bedienung ist in [SECURITY_UPGRADE.md](SECURITY_UPGRADE.md) beschrieben.

**Das öffentliche GitHub-Repository macht nicht automatisch den eigenen Server öffentlich.** Den internen Caddy-Port nicht ungeschützt ins Internet weiterleiten.

## Verhalten beim Update

Das [Update-Skript](../../update.sh) verteilt bei Bedarf eine neue `Caddyfile` und `compose.yaml`, bewahrt aber die bestehende `.env` mit individuellen Hostnamen auf. Auch folgende Ordner bleiben erhalten:

- `caddy/data/`: interne Caddy-CA mit Zertifikaten und Schlüsseln
- `caddy/config/`: persistente Konfiguration und Caddy-Zustand
- `secrets/`, `data/` und vorhandene Backups

Bei einer alten, direkt in der Caddyfile hinterlegten Domainkonfiguration kann das Update die zusätzlichen Hostnamen in `SITE_ADDRESSES` übertragen, wenn diese Variable noch fehlt. Nach dem Start wird kontrolliert, ob der Caddy-Container läuft; ein zusätzlicher HTTPS-Test im Browser beziehungsweise über NPM bleibt sinnvoll.

**Kein `docker compose down -v` bei Updates ausführen.**

## Diagnose und Konfigurationsänderungen

Als normaler Projektbenutzer im Installationsverzeichnis:

```bash
docker compose ps
docker compose logs --tail=80 caddy
docker compose config --quiet
```

Nach einer Änderung der Caddy-relevanten `.env`-Werte:

```bash
docker compose up -d --no-deps --force-recreate caddy
```

Weiterführende Informationen stehen in der [deutschen Installationsanleitung](../README.md) und in [SECURITY_UPGRADE.md](SECURITY_UPGRADE.md).
