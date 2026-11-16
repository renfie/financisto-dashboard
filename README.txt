Financisto-Dashboard v1.9.42 – zweisprachige, aktualisierte Einführung.

Upgrade ab v1.9.35 oder neuer ohne Zwischenversion:
  unzip -o financisto-dashboard-v1.9.42.zip
  ./financisto-release-1.9.42/update.sh /home/pi/docker-files/financisto-dashboard

Upgrade bitte als Eigentümer der Installation ohne sudo ausführen.
Vor der Aktualisierung legt update.sh eine Sicherung der SQLite-Datenbank
und der vorherigen Programmversion an. .env, Secrets, Finanzdaten, die
vorhandene Caddy-CA und vorhandene Benutzerrechte bleiben erhalten.

Geändert wurde nur der Einführungsrundgang (tour.js) und die Dokumentation.
DE und EN für Administratoren, Bearbeiter und Leseberechtigte. Manuell jederzeit
über „Hilfe / Einführung“ erneut aufrufbar. Bestandskonten werden nicht erneut
automatisch durch die Einführung geführt.

Englisch: README.md und package/docs/ONBOARDING.en.md
Deutsch: README.de.md und package/docs/ONBOARDING.de.md
