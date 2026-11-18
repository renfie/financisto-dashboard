FieLanzen 1.9.58-dev.3 – Zwei automatisch erstellte Financisto-Rückexport-Sicherungen des aktuellen Web-Datenbestandes zum Download sowie CSV-Export und Übersetzungen.
Entwicklungsstand, kein offizielles GitHub-Release.

Update als Projektbesitzer ohne sudo aus /home/pi/docker-files:
  unzip -o financisto-dashboard-1.9.58-dev.3.zip && \
  ./financisto-release-1.9.58-dev.3/update.sh /home/pi/docker-files/financisto-dashboard

Alle Daten, Bind-Mounts und Secrets bleiben bestehen.
