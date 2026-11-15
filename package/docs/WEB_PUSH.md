# Web Push: persönliche Regeln ab 1.9.34

- Pro Benutzer unter Einstellungen → App-Benachrichtigungen: Ausgaben an/aus, eigener EUR-Grenzbetrag, Einnahmen an/aus, Detailstufe.
- Die neuen Regeln sind unabhängig vom globalen Gotify-/Telegram-Grenzwert.
- Jeder Benutzer muss einmalig auf jedem gewünschten Browsergerät Push aktivieren.
- Private Detailstufe bleibt für alle bestehenden Geräte Standard; bestehende Abonnements bleiben erhalten.
- Ausführliche Benachrichtigungen können auf Android/Windows-Sperrbildschirmen sichtbar werden. Bitte bewusst wählen.
- Nur neu erstellte EUR-Buchungen, keine Imports, Umbuchungen, Kontostandskorrekturen oder Bearbeitungen.
- Kein zusätzlicher Container. Der vorhandene Notifications-Worker versendet die Meldungen.

# FieLanzen 1.9.31 – Web Push in Chrome/Android PWA

- Einmalig aktualisieren, auf dem Telefon in Chrome/PWA anmelden und Einstellungen → App-Benachrichtigungen öffnen.
- „Auf diesem Gerät aktivieren“ antippen; Android/Chrome um Erlaubnis bitten lassen.
- „Test-Push senden“ prüft die Zustellung auch bei geschlossener App. Manche Android-Akkuoptimierungen können Push verzögern.
- Für Ela dasselbe mit ihrem eigenen FieLanzen-Benutzerkonto auf ihrem Telefon wiederholen. Aktivierungen sind pro Benutzer und Browsergerät getrennt.
- Die Warnungen werden bei neuen echten Ausgaben nach dem bereits konfigurierten Grenzwert (z. B. 100 EUR) erzeugt; die Hauptfunktion „Warnungen bei größeren Ausgaben aktivieren“ bleibt erforderlich. Gotify und Telegram sind dafür nicht nötig.
- Der bestehende Notifications-Container verschickt die Push-Benachrichtigungen zusätzlich. Es ist **kein fünfter Container** nötig.
- Push-Texte sind bewusst neutral („Neue Ausgabe erfasst.“), damit auf Sperrbildschirmen keine Beträge oder Finanzdaten erscheinen.
- Web Push nutzt die Push-Infrastruktur des jeweiligen Browsers (z. B. Google FCM bei Android Chrome). Die verschlüsselten VAPID-Schlüssel werden bei der ersten Initialisierung erstellt und in der bestehenden SQLite-Datenbank aufbewahrt; der private Schlüssel ist mit dem vorhandenen app_secret verschlüsselt.
- Der Service Worker cached keine Bankdaten, Logins oder HTML-Seiten. Die Benachrichtigung öffnet die Dashboard-Startseite, die weiterhin Passwort und 2FA verlangt.
- Zum Entfernen des Abos bitte am jeweiligen Gerät „Deaktivieren“ drücken. Ein Ablauf der Web-Anmeldung beendet Push nicht automatisch.
- Wenn NPM Client-Zertifikate verlangt, muss die Browser-PWA wie bisher ihr Zertifikat vorlegen. Push selbst geht über den Browser-Push-Dienst; bei geschlossener App muss der Service Worker keine geschützte HTML-Seite abrufen.
- Nach Aktualisierung des PWA-Symbols können Android und Chrome einige Zeit das alte Symbol anzeigen. Falls nötig: PWA deinstallieren und aus Chrome wieder neu installieren; die Daten bleiben auf dem Server.

### Diagnose

`docker logs --tail 100 financisto-dashboard-notifications`

Die Web-Push-Ausgangswarteschlange liegt in `webpush_outbox`, die Geräteliste in `webpush_subscriptions`. Keine Push-URLs oder privaten Schlüssel in Logs veröffentlichen.
