# Mobile-API: vollständige Monatsauswertungen

**Entwicklungsstand `1.9.62-dev.3` auf `develop`.** Datum: 26.11.2026.

## Zweck

`GET /api/mobile/v1/reports/monthly` liefert sämtliche Monatswerte aus dem vollständigen serverseitigen Buchungsbestand. Die Buchungspaginierung mit bis zu 200 Einträgen ist davon unabhängig. Die API ist **rein lesend**. Eine erfolgreiche Antwort verwendet `Cache-Control: private, no-store`.

## Berechtigung und Capability

Wie die übrige Mobile-API: `Authorization: Bearer <API-Key>`. Bereits ein Read-Key genügt. `GET /api/mobile/v1/capabilities` meldet bereits **`"monthly_reports": true`** im Basisstand.

## Abfrage

`GET /api/mobile/v1/reports/monthly?from=2025-12&to=2026-11&currency=EUR`

| Parameter | Bedeutung |
|---|---|
| `from` | Anfangsmonat, YYYY-MM einschließlich |
| `to` | Endmonat, YYYY-MM einschließlich |
| `currency` | ISO-Währungscode mit drei Großbuchstaben, z. B. EUR; Standard: Dashboard-Standardwährung |
| `account_id` | Optional: vorhandenes Konto **in der gewählten Währung** |
| `category_id` | Optional: Kategorien-ID einschließlich aller Unterkategorien nach vorhandenen Nested-Set-Grenzen (`lft`/`rgt`) |
| `q` | Optional: Suche in Empfänger, Notiz und Kategoriename, maximal 100 Zeichen |

Ohne `from` und `to`: zwölf Monate einschließlich des aktuellen Monats. Werden Monatsgrenzen angegeben, sind **beide** erforderlich. Erlaubt sind 1 bis 36 Monate; rückwärts gerichtete und ungültige Bereiche werden zurückgewiesen. Alle Parameter werden validiert, die SQL-Abfragen parametrisiert.

## Antwortstruktur

```json
{
  "currency": "EUR",
  "decimals": 2,
  "from": "2026-10",
  "to": "2026-11",
  "complete": true,
  "months": [
    {
      "month": "2026-10",
      "income_minor": 0,
      "expense_minor": 0,
      "balance_minor": 0,
      "booking_count": 0,
      "transfer_count": 0,
      "transfer_minor": 0,
      "categories": {
        "income": [],
        "expense": []
      }
    }
  ]
}
```

Die Zahlen sind ausschließlich ein **Schemaplatzhalter**, keine realen Monatswerte. Bei tatsächlicher Antwort enthält `months` **jeden** angefragten Monat in aufsteigender Reihenfolge, auch ohne Buchungen. `complete: true` bezeichnet vollständige serverseitige Auswertung des ausgewählten Bestands, **nicht** eine Aussage, dass im aktuellen Monat bereits alle kommenden Buchungen stattgefunden haben.

Kategorieneinträge enthalten:

```json
{
  "category_id": 11,
  "category": "Einkauf / Lebensmittel",
  "amount_minor": 5000,
  "booking_count": 1
}
```

`income_minor`, `expense_minor`, `transfer_minor` und Kategorie-Summen sind positive ganze Zahlen der kleinsten Währungseinheit. `balance_minor = income_minor - expense_minor` kann negativ sein. `booking_count` umfasst reguläre berücksichtigte Einnahmen-/Ausgabenbuchungen mit Betrag ungleich null; Umbuchungen besitzen eigene Felder `transfer_count` und `transfer_minor` (absoluter Betrag aus Quellkontoperspektive). Saldoabgleiche und durchlaufende Posten samt Unterkategorien sind aus regulären Summen ausgeschlossen wie auf der Web-Startseite. Mehrere Unterkategorien werden niemals ohne ausdrücklichen Filter in eine einzige Kategorie zusammengefasst.

## Ist-Werte und zukünftige Buchungen

Nur Transaktionen mit Buchungsdatum **bis einschließlich heute in der Serverzeitzone** zählen als Ist-Werte. Später datierte Buchungen fließen nicht in die Monatswerte ein. Die interne gemeinsame Monatsfunktion kann Prognosesummen zusätzlich berechnen; der Mobile-Endpunkt **liefert derzeit bewusst keine Prognosefelder**. Android darf zukünftige Buchungen daher nicht in den Ist-Werten verstecken.

## Einheitliche Berechnung

Die Berechnung erfolgt durch die gemeinsam verwendete Funktion `summarize_months` in `package/src/monthly_reports.py`. Die beiden Monatsvergleiche auf der Web-Startseite und die historische Monats-Zeitreihe nutzen dieselbe Funktion. Damit werden Betragsvorzeichen, ausgeschlossene Sonderkategorien, Konten, Währungen und zukünftige Buchungen zentral behandelt. Web-Berichte mit zusätzlichen Suchtext- oder Kategorie-Ausblendungsfiltern sind **nicht** mit API-Anfragen ohne diese Filter vergleichbar.

## Fehlerverhalten

- `400`: ungültige Monatsgrenzen, mehr als 36 Monate, nicht vorhandene Währung/Kategorie, Konto in falscher Währung oder unbekannter Parameter.
- `401`: fehlender oder ungültiger API-Key.
- `500`: Datenbank-Lesefehler, ohne Veröffentlichung interner Fehlerdetails.

Fehler erscheinen im JSON-Objekt `{"error":"..."}`. Alte Server ohne `monthly_reports`-Capability werden nicht automatisch als vollständige Quelle behandelt; bei Fehlern darf Android keine Buchungs-Teilmenge als vollständige Monatsauswertung ausgeben.

## Unverändert

Kein Schreibendpunkt; keine Änderung an SQLite-Schema, Kontoständen, Buchungen, wiederkehrenden Regeln, Importen oder Backupformaten. Finanzdaten werden nicht in öffentlichen Caches gespeichert. Die bisherige Einzelbuchungs-API bleibt paginiert.

## Historische Spitzenbuchungen (Entwicklungsstand)

Das zusätzliche optionale Objekt `highlights` enthält die höchste **einzelne** gebuchte Ausgabe und Einnahme im gewählten Zeitraum. Es nutzt dieselben serverseitigen Filter (`from`, `to`, `currency`, `account_id`, `category_id`, optional `q`) wie `months[]` und die Webansicht **Historische Auswertung**. Umbuchungen, durchlaufende Posten und Saldoabgleiche einschließlich Unterkategorien, Vorlagen und künftige Buchungen sind ausgeschlossen. Gibt es keinen Treffer, ist der jeweilige Wert `null`. Die Beträge sind positive Integer in kleinsten Währungseinheiten; enthalten sind Buchungsdatum, Empfänger und vollständiger Kategorienpfad. `months[]` und `complete: true` bleiben unverändert.

Die Capabilities enthalten zusätzlich `features.history_highlights: true`, während `monthly_reports: true` erhalten bleibt. Ältere Clients dürfen das neue Feld ignorieren. Vorhandene Bearer-Read-Keys genügen; die API schreibt keine Daten. Der optionale Suchparameter `q` durchsucht Empfänger, Notiz und Kategoriebezeichnung (maximal 100 Zeichen; Steuerzeichen → HTTP 400). Der Suchtext wirkt gleichermaßen auf Monatswerte und Spitzenbuchungen.

```json
"highlights": {
  "largest_expense": {"date":"2026-11-12","amount_minor":12500,"payee":"Beispiel","category":"Haushalt / Einkauf"},
  "largest_income": null
}
```

Die Beispielbeträge sind keine echten Buchungswerte. Bei Betragsgleichheit entscheidet die kleinste Buchungs-ID. Web-Historie und Mobile-API verwenden dieselbe Funktion `largest_bookings` für die Spitzenwerte.
