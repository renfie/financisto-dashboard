Financisto-Dashboard v1.9.40 – Empfänger vor Kategorie, begrenzte Wiederholungen und gelb markierte zukünftige Buchungen.
Direktes Update ab 1.9.35 mit update.sh im Release-Hauptverzeichnis, als Projektbenutzer ohne sudo.
Vorhandene Finanzdaten, Secrets, Konfiguration und Caddy-CA bleiben erhalten.

FieLanzen v1.9.40 – Deutsch/Englisch für Weboberfläche und Installer (15.11.2026).

Direktes Update von v1.9.35 (keine Zwischenversion nötig):
  cd /home/pi/docker-files
  unzip -o financisto-dashboard-v1.9.40.zip
  ./financisto-release-1.9.40/update.sh /home/pi/docker-files/financisto-dashboard

Bisherige .env, Konten, Buchungen, 2FA, Datenbank, Backups, Secrets und
Caddy-Zertifikate bleiben erhalten. Das Update erstellt vorab eine SQLite-
und Programmcodesicherung. Kein sudo verwenden; als Projektbenutzer arbeiten.

Neu: DE / EN in der Weboberfläche auch auf der Anmeldung, mobil und Desktop.
Der Benutzer kann die Sprache jederzeit wechseln; Auswahl pro Sitzung.
Bei einer Erstinstallation fragt ./package/install.sh die Sprache ab.
Die dauerhafte Standardsprache steht in .env unter DEFAULT_LANGUAGE,
beim Update bestehender Installationen standardmäßig Deutsch.

English overview: README.md / package/README.en.md
Deutsch: README.de.md / package/README.md
Language: package/docs/LANGUAGE.en.md / LANGUAGE.de.md
