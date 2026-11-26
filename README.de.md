# Financisto-Dashboard (FieLanzen)

**Sprache / Language:** [English](README.md) | **Deutsch**

<p align="center">
  <img src="package/static/sea-wolves-logo.webp" alt="Sea Wolves Logo des Dashboards" width="260">
</p>



**Deutschsprachiges, selbst gehostetes Finanzdashboard für Docker** – mit Finanzberichten, Buchungsverwaltung, wiederkehrenden Buchungen, PWA und sicherem Import von [Financisto](https://github.com/dsolonenko/financisto)-Backups.

**Aktuelles Release:** [ZIP und Prüfsumme herunterladen](https://github.com/renfie/financisto-dashboard/releases/latest) · [Versionshistorie](https://github.com/renfie/financisto-dashboard/releases).


## Funktionen

- Konten, Buchungen, Umbuchungen, Empfänger und Kategorien verwalten; Rollen und Zwei-Faktor-Authentifizierung
- Monatsberichte, Haushaltsauswertung, Kontostände, historische Vergleiche und Druckansichten
- **Manueller Financisto-`.backup`-Import bleibt erhalten**; optional automatischer Import per SFTP/FolderSync, in der Weboberfläche steuerbar
- Finanzverwaltung mit wahlweise **Financisto oder der Weboberfläche als führendem System**; Schutz vor unbeabsichtigtem Überschreiben eigener Buchungen
- Wiederkehrende Buchungen mit optionalem Enddatum oder maximaler Anzahl an Ausführungen; Benachrichtigungen über Web Push, Gotify oder Telegram
- Zukünftig datierte Buchungen bleiben gelb sichtbar; der heutige angezeigte Kontostand berücksichtigt sie noch nicht und zeigt die Prognose separat (gespeicherte Buchungen werden nicht zeitversetzt ausgeführt)
- Responsive Oberfläche für PC, Tablet und Smartphone mit installierbarer PWA
- Gemeinsame tägliche und manuelle SQLite- sowie Financisto-Sicherungen mit Statusanzeige und Prüfung wiederkehrender Vorlagen
- Versionierte Mobile-API für Konten und Buchungen mit dauerhaft gültigen, sperr- und löschbaren Geräte-API-Schlüsseln
- Docker Compose, lokale HTTPS-Konfiguration und Backup-/Update-Skripte; persistente Daten in Bind-Mounts

## Interaktive Einführung für neue Benutzer

Neue Benutzer erhalten nach der Kontoeinrichtung eine **rollenabhängige Einführung auf Deutsch oder Englisch**. Erklärt werden aktuelle Funktionen einschließlich zukünftiger Buchungen, Wiederholungslimits, Datenführung und Sprachwechsel. Bestehende Benutzer werden nicht erneut automatisch durch den Rundgang geführt. Über **Hilfe / Einführung** kann jeder ihn jederzeit neu starten. [Anleitung auf Deutsch](package/docs/ONBOARDING.de.md) · [English](package/docs/ONBOARDING.en.md).

## Ursprung und Abgrenzung

Dieses Dashboard ist eine **eigenständige Webanwendung** und **keine offizielle Version, Weiterentwicklung oder ein Fork** der Android-App Financisto. Es ist durch deren Nutzungs- und Datenmodell inspiriert und unterstützt das Importformat ihrer Sicherungsdateien sowie das Format des verbreiteten Android-Forks.

- **Originalprojekt:** [Financisto – dsolonenko/financisto](https://github.com/dsolonenko/financisto), entwickelt von Denis Solonenko und Mitwirkenden.
- **Unterstützter Android-Fork:** [Financisto Holo – tiberiusteng/financisto1-holo](https://github.com/tiberiusteng/financisto1-holo).

Die Rechte an Financisto und dessen Kennzeichen verbleiben bei den jeweiligen Rechteinhabern. Für Android-App, deren Funktionsweise oder ihre Weiterentwicklung ist dieses Repository nicht zuständig.

## Screenshots

Die folgenden Bilder zeigen die **tatsächliche Gestaltung der Weboberfläche**, allerdings teilweise aus früheren Entwicklungsständen. Kontonamen, Beträge und weitere Angaben wurden durch **Demodaten** ersetzt. Die Desktop-/Mobilansichten stammen aus v1.9.17; einzelne Elemente der aktuellen v1.9.60 können abweichen.

### Dashboard am Desktop

![Desktop-Dashboard mit anonymisierten Beispieldaten](docs/screenshots/dashboard-desktop-demo.png)

### Mobile Ansicht

<img src="docs/screenshots/dashboard-mobil-demo.png" alt="Mobile Finanzübersicht mit anonymisierten Beispieldaten" width="340">

### Buchungen erfassen

![Buchungsformular mit anonymisiertem Beispielkonto](docs/screenshots/buchung-erfassen-demo.png)

## Deutsch und Englisch in der Weboberfläche

Die Oberfläche lässt sich jetzt über **DE / EN** jederzeit zwischen Deutsch und Englisch umschalten – bereits bei der Anmeldung, auf dem Smartphone im Kopfbereich und am Desktop in der Seitenleiste. Der Wechsel erfordert **keine neue Anmeldung**. Die Auswahl gilt für die jeweilige Sitzung und wird nicht dauerhaft in den Finanzdaten oder Benutzerprofilen gespeichert. Nach dem Abmelden beziehungsweise Ablauf der Sitzung gilt wieder die Installationsvorgabe.

Bei der **Neuinstallation fragt der Installer zuerst zweisprachig nach Deutsch oder Englisch** und führt die restliche Installation in dieser Sprache durch. Die Wahl wird als `DEFAULT_LANGUAGE=de` oder `DEFAULT_LANGUAGE=en` in der lokalen `.env` gespeichert. Bestehende Installationen bleiben standardmäßig deutsch, sofern der Administrator die Vorgabe nicht ausdrücklich ändert. Die Sprache kann trotzdem jederzeit über DE / EN gewechselt werden.

Alle Übersetzungen befinden sich lokal im Programm; es werden keine Finanzdaten an Übersetzungsdienste gesendet. Vereinzelte ältere Spezial- oder Diagnosemeldungen können noch deutsch erscheinen. [Sprachkonfiguration (Deutsch)](package/docs/LANGUAGE.de.md) · [English](package/docs/LANGUAGE.en.md).

## Caddy und HTTPS

**Caddy ist im Docker-Compose-Projekt bereits enthalten** und übernimmt internes HTTPS sowie die Weiterleitung zum Dashboard. Die mit `tls internal` erzeugte lokale Caddy-Zertifizierungsstelle und die Zertifikate liegen persistent in `caddy/data/`; beim Update bleiben sie erhalten. Wird zusätzlich Nginx Proxy Manager verwendet, benötigt dieser für externe Browser ein eigenes öffentlich vertrauenswürdiges HTTPS-Zertifikat.

**Ausführliche Anleitung:** [Caddy, HTTPS und Nginx Proxy Manager auf Deutsch](package/docs/CADDY.de.md) · [English](package/docs/CADDY.en.md).

**Update-Hinweis:** Auf v1.9.60 kann direkt von älteren Releases oder Entwicklungsständen aktualisiert werden; eine Zwischeninstallation ist nicht notwendig. Das Skript sichert vorab Programmcode und SQLite-Datenbank.

## Repository-Struktur

| Pfad | Inhalt |
| --- | --- |
| `package/` | Anwendungsquellcode, Docker-Dateien, `install.sh`, Oberfläche und Dokumentation |
| `update.sh` | Update vorhandener Installationen einschließlich Sicherung |
| `setup_financisto_sftp.sh` | Optionale Einrichtung für den SFTP-Import |
| `README.txt` | Versionshinweise zum Release |
| `package/CHANGELOG.md` | Versionshistorie |
| `package/docs/` | Ausführliche Funktions- und Betriebsdokumentation |

## Neuinstallation

Repository klonen oder als ZIP herunterladen. Im ausgepackten Verzeichnis:

```bash
cd package
./install.sh
```

Das Skript ist als regulärer Linux-Projektbenutzer **ohne sudo** auszuführen. Weitere Hinweise stehen in [package/README.md](package/README.md).

## Bestehende Installation aktualisieren

Quellcode **getrennt von der produktiven Installation** auschecken und im Repository-Hauptverzeichnis als Eigentümer der vorhandenen Installation ausführen:

```bash
./update.sh /pfad/zur/bestehenden/financisto-dashboard-installation
```

**Nicht** die vorhandenen Daten- und Konfigurationsverzeichnisse überschreiben. Das Update-Skript ist für die Datensicherung und die Übernahme der Programmdateien zuständig. Hinweise: [Backup & Restore](package/docs/BACKUP_RESTORE.md).

## Datenschutz und Sicherheit

Produktive SQLite-Datenbanken, Finanztransaktionen, Backups, Passwörter, private Schlüssel, Tokens, befüllte `.env`-Dateien und andere Laufzeitdaten gehören **nicht** in Git. Die Regeln in [`.gitignore`](.gitignore) schließen diese typischen Dateien aus. Vor jeder Veröffentlichung von Quellcode oder Releases muss der Inhalt dennoch kontrolliert werden.

## Änderungsverlauf

Alle Veröffentlichungen und Entwicklungsschritte stehen vollständig im [deutschen Changelog](CHANGELOG.md) und [englischen Changelog](CHANGELOG.en.md). Im Dashboard sind sie unter **Änderungsverlauf** und die vollständigen GPLv2-Rechte und Pflichten unter **Lizenz & Rechtliches** verfügbar, jeweils über DE/EN umschaltbar.

## Lizenz

Dieses Dashboard wird unter der **GNU General Public License, Version 2 (GPL-2.0-only)** angeboten. Die Lizenzbedingungen stehen in [LICENSE](LICENSE); Hinweise zu Projektzuordnung und Drittrechten in [NOTICE.md](NOTICE.md).

Bei Verteilung der Software dürfen Empfänger ihre Kopie gemäß GPL v2 verwenden, verändern und weitergeben. Daraus entsteht **kein Schreibzugriff** auf dieses GitHub-Repository; den verwaltet ausschließlich dessen Eigentümer.

Das ursprüngliche Android-Projekt Financisto steht ebenfalls unter GPL v2. Die Lizenzierung dieses Dashboards begründet weder eine offizielle Zugehörigkeit noch eine Freigabe fremder Marken oder Grafiken.

## Downloads und Releases

Über **Code → Download ZIP** lässt sich der aktuelle Quellstand herunterladen. Zusätzlich können versionierte ZIP-Pakete als **GitHub Releases** veröffentlicht werden.


Alle fertigen Versionen stehen öffentlich unter [GitHub Releases](https://github.com/renfie/financisto-dashboard/releases). Das Repository ist öffentlich; Bearbeitungsrechte erhält dadurch niemand automatisch.


## Urheberrecht und Weitergabe

Copyright © 2026 René Fieler (RenFie). Eigene Programmteile stehen unter der **GNU GPL v2 (GPL-2.0-only)**. Bei Weitergabe müssen vorhandene Urheber-, Lizenz- und Gewährleistungshinweise erhalten bleiben; geänderte Dateien und Änderungsdaten sind zu kennzeichnen. Die vollständige GPL v2 ist beizulegen; bei Weitergabe ausführbarer Programme ist der zugehörige Quellcode oder eine nach §3 GPL v2 zulässige Alternative bereitzustellen. Einzelheiten: [LICENSE](LICENSE) und [NOTICE.md](NOTICE.md). Rechte Dritter bleiben unberührt.

## Mobile-API: wiederkehrende Regeln (Entwicklungszweig)

Die authentifizierte Schnittstelle `/api/mobile/v1/recurring` stellt die serverseitigen Wiederholungsregeln für FieLanzen Android bereit. Die Regeln verbleiben **ausschließlich auf dem Dashboard-Server**. Es gibt keinen Abgleich mit den lokalen Android-Regeln. `GET /api/mobile/v1/capabilities` meldet die Verfügbarkeit über `features.recurring_rules: true`.

Verwendet werden die bisherigen Bearer-API-Schlüssel. Leseschlüssel dürfen Regeln anzeigen; Änderungen benötigen einen Schreibschlüssel, Administrator-/Editorrechte und `finance_mode=web`. Neue und bearbeitete Regeln bleiben zunächst pausiert. Automatische Ausführung dürfen ausschließlich Administratoren freigeben; die Ausführung übernimmt weiterhin der vorhandene Dashboard-Hintergrunddienst.

Endpunkte: `GET/POST /api/mobile/v1/recurring`, `PUT/DELETE /api/mobile/v1/recurring/{id}`, `PUT /api/mobile/v1/recurring/{id}/mode` und `POST /api/mobile/v1/recurring/{id}/post`. Jede Änderung benötigt einen UUID-`Idempotency-Key`, bei bestehenden Regeln zusätzlich die aktuelle 32-stellige `If-Match`-Revision. Manuelles Buchen verlangt `{"confirm":"BUCHEN"}`; Archivieren den exakten Regelnamen. Nach einer Zeitüberschreitung niemals mit einem neuen Idempotenzschlüssel erneut buchen.

Bestehende Wiederholungen, Ausführungshistorie, Kontostände, Sicherungsformate und API-Schlüssel bleiben erhalten. Weitere Details: [Mobile-API für Wiederholungen](package/docs/MOBILE_RECURRING_API.de.md).

## Vollständige Monatsauswertungen über die Mobile-API (Entwicklung)

`GET /api/mobile/v1/reports/monthly` berechnet bis zu 36 Monatswerte aus dem vollständigen Server-Buchungsbestand; 12 Monate einschließlich des aktuellen Monats sind Standard. Währung, Konto und Kategorien einschließlich Unterkategorien sind filterbar. Umbuchungen werden separat ausgewiesen, durchlaufende Posten und Saldoabgleiche ausgeschlossen, zukünftige Buchungen nicht als Ist-Werte gezählt. Die Web-Startseite, die historische Zeitreihe und die API verwenden dieselbe Aggregationsfunktion. Bestehende API-Schlüssel reichen aus, Schreibrechte werden nicht benötigt. **Capability: `features.monthly_reports=true` (Entwicklungszweig).** Details: [Mobile-Monatsberichte](package/docs/MOBILE_MONTHLY_REPORTS.de.md).

**Historische Spitzenwerte (Erweiterung auf develop):** Die Monats-API liefert zusätzlich `highlights.largest_expense` und `highlights.largest_income` mit Datum, positivem Einzelbetrag in Cent, Empfänger und vollem Kategorienamen; ohne Treffer `null`. Die Web-Historie verwendet dieselbe SQL-Auswahlfunktion. `q` ist als Suchfilter für Monatswerte und Highlights ergänzt. Optionale Capability `history_highlights: true`; bestehende `monthly_reports`-Funktion bleibt unverändert. Kein Schreibzugriff.

## Kontostandsabgleich über die Mobile-API

`POST /api/mobile/v1/accounts/{account_id}/reconcile` verwendet denselben transaktionalen Abgleichhelfer wie das Web-Dashboard. Erforderlich sind Bearer-Write-Key, Admin-/Editorrechte, `finance_mode=web` und ein UUID-`Idempotency-Key`. Übertragen werden der tatsächliche Kontostand, der vorher angezeigte Ist-Kontostand (jeweils Integer in kleinsten Währungseinheiten) und eine Notiz bis 500 Zeichen. Geänderte Kontostände ergeben `409 Conflict` ohne Korrekturbuchung; Null-Differenzen erzeugen keine Buchung. Die Korrekturkategorien bleiben von der regulären Monatsstatistik ausgeschlossen. Capability: `account_reconciliation: true`. Bei unklarer Antwort denselben Idempotency-Key wiederverwenden. [API-Dokumentation](package/docs/MOBILE_RECONCILIATION.de.md).
