# Financisto-Dashboard (FieLanzen)

**Deutschsprachiges, selbst gehostetes Finanzdashboard für Docker** – mit Finanzberichten, Buchungsverwaltung, wiederkehrenden Buchungen, PWA und sicherem Import von [Financisto](https://github.com/dsolonenko/financisto)-Backups.

**Aktueller Quellstand:** v1.9.36 · 14. November 2026.

## Funktionen

- Konten, Buchungen, Umbuchungen, Empfänger und Kategorien verwalten; Rollen und Zwei-Faktor-Authentifizierung
- Monatsberichte, Haushaltsauswertung, Kontostände, historische Vergleiche und Druckansichten
- **Manueller Financisto-`.backup`-Import bleibt erhalten**; optional automatischer Import per SFTP/FolderSync, in der Weboberfläche steuerbar
- Finanzverwaltung mit wahlweise **Financisto oder der Weboberfläche als führendem System**; Schutz vor unbeabsichtigtem Überschreiben eigener Buchungen
- Wiederkehrende Buchungen und Umbuchungen, Benachrichtigungen über Web Push, Gotify oder Telegram
- Responsive Oberfläche für PC, Tablet und Smartphone mit installierbarer PWA
- Docker Compose, lokale HTTPS-Konfiguration und Backup-/Update-Skripte; persistente Daten in Bind-Mounts

## Ursprung und Abgrenzung

Dieses Dashboard ist eine **eigenständige Webanwendung** und **keine offizielle Version, Weiterentwicklung oder ein Fork** der Android-App Financisto. Es ist durch deren Nutzungs- und Datenmodell inspiriert und unterstützt das Importformat ihrer Sicherungsdateien sowie das Format des verbreiteten Android-Forks.

- **Originalprojekt:** [Financisto – dsolonenko/financisto](https://github.com/dsolonenko/financisto), entwickelt von Denis Solonenko und Mitwirkenden.
- **Unterstützter Android-Fork:** [Financisto Holo – tiberiusteng/financisto1-holo](https://github.com/tiberiusteng/financisto1-holo).

Die Rechte an Financisto und dessen Kennzeichen verbleiben bei den jeweiligen Rechteinhabern. Für Android-App, deren Funktionsweise oder ihre Weiterentwicklung ist dieses Repository nicht zuständig.

## Repository-Struktur

| Pfad | Inhalt |
| --- | --- |
| `package/` | Anwendungsquellcode, Docker-Dateien, `install.sh`, Oberfläche und Dokumentation |
| `update.sh` | Update vorhandener Installationen einschließlich Sicherung |
| `setup_financisto_sftp.sh` | Optionale Einrichtung für den SFTP-Import |
| `README.txt` | Hinweise zum übernommenen Release v1.9.36 |
| `package/CHANGELOG.md` | Versionshistorie |
| `package/docs/` | Ausführliche Funktions- und Betriebsdokumentation |

## Neuinstallation

Repository klonen oder als ZIP herunterladen. Im ausgepackten Verzeichnis:

```bash
cd package
./install.sh
```

Das Skript ist als regulärer Linux-Projektbenutzer **ohne sudo** auszuführen. Weitere Hinweise stehen in [package/README.md](package/README.md).

## Bestehende Installation aktualisieren

Quellcode **getrennt von der produktiven Installation** auschecken und im Repository-Hauptverzeichnis als Eigentümer der vorhandenen Installation ausführen:

```bash
./update.sh /pfad/zur/bestehenden/financisto-dashboard-installation
```

**Nicht** die vorhandenen Daten- und Konfigurationsverzeichnisse überschreiben. Das Update-Skript ist für die Datensicherung und die Übernahme der Programmdateien zuständig. Hinweise: [Backup & Restore](package/docs/BACKUP_RESTORE.md).

## Datenschutz und Sicherheit

Produktive SQLite-Datenbanken, Finanztransaktionen, Backups, Passwörter, private Schlüssel, Tokens, befüllte `.env`-Dateien und andere Laufzeitdaten gehören **nicht** in Git. Die Regeln in [`.gitignore`](.gitignore) schließen diese typischen Dateien aus. Vor jeder Veröffentlichung von Quellcode oder Releases muss der Inhalt dennoch kontrolliert werden.

## Lizenz

Dieses Dashboard wird unter der **GNU General Public License, Version 2 (GPL-2.0-only)** angeboten. Die Lizenzbedingungen stehen in [LICENSE](LICENSE); Hinweise zu Projektzuordnung und Drittrechten in [NOTICE.md](NOTICE.md).

Bei Verteilung der Software dürfen Empfänger ihre Kopie gemäß GPL v2 verwenden, verändern und weitergeben. Daraus entsteht **kein Schreibzugriff** auf dieses GitHub-Repository; den verwaltet ausschließlich dessen Eigentümer.

Das ursprüngliche Android-Projekt Financisto steht ebenfalls unter GPL v2. Die Lizenzierung dieses Dashboards begründet weder eine offizielle Zugehörigkeit noch eine Freigabe fremder Marken oder Grafiken.

## Downloads und Releases

Über **Code → Download ZIP** lässt sich der aktuelle Quellstand herunterladen. Zusätzlich können versionierte ZIP-Pakete als **GitHub Releases** veröffentlicht werden.

**Achtung:** Solange dieses Repository privat ist, sind auch die dortigen Releases nicht öffentlich abrufbar. Öffentliche Downloads erfordern ein öffentliches Repository oder eine separate öffentliche Veröffentlichungsquelle.
