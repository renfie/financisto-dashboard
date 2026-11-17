FieLanzen v1.9.56 – Kategorieeingabe und korrigierte Docker-Image-Tags (17.11.2026).

- Vorgabekategorie wird beim Antippen markiert, damit neuer Suchtext sie direkt ersetzt.
- Alle drei Anwendungsdienste verwenden das Docker-Image financisto-dashboard:1.9.56.
- Update und Release-Build prüfen, ob VERSION und Docker-Image-Tags übereinstimmen.
- Alle Funktionen aus v1.9.54 und v1.9.55 sind enthalten.

Update als Projektbesitzer (ohne sudo), im Ordner /home/pi/docker-files:
  unzip -o financisto-dashboard-v1.9.56.zip && \
  ./financisto-release-1.9.56/update.sh /home/pi/docker-files/financisto-dashboard

Datenbank, .env, Secrets und Caddy-Zertifikate bleiben bestehen.
Details: package/CHANGELOG.md und package/CHANGELOG.en.md.
