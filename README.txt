FieLanzen v1.9.43 – Englischübersetzung in den Anmeldeansichten vervollständigt,
Dashboard-Aktionsbuttons auf PC und Tablet nebeneinander (16.11.2026).

Direktes Update einer bestehenden Installation, als Projektbenutzer ohne sudo:
  unzip -o financisto-dashboard-v1.9.43.zip
  ./financisto-release-1.9.43/update.sh /pfad/zum/financisto-dashboard

Die vorhandene SQLite-Datenbank, .env, Secrets, Backups und Caddy-Zertifikate
bleiben erhalten. Kein Datenbank-Schemawechsel und keine Veränderung der
Buchungslogik. Smartphone-Darstellung unverändert.
