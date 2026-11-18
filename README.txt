FieLanzen 1.9.58-dev.4 – Durchgehende farbliche Markierung von Umbuchungen und wiederkehrenden Buchungen sowie zwei Financisto-Rückexport-Sicherungen; update.sh ist im ZIP ausführbar.
Entwicklungsstand, kein offizielles GitHub-Release.

Update als Projektbesitzer ohne sudo aus /home/pi/docker-files:
  unzip -o financisto-dashboard-1.9.58-dev.4.zip && \
  ./financisto-release-1.9.58-dev.4/update.sh /home/pi/docker-files/financisto-dashboard

Alle Daten, Bind-Mounts und Secrets bleiben bestehen.
