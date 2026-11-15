# Eigener Titel und Fußzeile (ab Version 1.9.18)

Die drei Beschriftungen werden ausschließlich über die bestehende Projekt-.env konfiguriert.
Die .env wird bei Updates nicht überschrieben. Fehlende Variablen werden einmalig
mit den bisherigen Standardwerten ergänzt.

Datei: `/home/pi/docker-files/financisto-dashboard/.env`

```dotenv
APP_TITLE="Financisto"
APP_SUBTITLE="Dashboard"
APP_FOOTER="Privates Finanz-Dashboard · Daten bleiben auf deinem Server"
```

Wirkung:
- APP_TITLE: Produktname links oben (Login, Desktop und Mobil) sowie Browser-Tab.
- APP_SUBTITLE: Zusatz unter/neben dem Titel sowie Browser-Tab.
- APP_FOOTER: Fußzeile unten und Hinweis unten in der Desktop-Navigation.
- Die Versionsnummer wird unabhängig davon automatisch aus der Anwendung angezeigt.

Änderungen an der .env übernehmen:

```bash
cd /home/pi/docker-files/financisto-dashboard
nano .env
docker compose up -d --no-deps --force-recreate dashboard
```

Bitte nicht `docker compose down -v` verwenden. Die reinen Anzeigetexte haben
keinen Einfluss auf Finanzdaten, Rollen, Sitzungen oder den Hintergrunddienst.
Werte in der .env ggf. mit doppelten Anführungszeichen setzen (Leerzeichen / Sonderzeichen).

ACHTUNG: .env enthält auch andere lokale Einstellungen. Nur die drei APP_...-Werte ändern.
