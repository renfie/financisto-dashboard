FieLanzen 1.9.58-dev.18 – API-Schlüssel ohne Passwort/2FA-Zweitabfrage, mit Sperren und endgültigem Löschen; alle Financisto-Rückexporte prüfen jetzt Wiederholungsregeln. Unsichere Regelumwandlungen werden mit Fehler abgebrochen statt unvollständig exportiert. Dauerhafte, jederzeit widerrufbare Mobile-API-Schlüssel und vollständige Web-API; kein automatischer Ablauf. Der doppelte Backup-Import bei Wiederholungen ist entfernt. Korrektur für das Bearbeiten von Einnahmen über 999 € und Markieren des Empfängers bei Wiederholungsregeln. Notizspalte und sortierbare Tabellenüberschriften unter „Buchung erfassen“. Gleiche farbige Buchungstyp-Kennzeichen und Zeilenfarben in „Buchung erfassen“ und Dashboard. Ist-Kontostände und Monatssalden ohne künftige Buchungen; Prognosewerte inklusive künftiger Buchungen separat in Klammern. Wiederkehrend und Regel zugeordnet bleiben getrennt ausgewiesen. Empfängertext wird beim Antippen zum Überschreiben markiert. Durchgehende farbliche Markierung von Umbuchungen und wiederkehrenden Buchungen; 'Jetzt Sicherung erstellen' erzeugt SQLite und aktuellen Financisto-Rückexport separat; update.sh ist ausführbar.
Entwicklungsstand, kein offizielles GitHub-Release.

Update als Projektbesitzer ohne sudo aus /home/pi/docker-files:
  unzip -o financisto-dashboard-1.9.58-dev.18.zip && \
  ./financisto-release-1.9.58-dev.18/update.sh /home/pi/docker-files/financisto-dashboard

Alle Daten, Bind-Mounts und Secrets bleiben bestehen.

Mobile-API: Nach Anmeldung unter Einstellungen → Android-App API-Schlüssel erzeugen (Admin-Passwort + 2FA).
Schnittstellenübergabe an den separaten Android-Entwicklungschat: Basisadresse https://finance.fieler.de ohne /api/ verwenden, API-Token über HTTPS als Bearer senden. Android-Versionen ausschließlich dort erstellen; lokale Daten dürfen nicht automatisch übertragen werden.
