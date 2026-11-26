# Mobile-API für wiederkehrende Serverbuchungen

Version: 1.9.62-dev.1 · Stand: 26.11.2026 · nur Entwicklungszweig

Die Android-App verwendet dieselben Ansichten wie im Offline-Modus, liest und verändert im Servermodus jedoch ausschließlich Serverregeln. Keine Synchronisation lokaler Regeln, keine Änderungen an Backupformaten oder bestehenden Finanzdaten.

## Verbindung, Rechte und Endpunkte

Basis: `/api/mobile/v1`; Authentifizierung: `Authorization: Bearer <API-Key>`. Der bestehende Read-Key darf Regeln abrufen. Sämtliche Mutationen erfordern einen Write-Key, gültigen Administrator-/Editorzugang und führenden Web-Finanzmodus. Nur ein Administrator kann `auto` einschalten. `GET /capabilities` meldet `features.recurring_rules=true`.

| HTTP | Pfad | Verhalten |
|---|---|---|
| GET | /recurring | Nicht archivierte Regeln lesen |
| POST | /recurring | Vollständigen Entwurf speichern, immer pausiert |
| PUT | /recurring/{id} | Vollständig bearbeiten und pausieren |
| PUT | /recurring/{id}/mode | paused / manual / auto ausdrücklich wählen |
| POST | /recurring/{id}/post | Einen fälligen manuellen Termin bestätigen |
| DELETE | /recurring/{id} | Regel archivieren, keine historischen Buchungen löschen |

GET-Antwort:
```json
{"items":[{"id":11,"revision":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","title":"Miete","kind":"expense","account_id":1,"to_account_id":0,"category_id":2,"payee_id":0,"payee_title":"Vermieter","amount_minor":95000,"note":"","frequency":"monthly","interval_count":1,"day_of_month":28,"start_on":"2026-11-01","run_at":"09:30","end_on":null,"max_occurrences":12,"completed_count":3,"next_on":"2026-11-28","mode":"manual","needs_review":""}]}
```

POST/PUT verlangen dieselben Entwurfsfelder wie GET ohne `id`, `revision`, `mode`, `next_on`, `completed_count`, `needs_review` und `payee_id`. Der `amount_minor` ist im JSON stets positiv; die gespeicherten Vorzeichen ergeben sich aus `kind`. Unterstützte Frequenzen: daily, weekly, monthly, quarterly, yearly; Intervall 1–120, Monatstag 1–31, `run_at` HH:MM.

Jede Mutation benötigt `Idempotency-Key: <UUID>`, vorhandene Regeln zusätzlich `If-Match: <aktuelle 32-stellige Revision>`. Ein bereits gespeicherter erfolgreicher Request wird bei Wiederholung mit gleichem Schlüssel und Body ausschließlich aus dem Receipt beantwortet. Ein anderer Body oder eine veraltete Revision scheitert. Bei ungewisser Antwort denselben Schlüssel erneut verwenden und niemals unkontrolliert mit neuem Schlüssel buchen. Das Dashboard verhindert zusätzlich mehrere manuelle Buchungen derselben Regel am selben Kalendertag.

Moduswechsel:
```json
{"mode":"manual"}
```
Fällige manuelle Buchung:
```json
{"confirm":"BUCHEN"}
```
Archivierung:
```json
{"confirm_title":"Miete"}
```

Die Regelrevision wird als 32-stelliger Hex-Hash aus dem Regelstand und dem Ausführungszähler abgeleitet. Bereits erzeugte Buchungen, `recurring_runs`, Kontosalden und Audit-Historie bleiben bei Bearbeitung/Archivierung erhalten. Automatische Buchungen führt nur der vorhandene Scheduler aus. Fehler: 400 Eingabe, 401 Authentifizierung, 403 fehlendes Recht, 404 archiviert/nicht vorhanden, 409 Konflikt, 428 fehlende Revision.
