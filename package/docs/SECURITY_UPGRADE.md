# Umstellung auf mehrere Benutzer und verpflichtende 2FA (1.8.0)

## Erste Anmeldung nach dem Update

Melde dich mit dem **bisherigen** Benutzer `admin` und dem zuletzt im Dashboard gültigen Passwort an. Das bereits in SQLite hinterlegte Passwort wird übernommen, nicht das eventuell ältere Installations-Secret. Die App fordert dann zur TOTP-Einrichtung auf.

Scanne den QR-Code mit einer TOTP-App und bestätige den sechsstelligen Code. Die zehn Wiederherstellungscodes werden **nur einmal** gezeigt; sichere sie in deinem Passwortmanager. Ohne 2FA gibt es keinen Zugriff auf die Auswertung. Die Sitzung ist pro Benutzer getrennt. Ein Passwortwechsel oder eine Benutzersperre beendet bestehende Sitzungen.

## Benutzer anlegen

**Einstellungen → Benutzer und Zugriff → Neuen Benutzer hinzufügen.** Administratoren können Benutzer anlegen, sperren, ihre Passwörter neu vergeben und die 2FA anderer Benutzer zurücksetzen. Benutzer benötigen beim ersten Login ihr Startpasswort und richten dann ihre eigene 2FA ein. Bestehende Benutzer erhalten automatisch eine eindeutige Identität, beginnend mit `admin`.

## Sicherheit und Internetzugriff

- `PUBLIC_ACCESS` ist **standardmäßig 0** und die bestehende PC-IP-Allowlist bleibt aktiv.
- Den ersten Administrator **zuerst ausschließlich über das Heimnetz** mit 2FA aktivieren.
- Die öffentliche Erreichbarkeit nur über einen HTTPS-Reverse-Proxy (Nginx Proxy Manager) freigeben, mit gültigem öffentlichem Zertifikat, geeigneten Limits und korrekter Behandlung der echten Client-IP. Firewall-seitig den internen Caddy-Port nicht direkt ins Internet weiterleiten.
- Anschließend bewusst `PUBLIC_ACCESS=1` in `.env` eintragen und im Projektverzeichnis `docker compose up -d --force-recreate dashboard` ausführen. Ohne mindestens einen aktiven Admin mit aktivierter 2FA bleibt die bisherige IP-Sperre erhalten.
- `TRUSTED_PROXY_IPS` muss die tatsächlich bei Caddy ankommende **exakte IP** des NPM enthalten, niemals `0.0.0.0/0`. Bei unzutreffender Konfiguration können IP-basierte Sperren und Auditwerte falsch sein. Von einem nicht erlaubten externen Netz testen.
- Sicherheitskritisch: der bestehende `app_secret` unter `secrets/app_secret` ist nun zugleich der Verschlüsselungsschlüssel für TOTP-Seeds. **Sichere ihn zusammen mit der SQLite-Datenbank**; bei Verlust lassen sich TOTP-Seeds nicht mehr entschlüsseln. Secret nicht veröffentlichen oder unkoordiniert ersetzen.
- Die Verbindung sollte einen gültigen TLS-Hostnamen verwenden; die interne Caddy-CA ersetzt kein öffentliches HTTPS-Zertifikat am NPM.
- Es ist kein Ersatz für eine externe Sicherheitsprüfung des öffentlich erreichbaren Dienstes.

## Nächste Ausbaustufe: Finanzverwaltung

**Konten, Kategorien, Empfänger und Buchungen bleiben in 1.8.0 READ-ONLY.** Das ist absichtlich so: Der automatisierte Android-Sicherungsimport ersetzt diese Tabellen weiterhin. Erst nach einem geprüften einmaligen Import als eigene Buchhaltungsdatenbank schalten wir die Bearbeitung, die Buchungseingabe mit direkter Empfängeranlage, die nativen Backups und ggf. kompatible Financisto-Exporte frei. Der bestehende Android-Import wird erst beim tatsächlichen Wechsel des führenden Systems deaktiviert.

## Notfall: Authenticator verloren

Wenn auch alle Wiederherstellungscodes verloren sind, kann ein Eigentümer der Docker-Projektdateien die 2FA eines Benutzers lokal zurücksetzen:

```bash
cd /home/pi/docker-files/financisto-dashboard
docker compose exec -T dashboard python /app/manage.py reset-totp admin --yes
```

Danach mit dem bestehenden Passwort anmelden und 2FA neu einrichten. Dieser Vorgang wird protokolliert, die bestehenden Sitzungen dieses Benutzers werden ungültig. **Nicht** über das Internet als API anbieten.

Beim Zurücksetzen fremder Passwörter oder TOTP-Einstellungen fordert die Weboberfläche zusätzlich das **eigene Administratorpasswort und einen frischen Authenticator-Code** als Bestätigung an. Für diesen Code muss der nächste 30-Sekunden-TOTP-Schritt verwendet werden, falls unmittelbar zuvor bereits ein Code zur Anmeldung genutzt wurde (Wiederverwendung ist gesperrt).


### 1.9.2: Öffentlicher Zugang über Webeinstellungen

Der Schalter **Einstellungen → Öffentlicher Zugriff** wird nach Administratorpasswort + frischem TOTP + dem Bestätigungswort in SQLite gespeichert. Die Caddy-IP-Prüfung verwendet diesen Wert bei jeder Anfrage. Damit werden auch nicht freigegebene Client-IPs bis zur Anmeldeseite durchgelassen. Die NPM-Sicherheit, TLS-Konfiguration, Zugriffskontrolllisten, DNS und eventuelle Routerfreigaben werden dadurch nicht automatisch verändert. Der frühere Environment-Wert PUBLIC_ACCESS wird nur als Initialwert für Altinstallationen verwendet und nicht mehr zum dauerhaften Umschalten.

Falls das Abschalten des öffentlichen Modus den aktuellen Client aussperren würde, wird es verweigert. Zuerst eine eigene Client-IP unter PC-Freigaben hinterlegen.


### Version 1.9.3 – Berechtigungstrennung
- Editor erhält ausschließlich GET /settings (Finanz-Stammdaten) sowie POST /settings/payees/save, /settings/categories/save und /settings/master/delete mit `group=payees|categories`; nur im Web-Führungsmodus.
- POST /settings/master/delete prüft sowohl Benutzerrolle als auch Zielgruppe serverseitig. `group=accounts` bleibt admin-only.
- Alle System-, Benutzer-, 2FA-, PC-, Import-, Konto- und Backup-Aktionen sind weiterhin admin-only.
