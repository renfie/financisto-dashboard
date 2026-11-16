Financisto-Dashboard v1.9.49 – öffentliches Sammelrelease (16.11.2026)

Vollständiges Installations- und Update-Paket, kompatibel mit vorhandenem
Financisto-Dashboard v1.9.43–v1.9.48 (auch frühere unterstützte Versionen).

Alle Änderungen seit dem zuletzt auf GitHub veröffentlichten v1.9.43:
  * Zahlreiche deutsche/englische Übersetzungsfehler behoben, zuletzt beim
    Rückwechsel zu Financisto (das Bestätigungswort bleibt FINANCISTO).
  * Cashflow-Diagramm, 1W/1M/3M/6M-Schnellfilter, ausklappbare Suche.
  * Kontostände, Buchungen, Ausgaben nach Kategorien, Cashflow in Reihenfolge.
  * Buchungen standardmäßig offen, Cashflow standardmäßig geschlossen.
  * Anklickbare Seitenzahlen, kompakte Desktop-Buchungsaktionen.
  * Verbesserte A5-Berichts-/Importübersetzungen, optionales APP_FOOTER_EN.

Details: package/CHANGELOG.md und package/CHANGELOG.en.md.

Upgrade als Eigentümer der bestehenden Installation, OHNE sudo:
  unzip -o financisto-dashboard-v1.9.49.zip
  ./financisto-release-1.9.49/update.sh /pfad/zum/financisto-dashboard

Vor dem Update legt das Skript eine SQLite-Sicherung und eine Sicherung des
Programmcodes samt .env an. Produktive Daten, Benutzerkonten, Secrets und
Caddy-Zertifikate werden bei der regulären Aktualisierung beibehalten.

Neuinstallation: im entpackten package/ ./install.sh ausführen.
