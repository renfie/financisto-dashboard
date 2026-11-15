# FieLanzen · Ausgabenwarnungen (1.9.28)

## Einrichtung

1. Als Administrator anmelden. **Einstellungen → Benachrichtigungen bei größeren Ausgaben** öffnen.
2. Schwelle in EUR festlegen, z. B. `100,00` für Ausgaben ab 100,00 EUR einschließlich.
3. Für Gotify: `https://…` als Basisadresse und ein Gotify-**App-Token** (nicht das Client-Token) eingeben. Gewünschte Priorität 0–10 wählen.
4. Für Telegram: am besten **denselben eigenständigen FieLanzen-Bot** wie unter „Buchungen per Telegram“ verwenden. Sein Bot-Token und die Gruppen-Chat-ID separat bei den Benachrichtigungen eintragen. Der Empfang per `getUpdates` läuft nur im bestehenden Benachrichtigungscontainer; Node-RED wird für FieLanzen nicht benötigt.
5. Den gewünschten Kanal **separat speichern** (Telegram benötigt kein Gotify). Anschließend Grenzbetrag und „Warnungen bei größeren Ausgaben aktivieren“ im eigenen Formular speichern.
6. **Testbenachrichtigung senden** drücken. Der separate Container `financisto-dashboard-notifications` sendet die Testmeldung im Hintergrund. Der Versandstatus steht im selben Bereich; bei Fehlern `docker compose logs --tail 40 notifications` im Projektverzeichnis prüfen.

## Wichtige Abgrenzungen

- **Nur Web-Modus:** Neue manuelle Web-Ausgaben, per Telegram gespeicherte Ausgaben und neu ausgeführte wiederkehrende Ausgaben erzeugen bei Erreichen des Grenzbetrags eine Meldung. Kontoabgleiche, durchlaufende Posten, Importe, Umbuchungen und reine Änderungen bleiben ausgeschlossen.
- **Währung:** Die Schwelle ist in EUR. Ausgaben anderer Währungen werden ohne Wechselkurs nicht automatisch verglichen.
- **Telegram:** Für **Benachrichtigungen** wird nur `sendMessage` verwendet. Die **direkten Telegram-Buchungen** in 1.9.26 können über einen eigenen Bot unabhängig davon im selben Benachrichtigungscontainer mit `getUpdates` empfangen werden. Node-RED wird dafür nicht benötigt. Siehe `TELEGRAM_BOOKINGS.md`.
- **Gruppen-Privatsphäre:** Alle Mitglieder des Zielchats können Benachrichtigungen mit Betrag, Konto, Empfänger, Kategorie und optionaler Notiz lesen. Für sensible Meldungen ist ein Privat-Chat mit dem Bot empfehlenswert.
- **Speicherung:** Tokens liegen verschlüsselt in der SQLite-Datenbank (getrennt vom TOTP-Schlüssel, aber vom vorhandenen `secrets/app_secret` abgeleitet). Die Eingabemaske gibt gespeicherte Tokens niemals zurück.
- **Netzwerk:** Dashboard bleibt auf dem privaten internen Netz. Der neue, separate Versandcontainer hat nur ausgehende Netzwerkverbindungen und keine publizierten Ports. Automatischer Import und wiederkehrende Buchungen behalten ihren bisherigen netzlosen Hintergrunddienst.
- **Zuverlässigkeit:** Nachrichten werden in der SQLite-Ausgangswarteschlange gespeichert und mit begrenzten Wiederholungen versendet. Bei einem Absturz nach erfolgreicher Zustellung, aber vor Bestätigung in SQLite, kann ausnahmsweise eine Meldung doppelt erscheinen. Buchungsdaten bleiben unverändert.

## Installation

```bash
cd /home/pi/docker-files
unzip -o financisto-dashboard-v1.9.28.zip
./financisto-release-1.9.28/update.sh
```

Das Update legt ein SQLite-Backup unter `backups/upgrade-*` an, bevor es Code und Container aktualisiert. Es ändert keine vorhandenen Zugangsdaten, Benutzer, 2FA-Einstellungen, Finanzbuchungen oder Importdateien.

### Korrektur in 1.9.25
Der Grenzbetrag/Hauptschalter, Gotify und Telegram haben jetzt jeweils eigene Speicherformulare. Telegram kann ohne Gotify aktiviert werden. Leere Tokenfelder ändern gespeicherte Tokens nicht; Entfernen nur über die ausdrücklich dafür vorgesehene Checkbox.

### Übersichtliche Einstellungsseite ab 1.9.25

Die Bereiche „Benachrichtigungen bei größeren Ausgaben“ und „Buchungen per Telegram“ sind beim normalen Öffnen der Einstellungen zunächst zugeklappt. Ein Klick auf die jeweilige Überschrift öffnet die Formulare. Nach dem Speichern wird der betroffene Bereich automatisch wieder geöffnet; der Ein-/Aus-Status bleibt auch im zugeklappten Zustand sichtbar.

## Diagnose ab 1.9.28

Bei einer **neuen Ausgabe** zeigt die Weboberfläche nach dem Speichern,
ob eine Nachricht in die Warteschlange gestellt wurde oder warum nicht
(z. B. unter 100 EUR, Fremdwährung, neutraler Posten, Hauptschalter aus).
Die Testnachricht prüft dagegen ausschließlich die konfigurierten Versandkanäle.
Neue wiederkehrende Ausgaben werden ebenfalls in der Warteschlange erfasst.
Bereits vorhandene Buchungen werden durch das Update niemals nachträglich
versendet. Der Versand bleibt asynchron, der Status erscheint in den Einstellungen.
