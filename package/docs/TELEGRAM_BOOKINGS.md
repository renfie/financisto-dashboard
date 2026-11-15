# FieLanzen 1.9.28 – Buchungen direkt aus einer Telegram-Finanzgruppe

**Kein Node-RED und kein fünfter Docker-Container.** Der bereits vorhandene Container
`financisto-dashboard-notifications` übernimmt zusätzlich den direkten `getUpdates`-Empfang
für einen **eigenständigen FieLanzen-Bot**. Dieser darf nicht gleichzeitig in Node-RED
als Empfänger konfiguriert werden.

1. In Telegram `@BotFather` öffnen, `/newbot` wählen, Anzeigenamen und einzigartigen
   Benutzernamen (Endung `bot`) vergeben. Bot-Token **niemals in Chats oder Tickets veröffentlichen**.
2. Bot der bestehenden privaten Finanzgruppe als Mitglied hinzufügen. Für
   `/finanz` ohne `@Botname` bei mehreren Bots in der Gruppe über BotFather
   `/setprivacy` → FieLanzen-Bot → `Disable` wählen und den Bot anschließend
   aus der Gruppe entfernen und wieder hinzufügen. Es sind keine Adminrechte notwendig.
   Bei aktiviertem Privacy Mode stattdessen `/finanz@DEIN_BOTNAME ...` verwenden.
3. Version 1.9.28 installieren. Dashboard als Administrator öffnen, unter
   **Einstellungen → Buchungen per Telegram** den **Bot-Token** eintragen,
   Buchungen zunächst **noch nicht aktivieren**, speichern.
4. In der Gruppe `/finanzid` schicken (bei mehreren Bots ggf. `/finanzid@DEIN_BOTNAME`).
   Die Bot-Antwort nennt Gruppen-Chat-ID und deine persönliche Benutzer-ID. Dasselbe
   kann ein weiteres Gruppenmitglied mit `/finanzid` für seine ID machen.
5. Die **negative** Gruppen-ID und die freigegebenen Benutzer-IDs mit Komma getrennt
   in den Admin-Einstellungen eintragen. Standardkonto auswählen, Kategorie optional.
   Web-Datenführung muss aktiv sein. Checkbox „Buchungen erlauben“ aktivieren.
6. Checkbox **„Ohne Rückfrage direkt buchen“** aktivieren, wenn eindeutige Befehle
   sofort gespeichert werden sollen. Ohne Haken werden sie zuerst per Inline-Button
   vorgeschlagen und erst nach Bestätigung gebucht. Speichern.
7. `/finanz 1,23 Testkauf | Einkauf | Bargeld` senden, Buchungsübersicht und Kontostand
   kontrollieren. Die Testbuchung bei Bedarf über die Weboberfläche löschen.

Beispiele (neue Syntax ab 1.9.28):

- `/finanz` — aktuelle Anleitung direkt im Telegram-Chat anzeigen
- `/finanz 24,90 Edeka` — Ausgabe, konfiguriertes Standardkonto und Kategorie Einkauf (oder konfigurierte Standardkategorie)
- `/finanz 24,90 Edeka | Lebensmittel | Bargeld` — Ausgabe, **Kategorie zuerst, danach Konto**
- `/finanz 24,90 Edeka | Lebensmittel | Bargeld | Mittagessen` — optional mit Notiz
- `/finanz +150 Taschengeld | Ebay Direkteinzahlung` — **Einnahme auf das Konto Taschengeld**, Notiz `Ebay Direkteinzahlung`; keine Ausgabenkategorie
- `/finanz +150 Taschengeld` — Einnahme ohne Notiz
- `/finanzid` — Gruppen-ID und eigene Telegram-Nutzer-ID anzeigen

Das Format vor 1.9.28 (Konto vor Kategorie) wird bewusst nicht mehr verwendet.
Wichtig: Beträge ohne Plus sind Ausgaben. Freigegebene Nutzer benötigen ein
aktives Konto mit bekanntem Kontostand. Bei Standardkategorie 0 wird die
Ausgabenkategorie `Einkauf` verwendet; falls sie nicht existiert, entsteht sie
beim ersten Buchungsbefehl. Eine als Standard eingestellte Ausgabenkategorie
hat Vorrang. Einnahmen verwenden keine Ausgabenkategorie.

Sicherheit: Die Gruppe UND die Benutzer-ID müssen freigegeben sein. Empfänger-Namen
werden gegen bekannte Kategorien geprüft. Telegram-Nachrichten werden über eindeutige
Chat-/Nachrichten-IDs gegen Doppelbuchungen abgesichert. Bestehende Android-.backup-
Importe werden nicht verändert; alle Buchungen benötigen aktive Web-Datenführung.
Es wird kein öffentlicher Telegram-Webhook eingerichtet. Telegram-Bots verwenden
keine Ende-zu-Ende-Verschlüsselung, Buchungstexte sind für Gruppenmitglieder sichtbar.
Die Ausgabenwarnungen können optional denselben neuen Bot-Token und Gruppen-ID
verwenden (Einstellungen → Benachrichtigungen → Telegram), bleiben aber separat konfigurierbar.

Bei Problemen: `docker logs --tail 100 financisto-dashboard-notifications`. Bitte
**keine Tokens** oder personenbezogenen Finanztexte als Log-Auszug veröffentlichen.

## Gemeinsame Standardkategorie ab v1.9.30
Die Kategorie für neue Ausgaben wird unter **Einstellungen → Standardkonto für neue Buchungen** ausgewählt und gilt für Web und Telegram. Ein Telegram-eigener Standardkategorie-Schalter entfällt. Ein bereits explizit gewählter Telegram-Wert wird beim Update übernommen. Einnahmen verwenden keine Ausgaben-Standardkategorie.
