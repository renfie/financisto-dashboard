# Entwicklungsauftrag für FieLanzen Android – Server-Kontostandsabgleich

**Ziel:** Repository `renfie/fielanzen-android-offline`, Branch `developer`, geplant ab Alpha 37. Dieser Auftrag verändert das Android-Repository **nicht**.

Die bestehende lokale Abgleichmaske soll auch im Servermodus genutzt werden. Sie zeigt das ausgewählte Konto, den bisherigen Ist-Kontostand, das Eingabefeld für den tatsächlichen Kontostand, eine unmittelbar berechnete *Vorschau*-Differenz und eine optionale Notiz. Keine Weiterleitung zum Web-Dashboard. Nur der Daten- und Speicherweg unterscheidet sich; lokale Regeln und Buchungen bleiben vollständig unabhängig.

**Erkennung:** `GET /api/mobile/v1/capabilities` → `features.account_reconciliation === true`. Zusätzlich `GET /api/mobile/v1/session` auswerten: Schreibrecht und `finance_mode=web`. Ohne Capability/Recht keine Speicherung anbieten.

**Kontodaten:** Aus `GET /api/mobile/v1/accounts` `id`, `balance_minor` (heutiger Ist-Saldo), `projected_balance_minor`, `currency`, `decimals`, `active` verwenden. Negative Salden und Währungen mit null bis drei Nachkommastellen korrekt formatieren. Differenz nur als lokale Vorschau anzeigen; die verbindliche Berechnung und Buchung erfolgt ausschließlich auf dem Server.

**HTTP:** `POST /api/mobile/v1/accounts/{account_id}/reconcile`, Bearer-Write-Key, JSON, UUID-`Idempotency-Key`:

```json
{"actual_balance_minor":127500,"expected_balance_minor":125000,"note":"Kontostand abgeglichen"}
```

Alle Beträge sind vorzeichenbehaftete Integer in kleinsten Währungseinheiten. Der erwartete Saldo ist der **zuletzt vom Server gelesene** `balance_minor`. Keine Kategorie oder Buchungsdifferenz mitsenden. Notiz bis 500 Zeichen.

**Erfolg (200):** `success`, `account_id`, `currency`, `decimals`, `previous_balance_minor`, `actual_balance_minor`, `change_minor`, `booking_id`, `unchanged`, `balance_minor`, `projected_balance_minor`. Bei `unchanged:true` keine Korrekturbuchung melden. Nach Erfolg `GET /api/mobile/v1/accounts` und `GET /api/mobile/v1/bookings` erneut abrufen; auch Monatsberichte aktualisieren, soweit angezeigt. Keine lokale Finanzbuchung anlegen.

**Fehler:** 400 Eingaben prüfen, 401 Rechte/Schlüssel prüfen, 404 Konto nicht gefunden, 409 Konflikt oder nicht führender Server, 500 Datenbankfehler. Bei 409 wegen Saldoänderung neuen Serverstand anzeigen und ausdrücklich erneut bestätigen lassen. **Keine automatische Konfliktübernahme.**

**Unsichere Antwort (Timeout/Verbindungsabbruch):** Konto-ID, JSON-Body und UUID bis zur endgültigen Antwort unverändert halten; exakt diesen Request mit derselben UUID wiederholen oder zunächst auf dem Server prüfen. Niemals mit einer anderen UUID automatisch erneut buchen.

**Abnahme:** Gleiches Layout im Offline- und Servermodus; positive/negative/Null-Differenz, Negativsalden, mehrere Währungen, Konflikte, fehlende Rechte und Zeitüberschreitungen prüfen. Die lokale Offline-Implementierung unverändert lassen.
