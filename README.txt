FieLanzen v1.9.57 – Wiederkehrende Buchungen und Dokumentation (18.11.2026).

- Neue Wiederholungsregeln übernehmen den Tag im Monat aus dem Startdatum.
- Bei täglicher und wöchentlicher Wiederholung wird das Monatstagsfeld ausgeblendet.
- Manuell eingestellte Monatstage und bestehende Regeln bleiben erhalten.
- GitHub-READMEs aufgeräumt; vollständige Neuerungen in GitHub Releases und Changelog.
- Docker-Image der drei App-Dienste: financisto-dashboard:1.9.57.

Update als Projektbesitzer (ohne sudo), im Ordner /home/pi/docker-files:
  unzip -o financisto-dashboard-v1.9.57.zip && \
  ./financisto-release-1.9.57/update.sh /home/pi/docker-files/financisto-dashboard

Datenbank, .env, Secrets und Caddy-Zertifikate bleiben bestehen.
Details: package/CHANGELOG.md und package/CHANGELOG.en.md.
