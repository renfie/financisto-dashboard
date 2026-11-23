FieLanzen Dashboard v1.9.58 – Offizielles Sammelrelease aus 21 Entwicklungsständen (dev.1–dev.21).
Neuerungen: CSV-Export und sortierbare Buchungslisten; farbige Kennzeichnung von Buchungsarten,
Wiederholungen und Regelzuordnungen; heutige Kontostände mit Prognose für künftige Buchungen;
tägliche SQLite- und Financisto-Sicherung einschließlich kompatibler Wiederholungsvorlagen;
versionierte Mobile-API mit dauerhaften, widerrufbaren Geräteschlüsseln und Wiederholungskennzeichen.
Die vollständigen Änderungen stehen in den deutschen und englischen Release Notes auf GitHub.
 
Update als Projektbesitzer ohne sudo aus /home/pi/docker-files:
  unzip -o financisto-dashboard-v1.9.58.zip && \
  ./financisto-release-1.9.58/update.sh /home/pi/docker-files/financisto-dashboard

Direkter Wechsel von älteren Releases/Entwicklungsständen ohne Zwischenversion möglich.
Bestehende Finanzdaten, Bind-Mounts, Einstellungen und Secrets bleiben erhalten.

Die SQLite-Sicherung ist das vollständige Web-Wiederherstellungsformat.
Financisto-.backup-Rückimporte zuerst in einer isolierten Android-Testinstallation prüfen.
Geräte-API-Schlüssel werden durch angemeldete Administratoren unter Einstellungen verwaltet;
die Android-App selbst wird getrennt vom Dashboard entwickelt.
