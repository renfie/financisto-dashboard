# Financisto-Dashboard (FieLanzen)

Self-hosted Finanzdashboard mit Docker und browserbasierter Verwaltung, Berichten, wiederkehrenden Buchungen sowie Import/Export von Financisto-Backups.

**Aktueller Stand im Repository:** v1.9.36 (14. November 2026). Das Repository ist derzeit privat.

## Inhalt

- `package/` – vollständiger Anwendungsquellcode inklusive Docker Compose, `install.sh`, Weboberfläche und Dokumentation
- `update.sh` – Update-Skript für bestehende Installationen; vorhandene Daten bleiben erhalten
- `setup_financisto_sftp.sh` – optionale Einrichtung des separaten SFTP-Importkontos
- `README.txt` – Release-Hinweise zu v1.9.36
- `package/CHANGELOG.md` – Versionshistorie
- `package/docs/` – Dokumentation einzelner Funktionen

## Neuinstallation

Das Repository herunterladen oder klonen, in das Verzeichnis `package/` wechseln und `./install.sh` als normalen Projektbenutzer **ohne sudo** ausführen. Das Skript führt die Ersteinrichtung durch. Details in [package/README.md](package/README.md).

## Update einer vorhandenen Installation

Das Repository in ein **separates** Verzeichnis herunterladen oder klonen – nicht direkt über die produktive Installation kopieren. Im Wurzelverzeichnis des ausgecheckten Projekts:

```bash
./update.sh /pfad/zur/bestehenden/financisto-dashboard-installation
```

Das Update-Skript legt eine Sicherung an, kontrolliert Daten und Rechte und aktualisiert die Programmdateien. Es muss als der Benutzer laufen, dem die bestehende Installation gehört, **nicht mit sudo**. Einzelheiten stehen in [package/README.md](package/README.md) und [package/docs/BACKUP_RESTORE.md](package/docs/BACKUP_RESTORE.md).

## Sicherheit und Datenschutz

Dieses Git-Repository enthält **keine produktiven** Kontodaten, SQLite-Datenbanken, Passwörter, Authentifizierungsschlüssel oder befüllten `.env`-Dateien. Solche Daten werden bei Git-Commits ausgeschlossen und gehören in die lokale Konfiguration bzw. die persistenten Bind-Mounts.

Die Anwendung unterstützt sowohl den manuellen als auch den konfigurierbaren automatischen Financisto-Backup-Import. Bei produktiven Finanzdaten stets Backups anlegen und die Import-/Führungsmodi beachten.

## Downloads

Auf der Repository-Seite unter **Code → Download ZIP** lässt sich der aktuelle Quellstand herunterladen. Ein separat verpacktes GitHub-Release mit Versions-Tag wurde noch nicht angelegt.
