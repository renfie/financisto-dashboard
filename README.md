# Financisto-Dashboard (FieLanzen)

Self-hosted Finanzdashboard mit Docker, Weboberfläche und Unterstützung für Financisto-Backups.

## Letztes vorbereitetes Release
**v1.9.36** (14. November 2026)

Enthält unter anderem:
- Erfassung und Verwaltung von Buchungen sowie wiederkehrende Buchungen
- Finanzberichte und Kontostandsabgleich
- Manuellen und automatischen Import von Financisto-Backups
- Responsive Dashboard-Ansichten für Smartphone, Tablet und Desktop
- Benachrichtigungen über Web Push, Gotify und Telegram
- Benutzerkonten, Zwei-Faktor-Authentifizierung und Datensicherung

## Installation
Das komplette Release-Paket enthält ein `package/`-Verzeichnis mit `install.sh`, Docker-Konfiguration, Anwendungsquellcode und Dokumentation sowie ein `update.sh` im Release-Hauptverzeichnis.

Die produktive Installation darf nicht durch ein unkontrolliertes Überschreiben von `data/`, `secrets/`, `caddy/` oder `.env` ersetzt werden. Updates erfolgen als normaler Projektbenutzer, nicht mit `sudo`.

## Sicherheit
Persönliche Finanzdaten, Kennwörter, private Schlüssel, Datenbanken und konfigurierte `.env`-Dateien gehören **nicht** ins Repository. Die mitgelieferten Vorlagen und `.gitignore` helfen, diese Daten auszuschließen.

## Status
Repository für die Quellcodeübernahme aus dem geprüften Release v1.9.36 vorbereitet.
