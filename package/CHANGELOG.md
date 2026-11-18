## 1.9.58-dev.5 – Empfängerfeld bei neuen Buchungen (18.11.2026)
- Vorhandener Empfänger wird beim Antippen/Fokussieren markiert und durch direkte Texteingabe ersetzt, wie bereits bei der Kategorie.
- Bereits begonnene eigene Suchtexte bleiben während der Eingabe editierbar; die Empfänger-Vorschläge funktionieren weiterhin.
- Keine Änderungen an Datenbank, gespeicherten Buchungen und Bind-Mounts.

## 1.9.58-dev.4 – Buchungszeilen, manuelle Doppel-Sicherung und ausführbares Updatepaket (18.11.2026)
- „Jetzt Sicherung erstellen“ erstellt unabhängig voneinander eine manuelle SQLite-Sicherung und einen neuen Financisto-Export des aktuellen Web-Datenbestands und meldet die beiden Resultate einzeln.
- Umbuchungen über die gesamte Tabellenzeile hellblau hervorgehoben.
- Wiederkehrende Buchungen über die gesamte Zeile mintgrün markiert; wiederkehrende Umbuchungen in einem eigenen Violettton.
- Zukünftige Buchungen behalten ihre gelbe Markierung mit Vorrang vor anderen Kennzeichnungen.
- Die Hervorhebung gilt auch für die kompakte Buchungsliste auf mobilen Geräten.
- ZIP enthält `update.sh` mit ausführbaren Dateirechten, damit der gewohnte Update-Befehl funktioniert.
- Keine Änderung an Buchungslogik, Kontoständen, Datenbank oder Bind-Mounts.

## 1.9.58-dev.3 – Zwei aktuelle Financisto-Rückexport-Sicherungen (18.11.2026)
- Täglich zusätzlich zur SQLite-Sicherung ein validierter Export des aktuellen Web-Datenbestandes als `.backup`.
- Es bleiben die letzten zwei erfolgreichen Exportversionen unter `data/financisto-backups/`; Download nur durch Administratoren unter Einstellungen.
- Nutzt den bestehenden Standard-Rückexport ohne optionale Web-Wiederholungsregeln; bei fehlender Exportgrundlage wird nichts Falsches gespeichert, die SQLite-Sicherung läuft unabhängig weiter.
- Keine Löschung von Buchungen, keine Änderungen an den bestehenden Android-Importarchiven, Bind-Mounts oder Secrets.

## 1.9.58-dev.2 – CSV-Export kompakt und englische Texte (18.11.2026)
- CSV-Export-Schaltfläche direkt neben der Seitennavigation, ohne zusätzliche Zeile am Desktop.
- Englische Übersetzungen für Seitenzählung, CSV-Export und Kontostand nach der Buchung ergänzt.
- Weiterhin Entwicklungsstand ohne offizielles Release. Finanzdaten und Bind-Mounts bleiben unverändert.

## 1.9.58-dev.1 – CSV-Export der Dashboard-Buchungsliste (Entwicklungsstand, 18.11.2026)
- CSV-Export direkt unter der Dashboard-Buchungsliste, inkl. aller Seiten des aktuell gefilterten und sortierten Zeitraums.
- Datum, Buchungsart, Quell-/Zielkonto, Kategorie, Empfänger, Notiz, Betrag, Währung, Wiederholung und Kontostand danach.
- Excel-kompatibel: UTF-8-BOM, Semikolon und deutsches Dezimalkomma; Text wird gegen Formelausführung abgesichert.
- Nur lesend, keine Änderung an Buchungen, Datenbank oder Bind-Mounts.
- Kein offizielles Release: Entwicklungszweig, vorläufige Version.

## 1.9.57 – Wiederkehrende Buchungen und aufgeräumte Dokumentation (18.11.2026)
- Bei neuen wiederkehrenden Regeln entspricht der vorausgefüllte „Tag im Monat“ automatisch dem Startdatum. Wird das Startdatum geändert, folgt der Monatstag, bis dieser bewusst separat verändert wird.
- Bei täglicher und wöchentlicher Wiederholung ist das nicht benötigte Monatstagsfeld ausgeblendet; monatliche, vierteljährliche und jährliche Regeln lassen eine freie Abweichung zu.
- Bestehende gespeicherte Regeln, Termine und Buchungen bleiben unverändert.
- GitHub-READMEs enthalten keine veralteten Releaseblöcke und keinen lokalen Teststand 1.9.48 mehr. Änderungen werden in den Releases und Changelogs dokumentiert.
- Anwendung und Docker-Image-Versionen sind konsistent 1.9.57; vorhandene Bind-Mounts, Datenbank und Secrets bleiben erhalten.

## 1.9.56 – Kategoriefeld und Docker-Image-Version (17.11.2026)
- Die vorausgewählte Kategorie wird beim Antippen/Fokussieren zum direkten Überschreiben markiert; Tipp-Eingaben hängen sich nicht mehr an den vorhandenen Text an.
- Alle drei Anwendungsdienste verwenden wieder einen zur VERSION passenden Docker-Image-Tag (1.9.56).
- Updates und GitHub-Release-Build prüfen die Übereinstimmung der Image-Tags vor dem Ausrollen.
- Unveränderte Bind-Mounts, Finanzdaten, Secrets und Einstellungen; SQLite-Sicherung vor dem Update.

## 1.9.54 – Buchungsliste, Wiederholungen und Filter (17.11.2026)
- Zukunftsmarkierung färbt jetzt die vollständige Tabellenzeile einschließlich der Aktionsspalte bündig ein.
- Als wiederkehrend erkannte Buchungen werden in Dashboard und Buchungsliste zusätzlich gekennzeichnet. Die Kennzeichnung wird aus bestehenden `recurring_runs` abgeleitet; es werden keine Buchungen geändert.
- Schnellsuche in der Buchungsliste immer direkt sichtbar, kompakt neben bzw. unter den Zeitraum-Schaltflächen; „Erweitert“ öffnet weiterhin die vorhandenen Monats-, Konto- und Kategoriefilter.
- Verzögerung der automatischen Schnellsuche von 5 auf 4 Sekunden gesenkt; Suchen/Enter bleiben unmittelbar.
- Wiederkehrende Buchungsregeln: freie Eingabe neuer Empfänger mit der gleichen kompakten Smartphone-Vorschlagsliste; der Empfänger wird erst beim Speichern der Regel atomar angelegt. Bestehende Empfänger werden über ihren Namen wiederverwendet.
- Keine Änderungen an bestehenden Finanzdaten, Buchungsalgorithmen, Imports oder Zertifikaten. Upgrade mit `update.sh` und vorheriger SQLite-Sicherung.

## 1.9.53 – Empfängervorschläge direkt beim Antippen (16.11.2026)
- Beim Antippen oder Fokussieren des Empfängerfelds werden bekannte Empfänger nun sofort alphabetisch angezeigt, auch ohne Suchtext – analog zur Kategorieauswahl.
- Während der Eingabe wird weiterhin nach passenden Empfängern gefiltert; durch erneutes Antippen kann die vollständige Vorschlagsliste wieder geöffnet werden.
- Die gemeinsame Admin-Einstellung für die maximale Anzahl von Empfänger- und Kategorienvorschlägen (1–100, Standard 20) bleibt erhalten. Die Liste ist mobil kompakt und scrollbar.
- Frei eingegebene neue Empfänger, bestehende Buchungen, Finanzdaten, Import/Export, Datenbankschema und Benutzerrechte bleiben unverändert.

## 1.9.52 – Admin-Einstellung für Vorschlagsanzahl (16.11.2026)
- Empfänger- und Kategorienvorschläge sind auf maximal 20 statt 8 Einträge voreingestellt.
- Administratoren können unter **Einstellungen → Buchungsliste** die Höchstanzahl gemeinsam für beide Listen auf 1–100 einstellen; ohne Deployment oder Neustart. Gilt für alle Benutzer.
- Einstellung wird persistent im vorhandenen SQLite-Metadatenspeicher gehalten und beim Update nicht überschrieben. Bestehende Buchungen, Kategorie-IDs, Empfänger und Zugangsdaten bleiben erhalten.
- Smartphone-Listen bleiben maximal 236 px hoch und scrollbar; Bedienung per Tastatur/Touchscreen bleibt erhalten.

## 1.9.51 – Suchbare, mobile Kategorieauswahl und 5-Sekunden-Suchpause (16.11.2026)
- Die Kategorieauswahl verwendet eine eigene, kompakte und durchsuchbare Liste statt des geräteabhängigen, bildschirmfüllenden Android-Select-Dialogs. Höchstens acht passende Kategorien werden angezeigt; Haupt- und Unterkategorien behalten ihre Bezeichnung.
- Der bisherige Select-Wert und die originale Kategorie-ID bleiben das einzige gesendete Formularfeld. Neue Kategorien, Editieren/Klonen, Wechsel von Ausgabe zu Einnahme und Umbuchungen bleiben kompatibel. Ohne JavaScript steht weiterhin die native Auswahl zur Verfügung.
- Der automatische Dashboard-Schnellfilter wird erst fünf Sekunden nach der letzten Eingabe ausgelöst (zuvor 650 Millisekunden); manuelles Suchen oder Enter löst die Suche unverzüglich aus.
- Keine Änderung an Finanzdaten, Datenbankschema, Import/Export oder Serverzugriff. GitHub-Veröffentlichung mit Freigabe des Auftraggebers.

## 1.9.50 – Mobile Empfängervorschläge ohne Browser-Popup (16.11.2026)
- Die native HTML-datalist für bekannte Empfänger wurde durch eine eigene, kompakte Vorschlagsliste ersetzt, um übergroße und durchscheinende Auswahlfenster auf Android-Geräten zu vermeiden.
- Vorschläge bleiben an das Eingabefeld gebunden, zeigen maximal acht Treffer und öffnen sich bei wenig Platz oberhalb der Bildschirmtastatur.
- Beliebige neue Empfänger können weiterhin frei eingetragen werden; bestehende Formulardaten und Buchungslogik bleiben unverändert.
- Tastaturbedienung über Pfeiltasten, Enter, Escape; keine externen Dienste.

## 1.9.49 – Sammelrelease seit dem letzten GitHub-Release v1.9.43 (16.11.2026)
- **Englischübersetzung (v1.9.44–1.9.49):** Viele bisher gemischte Beschriftungen und erklärende Texte in Dashboard, historischer Auswertung, Kontenverwaltung, Import, A5-/A4-Berichten, Einstellungen, Benachrichtigungen, Web Push, Systemstatus, Telegram, Gotify und Financisto-Rückexport korrigiert. Zahlen, Monate und zusammengesetzte Sätze werden lokal übersetzt. Eigene Kategorien, Konten, Empfänger und Notizen bleiben unverändert.
- **Letzte Übersetzungskorrektur (v1.9.49):** Die Warnung über wiederkehrende Web-Regeln beim Wechsel zurück zu Financisto wird im englischen Modus vollständig englisch ausgegeben. Das Bestätigungsfeld heißt „Enter FINANCISTO to confirm“; das erforderliche Bestätigungswort bleibt technisch weiterhin exakt `FINANCISTO`.
- **Cashflow (seit v1.9.45):** Neue Einnahmen-/Ausgabenbalken mit Netto-Linie und erklärter gestrichelter Linie; Abstimmung der Farben mit den Kategorieauswertungen, korrigierte Achsen-/Linienausrichtung und mobiles Scrollverhalten. Umbuchungen, durchlaufende Posten, Abgleiche und künftige Buchungen bleiben aus dem realisierten Cashflow ausgeschlossen.
- **Zeiträume und Filter (v1.9.45):** Schnellfilter 1 Woche, 1/3/6 Monate für die Buchungsliste und separat aufrufbare ausführliche Suche; bestehender Zwei-Monats-Vergleich und Monatsfilter bleiben erhalten.
- **Dashboard-Struktur (v1.9.46–1.9.47):** Kontostände → Buchungen → Ausgaben nach Kategorien → Cashflow. Buchungen sind beim Laden standardmäßig geöffnet, Cashflow geschlossen. Buchungslisten können zu- und aufgeklappt werden; Links öffnen die passende Sektion.
- **Seitennavigation und Aktionen (v1.9.45–1.9.46):** Direkte anklickbare Seitennummern sowie Zurück/Weiter; kompakte nebeneinander stehende Schaltflächen Klonen, Bearbeiten und Löschen am Desktop.
- **Haushaltsberichte und Fußzeile (v1.9.48):** Feste Beschriftungen des A5-Berichts und weitere englische Import-/Kontotexte ergänzt. Fußzeilen sind über die bestehende `.env` getrennt einstellbar: `APP_FOOTER` (Deutsch) und optional `APP_FOOTER_EN` (Englisch). Vorhandene Werte bleiben beim Upgrade erhalten.
- **Sicherheit / Kompatibilität:** Keine Änderung an Buchungs- und Importlogik, Kontostandsberechnung, Finanzdaten, SQLite-Datenbankschema, Benutzerkonten, 2FA, Caddy-Zertifikaten und Zugriffsrechten. Die unveränderte Funktion zum manuellen Financisto-`.backup`-Import bleibt erhalten.
- **Upgrade:** Komplett-ZIP inklusive `update.sh`; direkt von v1.9.43 bis v1.9.48 auf v1.9.49. Vor Ausführung sichert das Update-Skript die bestehende SQLite-Datenbank, Quellcode und `.env`.

## 1.9.48 – Lokale Testversion: englische Texte und konfigurierbare Fußzeilen (16.11.2026)
- Englische Beschriftungen für Konten, Kontostands-Sortierhinweis und Importerklärung vollständig gemacht.
- A5-Haushaltsbericht mit sprachabhängigen festen Überschriften, Summen und Quellenhinweisen; eigene Kategorien und Buchungsnotizen bleiben unverändert.
- Fußzeile bleibt über APP_FOOTER in .env anpassbar, APP_FOOTER_EN ermöglicht optional eine eigene englische Fußzeile; alte Werte werden beibehalten.
- Keine Änderung an Finanzdaten, Buchungslogik, Benutzerkonten oder Caddy.

## 1.9.47 – Aufklappzustände und englische Oberfläche (lokale Testversion, 16.11.2026)
- Dashboard: Buchungsliste ist beim Laden standardmäßig geöffnet, Cashflow standardmäßig geschlossen. Direkte Links auf beide Bereiche öffnen den jeweiligen Abschnitt.
- Zusätzliche lokale Englischübersetzungen für Buchungszusammenfassungen, wiederkehrende Buchungen, Push-Benachrichtigungen, Systemstatus/Hintergrunddienst, öffentlichen Zugriff, Telegram, Gotify, Rückexport nach Financisto und Stammdaten.
- Dynamische Texte mit Anzahl, Datumswerten und geschützten Bestätigungswörtern werden gezielt übersetzt; personenbezogene Bezeichnungen und Finanzdaten bleiben unverändert.
- Keine Änderungen an Buchungslogik, Finanzdaten, Datenbankstruktur oder Docker-Diensten. Keine GitHub-Veröffentlichung ohne ausdrückliche Freigabe.

## 1.9.46 – Dashboard-Reihenfolge, Seitenzahlen und Cashflow-Ausrichtung (16.11.2026)
- Buchungsliste direkt nach den Kontoständen, standardmäßig einklappbar; Aufruf über Buchungslinks sowie Seitenzahlen öffnet sie automatisch.
- Direkte Seitenauswahl mit Seitenzahlen, Auslassungszeichen und Zurück/Weiter; Zeitraum- und Suchfilter bleiben erhalten.
- Darunter Kategorienauswertung und Cashflow in der bisherigen Funktion.
- Cashflow-Balkenfarben an die Farbpalette der Monats-/Kategorieauswertung angeglichen (Türkis/Orange). Die Netto-Linie ist dunkel gestrichelt und wird in der Hilfe erklärt (separate Nulllinie, kein Kontostand).
- Die SVG-Linie liegt nun auf demselben Raster wie die Balken; die Drei-Monats-Ansicht bleibt ausgerichtet. Mobile Diagramme sind bei Bedarf horizontal scrollbar.
- Nur Anzeige, Layout und Hilfe geändert. Kein Datenbank- oder Buchungsverhalten geändert. Lokale Testversion – kein GitHub-Upload.

## 1.9.45 – Cashflow, Schnellfilter, kompakte Buchungsaktionen und Übersetzungen (16.11.2026)
- Auf dem Dashboard gibt es separate Zeitraum-Schnellfilter 1W, 1M, 3M und 6M für die Buchungsliste; die vorhandene Zwei-Monats-Auswertung und erweiterten Filter bleiben erhalten.
- Der Suchfilter liegt platzsparend hinter einer eigenen Filter-Schaltfläche, statt ständig als lange Zeile angezeigt zu werden.
- Neues lokales Cashflow-Balkendiagramm mit Einnahmen, Ausgaben und Netto des ausgewählten Zeitraums; Umbuchungen, durchlaufende Posten, Saldoabgleiche und zukünftige Buchungsdaten zählen nicht als realisierter Cashflow. Bestehende Kontostände werden nicht neu berechnet.
- Klonen, Bearbeiten und Löschen in der Desktop-Tabelle deutlich kleiner und nebeneinander, ohne Zeilenumbruch. Smartphone-Karten bleiben berührungsfreundlich.
- Erweiterte englische Übersetzungen, besonders für historische Auswertungen, Haushaltsbericht, Import und dynamische Zeiträume; Dateiauswahl mit lokal übersetzten Bedienelementen.
- Keine Änderung am Datenbankschema, an Finanzdaten, an wiederkehrenden Buchungen oder den Import-/Exportformaten.

## 1.9.44 – Englischübersetzung der Oberfläche vervollständigt (16.11.2026)
- Fehlende Übersetzungen insbesondere im Dashboard ergänzt: Importstatus, Monatsvergleich, Buchungsanzahl, Sortierhinweise, Schnellfilter und Suchfeld.
- Zusammengesetzte Texte mit Zahlen, Monatsnamen, Datumsangaben und Statuswerten werden anhand gezielter Muster lokal übersetzt; sensible Finanzdaten bleiben unverändert.
- Zusätzlich feste Beschriftungen, Hilfetexte und Statusmeldungen in Import, Berichten, Wiederholungsregeln und Einstellungen erweitert.
- Keine Änderung an Finanzdaten, Buchungs-/Importlogik, Datenbank, Benutzerrechten, 2FA, Caddy oder Docker-Netzwerken.
- Das Paket ist zunächst lokal bereitgestellt, keine automatische GitHub-Veröffentlichung.

## 1.9.43 – Englische Anmeldung vervollständigt und Dashboard-Aktionen kompakt (16.11.2026)
- Auf der 2FA-Bestätigungsseite ist der Erklärungssatz nun vollständig englisch, ohne den Benutzernamen zu verändern.
- Auch 2FA-Einrichtung, QR-Code-Anleitung, Wiederherstellungscodes und Passwortänderung sind auf Englisch ergänzt.
- Die drei Dashboard-Aktionen rechts stehen auf Desktop und Tablet nebeneinander; die Importinformation steht kompakt darunter. Auf Smartphones bleibt das bisherige responsive Layout erhalten.
- Keine Änderungen an Buchungen, Benutzerkonten, 2FA-Geheimnissen, Datenbank, Import oder Caddy-Zertifikaten.

## 1.9.42 – Aktualisierte zweisprachige Einführung (16.11.2026)
- Einführungsrundgang auf den Funktionsstand 1.9.41 gebracht, vollständig auf Deutsch und Englisch mit lokaler Sprachauswahl.
- Erläutert jetzt Kontostände, zukünftige Buchungen (gelb und sofort saldo-wirksam), Empfänger/Kategorie, Wiederholungen mit Enddatum oder maximaler Ausführungszahl, Import-/Datenführungsmodus sowie DE/EN-Umschaltung.
- Rechteabhängige Hinweise für Administratoren, Bearbeiter und Benutzer mit Leserechten; keine unberechtigten Funktionen versprochen.
- Erstmalige automatische Einführung nur für neue Benutzer, deren Einführung noch nicht abgeschlossen ist; bestehende Nutzer werden nicht erneut gestört.
- Hilfe / Einführung bleibt jederzeit manuell aufrufbar, inklusive Zurück, Weiter, Überspringen und Abschluss.
- Keine Änderungen an Finanzdaten, Datenbank, Buchungs-/Importlogik, Secrets oder Caddy-Zertifikaten.

## 1.9.41 – Formularraster auf Desktop und Tablet korrigiert (15.11.2026)
- Buchungserfassung: Empfänger und Kategorie stehen auf PC und Tablets wieder in derselben Zeile (Empfänger links, Kategorie rechts), passend zur bereits korrekten Reihenfolge der Felder.
- Bei Umbuchungen bleiben Zielkonto und Empfänger auf großen Bildschirmen nebeneinander; die Smartphone-Darstellung bleibt unverändert untereinander.
- Reine CSS-Korrektur. Keine Änderung an Buchungsdaten, Formularnamen, Wiederholungsregeln, Import, Authentifizierung oder Caddy.

## 1.9.40 – Wiederholungsgrenzen und Hervorhebung zukünftiger Buchungen (15.11.2026)
- Eingabemaske: Empfänger steht auf Mobilgeräten und am Desktop vor der Kategorie; Tastaturreihenfolge entsprechend angepasst.
- Wiederkehrende Buchungen: Optionales inklusives Enddatum und/oder maximale Anzahl tatsächlicher Ausführungen. Sobald die erste Grenze erreicht wird, endet die automatische/manuelle Regel. Vorhandene Regeln bleiben unbegrenzt; bereits ausgeführte Termine zählen zum Maximum, vorhandene Buchungen werden niemals gelöscht.
- Buchungen mit zukünftigem Datum erscheinen gelb und mit Hinweis in Dashboard-Tabellen, kompakten mobilen Karten und Web-Buchungsliste, bis das Datum erreicht ist (bei erneutem Laden der Seite). Nur die Darstellung ändert sich, nicht die Kontostandsberechnung.
- Sprachübersetzungen der neuen Bedienelemente ergänzt. Keine Änderungen an Authentifizierung, Import, Secrets oder Caddy-CA.

## 1.9.39 – Deutsche und englische Weboberfläche und Installation (15.11.2026)
- Bisherige deutschsprachige Oberfläche erhält vollständige lokale Übersetzungstabellen für Navigation, Formulare, Berichte, Einstellungen und zentrale Systemmeldungen.
- Umschalter DE / EN bereits bei der Anmeldung, auf Mobilgeräten und in der Desktop-Seitenleiste; die Wahl gilt pro Sitzung und ist jederzeit änderbar.
- Installer fragt bei der Neuinstallation zweisprachig nach Deutsch/Englisch und verwendet die gewählte Sprache für Einrichtungsdialoge. Die Installationsvorgabe wird in der lokalen .env als DEFAULT_LANGUAGE gespeichert.
- Keine externe Übersetzungs-API, keine Migration der Finanzdaten, keine dauerhafte Speicherung der individuellen Sprachwahl.
- Ergänzte zweisprachige Installations-, Sprach- und Release-Dokumentation. Einzelne seltene ältere Diagnosemeldungen können weiterhin deutsch erscheinen.
- Direkter Updatepfad von v1.9.35 auf v1.9.39, ohne Zwischenversion.

## 1.9.38 – Direkter Versionssprung und Caddy-Dokumentation (15.11.2026)
- Fehler in der Update-Vorprüfung behoben: Die Prüfung verwendet die Versionsnummer aus `package/VERSION` statt des früher hart codierten Wertes 1.9.36.
- Direkter Updatepfad von v1.9.35 auf v1.9.38, ohne v1.9.36 oder v1.9.37 dazwischen zu installieren.
- Integrierten Caddy-Dienst mit HTTPS, eigener lokaler CA, optionaler Nginx-Proxy-Manager-Anbindung, .env-Konfiguration und dauerhaft gespeicherten Zertifikaten in englischer und deutscher Anleitung dokumentiert.
- Das bestehende Caddy-/Finanzdaten-Verzeichnis, Zertifikate, Benutzerkonten, Import und Buchungslogik werden durch diese Korrektur nicht verändert.

## 1.9.37 – Bereinigtes öffentliches Release und zweisprachige GitHub-Dokumentation (15.11.2026)
- GitHub-Startseite vollständig auf Englisch, zusätzliche deutsche README und Sprachlinks.
- Englische Installations-/Betriebsanleitung; bestehende ausführliche deutsche Anleitung bleibt erhalten.
- Datenschutzbereinigte Screenshots in der Projektbeschreibung.
- Private Hostnamen und interne IP-Adressen aus veröffentlichten Beispielen/Standardwerten entfernt; produktive Werte in der vorhandenen .env werden beim Update beibehalten.
- Englische und deutsche Release-Hinweise sowie vollständiges ZIP mit SHA256-Prüfsumme.
- Keine Änderungen an Finanzdaten, Buchungslogik, Importarten, Benutzerkonten oder Secrets.

## 1.9.36 – Kompakte Dashboard-Buchungsliste (14.11.2026)
- Smartphone- und Tablet-Ansicht: kurze Buchungszeilen mit Betrag, Datum, Buchungstext und Konto; Details erst auf Fingertipp.
- Ausklappdetails enthalten Kategorie, Empfänger, Notiz, Kontostand nach Buchung und bei Umbuchungen Quell- und Zielkonto.
- Klonen, Bearbeiten und Löschen erscheinen innerhalb der aufgeklappten Buchung nur für berechtigte Benutzer.
- Tablet-Querformat: Anstelle der horizontal scrollbareren Tabelle wird die kompakte, sortierbare Liste gezeigt.
- Keine Änderungen an Buchungsdaten, Finanzführung, Push, Telegram, Gotify oder Import.

## 1.9.35 (2026-11-13)
- Die Dashboard-Buchungsliste zeigt jetzt auch Umbuchungen (einschließlich automatisch erzeugter wiederkehrender Umbuchungen) mit Quell- und Zielkonto.
- Konto-Filter der Buchungsliste berücksichtigen Quell- und Zielkonto. Die Diagramme und Einnahmen-/Ausgabensummen bleiben unverändert und schließen Umbuchungen weiterhin aus.
- Buchungs-Kontostand bei Umbuchungen ist ausdrücklich als Saldo des Quellkontos gekennzeichnet. Kein Eingriff in vorhandene Finanzdaten.
- Wiederkehrende automatische Buchungen erhalten eine optionale lokale Ausführungsuhrzeit (Europe/Berlin, ab HH:MM, Prüfung alle 15 Minuten). Vorhandene Regeln bleiben bei 00:00; manuelle Buchungen sind davon unabhängig.

## 1.9.34 (2026-11-13)
- Persönliche Web-Push-Einstellungen pro Benutzer: Ausgaben ab individuellem Grenzwert, Einnahmen optional, Meldungsdetails (privat, Betrag, ausführlich).
- Push unabhängig von Gotify-/Telegram-Grenzen; neue Web-/Telegram-/wiederkehrende Buchungen berücksichtigt.
- Bestehende Push-Abonnements werden beibehalten; keine Änderungen an Importen oder Tokens.

## 1.9.33 (2026-11-13)

- Versionsanzeige im Dashboard wird ab jetzt aus `VERSION` gelesen statt im Quellcode fest hinterlegt.
- `VERSION` wird mit dem Python-Code ins Docker-Image aufgenommen.
- Browser-Asset-Versionen werden aus demselben Wert abgeleitet; alte CSS/JS-URLs werden aktualisiert.
- Keine Änderungen an Datenbank, Import, Finanzdaten, Benachrichtigungen oder Rechteverwaltung.

## 1.9.32 (2026-11-13)

- Serverstruktur: Python-Dateien nach `src/`, Anleitungen nach `docs/`.
- Docker kopiert den Python-Code weiterhin nach `/app`; Containerstartpfade bleiben unverändert.
- Update-Skript auf neue Host-Pfade angepasst; SQLite, Tokens, Secrets und Backups unverändert.
- Installations- und Verwaltungsaufgaben auf `src/setup_secrets.py` umgestellt.

## 1.9.31 – PWA-Symbol und persönliche Web-Push-Benachrichtigungen

- Originales SEA-WOLVES-Logo als kreisrundes transparentes PWA-Icon mit sicherem Android-Maskierabstand.
- Web Push für Android Chrome/PWA und kompatible Desktop-Browser, je Gerät und Benutzer per ausdrücklichem Opt-in.
- Eigener VAPID-Schlüssel, verschlüsselt in bestehender DB; Ausgabengrenze aus vorhandenen Warnungseinstellungen.
- Bestehender Notifications-Container versendet Push mit generischem, datensparsamem Text. Kein zusätzlicher Docker-Container.
- Kein Offline-Cache für Finanzdaten und keine Veränderungen der Import- oder Buchungslogik.

## 1.9.30 – Gemeinsame Standardkategorie (13.11.2026)
- Einstellungen → Standardkonto für neue Buchungen: gemeinsame Ausgabenkategorie für Web und Telegram.
- Beim Update Übernahme einer bisherigen expliziten Telegram-Standardkategorie; falls nicht festgelegt, wird eine vorhandene eindeutig benannte Kategorie „Einkauf“ vorausgewählt.
- Bearbeiten/Klonen vorhandener Buchungen bleibt unverändert. Ohne Standardkategorie werden keine Kategorien automatisch erzeugt.

## 1.9.29 – Kompaktere Buchungseingabe (13.11.2026)

- Buchungsart und Konto in einer Zeile, danach Betrag und Datum.
- Kategorie, Empfänger und Notiz folgen ohne dazwischenliegende Zusatzfelder.
- „Durchlaufender Posten“ und Kategorie-Neuanlage in einem optionalen Aufklappbereich.
- Smartphone: wichtige Felder bleiben groß und gut bedienbar, zwei Spalten nur bei passenden Eingaben.
- Unveränderte Formularnamen, serverseitige Validierung, Buchungen, 2FA, Import und Telegram.

## 1.9.28 – Telegram-Buchungssyntax und echte Ausgabenwarnungen
- Telegram-Ausgabe: `/finanz BETRAG EMPFÄNGER | KATEGORIE | KONTO | optionale Notiz`.
- Telegram-Einnahme: `/finanz +BETRAG KONTO | optionale Notiz`, z. B. `+150 Taschengeld | Ebay Direkteinzahlung`.
- `/finanz` ohne Argumente gibt aktuelle Hilfe aus. Standardkategorie bei Ausgaben ist Einkauf, sofern keine andere Standardkategorie konfiguriert ist. Einnahmen bekommen keine Ausgabenkategorie.
- Ausgabenwarnungen zentral und nachvollziehbar geprüft: neuer Web-Buchungsvorgang zeigt Grund bei unterdrückter Warnung oder Anzahl vorgemerkter Versandaufträge. Neue wiederkehrende Ausgaben werden ebenfalls berücksichtigt, keine Warnung beim Import, Bearbeiten, Umbuchen oder bei neutralen Buchungen. Alte Buchungen bleiben unverändert.
- Keine zusätzlichen Docker-Container, keine Änderungen an `.env`, Secrets, Import-Schnittstellen oder PWA.

## 1.9.27 – Installierbare Android-PWA
- PWA-Manifest und aus bestehendem Wolfslogo generierte 192/512-Pixel-Icons.
- Android-Installation im Standalone-Fenster.
- Netzwerkorientierter Service Worker ohne Cache für Finanzdaten.
- Keine Änderungen an Import, Telegram, Gotify, Konten oder Benutzerrechten.

## 1.9.26 – Eigener Telegram-Bot, direkter Gruppenempfang
- Telegram-Finanzbuchungen direkt per Telegram getUpdates, ohne Node-RED und ohne weiteren Container.
- Gruppen- und Benutzerfreigabe, sichere Token-Aufbewahrung, `/finanzid` für Chat- und Nutzer-ID.
- Wählbar: automatische Buchung oder Bestätigung per Inline-Schaltfläche.
- Vorhandene Finanz-/Importdaten bleiben unverändert. Benachrichtigungen lassen sich unabhängig konfigurieren.

## 1.9.25 – Telegram-Buchungen und getrennte Benachrichtigungseinstellungen (13.11.2026)
- Einstellungen: Telegram-Buchungen und Ausgabenbenachrichtigungen standardmäßig zugeklappt, Aktiv-Status bleibt sichtbar; nach Speichern wird der entsprechende Bereich automatisch geöffnet.

- **Telegram-Buchungen:** Neue private Node-RED-Brücke für `/finanz 24,90 Edeka`, Buchungsvorschläge mit Konto-/Kategorieauswahl und expliziter Bestätigung. Nur freigegebene Telegram-Benutzer; keine Buchung ohne Bestätigung, kein zweiter Bot-Empfänger.
- **Doppelte Buchungen verhindert:** Nachrichten-IDs und Zustandsverwaltung in SQLite schützen die bestätigten Vorschläge bei erneutem Callback; ausstehende Vorschläge laufen nach 30 Minuten ab.
- **Gotify-/Telegram-Einstellungen getrennt:** Jeder Versandkanal wird unabhängig gespeichert. Bot-Token bleiben bei leerer Eingabe erhalten; Telegram erfordert keine Gotify-Konfiguration mehr. Der Ausgaben-Grenzbetrag wird separat gepflegt.
- **Bestehende Installation erhalten:** Alle vier Container, Datenbank, Import, Backup, Benutzerkonten und Finanzdaten bleiben bestehen. Auf dem Livesystem vor Aktivierung testen.

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

## 1.9.21 — Buchungen klonen und durchlaufende Posten

- Klonen in der Dashboard-Buchungsliste und in „Buchungen erfassen“; neues Datum ist heute und Betrag leer. Funktion nur bei Web-Datenführung und Schreibberechtigung. Original wird niemals verändert.
- Option „Durchlaufender Posten“ für Ein-/Ausgaben: dedizierte Financisto-kompatible Kategorie, reale Kontostandsänderung, aber Ausschluss von Einnahmen/Ausgaben, Kategorien, Diagrammen, Durchschnittswerten und Monats-Druckberichten des Dashboards.
- Als reguläre Kategorie bleibt die Kennzeichnung durch .backup-Export/Reimport nachvollziehbar. Die eigenständigen Android-Statistiken werden dadurch nicht geändert.
- Keine zusätzlichen Container; bestehende Buchungen und Daten bleiben unangetastet.

## 1.9.20 – Mobile-Feintuning (05.11.2026)

- Feste Daumen-Navigation am unteren Rand: Übersicht, Buchung (mit Rechten) bzw. Regeln, Historie und Mehr. Das bestehende Hauptmenü bleibt über Mehr erreichbar und schließbar.
- Mobile Buchungslisten als lesbare Karten statt seitlichem Scrollen; Datum, Betrag, Saldo, Empfänger und weitere Felder klar angeordnet. Sortieren weiterhin über eigenen aufklappbaren Bereich.
- Web-Buchungen und Benutzerverwaltung ebenfalls in mobile Karten umgestellt; Aktionen und Bestätigungen bleiben erhalten.
- Optimierte Touch-Flächen (mind. 44 px), Schriftgröße in Eingabefeldern und Formulare; reduziert automatisches Zoomen bei Fokus.
- Kompaktere Kopfzeilen, Kennzahlen, Filter, Diagramme, Pagination und Dialoge auf dem Smartphone.
- Screenreader-Navigation, aria-current und zugänglicher Sprung zum Hauptinhalt; bestehendes Onboarding bleibt vorhanden.
- Verbesserungen gelten nur für schmale Bildschirme; A4/A5-Druckausgaben, Geschäftslogik, Datenbank, Import/Export, 2FA und drei Docker-Dienste unverändert.

## 1.9.19 – Historische Auswertung kompakter (05.11.2026)

- Filterbereich der historischen Auswertung standardmäßig zugeklappt; per Tastatur und Touch bedienbar.
- Zusammenfassung zeigt immer den gewählten Zeitraum, die Währung und aktive Konto-/Kategorie-/Suchfilter.
- Nach dem Auswerten direkt zu Kennzahlen/Diagrammen; Filter bleiben erhalten und mit dem Dashboard synchron.
- Direkte Links zu Filterankern öffnen die Sektion automatisch.
- Smartphone: kompakter Filterkopf, unverändert volle Funktion bei aufgeklappter Ansicht.
- Keine Änderungen an Finanzdaten, Authentifizierung, Import oder Docker-Diensten.

## 1.9.18 – Konfigurierbare Titel und Fußzeile (05.11.2026)

- APP_TITLE, APP_SUBTITLE und APP_FOOTER werden über die bestehende .env konfiguriert.
- Auf Anmelde-/2FA-Seiten, im Desktop-Menü, in mobiler Kopfzeile und Browser-Titeln konsistent.
- Fehlende Einträge werden beim Update einmalig ergänzt; vorhandene Werte bleiben erhalten.
- Die Fußzeile und der Hinweis im linken Menü nutzen denselben konfigurierten Text.
- Keine Änderung an SQLite, Authentifizierung, Hintergrunddienst oder Containerzahl.

## 1.9.17 – Sea-Wolves-Design (05.11.2026)
- Einheitliche Gestaltung im Stil der zuvor erstellten Sea-Wolves-NPM-Fehlerseiten.
- Original-Wolf-Logo und Favicon aus den bereitgestellten Fehlerseiten als lokale Assets.
- Helle Navigation, anthrazitfarbene Texte, goldene Akzentlinien, dezentes Wasserzeichen im Hintergrund.
- Responsive Desktop- und Smartphone-Darstellung, weiterhin barrierearme Tastaturfokussierung.
- Tabellenwerte, Ausgaben-/Einnahmen-Farbgebung und Druckansichten bleiben gut lesbar.
- Nur Templates und CSS/Assets geändert; keine Migration der Datenbank, keine neuen Container.

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

## Version 1.9.14 (04.11.2026)

- Kontrollierter Rückexport der Web-Dauerbuchungen in Financisto-Test-Backups: aktualisierte und neue Vorlagen, sichere ID-Zuordnung.
- Pausierte und archivierte Vorlagen nicht mehr als aktive Android-Vorlagen übertragen.
- Schutz vor versehentlicher Automatik bei manuell aktiven Regeln und nicht sicher codierbaren Intervallen.
- Ursprünglicher Rückexport ohne Regeländerung weiterhin wählbar.
- Updateskript entfernt die drei alten Hintergrundcontainer vor dem Start der aktuellen Compose-Dienste. Orphan-Warnung beim Image-Test wird unterdrückt, ohne fremde Container zu entfernen.
- Wiederherstellungsskript stoppt/startet jetzt die beiden SQLite-schreibenden Dienste (Dashboard und background), statt veraltete Service-Namen zu verwenden.
- Weiterhin nur drei Laufzeitdienste; keine zusätzlichen Volumes, Secrets oder Container.

## Version 1.9.13 (04.11.2026)

- Drei statt fünf laufende Container: Dashboard, Caddy und ein netzwerkloser Hintergrunddienst.
- Auto-Import, wiederkehrende Buchungen und Tagesbackups behalten ihre Intervalle und getrennten Fehlerbehandlungen.
- Aktualisierung beendet und entfernt ausschließlich die drei abgelösten Hintergrundcontainer nach Start des neuen Dienstes.
- Keine weiteren Images bereinigt; Datenbank, Secrets, SFTP-Ordner und Rollen unverändert.
- Hinweis für Financisto als führendes System: Im Web bearbeitete Wiederholungsregeln werden noch nicht zurückexportiert.

## Version 1.9.12 (04.11.2026)

- Geführte Einführung mit Highlight, abgedunkeltem Hintergrund, Sprechblase, Weiter/Zurück/Überspringen.
- Neue Benutzer starten automatisch bei der ersten vollständig abgeschlossenen Anmeldung (nach 2FA).
- Zustand pro Benutzer in bestehender SQLite-Datenbank. Bestehende Benutzer beim Update nicht automatisch unterbrechen.
- Für jeden Benutzer jederzeit erneut aufrufbar unter „Hilfe / Einführung“ im Menü.
- Administratoren, Bearbeiter und Leser sehen nur passende Einführungsschritte.
- Desktop/Mobilnavigation, verkleinerte Bildschirme und Tastatur-Bedienung berücksichtigt.
- Kein gesonderter Javascript-Bestätigungsdialog bei „Automatische Buchung“; die Moduswahl und Übernehmen bleiben.
- Keine zusätzlichen Container oder externen Tracker/Bibliotheken.

## Version 1.9.10 – Einheitliche Aktionen

- Wiederkehrende Buchungen: Ein einziges Modus-Menü (Pausiert / Manuelle Buchung / Automatische Buchung) mit Übernehmen. Kein doppelter Aktivieren-Button mehr.
- Administrationsrechte unverändert: automatische Buchung ausschließlich durch Administrator; manuelle Regeln auch für Bearbeiter.
- Wechsel zur automatischen Buchung verlangt ausdrückliche Bestätigung. Fällige manuelle Buchungen werden weiterhin mit dem Wort BUCHEN bestätigt.
- Benutzerverwaltung: kompakte Aktionen Aktivieren/Sperren und Verwalten; Passwort, 2FA, endgültiges Löschen unter Verwalten. Bestehende Authentifizierung und Schutzprüfungen unverändert.
- Reine UI-Änderung plus eindeutige Modi-Übermittlung, keine Datenbankmigration.

# Version 1.9.9 – Wiederkehrende Buchungen und Benutzerlöschung

- Importvorschau für eine aktuelle originale Financisto-.backup-Datei; ausschließlich Vorlagen mit `is_template=2` und Wiederholungsregeln; Konten, Buchungen und Salden bleiben unberührt.
- Monatliche Regeln inklusive Stichtag und Intervall, Sonderregeln (z. B. GEEKY-Quartal) mit Prüfhinweis.
- Deaktivierte Übernahme in eigene SQLite-Tabellen; bestehende Regeln werden bei erneuter Übernahme nicht überschrieben.
- Verwaltung und bewusstes Aktivieren für Bearbeiter/Admin; automatische Ausführung nur nach expliziter Admin-Freigabe.
- Separater Docker-Dienst zur Prüfung alle 15 Minuten, gesperrt bei Financisto als führendem System.
- Eindeutige Ausführungskennungen, atomare Kontostandsaktualisierung, keine rückwirkende Massenbuchung.
- Bestehende manuellen Importe, Android-Sync, SQLite-Backups, Financisto-Rückexport und 2FA bleiben erhalten.
- Kein Backupdatei-Inhalt im Installationspaket.
- Administratoren können fremde Benutzerkonten nach Bestätigung von Benutzername, Passwort und frischem 2FA-Code dauerhaft löschen. Eigener Account und letzter aktiver Admin sind geschützt; Finanzbuchungen und Auditverlauf bleiben erhalten.

## Version 1.9.8 — 04.11.2026
- Buchungsübersicht zeigt alle Monate zwischen zwei ausgewählten Monatsgrenzen (einschließlich).
- Buchungsseiten: Standard 30; 20/30/50/100 unter Einstellungen → Buchungsliste.
- Rechnerischer Kontostand nach jeder Buchung; Umbuchungen werden berücksichtigt, fremdwährungsübergreifende Zielsalden als unbekannt markiert.
- Neue historische Auswertung mit Monatsverlauf, Durchschnittskennzahlen, Höchstbeträgen und Kategorie-Kreisdiagrammen.
- Dashboard und historische Auswertung teilen Monats-/Konto-/Kategorie-/Währungs-/Suchfilter pro angemeldeter Sitzung.
- Bisherige TOTP-2FA, Rollen, manueller Import, Auto-Import-Regelung und Datensicherung bleiben erhalten.

## 1.9.7 – Reparatur des Dashboard-Starts

- `financisto_export.py` wird nun in das Docker-Image kopiert.
- Update prüft vor dem Neustart, ob das Exportmodul im neuen Image importierbar ist.
- Statische Prüfung auf fehlende lokale Module des Flask-Einstiegsmoduls.
- Datenbank, Benutzer, 2FA, Import, Export und SFTP-Konfiguration bleiben erhalten.

# Änderungsverlauf

## 1.9.6 – Schnellsuche für Finanz-Stammdaten

- Sofortfilter in den Einstellungen für Empfänger, Haupt- und Unterkategorien sowie Konten.
- Trefferzählung, Meldung bei keinem Treffer und Zurücksetzen-Knopf je Bereich.
- Kategorien über die vollständige Hierarchie durchsuchbar; Suche ignoriert Groß-/Kleinschreibung und Akzente.
- Keine Datenbankmigration, kein Serverkontakt während des Suchens; Formulare und Rollenrechte bleiben unverändert.
- Manueller Financisto-Import, Auto-Import-Schalter, SQLite-Backups und experimenteller Android-Rückexport bleiben erhalten.



## 1.9.5 – Experimenteller Financisto-Rückexport

- Eigenständiger, schreibgeschützter Android-Testexport `.backup` in Einstellungen.
- Basierend auf exakt SHA256-passender Originaldatei; vollständige Originalattribute und unbekannte Datentypen bleiben im Export erhalten.
- Beim Import wird die Originaldatei atomar in SQLite als BLOB gespeichert; tägliche SQLite-Backups enthalten die Exportgrundlage.
- Für bestehende Installationen wird die passende Originaldatei aus `import-archive/` gesucht und ohne Buchungsänderung in SQLite übernommen.
- Bei fehlender Datei ist ein SHA256-verifizierter Upload der alten Originaldatei möglich.
- Export nur mit Administratorpasswort und frischem 2FA-Code. Keine Änderung an Daten oder Android-App.
- Zusätzliche Plausibilitätsprüfung (Dateiformat, Buchungszahlen, IDs, Werte).

**Grenze:** Echte Rücksicherung in die Android-App `tw.tib.financisto` (DB 257) ist noch nicht getestet. Testexport nicht auf der produktiven Android-Installation wiederherstellen.

---
# Version 1.9.4

- Automatische konsistente SQLite-Tagesbackups, 14 Stände unter data/web-backups
- Administrator kann Tagesbackup aktivieren/deaktivieren und manuelles Backup erstellen
- Backup-Hintergrunddienst ohne Netzwerk, eigene CPU-/Prozesskonfiguration
- Offline-Wiederherstellung per restore.sh mit Prüfung, Vorabkopie und Bestätigung
- Importkontrolle und manueller Financisto-.backup-Import unverändert

## 1.9.3 – Rollentrennung für Finanz-Stammdaten
- Bearbeiter können Einstellungen öffnen und im Web-Modus Empfänger sowie Haupt- und Unterkategorien anlegen und umbenennen.
- Bearbeiter können unbenutzte Empfänger und Kategorien löschen; verwendete Datensätze und Kategorie-Eltern mit Unterkategorien bleiben geschützt.
- Kontoverwaltung, Standardkonto, Benutzer, Freigaben, öffentlicher Zugang, Importsteuerung und Backups bleiben Administratoren vorbehalten.
- Zusätzliche serverseitige Rollenprüfung auch für Lösch-POSTs; keine rein optische Sicherheit.
- Leser können die Einstellungen weiterhin nicht öffnen. Import- und Datenführungslogik unverändert.

## 1.9.2
- Öffentlicher Login per adminbestätigtem UI-Schalter (SQLite, 2FA).
- PC-Freigaben sichtbar auf Einstellungsseite.
- Kontrollierter Rückwechsel zu Financisto auch bei Web-Änderungen; Sicherung und doppelte Zustimmung vor Verlust.
- Einheitliche Aktions-Buttons und mobil nutzbare Einstellungsdialoge.

## Version 1.9.1

- PC-Allowlist weiterhin in Einstellungen verlinkt; öffentliche Freigabe bleibt opt-in.
- Sicherer Rückweg zur Android-Datenführung, nur ohne Web-Änderungen und nach frischer 2FA; Auto-Import bleibt beim Wechsel aus.
- Standardkonto in Einstellungen für neue Buchungen, bestehende Buchungen nicht verändert.
- Zielkonto-Feld erscheint ausschließlich bei Umbuchungen; die Kategorie wird bei Umbuchungen ausgeblendet.
- Empfänger, Kategorien und Konten in den Einstellungen exklusiv aufklappbar.
- Manuelle .backup-Prüfung in Web-Betriebsart bleibt erhalten.

## 1.9.1 – Importsteuerung, Web-Buchungen und Stammdaten

- Automatischen Import in den Einstellungen aus-/einschalten (persistente SQLite-Einstellung).
- Sicherheitsprüfung der Einstellung direkt im Importdienst und in der SQLite-Transaktion.
- Expliziter Wechsel zur Web-Finanzverwaltung mit Admin-Passwort, frischer TOTP und SQLite-Sicherheitskopie.
- Neue Web-Buchungen (Einnahme, Ausgabe, Umbuchung), Änderung/Löschung nur selbst erfasster Buchungen.
- Konten, Kategorien und Empfänger unter Einstellungen verwalten; neue Empfänger direkt aus dem Buchungsformular.
- Manueller .backup-Upload bleibt verfügbar; im Web-Modus zunächst nur Validierungs-Vorschau, um Web-Daten nicht zu überschreiben.
- Herunterladbare SQLite-Sicherung; kein kompatibler .backup-Export in diesem Release.
- Bestehende Finanzdaten, Secrets und Caddy/Proxy-Hostnamen bleiben erhalten.

## 1.7.1 – Sortierte Konten, einklappbare Diagramme, ausführbares Update-Skript

- Konten mit aktivem, von 0 abweichendem Saldo erscheinen alphabetisch zuerst; danach inaktive Konten mit Saldo, unbekannte Salden und zuletzt alle Konten mit 0 €.
- Zweispaltige Kontoübersicht wird von oben nach unten je Spalte alphabetisch gelesen; auf schmalen Bildschirmen einspaltig.
- Das Diagramm „Ausgaben nach Kategorien“ startet beim Laden der Seite eingeklappt. Der Kopf zeigt die Monate und die Anzahl Kategorien; auf Wunsch per Klick öffnen. Ein direkter Sprunglink klappt es auf.
- `update.sh`, `install.sh` und das SFTP-Skript sind im vollständigen ZIP-Paket ausdrücklich als ausführbar (755) gespeichert und bleiben es nach dem Entpacken.
- Keine Änderungen an Importdaten, Kontoständen, Caddy, SFTP, Secrets oder SQLite-Schema.

## 1.7.0 – Navigation, kompakte Dashboard-Ansicht und Buchungstyp

- Auf Desktop-Bildschirmen bleibt eine feste Seitenleiste links sichtbar; kleine Bildschirme nutzen eine ausklappbare obere Navigation.
- Hauptfilter und Kontostände sind beim Öffnen des Dashboards standardmäßig eingeklappt.
- Im geschlossenen Zustand bleiben Zeitraum, Filterstatus, Gesamtkontostand und Stand der letzten Sicherung sichtbar.
- Direkte Navigationslinks zu Filtern und Kontoständen öffnen die betroffenen Abschnitte bei Bedarf.
- Desktop-/Mobil-Layouts werden im Druck vollständig ausgeblendet; vorhandene A4-/A5-Druckansichten bleiben erhalten.
- Unter den Buchungen wird die bisher überall gleiche Spalte „Quelle“ durch gut sichtbare Kennzeichnungen „Einnahme“/„Ausgabe“ ersetzt (auch sortierbar).
- Reines UI-Update ohne Änderungen an Finanzdatenbank, Importdienst, Zugangsdaten oder Caddy-Vertrauensstellung.

## 1.6.9 – Kontostände der Finanzkonten

- Neu zwischen Monatskarten und Diagrammen: Gesamtkontostand und Salden aller Konten in der ausgewählten Währung.
- Grundlage ist `account.total_amount` aus der letzten Financisto-Sicherung; Monatsbuchungen werden nicht als Kontostand missverstanden.
- Für die Gesamtsumme zählt allein Financistos `is_include_into_totals`-Kennzeichen. Ausgeschlossene und inaktive Konten bleiben einzeln sichtbar und werden entsprechend markiert.
- Kontostände sind unabhängig von Zeiträumen, Suchbegriffen, Konten- und Kategorienfiltern; keine Vermischung unterschiedlicher Währungen.
- Neue Tabelle `account_snapshots`; bei künftigen Importen werden die Werte in derselben SQLite-Transaktion wie die Buchungen aktualisiert.
- Bestehende Installationen können Kontostände aus einer Archiv-Sicherung übernehmen, wenn deren SHA-256 exakt dem letzten importierten Stand entspricht. Andernfalls erscheinen sie erst mit dem nächsten vollständigen Import, ohne erfundene Nullsalden.
- Keine Änderungen an Caddy/Proxy, SFTP, Secrets oder alten Daten; reguläres Update mit `update.sh` und SQLite-Backup.

## 1.6.8 – Filter führt zum Monatsvergleich

- Nach „Auswerten“ springt die Seite zum Vergleich der beiden Monatskarten, statt zur Buchungstabelle.
- Automatisches Absenden nach Wechsel von Monat, Konto, Währung oder Kategorie verwendet denselben Monatsanker.
- Der separate Schnellfilter sowie Tabellen-Sortierung und Seitennavigation springen unverändert zu den Buchungen.
- Kein Eingriff in Finanzdaten, Importdienst, Caddy, SFTP oder Secrets.

## 1.6.7 – Beschriftungen der Balkendiagramme korrigiert

- Monatsnamen stehen in einer ausreichend breiten eigenen Spalte und überlagern keine Balken mehr.
- Responsive Spaltenaufteilung für Desktop, Tablet und Smartphone optimiert.
- Die vorhandenen Monatsfarben, Diagrammwerte und Filter bleiben unverändert.
- Keine Änderungen an Datenbank, Import, SFTP, Secrets oder Caddy.

## 1.6.6 – Monatsvergleich und zusammenklappbare Filter
- Aktueller und Vergleichsmonat sind durch unterschiedliche Kopfbereiche, Nummern und ausgeschriebene deutsche Monatsnamen sofort unterscheidbar.
- Balkendiagramme übernehmen exakt dieselben Kontrastfarben und erhalten klar beschriftete Legenden sowie kurze Monatsnamen direkt an jeder Balkenreihe.
- Haushaltsauswertung öffnet ohne Monatsparameter den neuesten Monat mit echten Buchungen in gewählter Währung/Konto (explizit gewählte Monate bleiben erhalten).
- Kategorienauswahl klappt nach „Auswahl übernehmen“ automatisch wieder zu; Anzahl ausgeblendeter Kategorien bleibt sichtbar.
- Keine Änderung an den Buchungen oder Finanzdaten; alle bisherigen Sicherungs- und SFTP-Einstellungen bleiben erhalten.

## 1.6.5 – Neue Android-Financisto-Sicherungen kompatibel
- Unterstützt zusätzlich `PACKAGE:tw.tib.financisto` (Android, 2026-10-18, Datenbankversion 257) und die bisherige `ru.orangesoftware.financisto`.
- Der Import prüft notwendige Buchungsfelder, bevor eine vorhandene Finanzdatenbank verändert wird.
- Der Import wählt Sicherungen anhand der im Dateinamen angegebenen Sicherungszeit aus, nicht anhand des FolderSync-Übertragungszeitpunkts.
- Auch die drei Archiv-Reservekopien werden anhand der Sicherungszeit ausgewählt.
- Beim Update erfolgt eine rein lesende Vorprüfung der neuesten Datei aus `data/inbox`, bevor der Importdienst startet.
- Bestehende Finanzdaten, SFTP-ACLs, Caddy-Secrets und `.env` bleiben unberührt.

## 1.6.4 – Auto-Import-Image-Build repariert
- Das Updateskript baut ab sofort sowohl `dashboard` als auch `auto-import` neu.
- Die ausgerollte `sync_import.py` im Auto-Import-Container wird per SHA-256 mit dem Release verglichen. Ein veraltetes Image kann nicht mehr unbemerkt als Update-Erfolg gelten.
- Keine Änderungen an der SQLite-Datenbank, Caddy-Zertifikaten, .env oder Secrets.
- Vor einem Bulk-Import von alten Android-Sicherungen empfiehlt sich die Prüfung, ob die neueste Datei wirklich vom unterstützten Financisto-Format ist.

## 1.6.3 – SFTP-Inbox-Rechte und Updateprüfung
- Keine falsche Fehlermeldung nach einem erfolgreichen Update, wenn die SFTP-Inbox dem Benutzer root gehört und der Projektbenutzer per ACL Schreibzugriff hat.
- Eigentümer und SFTP-Gruppe werden vom Updateskript nicht verändert.
- Das SFTP-Einrichtungsskript akzeptiert bei erneuter Ausführung für die Inbox auch root als Eigentümer.
- Zusätzliche Domains müssen dauerhaft in der .env unter SITE_ADDRESSES stehen; sie werden bei künftigen Updates nicht überschrieben.

## 1.6.2 – Persistente NPM-Domain und sichere Quell-IP
- Beliebige HTTPS-Hostnamen in SITE_ADDRESSES in .env, dauerhaft updatefest.
- Bestehende manuelle Hostnamen aus dem Caddyfile werden beim Upgrade nach .env übernommen.
- Caddy wertet bei explizit vertrauenswürdigen Proxy-IP-Adressen die tatsächliche Client-IP aus.
- Die Freigabeliste der Dashboard-Weboberfläche prüft weiterhin einzelne Client-IP-Adressen; NPM selbst nicht pauschal freigeben.
- `TRUSTED_PROXY_IPS` standardmäßig nur Loopback, externe NPM-Vertrauensstellung ist bewusst manuell.

## 1.6.1
- A5-Monatszettel öffnet im selben Tab.
- A4-Auswertung bleibt per eigenem Druckknopf verfügbar und ist aus der A5-Ansicht erreichbar.
- Kategorieüberschriften in A5 und A4 deutlich fett, auch beim Druck.
- SFTP-Einrichtungsskript aktualisiert: zuverlässige sshd-T Prüfung mit Fehlerdiagnose.

## 1.6.0 — A5-Kompaktblatt und begrenzter Auto-Import-Speicher
- Eigenständige, papiersparende Monatsübersicht in A5, mit Einnahmen, kategorisierten Ausgaben, Einzelbeträgen und Saldo.
- Ausführlicher A4-Ausdruck bleibt erhalten.
- Importierte Android-Sicherungen werden erst nach SQLite-Commit verschoben; maximal drei erfolgreiche Backups im Archiv.
- Fehlerhafte Backups werden getrennt aufbewahrt (maximal fünf, maximal 14 Tage).
- Beide Formate nutzen die gleiche Filterauswahl, keine zusätzliche Datenbank.

## 1.5.0 – Haushaltsbericht und Druck optimiert

- A4-Hochformat mit breiter, klar gegliederter Tabelle statt drei schmaler Spalten; sinnvoller Umbruch langer Kategoriegruppen.
- Einnahmen sind ein eigener Bereich oberhalb der Ausgaben.
- Einkauf / Lebensmittel und Einkauf / Haushaltsartikel werden anhand der Financisto-Unterkategorien getrennt.
- Einzelne Einnahmen- und Ausgabenkategorien lassen sich über die Monatsauswertung ausblenden, auch beim Druck.
- Angezeigte Summen und Saldo berücksichtigen nur sichtbare Kategorien und sind bei aktivem Filter markiert.
- Keine separate Haushaltsbuch-Datenerfassung. Finanzdaten, Secrets und Caddy-Dateien bleiben unverändert.
- Normales Update unter dem Projektbenutzer ohne sudo.

# Änderungen

## 1.5.0
- Monatliche Haushaltsauswertung ausschließlich aus Financisto, als A4-Querformat druckbar / Browser-PDF.
- Manuelle Haushaltsbuch-Erfassung aus der Oberfläche und aus den aktiven Routen entfernt; alte Tabellen bleiben aus Datenschutz- und Migrationsgründen unverändert.
- Schnellfilter unmittelbar über den Buchungen mit verzögerter automatischer Suche; Auswertungen bleiben davon unabhängig.
- Navigationssprung zum Buchungsabschnitt und Sortier-/Seitenlinks mit Anker.
- Installations- und Update-Skripte für den aktuellen Linux-Projektbenutzer ohne sudo; keine rekursiven Eigentümerwechsel.
- Vollständiges Docker-Release mit update.sh und Sicherung vor jeder Aktualisierung.

## 1.3.0
- Automatischer Import neuer Android-Sicherungen aus data/inbox.

## 1.8.0 – Sicherheitsfundament für die spätere Web-Finanzverwaltung
- Mehrere lokale Benutzer (Administrator, Bearbeitung, Nur Lesen) mit eigenen Passwörtern.
- Verpflichtende TOTP-2FA ab der ersten Anmeldung, mit QR-Einrichtung und einmalig angezeigten Wiederherstellungscodes.
- TOTP-Seeds verschlüsselt mit dem persistenten app_secret; Codes als Hash gespeichert.
- Persistente Login- und 2FA-Versuchssperre, TOTP-Replay-Sperre und Audit-Ereignisse.
- Benutzerverwaltung und read-only Stammdatenübersicht gesammelt unter **Einstellungen**.
- Optionale spätere NPM-Internetfreigabe über PUBLIC_ACCESS=1, standardmäßig AUS.
- Noch keine Änderung von Financisto-Stammdaten oder Buchungen: Die Android-Importlogik ersetzt sie weiterhin, bis die führende Datenquelle kontrolliert umgestellt ist.

## 1.9.11 (2026-11-04)
- Wiederkehrende Buchungen direkt im Dialog bearbeiten, ohne ans Seitenende zu springen.
- Kontrolliertes Entfernen mit Regelname als Bestätigung und archivierter Ausführungshistorie.
- Ein gemeinsames Anwendungsimage für Dashboard, Import, Backups und Wiederkehrend.
- Kein erzwungenes Neuanlegen aller Container bei jedem Update.

## 1.9.25 – Telegram-Buchungen
- Administrativer Schalter, separate verschlüsselte Bridge-Zugangsdaten und Benutzerfreigaben für private Telegram-Chats.
- Sicherer Node-RED-Bridge-Endpunkt für Buchungsvorschläge und einmalige Bestätigung; keine zweiten Telegram-Listener.
- Inline-Konto-/Kategoriewahl; Bestätigung bucht über dieselbe Ledger- und Kontostandslogik wie die Web-Buchung.
- Beibehaltung sämtlicher vorhandener Import-, Backup- und Benachrichtigungsfunktionen.
