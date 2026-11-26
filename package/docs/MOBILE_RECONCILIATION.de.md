# Mobile-API: Kontostandsabgleich

**Version:** 1.9.62-dev.4 (`develop`), 26.11.2026.

Der Server ist bei `DASHBOARD-SERVER` die einzige Datenquelle. Die Weboberfläche `POST /settings/accounts/reconcile` und die Mobile-API verwenden denselben transaktionalen Abgleichhelfer.

## Verfügbarkeit und Rechte

`GET /api/mobile/v1/capabilities` liefert `features.account_reconciliation: true`, zusätzlich zu `monthly_reports`, `history_highlights` und `recurring_rules`. Authentifizierung über `Authorization: Bearer <API-Key>`. Erforderlich sind ein gültiger **Write-Key**, eine aktive Admin-/Editorrolle und `finance_mode=web`. Antworten sind privat und nicht öffentlich cachebar.

## Aufruf

`POST /api/mobile/v1/accounts/{account_id}/reconcile`

```http
Authorization: Bearer <API-Key>
Content-Type: application/json
Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000
```

```json
{"actual_balance_minor":127500,"expected_balance_minor":125000,"note":"Kontostand abgeglichen"}
```

Alle drei Felder sind vorhanden, die Notiz darf leer sein und höchstens 500 Zeichen enthalten. Die Kontostände sind vorzeichenbehaftete Integer in den kleinsten Währungseinheiten des Serverkontos. Android übermittelt weder Differenz noch Währung. Die serverseitige Währung und Dezimalstellen stammen aus `GET /api/mobile/v1/accounts`.

## Antwort

```json
{
 "success":true,"account_id":12,"currency":"EUR","decimals":2,
 "previous_balance_minor":125000,"actual_balance_minor":127500,
 "change_minor":2500,"booking_id":15432,"unchanged":false,
 "balance_minor":127500,"projected_balance_minor":127500
}
```

Die Beträge sind Beispiele. `balance_minor` bezeichnet den geprüften Ist-Kontostand, `projected_balance_minor` enthält bereits gespeicherte zukünftige Buchungen. Bei keiner Differenz: `unchanged: true`, `change_minor: 0` und `booking_id: null`.

## Gemeinsame Buchungslogik

Innerhalb `BEGIN IMMEDIATE` ermittelt der Server den Ist-Kontostand als `account_snapshots.balance_minor - future_account_deltas(today)`. Stimmt er nicht mehr mit `expected_balance_minor` überein, erfolgt **409 ohne Buchung**. Die Differenz berechnet nur der Server. Positive/negative Korrekturen verwenden die schon bestehenden Kategorien **Kontostandskorrektur (Zugang/Abgang)**, die aus den regulären Einnahmen-/Ausgabenstatistiken ausgeschlossen sind. `apply_balance_delta` aktualisiert den Snapshot. Die Verifikation prüft den vollständigen Snapshot gegen tatsächlichen Saldo plus künftige Buchungsdifferenzen. Buchungsdatum ist der aktuelle Tag in `Europe/Berlin`. Der bestehende Audit-Eintrag erhält den API-Benutzer.

## Fehler, Konflikte, unklare Antworten

| Status | Bedeutung |
|---|---|
| 200 | Erfolgreich, auch bei Null-Differenz |
| 400 | Ungültiger Request, Betrag, Notiz oder UUID |
| 401 | Fehlender/ungültiger Schlüssel oder kein Schreibrecht |
| 404 | Konto unbekannt |
| 409 | Veralteter Ist-Saldo, inaktives Konto, Import-Modus oder UUID mit anderem Body |
| 500 | Datenbankfehler, **kein bestätigter Erfolg** |

Fehlerantwort: `{"error":"..."}`. Jeder Request braucht eine UUID als `Idempotency-Key`. Wiederholungen mit identischer Konto-ID, UUID und JSON erhalten dieselbe gespeicherte Antwort. Bei Timeout oder Verbindungsabbruch **niemals mit neuer UUID blind neu buchen**: Den identischen Request mit derselben UUID wiederholen oder zunächst den Serverzustand prüfen. Ein 409 wegen verändertem Saldo verlangt erneutes Abrufen und bewusste Bestätigung.

Nach 200: Konten über `GET /api/mobile/v1/accounts` und Buchungen über `GET /api/mobile/v1/bookings` neu laden; bei Bedarf Monatsberichte aktualisieren. Keine lokale Buchung in Android anlegen.

Keine neue Datenbankstruktur, keine Änderungen an Sicherungsformaten oder bestehenden API-Endpunkten.
