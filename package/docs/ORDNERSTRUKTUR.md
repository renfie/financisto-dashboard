# Ordnerstruktur ab 1.9.32

- `src/`: Python-Quellcode und Dienstprogramme. Docker kopiert diese Module nach `/app`.
- `docs/`: ergänzende Dokumentationen.
- `templates/` und `static/`: Webvorlagen und Assets.
- `data/`: SQLite-Datenbank und Import-Inbox. Nicht verschieben.
- `secrets/`: Servergeheimnisse (`app_secret`). Nicht verschieben.
- `backups/`: Sicherungen. Nicht verschieben.
- `caddy/`: bestehende Caddy-Daten und Schlüssel. Nicht verschieben.

Das Update räumt die alten Python- und Dokumentationsdateien im Hauptverzeichnis **erst nach erfolgreichen Containerprüfungen** weg. Vorher wird die bisherige Codefassung und die Datenbank gesichert.

Die Gotify- und Telegram-Tokens liegen verschlüsselt in `data/finanzen.sqlite3` in den Tabellen `notification_settings` und `telegram_booking_settings`. Der Schlüssel ist aus `secrets/app_secret` abgeleitet. `app_secret` nie löschen oder ersetzen, da sonst bestehende verschlüsselte Tokens und weitere geheimnisbasierte Daten nicht mehr entschlüsselt werden können.

Zum manuellen Start eines Dienstprogramms vom Host aus:

```bash
cd ~/docker-files/financisto-dashboard
FINANCISTO_PROJECT_DIR="$PWD" PYTHONPATH="$PWD/src" python3 src/manage.py --help
```

Alle bestehenden Web-, Import- und Benachrichtigungsfunktionen bleiben unverändert.
