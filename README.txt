Financisto-Dashboard v1.9.41 – Buchungsformular für PC und Tablet korrigiert.

Empfänger links und Kategorie rechts stehen auf größeren Bildschirmen jetzt
wieder nebeneinander. Auf dem Smartphone bleibt die Darstellung wie bisher.
Umbuchungen: Zielkonto und Empfänger werden am Desktop ebenfalls nebeneinander dargestellt.

Direktes Update von 1.9.35, 1.9.39 oder 1.9.40 möglich, ohne Zwischenversion:
  cd /home/pi/docker-files
  unzip -o financisto-dashboard-v1.9.41.zip
  ./financisto-release-1.9.41/update.sh /home/pi/docker-files/financisto-dashboard

Als Eigentümer der Installation ausführen, ohne sudo.
Die bestehenden Finanzdaten, .env, Secrets, Backups und die lokale Caddy-CA
bleiben erhalten; das Update erstellt vorab Programm- und SQLite-Sicherungen.

English: This maintenance release fixes desktop/tablet transaction form layout.
Payee and Category now share a row. Mobile layout and stored data remain unchanged.
