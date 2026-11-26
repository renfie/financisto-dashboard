# Separater Entwicklungsauftrag: FieLanzen Android – vollständige Monatsauswertungen im Servermodus

**Repository:** `renfie/fielanzen-android-offline`

**Zielbranch:** `developer` (erst nach separater Freigabe)

**Ausgangsversion:** mindestens `0.1.0-alpha.34`

**Voraussetzung:** Die Dashboard-API `/api/mobile/v1/reports/monthly` wurde erfolgreich getestet, zur Veröffentlichung freigegeben und meldet `features.monthly_reports: true`.

## Arbeitsauftrag

1. **Darstellung:** Die lokalen Startseiten-, Vergleichs-, Grafik- und Monatsansichten bleiben identisch; ausschließlich der Datenanbieter ist je nach aktivem Modus unterschiedlich. Keine abweichende Server-UI erstellen.
2. **Capability-Prüfung:** Bei Verbindungsaufbau die vorhandenen Capabilities abrufen. Nur bei `features.monthly_reports === true` den neuen Endpunkt als vollständige Monatsquelle verwenden.
3. **Abruf:** Beim Öffnen und bei Filteränderung `GET /api/mobile/v1/reports/monthly` anfragen, mit ISO-Monaten `from`/`to`, ausgewählter Währung, Konto- und Kategorie-ID. Voreinstellung: zwölf Monate; bei zwei frei gewählten Vergleichsmonaten ggf. ihren Bereich zusätzlich anfordern (maximal 36 Monate pro Anfrage).
4. **Startseite:** Die zwei frei gewählten Vergleichsmonate einschließlich historischer Monate ausschließlich aus den jeweils vollständigen Monatsdatensätzen darstellen. Die vorhandene Vergleichsgrafik aus `income_minor` und `expense_minor` aufbauen.
5. **Reiter „Monat“:** Vollständigen Zwölfmonatsverlauf mit jedem Monat (auch Nullmonaten) aus der Serverantwort aufbauen. Kategorien gruppenweise aus `months[].categories.income/expense` anzeigen; absolute Minorbeträge anhand `decimals` für die Anzeige formatieren, niemals vor der Berechnung runden.
6. **Ist-/Prognose-Trennung:** `complete:true` bedeutet sämtliche serverseitig berücksichtigten Buchungen bis einschließlich heutigem Datum, keine Prognose. Zukünftige Transaktionen nicht ergänzen. Falls später Prognosefelder hinzukommen, getrennt visualisieren.
7. **Buchungsliste:** Weiterhin über die vorhandene, paginierte `/api/mobile/v1/bookings` abrufen; diese Teilmenge darf niemals als vollständige Monatsauswertung gelten.
8. **Offline-Modus:** Die lokale Datenbank, lokalen Wiederholungsregeln und lokalen Monatsauswertungen unverändert beibehalten. Kein Speichern serverseitiger Monatswerte als lokale Finanzbuchungen und keine Synchronisation der Datenbestände.
9. **Fehlerzustand:** Fehlt die Capability, lautet der Zustand „Vollständige Monatsauswertung vom Server nicht unterstützt“. Bei Netzwerk-/API-Fehler „Monatsauswertung derzeit nicht verfügbar“. Keinesfalls Zahlen aus unvollständig geladenen Einzelbuchungen als vollständige Monatswerte darstellen. Bereits zuletzt angezeigte Serverwerte nur mit sichtbarer Kennzeichnung „veraltet“, niemals als frisch und vollständig ausgeben.
10. **Aktualisierung:** Nach einer erfolgreich gespeicherten Serverbuchung oder Änderung an wiederkehrenden Serverregeln die betroffenen Berichte neu abrufen; keine Einzelbuchungs-Differenz nachträglich in aggregierte Werte hineinrechnen.

## Abnahmetests

- Vergleich der Android-Anzeige mit der Dashboard-Startseite bei identischer Währung/Konto/Kategorie sowie zwei frei gewählten Monaten.
- Lückenlose historische Monatswerte unabhängig von API-Buchungspagination, auch bei 0 Buchungen.
- Gleiche Ein-/Ausgaben, Saldo, Kategoriepfade, Umbuchungsausschluss sowie Ausschluss durchlaufender Posten und Saldoabgleiche.
- Getrennte Währungen, unterschiedliche Konto- und Kategorieauswahl, einschließlich Unterkategorien.
- Zukunftsdatierte Buchung verändert die gebuchten Ist-Werte nicht.
- Fehlende Capability, 401, 400 und Verbindungsverlust zeigen keinen als vollständig bezeichneten Teilbericht.
- Umschalten Server → Lokal → Server verändert keine Daten, hält die lokale UI einheitlich und ruft im Servermodus ausschließlich Serverwerte ab.

**Nicht Bestandteil des jetzigen Dashboard-Auftrags:** Commit, APK-Build oder Android-Repository-Änderung. Alle Android-Änderungen erst nach separater Beauftragung und Zustimmung durchführen.
