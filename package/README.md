## Neu in v1.9.51
- Android: Empfänger-Autovervollständigung ohne natives datalist-Overlay; maximal acht Vorschläge, passend zur verfügbaren Bildschirmhöhe.
- Neue Empfänger bleiben frei eingebbar, keine Änderung an Buchungsdaten oder Datenbank.

## Neu in v1.9.51

Die Kategorieauswahl im Buchungsformular ist jetzt wie die Empfängersuche kompakt und durchsuchbar. Die Dashboard-Schnellsuche startet fünf Sekunden nach der letzten Eingabe; per Suchen/Enter sofort. Vorhandene Kategorien und Buchungen bleiben unverändert.

## Neu: v1.9.49 – öffentliches Sammelrelease (16.11.2026)

Alle Änderungen der lokalen Testversionen v1.9.44 bis v1.9.48 sowie die letzte vollständig englische Warnung zum Rückwechsel zu Financisto sind in v1.9.49 enthalten. [Deutsches Changelog](CHANGELOG.md) · [English changelog](CHANGELOG.en.md).

## v1.9.48 – Lokale Testversion (16.11.2026)
Englische Texte in Konten/Import/A5-Berichten ergänzt. Die vorhandene `.env` bleibt erhalten. Für die zweisprachige Fußzeile:
```dotenv
APP_FOOTER="Alles im Blick. Bis auf den letzten Cent."
APP_FOOTER_EN="Your finances at a glance. Down to the last cent."
```
`APP_FOOTER_EN` ist optional; bei bestehender Konfiguration kann der Wert ergänzt werden. Nach Änderung der `.env`: `docker compose up -d --no-deps --force-recreate dashboard`.

**v1.9.47 (lokale Testversion, NICHT auf GitHub):** Buchungen standardmäßig aufgeklappt; Cashflow standardmäßig zugeklappt. Weitere Englischübersetzungen insbesondere für Einstellungen und Systemstatus.

**v1.9.46 (lokale Testversion, nicht auf GitHub):** Klappbare Buchungsliste direkt unter den Kontoständen mit anklickbaren Seitenzahlen; darunter Kategorien und Cashflow mit angepassten Farben, ausgerichteter und erklärter Netto-Linie.

## Neu in v1.9.46 – lokale Testversion (noch nicht auf GitHub)
- Schnellfilter **1 Woche, 1 Monat, 3 Monate und 6 Monate** für die Buchungsliste, separat von der bisherigen Monatsauswertung; die Monatsauswahl bleibt als fünfte Option.
- Suchfeld hinter dem eigenen **Filter**-Bereich, weiterführende Konto-/Kategorie-/Monatsfilter per Verweis erreichbar.
- **Cashflow-Balkendiagramm** mit Einnahmen, Ausgaben und Saldo für den gewählten Zeitraum, ohne Umbuchungen, durchlaufende Posten, Kontostandskorrekturen oder zukünftige Buchungsdaten. Die Cashflow-Anzeige ändert keine Buchung und keinen Kontostand.
- **Klonen / Bearbeiten / Löschen** am Desktop kompakt nebeneinander; mobile Karten unverändert.
- Verbesserte englische dynamische Texte bei historischen Auswertungen, Import und Haushaltsberichten; Dateiauswahl mit eigener übersetzbarer Schaltfläche.
- Keine Änderungen an Datenbankstruktur, Benutzern, Sicherungen, Caddy, Importen und wiederkehrenden Regeln.

## Neu in v1.9.46 – Englischübersetzungen vervollständigt
Die englische Oberfläche übersetzt nun auch dynamische Dashboard-Texte (Importdaten, Monatsvergleich, Buchungszahlen, Sortierhinweise und Schnellfilter). Weitere Texte in Einstellungen und Berichten sind ergänzt. Kontonamen, Empfänger und Notizen bleiben unverändert. Finanzlogik und gespeicherte Daten werden nicht verändert.

## Neu in v1.9.43

Die 2FA-Bestätigung, Authenticator-Einrichtung, Wiederherstellungscodes und Passwortänderung werden auf Englisch vollständig übersetzt. Die Dashboard-Aktionsbuttons stehen bei PC und Tablet wieder nebeneinander; auf Smartphones bleibt die Darstellung unverändert. Finanzdaten und Sicherheitskonfiguration werden nicht verändert.

**Sprache / Language:** [English](README.en.md) | **Deutsch (ausführliche Dokumentation)**

## Neu in v1.9.42 – Einführung aktualisiert
- Einführungsrundgang vollständig deutsch/englisch und auf den Funktionsstand 1.9.41 aktualisiert.
- Behandelt neue Wiederholungsbegrenzungen, zukünftige Buchungen, Benutzerrechte und Sprachumschaltung.
- Neue Benutzer einmalig; bestehende Konten behalten ihren Status. Über [Hilfe / Einführung](docs/ONBOARDING.de.md) ist der Rundgang jederzeit erneut aufrufbar.

## Neu in v1.9.41
- Buchungsformular auf PC und Tablet: Empfänger und Kategorie stehen wieder nebeneinander (Empfänger links, Kategorie rechts). Smartphone-Layout unverändert.
- Keine Änderungen an Finanzdaten, Buchungslogik und Wiederholungsregeln.

## Neu in v1.9.40

Die Buchungsmaske zeigt den Empfänger vor der Kategorie. Wiederkehrende Regeln können durch ein Enddatum und/oder eine maximale Zahl von tatsächlichen Ausführungen begrenzt werden. Bereits angelegte Regeln bleiben unbegrenzt. Buchungen mit Datum in der Zukunft werden in der Buchungsliste gelb markiert, die bisherige sofortige Kontostandsänderung bleibt bestehen.


## Neu in v1.9.40 – Deutsch und Englisch
- Bei der Neuinstallation kann zwischen Deutsch und Englisch gewählt werden; alle Dialoge und Installationshinweise werden entsprechend angezeigt.
- Weboberfläche mit Umschalter DE / EN auf Anmeldeseite, Desktop und Mobilgeräten. Benutzer können die Sprache jederzeit ohne erneute Anmeldung wechseln.
- Die Sprachwahl wird nur für die aktuelle Sitzung gespeichert; Standard aus `DEFAULT_LANGUAGE` in `.env`, ohne Datenbankmigration.
- Übersetzungen sind lokal und schützen Buchungsdaten vor externen Übersetzungsdiensten.
- [Sprachkonfiguration](docs/LANGUAGE.de.md) und [English guide](docs/LANGUAGE.en.md).
- Bestehende Finanzdaten, Benutzer, 2FA, Caddy-Zertifikate und Importlogik bleiben unverändert.

## Neu in v1.9.38 – Updatekorrektur und Caddy-Dokumentation
- Direkte Aktualisierung von v1.9.35 auf v1.9.38 ohne Zwischeninstallation möglich; die interne Versionsprüfung im Update-Skript verwendet die tatsächliche Releaseversion statt einer festen Versionsnummer.
- [Caddy-/HTTPS-/NPM-Dokumentation auf Deutsch](docs/CADDY.de.md) sowie [auf Englisch](docs/CADDY.en.md).
- Keine Änderung an Buchungslogik, Finanzdaten, Passwörtern oder bestehender Caddy-CA.


## Neu in v1.9.36

- Dashboard-Buchungen auf Smartphone und Tablet kompakt: Text, Datum, Konto und Betrag; per Fingertipp Details und berechtigte Aktionen einblenden.
- Auf dem Tablet im Querformat keine horizontal scrollende Buchungstabelle mehr; Sortierung weiterhin verfügbar.
- Keine Veränderungen an Finanzdaten, Web Push, Telegram, Gotify oder Import.

## Neu in v1.9.35
Die Buchungsliste auf der Dashboard-Startseite zeigt auch Umbuchungen mit Quell- und Zielkonto. Die Einnahmen-/Ausgabenstatistik bleibt davon unberührt. Wiederkehrende Buchungen werden nur bei aktiver und fälliger Regel durch den Hintergrunddienst ausgeführt. Dafür ist eine frühestmögliche Ausführungsuhrzeit in Europe/Berlin einstellbar; die Prüfung erfolgt alle 15 Minuten.

## Neu in v1.9.34

Persönliche Web-Push-Regeln für Ausgaben und Einnahmen mit eigenem EUR-Grenzbetrag und Detailstufen.

## 1.9.24 – Benachrichtigung über größere Ausgaben (13.11.2026)

- **Administrator-Einstellungen:** Unter „Benachrichtigungen“ lassen sich Grenzbetrag (EUR), Gotify (URL, App-Token, Priorität) und Telegram (bestehender Bot, Chat-ID) einschalten und per Testmeldung prüfen.
- **Nur echte neue Ausgaben:** Nachrichten entstehen im Web-Modus für neue Ausgaben ab dem Schwellwert. Ausschluss von Importen, durchlaufenden Posten, Umbuchungen, Saldoabgleichen, Bearbeitungen und Fremdwährungen ohne Umrechnung.
- **Verschlüsselte Zugangsdaten:** App-/Bot-Token werden in SQLite verschlüsselt gespeichert und niemals in HTML zurückgegeben. Bearbeiter haben keinen Zugriff auf System-Konfiguration.
- **Separater Versanddienst:** Vierter Docker-Container nur mit ausgehender Netzwerkverbindung, keine zusätzlichen HTTP-Ports. Der bisherige Node-RED-Telegram-Empfang und der netzlose Import-/Backup-Worker bleiben erhalten.
- **Transaktionssichere Warteschlange:** Warnmeldung wird in derselben SQLite-Transaktion wie die neue Buchung eingereiht; externe Übertragungsfehler können die Buchung nicht nachträglich zurückrollen. Versandwiederholungen und Statusanzeige enthalten keine geheimen Tokens.
- **Import erhalten:** Manueller `.backup`-Import, automatische Importsteuerung, Web-Datenschutz beim Wechsel, bestehende Konten, Benutzer und 2FA bleiben erhalten.
- Einrichtung: `NOTIFICATIONS.md`.

## 1.9.23 – Vereinfachter Kontostandsabgleich für Administrator und Bearbeitung (13.11.2026)

- **Dashboard:** Zusammenklappbarer Kontostandsabgleich direkt unter den Kontoständen, begrenzt auf aktive Konten mit bekanntem Saldo in der ausgewählten Währung.
- **Berechtigungen:** Rolle „Bearbeitung“ darf Kontostände abgleichen, serverseitig mit `finance_editor_required` (CSRF und aktive Web-Datenführung). Administratorfunktionen für Konten, Währungen, Benutzer und System bleiben gesperrt.
- **Einstellungen:** Für Administratoren weiterhin im Kontenbereich; Bearbeitung erhält eine eigene, beschränkte Abgleichmaske und keine administrative Kontenliste.
- **Vereinfachung:** Auswahl der Anpassungsart entfällt; jede Differenz verwendet dieselben neutralen Kontostandskorrektur-Kategorien. Optionaler Notiztext; historische Depot-Wertanpassungen bleiben unverändert.
- **Datensicherheit:** Keine Migration und keine automatische Änderung bestehender Kontostände. Jede Korrektur wird als separate Buchung mit Audit und anschließender Saldo-Prüfung gespeichert. Web-Modus bleibt Pflicht.

## 1.9.22 – Buchungsaktionen, Saldoabgleich und Stammdaten (13.11.2026)

- **Dashboard-Buchungsliste:** Im Web-Führungsmodus können Administratoren und Bearbeiter alle Buchungen (einschließlich importierter Originalbuchungen) klonen, bearbeiten oder löschen. Klonen setzt das aktuelle Datum, übernimmt Stammdaten und leert den Betrag. Im Financisto-Führungsmodus keine Bearbeiten-/Löschen-Aktionen, um die Android-Datenhoheit zu schützen.
- **Financisto-Rückexport:** Absichtlich geänderte Originalbuchungen behalten ihre ursprüngliche ID und, soweit möglich, unbekannte Originalfelder. Gelöschte Buchungen werden im Export nicht wiederhergestellt. Historische Verweise auf nicht mehr vorhandene Empfänger bleiben erhalten, sofern unverändert.
- **Kontostandsabgleich:** Einstellungen → Finanz-Stammdaten → Konten. Aktuellen Ist-Kontostand bzw. Depotwert angeben: Die Differenz wird als eigene, auditierte Web-Buchung erfasst und der Kontostand auf den Zielbetrag gestellt. Ausgleichskategorien sind von Haushaltsstatistiken ausgeschlossen, bleiben im Kontoverlauf und Android-Export sichtbar.
- **Währungen:** Standard EUR statt erster alphabetischer Währung (DKK); Administratoren können die bevorzugte Währung wechseln und zahlreiche weitere ISO-Währungen vor dem Erstellen neuer Konten hinzufügen. Keine automatische Umrechnung zwischen verschiedenen Währungen.
- **Kontostatus:** Aktive Konten grün, deaktivierte rot hervorgehoben; Funktionen und Berechtigungen unverändert.
- **Neue Kategorie direkt in der Buchungsmaske:** Ein Dialog ermöglicht neue Haupt- oder Unterkategorien ohne Seitenwechsel. Die neue Kategorie wird sofort gewählt, bereits ausgefüllte Buchungsfelder bleiben unverändert. Bestehende Kategoriehierarchie und Rechte werden eingehalten.
- Drei Docker-Container unverändert. Keine neuen externen Dienste; `.env`, Finanzdaten, Benutzer/2FA und bestehende Backups bleiben erhalten. Update erstellt wie gewohnt einen SQLite-Snapshot.

## 1.9.18 – Eigenes Branding aus der .env

Für APP_TITLE, APP_SUBTITLE, APP_FOOTER und das Neuladen der Dashboard-Konfiguration
siehe [BRANDING.md](docs/BRANDING.md). Die drei Werte sind updatefest.

## 1.9.16 – Systemstatus unter Einstellungen, nur Administratoren (04.11.2026)

- Der Abschnitt „Systemstatus & Hintergrunddienste“ befindet sich unter Einstellungen → System und Sicherheit; nicht mehr auf der Dashboard-Startseite.
- Der Status wird nur für die Rolle Administrator aus SQLite ausgelesen und an die Ansicht übergeben. Bearbeiter sehen ausschließlich Finanz-Stammdaten, Leser können Einstellungen nicht öffnen.
- Erhalten bleiben die Betriebsdaten aus 1.9.15 (Führendes System, letzter Import, letzte Sicherung, Prüf- und Fehlerstatus, nächste Prüfungen).
- Keine neue Route, kein Container und keine Datenbankmigration; der bestehende SQLite- und 2FA-Schutz bleibt unverändert.

## 1.9.15 – Status des Hintergrunddienstes (04.11.2026)

- Dashboard zeigt führendes System, letzten erfolgreichen Financisto-Import und letzte verifizierte Datenbanksicherung im Projekt-Sicherungsordner.
- Weitere Details: tatsächliche letzte und geplante nächste Prüfung pro Hintergrundaufgabe, inklusive Fehleranzeige und Statuswarnung, wenn Prüfungen ausbleiben.
- Hintergrunddienst schreibt ausschließlich Betriebsmetadaten in die vorhandene SQLite-Datenbank; keine neuen Container, keine neuen Berechtigungen oder externen Dienste.
- Wiederkehrende Regeln zeigen bei führendem Financisto jetzt „Von Financisto verwaltet“ für ursprünglich aus Financisto importierte Vorlagen; reine Web-Vorlagen sind als nicht aktiv gekennzeichnet. Ein Wechsel des führenden Systems überträgt nicht automatisch Vorlagen an Android.
- Statuszeiten werden beim Neuladen des Dashboards aktualisiert. Datenbanken, Secrets, 2FA und Finanzbuchungen werden nicht verändert.

## Version 1.9.8 — 04.11.2026
- Buchungsübersicht zeigt alle Monate zwischen zwei ausgewählten Monatsgrenzen (einschließlich).
- Buchungsseiten: Standard 30; 20/30/50/100 unter Einstellungen → Buchungsliste.
- Rechnerischer Kontostand nach jeder Buchung; Umbuchungen werden berücksichtigt, fremdwährungsübergreifende Zielsalden als unbekannt markiert.
- Neue historische Auswertung mit Monatsverlauf, Durchschnittskennzahlen, Höchstbeträgen und Kategorie-Kreisdiagrammen.
- Dashboard und historische Auswertung teilen Monats-/Konto-/Kategorie-/Währungs-/Suchfilter pro angemeldeter Sitzung.
- Bisherige TOTP-2FA, Rollen, manueller Import, Auto-Import-Regelung und Datensicherung bleiben erhalten.

# Financisto-Dashboard – Version 1.9.7

Deutschsprachiges, privates Finanz-Dashboard mit wahlweise Financisto als führender Datenquelle oder nach ausdrücklicher Umstellung als eigenständiger Web-Finanzverwaltung. Mit Caddy (`tls internal`), freigegebenen PC-IP-Adressen, HTTPS, Admin-Login und Passwortwechsel, sortierbaren Buchungen, Schnellfilter, Zwei-Monats-Vergleich und **monatlicher, druckbarer Haushaltsauswertung**.

## Betrieb ohne sudo

Der Linux-Projektbenutzer (egal wie er heißt) muss sein Verzeichnis besitzen, dort schreiben können und berechtigten Zugriff auf den Docker-Daemon haben. Für Installation und Updates wird **kein sudo** benötigt. Bei erstmaliger Einrichtung:

```
mkdir -p ~/docker-files/financisto-dashboard
cp -R ./financisto-release-1.9.7/package/. ~/docker-files/financisto-dashboard/
cd ~/docker-files/financisto-dashboard
./install.sh
```

Bestehende Installation aktualisieren:

```
cd ~/docker-files/financisto-release-1.9.7
./update.sh
```

Liegt das Projekt nicht neben dem Release, den absoluten Projektpfad als Argument angeben.

**Achtung:** Ein bereits Root gehörendes Projekt braucht einmalig eine bewusste Berechtigungsreparatur durch den Systemadministrator. Das Skript nimmt keine Besitzwechsel vor. Auch `data/`, `secrets/`, `caddy/` und `.env` werden niemals überschrieben oder gelöscht.

## Monatsblatt und Druck

Menü **Haushaltsauswertung / Druck** öffnen, Monat, Währung und ggf. Konto wählen. Das Blatt gruppiert alle negativen Financisto-Buchungen wahlweise nach ihren Hauptkategorien oder den Geschäften/Empfängern, zeigt darunter einzelne Ausgaben mit Datum/Empfänger/Notiz sowie Zwischensummen, oben die Gesamtsummen für Einnahmen, Ausgaben und den Monatssaldo. Einnahmen werden gesondert aufgelistet. Über **Drucken / als PDF speichern** den Browserdruck öffnen und Papierdruck oder PDF-Ziel wählen. A4-Querformat ist voreingestellt.

Es werden weder manuelle Buchungen erfasst noch doppelt gezählt. Eventuelle historische manuelle Tabellen aus vorherigen Versionen bleiben in der Datenbank erhalten, sind jedoch nicht mehr in der Oberfläche erreichbar. Vor Entfernung eventueller Altbestände immer ein separates Backup erstellen.

## Schnellfilter

In der Buchungstabelle über das Suchfeld nach Datum, Empfänger, Konto, Kategorie, Betrag oder Notiz suchen. Die Suche wird mit kurzer Verzögerung abgeschickt und umfasst **alle** Buchungen der gewählten Monate (nicht nur Seite 1). Einnahmen, Ausgaben und Diagramme verändern sich **nicht** durch diesen Schnellfilter. Die obere Auswertungs-Suche beeinflusst hingegen die Summen.

## Daten und Docker

Alle persistenten Dateien sind Bind-Mounts unter dem Projektverzeichnis: `data/` (SQLite und Inbox), `secrets/`, `caddy/data`, `caddy/config`, `Caddyfile`. Caddy publiziert nur den HTTPS-Port aus `.env` (z.B. 4443). Der Importer `auto-import` verarbeitet stabil übertragene `.backup`-Dateien aus `data/inbox` und ersetzt ausschließlich Financisto-Tabellen. Haushaltsbericht und Druckansicht sind rein lesend. Kontoumbuchungen und Vorlagen werden bei den Auswertungen ausgeschlossen. Beträge verschiedener Währungen werden nicht vermischt.

## Updates und Wiederherstellung

`update.sh` prüft Dateiberechtigungen, sichert SQLite mit der offiziellen Backup-API und archiviert den bisherigen Anwendungscode unter `backups/upgrade-<Zeitstempel>/`. Es ersetzt nur Programmdateien, aktualisiert die vorhandenen `APP_UID`/`APP_GID` auf den aktuellen Projektbenutzer und baut die Anwendung neu. Die `.env` bleibt im Übrigen erhalten. Geprüft werden Gesundheit von Dashboard und laufende Container `caddy` und `auto-import`.

Wegen der Docker-Gruppenberechtigung können Mitglieder der Docker-Gruppe trotz nicht erforderlichem sudo weitreichende Rechte auf dem Host haben. Nur vertrauenswürdige Systembenutzer für Docker freischalten.


## Version 1.6.1 – Druck und Filter

Die Monatsauswertung ist für A4 **Hochformat** gestaltet. Einnahmen erscheinen separat vor den Ausgaben.
Die Kategoriehierarchie aus Financisto bleibt erhalten, darunter
`Einkauf / Lebensmittel` und `Einkauf / Haushaltsartikel`.
In der aufklappbaren Kategorieauswahl markierte (ausgeblendete) Kategorien werden
weder auf der Webseite noch beim Druck dargestellt. Bei aktiven Filtern werden
auch Einnahmen, Ausgaben und Saldo ausschließlich über die **sichtbaren**
Buchungen berechnet; die eingeschränkte Aussagekraft ist deutlich markiert.
Die Einstellung verändert keine Finanzdaten und gilt für die URL/den Ausdruck.
Beim Browserdruck „Kopf- und Fußzeilen“ möglichst deaktivieren, Papier A4 Hochformat.

## Android-Synchronisierung vorbereiten

`data/inbox` ist der Eingangsordner; `auto-import` verarbeitet darin vollständig
übertragene `.backup`-Dateien (mindestens 120 Sekunden alt) automatisch.
Für FolderSync empfiehlt sich die Richtung „Zum Remote-Ordner“, nur lokale
`*.backup`-Dateien, keine Löschsynchronisation. Der SFTP-Benutzer sollte
separat und nur für den Upload angelegt werden. Für eine rein private
LAN-Nutzung keine Portfreigabe im Internet einrichten.

## Version 1.6.1 – A5-Zettel und Archivbereinigung
Der Button „Kompakter Ausdruck (A5)“ öffnet ein separates Monatsblatt mit Einnahmen, Saldo und den Einzelbeträgen pro Kategorie. Die ausführliche A4-Version bleibt über „Ausführlich drucken (A4)“ verfügbar. Die aktuelle Kategorieauswahl (auch ausgeblendete Kategorien) wird an den A5-Ausdruck übergeben; nach Änderungen zuerst „Auswahl übernehmen“ anklicken. Druckformat: A5 Hochformat; Browser-Kopf- und Fußzeilen deaktivieren. Sehr viele Buchungen können dennoch mehrere A5-Seiten benötigen.

Neue, vollständig übertragene .backup-Dateien in `data/inbox` werden geprüft und atomar in SQLite importiert. Erst nach erfolgreichem Import werden diese Sicherungen nach `data/import-archive` verschoben. Das Archiv behält maximal drei gültige Sicherungen. Ältere oder bereits verarbeitete Sicherungen werden ebenfalls aus `inbox` entfernt und rotiert. Ungültige Dateien kommen nach `data/import-errors` (maximal fünf, bis zu 14 Tage). Ein vorübergehender Datenbankfehler löscht keine Datei. Die Bereinigung betrifft **nur Dateien auf dem Server**; FolderSync darf **keinen Löschabgleich** aktivieren.

## Version 1.6.1 – Druck und SFTP
Der A5-Monatszettel öffnet nun in **demselben Browser-Tab**. Auf dem Monatszettel kann man A5 drucken oder über die zweite Schaltfläche zur **A4-Auswertung** zurückkehren und A4 drucken. Kategorieüberschriften werden auf Papier kräftig fett dargestellt. Die Auswahl ausgeblendeter Kategorien bleibt unverändert über URL-Parameter erhalten.

`setup_financisto_sftp.sh` ist als gesondertes Host-Skript im Release enthalten. Es benötigt als einzige Komponente Root-Berechtigungen, weil es eine SFTP-only-Kennung und einen SSH-Match-Block einrichtet. Prüft `sshd -T` die erwartete Konfiguration nicht, wird der SSH-Block zurückgenommen und die tatsächlich geladene Einstellung angezeigt. Das Dashboard-Update benötigt kein sudo.

## Version 1.6.2 – Externer Nginx Proxy Manager

`SITE_HOST` ist die lokale IP bzw. der lokale DNS-Name für HTTPS. Zusätzliche
HTTPS-Siteadressen werden dauerhaft in der .env-Datei hinterlegt:

```dotenv
SITE_HOST=192.0.2.61
SITE_ADDRESSES=https://192.0.2.61, https://finance.example.org
TRUSTED_PROXY_IPS=127.0.0.1/32
```

Nach einer Anpassung an .env `docker compose up -d --force-recreate caddy`.
Die Caddyfile wird bei Updates weiterhin verteilt, aber die individuellen Hostnamen
werden nicht mehr dort eingetragen. Bei einem Update von 1.6.1 übernimmt das
Skript bestehende zusätzliche Hostnamen aus der ursprünglichen Caddyfile.

**Sicherheit:** Wenn ein vorgeschalteter Nginx Proxy Manager verwendet wird,
steht in `TRUSTED_PROXY_IPS` *nur* dessen tatsächlich bei Caddy sichtbare
Quell-IP (/32) bzw. dessen dediziertes, enges Proxy-Netz. Dadurch kann Caddy
`{client_ip}` korrekt aus `X-Forwarded-For` ermitteln, statt alle Benutzer
als den Proxy zu sehen. Kein `private_ranges`, `0.0.0.0/0` oder ein breit
geteiltes Gateway einsetzen: sonst könnte eine direkt zugängliche Verbindung
mittels gefälschter Header eine fremde IP vorgeben.

Der Proxy muss die Client-IP mit `X-Forwarded-For` anhängen und den Hostnamen
`finance.example.org` beibehalten. NPM kann `https://192.0.2.61:4443` als
Upstream ansprechen, sofern dieser erreichbar ist; für die interne TLS-Strecke
die lokale Caddy-CA im NPM vertrauen oder die Transportabsicherung separat
prüfen. HTTPS für den Benutzer wird am NPM mit einem öffentlichen Zertifikat
terminiert. Es genügt nicht, die NPM-IP in der Dashboard-Freigabeliste zu
hinterlegen, da damit alle Besucher hinter NPM dieselbe Freigabe hätten.

**Zugangsmodus:** Standardmäßig ist `PUBLIC_ACCESS=0`: Nur die IP-Adressen
unter „PC-Freigaben“ dürfen durch Caddy zum Login. Bei einem NPM-Proxy muss
die echte Client-IP durch eine eng gefasste `TRUSTED_PROXY_IPS`-Einstellung
korrekt ermittelt werden; die bloße Freigabe der NPM-IP würde sonst alle
NPM-Besucher gleich behandeln.

Für ausdrücklich gewünschten externen Login mit mehreren Geräten kann nach
Sicherheitsprüfung `PUBLIC_ACCESS=1` in `.env` gesetzt und der Dashboard-Container
mit `docker compose up -d --force-recreate dashboard` neu erstellt werden.
**Achtung:** Dieser Modus hebt die IP-Allowlist auf und erlaubt jedem Besucher
der freigegebenen URL, die Anmeldeseite zu erreichen. Passwort + persönliche
TOTP-2FA bleiben verpflichtend; das ist dennoch keine Garantie für sicheren
öffentlichen Betrieb. NPM mit gültigem öffentlichen TLS-Zertifikat,
Zugriffsschutz/Rate-Limits und korrektem Client-IP-Forwarding betreiben.
Caddy-Port `4443` nicht zusätzlich direkt im Internet veröffentlichen. Eine
VPN-Lösung (z. B. WireGuard) ist die engere Alternative. Der externe Zugriff
ist nicht automatisch aktiviert; vor Freigabe Tests mit unerlaubten IPs und
separatem Testbenutzer durchführen.

## 1.6.3: SFTP-Eingangsordner und Besitzer

Bei einem eingeschränkten SFTP-Zugang kann `data/inbox` einem anderen
Besitzer (insbesondere `root`) und der Gruppe `financisto-sftp` gehören.
Entscheidend ist, dass der Projektbenutzer über POSIX-ACLs Schreibrechte hat.
`update.sh` ändert weder Besitzer noch Gruppenmitgliedschaft der Inbox und
kontrolliert deren tatsächliche Schreibbarkeit statt des Eigentümers.

Prüfen: `ls -ld data/inbox` und `getfacl -p data/inbox`. Die Chroot-Wurzel
`/srv/financisto-sftp` muss weiterhin root gehören und darf für andere nicht
beschreibbar sein. Diese Rechte niemals durch einen rekursiven chown ändern.

Eine Domain, die nur in einer älteren Caddyfile vorkam und beim letzten
Update nicht übernommen wurde, ist in `.env` einmalig nachzutragen, z.B.
`SITE_ADDRESSES=https://192.0.2.61, https://finance.example.org`.
Niemals die Domain in die verwaltete Caddyfile eintragen.

## Version 1.6.4 – Update des Auto-Import-Dienstes
Update baut jetzt beide Images und prüft den tatsächlich laufenden Importer.


### Neu in 1.6.6
Die Monatsübersicht kennzeichnet beide Vergleichsmonate farblich und textlich auch in den Balken. Die Haushaltsauswertung startet mit dem letzten Monat mit Finanzbuchungen, sofern kein Monat in der URL vorgegeben wurde. Die Kategorieauswahl schließt nach dem Übernehmen.

### Neu in 1.6.7

Die Monatsbeschriftung in den Balkendiagrammen hat jetzt einen eigenen, ausreichend breiten Bereich. Damit wird sie auf Desktop, Tablet und Smartphone nicht mehr von den Balken überdeckt.

### Neu in 1.6.8

„Auswerten“ und Änderungen an den Hauptfiltern führen jetzt direkt zu den Monatskarten. Buchungs-Schnellfilter, Sortierung und Seitennavigation bleiben auf der Buchungstabelle.

### Version 1.6.9 – Gesamtkontostand und Einzelkonten

Das Dashboard zeigt nach dem Monatsvergleich die aktuellen Kontostände aus
`total_amount` der letzten Financisto-Sicherung, separat für die oben gewählte
Währung. Die Gesamtsumme berücksichtigt ausschließlich Konten mit
`is_include_into_totals=1`. Ausgeschlossene oder inaktive Konten bleiben
als solche gekennzeichnet. Kontostände sind unabhängig von den Monatsfiltern.
Der Import schreibt die Kontostände atomar mit dem restlichen Snapshot.

Bei einer Aktualisierung von 1.6.8 versucht `update.sh`, die Kontostände
aus einer Archivdatei nur dann zu ergänzen, wenn deren SHA-256 exakt zum
letzten importierten Snapshot passt. Andernfalls erfolgt die Aktualisierung
beim nächsten Android-Import.


### Version 1.7.0: Navigation und kompakte Bedienung

Auf PCs (> 1080 px) erscheint das Menü links als feststehende Navigation, auf schmaleren Geräten oben als aufklappbares Menü. Filter und Kontostände sind zunächst eingeklappt; der Gesamtkontostand ist trotzdem sichtbar. Im Abschnitt „Buchungen“ zeigt die bisherige Spalte „Quelle“ nun klar erkennbar „Einnahme“ oder „Ausgabe“; die Spalte „Typ“ kann sortiert und im Schnellfilter durchsucht werden. Einstellungen und gespeicherte Finanzdaten bleiben beim Update erhalten.


### Version 1.7.1

Die Konten sind nach aktivem Saldo und Kontonamen sortiert (Nullsalden zuletzt). Die Kategorie-Diagramme starten eingeklappt. `update.sh` und die Installations-/SFTP-Skripte sind im ZIP ausführbar (Modus 755). Ein Update erfordert kein sudo.

## Version 1.8.0 – Benutzer / 2FA

Ab dieser Version sind alle Benutzer verpflichtet, bei der ersten Anmeldung TOTP-2FA einzurichten. Mehrere Benutzer sowie die gemeinsame Stammdatenübersicht werden unter **Einstellungen** verwaltet. Das bisherige Admin-Passwort aus SQLite bleibt erhalten. Die Finanzdaten werden durch das Upgrade nicht verändert. **Vor einer externen Freigabe unbedingt `SECURITY_UPGRADE.md` lesen.** Die neue Opt-in-Einstellung `PUBLIC_ACCESS=1` ist standardmäßig deaktiviert.


## 1.9.1: Importsteuerung und erste eigenständige Web-Finanzverwaltung

- Unter **Einstellungen → Datenführung und Sicherung** kann der Administrator
  den automatischen `.backup`-Import jederzeit deaktivieren. Der Import-Dienst
  läuft technisch weiter, prüft alle 60 Sekunden den Schalter in SQLite und
  lässt bei ausgeschaltetem Import die Dateien im Eingangsordner unangetastet.
  Der Import-Schalter wird nach Container-Neustart beibehalten.
- Der manuelle Upload bleibt jederzeit erreichbar. Im Importbetrieb ersetzt
  er bewusst den aktuellen Financisto-Snapshot. Im **Webbetrieb** prüft er
  die hochgeladene Datei nur noch, ohne Daten zu verändern. Eine kompatible
  Zusammenführung mehrerer Datenbestände ist noch nicht implementiert.
- Der Wechsel zur Web-Finanzverwaltung ist bewusst **einseitig** und benötigt
  das Adminpasswort, einen frischen TOTP-Code und die Eingabe `WEB`. Vorher
  wird eine SQLite-Sicherung unter `data/web-backups/` angelegt. Der Auto-Import
  wird in derselben SQLite-Transaktion deaktiviert. Nach Web-Änderungen ist
  kein Rückwechsel per Webseite möglich – nur eine geprüfte Wiederherstellung
  vor dem Wechsel kann das ursprüngliche Importverfahren zurückbringen.
- Unter Einstellungen können Konten angelegt/umbenannt und unbenutzte Konten
  ohne Restsaldo gelöscht werden. Kategorien inkl. Unterkategorien können
  hinzugefügt/umbenannt werden; verwendete Kategorien dürfen nicht gelöscht
  werden. Empfänger lassen sich hinzufügen, umbenennen und – unbenutzt – löschen.
  Für vorhandene Haupt-/Unterkategorien ist das Umhängen in einen neuen
  Elternzweig noch nicht implementiert.
- Unter **Buchungen erfassen** werden neue Einnahmen, Ausgaben und Umbuchungen
  erstellt, bearbeitet oder gelöscht. Ein unbekannter Empfänger kann direkt
  im Buchungsformular neu angelegt werden. Kontostandsänderungen erfolgen
  zusammen mit der jeweiligen Buchung atomar. Änderungen an ursprünglich
  importierten Financisto-Buchungen sind in dieser ersten Stufe noch gesperrt.
- SQLite-Backups stehen über **Einstellungen → Aktuelle SQLite-Sicherung
  herunterladen** bereit. Eine serverseitige Wiederherstellung und ein
  kompatibler Financisto-.backup-Export sind noch nicht implementiert.
  Die SQLite-Sicherung allein enthält keine unverschlüsselten 2FA-Secrets:
  Für eine vollständige Wiederherstellung müssen die aktuellen Dateien unter
  `secrets/` geschützt separat aufbewahrt werden.
- Vor einer Internetfreigabe unbedingt TLS/NPM-Konfiguration, 2FA,
  Zugangsschutz, Ratenbegrenzung und Sicherheits-Backups auf dem Zielsystem
  testen. Die Einstellung `PUBLIC_ACCESS` wird bei diesem Update nicht verändert.
- Alle Projektdateien bleiben auf Bind-Mounts im Projektverzeichnis.
  Normale Installation und Updates benötigen kein sudo.


## Version 1.9.1 – Rückschaltung und Eingabekomfort

- **Rückschalten:** Unter „Einstellungen → Datenführung“ ist die Rückkehr zu
  Financisto möglich, **solange `ledger_web_writes=0` und keine `origin=web`-Buchung
  existiert**. Der Administrator bestätigt mit Passwort und frischer TOTP. Vorher
  wird eine SQLite-Sicherung unter `data/web-backups` erstellt. Anschließend
  bleibt der automatische Import **bewusst deaktiviert**, bis die Inbox geprüft
  und die Automatik explizit eingeschaltet wurde.
- Bei Web-Änderungen lässt sich nicht gefahrlos direkt zurückschalten. Auch
  wenn eine Testbuchung wieder gelöscht wurde, wird der Änderungszähler aus
  Sicherheitsgründen nicht zurückgesetzt. Eine Wiederherstellung aus einem
  früheren Snapshot darf nicht ohne Abgleich passieren.
- **Standardkonto:** Einstellungen → Standardkonto für neue Buchungen. Gilt für
  neue Buchungen; beim Bearbeiten bestehender Buchungen bleibt deren Konto
  vorausgewählt. Es können nur Konten mit bekanntem Saldo und aktivem Status
  gewählt werden.
- Zielkonto ist nur für Umbuchungen sichtbar und muss dann angegeben werden;
  bei Umbuchungen wird die Kategorie ausgeblendet.
- Empfänger, Kategorien und Konten sind im Bereich Stammdaten exklusiv
  aufklappbar. Der manuelle `.backup`-Import bleibt dauerhaft erhalten (im
  Webmodus vorerst nur als sichere Vorschau, **ohne** Überschreiben).


## Version 1.9.2 – Zugriff, Rückschaltung und Bedienung

- Unter **Einstellungen → PC-Freigaben** sind Geräte und zugelassene IPs direkt sichtbar und bearbeitbar.
- Unter **Einstellungen → Öffentlicher Zugriff** kann der Administrator nach Passworteingabe, frischem TOTP und Bestätigung die Login-Seite freigeben oder sperren. Der Schalter wird in SQLite gespeichert; kein Container-Neustart erforderlich.
- Die Freigabe ersetzt keine NPM-Konfiguration und öffnet keinen Router-Port. Für Internetzugriff muss NPM ein öffentlich gültiges TLS-Zertifikat nutzen; bestehende NPM-ACLs müssen bewusst geprüft und die echte Client-IP vertrauenswürdig weitergereicht werden. Nur den explizit bekannten Proxy in TRUSTED_PROXY_IPS eintragen, keine Netze oder die ganze Welt.
- Rückwechsel von Web zu Financisto kann der Admin trotz Änderungen nach ausdrücklicher Datenverlust-Bestätigung auslösen. Es wird zuvor eine SQLite-Sicherung erstellt. Beim Umschalten selbst werden keine Webdaten gelöscht. Der automatische Import bleibt aus.
- Der erste vollständige Import, der Webdaten überschreiben kann, benötigt eine weitere bewusste Freigabe. Automatischer Import braucht Vorab-Sicherung, 2FA, Passwort und das Wort UEBERSCHREIBEN; der manuelle Import zeigt zunächst eine Vorschau.
- Der manuelle .backup-Import ist weiterhin vorhanden und bleibt auch im Web-Modus als nicht-destruktive Vorschau verfügbar.
- Buttons in Einstellungen/Tabellen haben konsistente Größe, Farben, Abstände und Tastaturfokus.


### Rollen in Version 1.9.3
- Administrator: sämtliche Bereiche einschließlich System/Sicherheit, Konten, Importe und Backups.
- Bearbeiter: Web-Buchungen und im Web-Modus die Finanz-Stammdaten Empfänger/Kategorien (anlegen, umbenennen, nur unbenutzte löschen). Einstellungen zeigt nur diesen Finanzbereich.
- Nur Lesen: Auswertungen und Berichte; keine Einstellungen und keine Buchungsänderungen.
- Die Berechtigungen werden für jede zustandsverändernde Route serverseitig geprüft.
- Bei Datenführung durch Financisto bleibt die Stammdatenpflege auch für Bearbeiter schreibgeschützt.


## Experimenteller Financisto-Rückexport (1.9.6)
Unter Einstellungen als Administrator verfügbar. Siehe `FINANCISTO_EXPORT.md`. Nur Testdatei; kein bestätigter Android-Restore.


## Schnellfilter für Stammdaten (1.9.6)

Unter Einstellungen → Finanz-Stammdaten enthalten die aufgeklappten Bereiche Empfänger, Kategorien und Konten jeweils eine Suche. Die lokale Suche filtert sofort während der Eingabe; leere Suche zeigt alle Einträge. Bei Kategorien wird auch der vollständige Name mit Oberkategorie berücksichtigt. Es werden keine Daten an einen zusätzlichen Dienst gesendet, keine Finanzdaten verändert und keine Benutzerrechte erweitert.


## 1.9.9 Wiederkehrende Buchungen
Über **Wiederkehrend** die originale aktuelle Financisto-Sicherung zunächst als Vorschau prüfen und anschließend nur die Vorlagen deaktiviert übernehmen. Die vorhandenen Buchungen, Konten und Salden werden dabei nicht überschrieben. Eine umbenannte oder unbekannte Kontozuordnung wird ausdrücklich gekennzeichnet. Besondere Vierteljahresregeln aus dem GEEKY-Format benötigen manuelle Kontrolle und Anpassung. Die Web-Finanzverwaltung muss führend sein, um eine Regel aktivieren zu können. Automatik wird nur bei gesonderter Admin-Freigabe eingeschaltet und prüft alle 15 Minuten. Vorhandene Jahres- und Monatslücken werden nicht automatisch massenhaft nachgebucht. Jeder geplante Termin kann pro Regel nur einmal geschrieben werden.


### Benutzer endgültig löschen (1.9.9)

Unter Einstellungen → Benutzer und Zugriff kann der Administrator einen fremden Benutzer dauerhaft löschen. Bestätigung des exakten Benutzernamens sowie eigenes Administratorpasswort und frischer TOTP-Code sind Pflicht. Das eigene Konto und der letzte aktive Administrator sind gegen Löschung geschützt. Bestehende Finanzbuchungen und Audit-Einträge bleiben erhalten; die Zugangsdaten, TOTP und Wiederherstellungscodes des Benutzers werden entfernt.


### 1.9.10: Einheitliche Aktionssteuerung

Wiederholungsregeln haben nun einen expliziten Ausführungsmodus (Pausiert, Manuell, Automatisch) statt getrennter Aktivierungsschaltflächen. Nur Admins dürfen automatisch buchen lassen. Die Benutzeraktionen werden in einem gemeinsamen Bereich „Verwalten“ gruppiert. Bestehende Zugriffsprüfungen bleiben erhalten.

### Version 1.9.11
Regelbearbeitung im Dialog und kontrollierte Regellöschung mit Erhalt bereits erzeugter Buchungen. Ein gemeinsames Docker-Anwendungsimage reduziert redundante Builds und Plattenbelegung.


### Einführung (ab 1.9.12)

Neu angelegte Benutzer werden nach der verpflichtenden 2FA-Einrichtung auf dem Dashboard einmalig durch eine kurze Einführungsrunde geführt. Sie können mit Weiter/Zurück navigieren und überspringen. Abschluss und Überspringen werden ausschließlich pro Benutzer in `users.tutorial_completed` gespeichert. Vor dem Update bestehende Benutzer behalten Ruhe: ihr Zustand wird einmalig auf abgeschlossen gesetzt. Über „Hilfe / Einführung“ in der Seitennavigation lässt sich der Rundgang jederzeit neu starten. Der Rundgang ist rollenabhängig, mobil nutzbar und verwendet keinerlei externe JavaScript-Dienste.


### Container-Reduktion (1.9.13)

Ab 1.9.13 laufen drei statt fünf Container: `financisto-dashboard-app`, `financisto-dashboard-caddy` und `financisto-dashboard-background`. Der gemeinsame, netzwerklose Hintergrunddienst führt die bisherigen Prüfungen unverändert aus: Auto-Import jede Minute, Wiederholungen alle 15 Minuten, Tagesbackup stündlich. Alle drei Aufgaben bleiben in den Einstellungen separat steuerbar. Die Umstellung entfernt ausschließlich die drei ehemaligen Container mit fest vergebenen Projektnamen. Andere Container und Docker-Images werden nicht bereinigt.

**Wichtig:** Der Financisto-Rückexport der Version 1.9.13 synchronisiert **keine im Web neu erstellten oder geänderten Wiederholungsregeln**. Die ursprünglich importierten Vorlagen verbleiben in der passenden Original-Sicherung. Bei einer Rückschaltung werden Web-Wiederholungen pausiert und nicht automatisch aufs Android-Gerät übertragen.


### Version 1.9.14: kontrollierter Rückexport von wiederkehrenden Buchungen

Im Administrationsbereich kann optional die Wiederholungssteuerung in eine Financisto-Test-`.backup` übernommen werden. Aktiv-automatische Regeln für Monats-/Quartals-/Jahrestermine werden auf das bekannte Monatsintervall abgebildet. Manuelle oder unbekannte Wiederholungsregeln blockieren den Export statt versteckt aktiviert zu werden. Die bisherige Exportfunktion ohne Wiederholungsoption bleibt verfügbar. Android-Testimport bleibt empfohlen.

### Durchlaufende Posten / Klonen (1.9.21)
Bei Web-Datenführung in der Buchungsliste auf „Klonen“ klicken. Die neue Eingabemaske übernimmt die Stammdaten, aber nicht den Betrag; das Datum ist heute.

Für fremde Geldbeträge beim Eingang und bei der späteren Auszahlung jeweils „Durchlaufender Posten“ aktivieren. Dabei wird je nach Buchungsart die Android-kompatible Kategorie „Durchlaufender Posten (Eingang)“ oder „Durchlaufender Posten (Ausgabe)“ automatisch angelegt und gewählt. Das Dashboard berücksichtigt die echten Kontobewegungen, zeigt aber diese Kategorie nicht als Haushalts-Einnahme/-Ausgabe. Dies gilt auch für Unterkategorien und nach einem Financisto-Backup-Rundlauf, solange dieselbe Kategorie im Backup erhalten bleibt. Die Android-App kann solche Beträge in ihren eigenen Berichten anders auswerten.

### Telegram-Buchungen (seit 1.9.26 direkt mit eigenem Bot)
Siehe `TELEGRAM_BOOKINGS.md` im Installationsordner. Direkt per Bot-Token und der bereits vorhandenen Finanzgruppe; kein Node-RED-Flow und kein zusätzlicher Docker-Container. Der FieLanzen-Bot darf nicht parallel durch andere Telegram-Empfänger abgefragt werden. Eine bewusste Freigabe von Gruppe und Nutzern ist erforderlich; standardmäßig deaktiviert.

Ab 1.9.29: `/finanz 24,90 Edeka | Lebensmittel | Bargeld` (Ausgabe mit Kategorie und Konto) oder `/finanz +150 Taschengeld | Ebay Direkteinzahlung` (Einnahme auf Taschengeld, Notiz). `/finanz` ohne Argumente zeigt die vollständige Hilfe im Bot. Ausgabenwarnungen werden für berechtigte neue EUR-Ausgaben ab Grenzbetrag in die Warteschlange gestellt. Der bisherige Brücken-Endpunkt aus 1.9.25 bleibt nur für alte Installationen im bisherigen Brückenmodus aktiv.


Ab 1.9.30: Unter Einstellungen → Standardkonto für neue Buchungen werden Web-Standardkonto und eine zentrale Ausgaben-Standardkategorie gewählt; die Kategorie gilt auch für Telegram.
