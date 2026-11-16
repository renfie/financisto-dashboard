# Deutsche und englische Weboberfläche

**Sprache / Language:** [English](LANGUAGE.en.md) | **Deutsch**

## Sprache umschalten

Oben auf der Anmeldeseite, im mobilen Kopfbereich oder auf dem Desktop in der Seitenleiste stehen **DE / EN** zur Verfügung. Die Auswahl wirkt beim Laden derselben Seite ohne erneute Anmeldung. Es wird keine Benutzereinstellung in der SQLite-Datenbank angelegt. Die Auswahl gilt nur für die angemeldete bzw. aktuelle Browser-Sitzung und fällt nach dem Abmelden oder Sitzungsablauf auf den Installationsstandard zurück.

Die englischen Übersetzungen werden vollständig lokal aus `static/i18n.js` geladen. Es werden keine Buchungen, Empfänger, Kontobezeichnungen, persönlichen Notizen, Passwörter oder Finanzdaten an externe Übersetzungsdienste übertragen oder verändert. Einzelne seltene ältere Diagnosemeldungen können noch in Deutsch angezeigt werden.

## Neuinstallation

`package/install.sh` ohne sudo als regulärer Projektbenutzer starten. Zu Beginn erscheint die zweisprachige Eingabe:

```text
Sprache wählen / Select language [1=Deutsch, 2=English] (1):
```

Die folgenden Installationsfragen erscheinen auf Deutsch oder Englisch. Die Wahl wird für **neue Benutzer-Sitzungen** in der lokalen `.env` gespeichert:

```dotenv
DEFAULT_LANGUAGE=de
# oder
DEFAULT_LANGUAGE=en
```

Jeder Anwender kann diese Vorgabe jederzeit durch DE / EN für seine Sitzung überschreiben. Bei bestehenden Installationen fehlt `DEFAULT_LANGUAGE` bisher; dann gilt weiterhin Deutsch.

## Standard nachträglich ändern

Im vorhandenen Projekt die echte `.env` bearbeiten, `DEFAULT_LANGUAGE=de` oder `DEFAULT_LANGUAGE=en` setzen und nur den Dashboard-Dienst neu erzeugen:

```bash
cd /pfad/zum/financisto-dashboard
docker compose up -d --no-deps --force-recreate dashboard
```

Eigene Konten, Buchungen, Benutzer, 2FA, Finanz-Import und Caddy-Zertifikate werden davon nicht berührt.

## Übersetzungen pflegen

Deutsche Templates bilden den unveränderten Originaltext. Das offline arbeitende Übersetzungswörterbuch liegt in `static/i18n.js`. Neue Oberflächentexte sollten dort ebenso ergänzt und in beiden Sprachen geprüft werden. Kontonamen, Empfänger, Kategorien und Buchungsnotizen dürfen nicht automatisch verändert werden.

## Aktualisierung 1.9.47
Zahlreiche feste und dynamische Beschriftungen in Buchungen, wiederkehrenden Buchungen, Systemstatus, öffentlichem Zugriff, Telegram, Gotify, Benachrichtigungen, Financisto-Export und Stammdaten werden nun in Englisch ausgegeben. Bestätigungswörter sowie Benutzerdaten bleiben unverändert.
