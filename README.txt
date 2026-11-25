FieLanzen Dashboard 1.9.61-dev.3 – Mobile Buchungskarten jetzt mit denselben Farben, Statusabzeichen und Details wie auf der Startseite; Kategorie in der Desktop-Tabelle.
Neuerung: Kategorie inklusive Unterkategorie und Sortierung in der Web-Buchungsliste.\nWeitere Funktionen: CSV-Export und sortierbare Buchungslisten; farbige Kennzeichnung von Buchungsarten,
Wiederholungen und Regelzuordnungen; heutige Kontostände mit Prognose für künftige Buchungen;
tägliche SQLite- und Financisto-Sicherung einschließlich kompatibler Wiederholungsvorlagen;
versionierte Mobile-API mit dauerhaften, widerrufbaren Geräteschlüsseln und Wiederholungskennzeichen.
Vollständige Änderungen: CHANGELOG.md und CHANGELOG.en.md. Weitergabe nach GNU GPL v2, siehe LICENSE und NOTICE.md.
 
Update als Projektbesitzer ohne sudo aus /home/pi/docker-files:
  unzip -o financisto-dashboard-v1.9.61-dev.3.zip && \
  ./financisto-release-1.9.61-dev.3/update.sh /home/pi/docker-files/financisto-dashboard

Direkter Wechsel von älteren Releases/Entwicklungsständen ohne Zwischenversion möglich.
Bestehende Finanzdaten, Bind-Mounts, Einstellungen und Secrets bleiben erhalten.

Die SQLite-Sicherung ist das vollständige Web-Wiederherstellungsformat.
Financisto-.backup-Rückimporte zuerst in einer isolierten Android-Testinstallation prüfen.
Geräte-API-Schlüssel werden durch angemeldete Administratoren unter Einstellungen verwaltet;
die Android-App selbst wird getrennt vom Dashboard entwickelt.
