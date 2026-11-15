FieLanzen v1.9.38 – Updatekorrektur und Caddy-Dokumentation (15.11.2026).

Ein direktes Update von v1.9.35 auf v1.9.38 ist vorgesehen.
Die falsche harte Versionsprüfung der v1.9.37 wurde behoben.

Update als Projektbenutzer (nicht root) im Verzeichnis mit der ZIP-Datei:
  unzip -o financisto-dashboard-v1.9.38.zip
  ./financisto-release-1.9.38/update.sh /pfad/zur/bestehenden/financisto-dashboard-installation

Bestehende .env, Finanzdaten, Benutzer, Secrets, Backups und
Caddy-Zertifikatsdaten bleiben erhalten. Das Update legt vor der
Programmänderung eine Sicherung der Datenbank und des Programmcodes an.

Englisch: README.md und package/README.en.md
Deutsch: README.de.md und package/README.md
Caddy/HTTPS: package/docs/CADDY.en.md und CADDY.de.md

Keine Änderung an Buchungs- und Importlogik.
