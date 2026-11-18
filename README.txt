FieLanzen 1.9.58-dev.6 – Wiederkehrend-Kennzeichnung jetzt unter dem Buchungsdatum. Empfängertext wird beim Antippen zum Überschreiben markiert. Durchgehende farbliche Markierung von Umbuchungen und wiederkehrenden Buchungen; 'Jetzt Sicherung erstellen' erzeugt SQLite und aktuellen Financisto-Rückexport separat; update.sh ist ausführbar.
Entwicklungsstand, kein offizielles GitHub-Release.

Update als Projektbesitzer ohne sudo aus /home/pi/docker-files:
  unzip -o financisto-dashboard-1.9.58-dev.6.zip && \
  ./financisto-release-1.9.58-dev.6/update.sh /home/pi/docker-files/financisto-dashboard

Alle Daten, Bind-Mounts und Secrets bleiben bestehen.
