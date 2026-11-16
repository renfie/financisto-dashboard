# Einführungsrundgang (Version 1.9.42)

**Sprache / Language:** [English](ONBOARDING.en.md) | **Deutsch**

## Start und erneuter Aufruf

Nach dem Einrichten eines neuen Kontos mit Zwei-Faktor-Anmeldung erscheint beim ersten Besuch des Dashboards eine interaktive Einführung. **Bereits vorhandene Benutzer werden durch das Update nicht automatisch erneut geführt.** Die Information, ob der Rundgang beendet oder übersprungen wurde, liegt weiter pro Benutzer in der Tabelle `users.tutorial_completed`.

Über **Hilfe / Einführung** im Menü lässt sich der Rundgang unabhängig vom gespeicherten Status jederzeit erneut starten. Die Schaltflächen **Zurück**, **Weiter**, **Überspringen** und **Fertig** ermöglichen die Navigation. Die manuelle Wiederholung setzt den Erledigt-Status nicht zurück.

## Sprache

Die Einführung folgt der aktuell ausgewählten Oberflächensprache **DE / EN**. Die Texte werden lokal aus `static/tour.js` geladen; externe Übersetzungsdienste oder Analysedienste sind nicht erforderlich. Die Sprachauswahl gilt weiterhin nur für die Browser-Sitzung und ändert keine Finanzdaten.

## Was erklärt wird

- Vergleich der Monatssummen, Filter, Kontostände und Buchungsliste
- Gelbe Kennzeichnung zukünftiger Buchungsdaten und ihre sofortige Wirkung auf den gespeicherten Kontostand
- Historische und druckbare monatliche Auswertungen (A5/A4)
- Buchungserfassung mit Empfänger vor Kategorie, Bearbeiten, Klonen und zukünftigen Buchungsdaten
- Wiederkehrende Buchungen mit manueller oder automatischer Ausführung, optionalem Enddatum und maximaler Anzahl
- Manueller Financisto-Backup-Import und optionaler automatischer SFTP-Import
- Benutzerrechte, Einstellungen, Sprachwechsel und erneuter Aufruf der Hilfe

Die Einführung berücksichtigt die Benutzerrolle: Administratoren, Bearbeiter und Benutzer mit Leserechten erhalten nur die zu ihrer Rolle passenden Hinweise. Für Buchungen im Web ist außerdem der entsprechende führende Datenmodus erforderlich. Der Rundgang führt keine Buchungen oder Einstellungen aus, sondern erklärt nur die Oberfläche.

## Technische Dateien

- `static/tour.js` – Ablauf, deutsche und englische Texte, Highlight und Tastaturbedienung
- `static/style.css` – vorhandene Darstellungsregeln
- `src/app.py` – bisheriger Endpunkt `/account/tutorial/complete` zur Statusspeicherung

Alle bestehenden Datenschutz- und Sicherheitsfunktionen bleiben unverändert.
