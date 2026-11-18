# Datensicherung und Wiederherstellung

**Wichtig:** SQLite-Sicherungen sind das Wiederherstellungsformat **dieser Webanwendung**, nicht Financisto-.backup-Dateien. Der manuelle Financisto-Import bleibt unverändert. Für den aktuellen Web-Datenbestand gibt es zusätzlich den gesonderten Financisto-Rückexport; dieser ersetzt keine SQLite-Sicherung.

## Tagesbackup

Der Dienst `backup` prüft beim Start und anschließend stündlich, ob für den aktuellen Kalendertag in Europe/Berlin eine automatische Sicherung existiert. Er erstellt eine konsistente SQLite-Sicherung über die offizielle Online-Backup-API. Die letzten 14 **automatischen** Stände werden aufbewahrt. Andere Sicherungen werden nicht automatisch gelöscht.

**Achtung:** Die automatische Sicherung befindet sich auf dem *gleichen* Docker-Host. Bei Verlust des Hosts wäre sie ebenfalls verloren. Zusätzlich regelmäßig verschlüsselt auf ein anderes System kopieren.

## Wiederherstellung (lokal)

1. Benutzer abmelden; die Webseite ist währenddessen kurz nicht verfügbar.
2. Sicherstellen, dass die zur Sicherung passenden Projekt-Secrets (vor allem `secrets/app_secret`) vorhanden sind. Niemals das Secret beim Restore neu erzeugen.
3. Auf dem Docker-Host als Eigentümer des Projekts (nicht root) ausführen:

```bash
cd /home/pi/docker-files/financisto-dashboard
./restore.sh data/web-backups/automatisch-YYYYMMDD-HHMMSS-xxxxxx.sqlite3
```

Das Skript prüft die SQLite-Datei, verlangt das Wort `WIEDERHERSTELLEN`, stoppt die beiden Datenbank-Schreiber sowie den Sicherungsdienst, erstellt `backups/vor-restore-...sqlite3`, stellt die Datenbank wieder her und startet die Dienste. Benutzer, Buchungen, 2FA-Daten und Einstellungen werden auf den Stand der Sicherung zurückgesetzt. Kein `.backup`-Import ist damit verbunden. Vor dem ersten realen Restore in einer Testinstallation ausprobieren.

**Sicherheitskopien der Secrets** getrennt sichern; die von der App gespeicherten TOTP-Seeds sind ohne den ursprünglichen `app_secret` nicht entschlüsselbar.

## Aktuelle Financisto-Rückexporte zum Herunterladen (ab 1.9.58-dev.3)

Bei aktiver automatischer Datensicherung wird täglich neben dem SQLite-Backup ein eigener `.backup`-Rückexport aus den **aktuellen Web-Buchungen** und freigegebenen wiederkehrenden Regeln erzeugt. Der bestehende Rückexport erfordert eine passende Originalvorlage und lehnt unbekannte oder nicht unterstützte Wiederholungsregeln ab; bei einem Fehler wird kein alter Android-Importstand als neue Sicherung ausgegeben. Die tägliche SQLite-Sicherung bleibt unabhängig funktionsfähig.

Unter `data/financisto-backups/` bleiben maximal die **zwei letzten erfolgreich erzeugten** Versionen erhalten; der Administrator kann sie unter Einstellungen herunterladen. Mit einer separaten Testinstallation den Rückimport prüfen, bevor auf einem Android-Gerät produktive Daten ersetzt werden. Diese Sicherungen ersetzen das SQLite-Backup nicht; für die Wiederherstellung des Websystems außerdem `secrets/app_secret` sicher getrennt verwahren.
