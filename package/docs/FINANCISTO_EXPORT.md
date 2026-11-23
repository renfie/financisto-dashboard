# Financisto-Rückexport (`.backup`) – Stand 1.9.58-dev.18

## Ein zentraler Sicherungsbereich

Unter **Einstellungen → Automatische Datensicherung** werden täglich unabhängig voneinander eine SQLite-Sicherung sowie ein Financisto-Rückexport versucht. **Jetzt Sicherung erstellen** löst beide unabhängig voneinander aus – ohne erneut Adminpasswort oder 2FA abzufragen; die reguläre Admin-Sitzung mit CSRF-Schutz ist ausreichend. Den früheren separaten Testexport gibt es nicht mehr.

Die SQLite-Sicherung ist das vollständige Wiederherstellungsformat des Web-Dashboards und enthält alle Regeln. Die `.backup`-Datei ist für den separat zu prüfenden Rückimport in Financisto vorgesehen. Die zwei letzten erfolgreichen `.backup`-Dateien stehen als Download bereit. Der tatsächliche letzte Exportversuch, seine Uhrzeit und eine eventuelle Fehlermeldung sind gesondert sichtbar; ältere Backups sind bei einem Fehler nicht aktuell.

Die **zuletzt importierte Originaldatei** muss SHA256-genau als Vorlage gespeichert sein. Ist sie nicht vorhanden, lässt sie sich im gleichen Sicherungsbereich hochladen; das ändert keine Finanzdaten und überschreibt keine Buchungen.

## Terminierte Buchungen und Vorlagen

Ausgeführte Buchungen werden als Buchungsdatensätze exportiert. Wiederkehrende Regeln werden als Financisto-Wiederholungsvorlagen exportiert, sofern ihr Verhalten im bekannten nativen Format sicher darstellbar ist. Unveränderte ursprüngliche Vorlagen werden übernommen. Kompatible automatisch aktive Monats-/Quartals-/Jahresregeln werden erzeugt und gezählt. Die tatsächlich ausgegebenen Vorlagen werden gegen die erwartete Zahl geprüft.

**Nicht sicher unterstützte** Web-Regeln (u. a. wöchentliche oder tägliche Sonderformen, individuelle Ausführungszeiten, begrenzte Laufzeit sowie pausierte Web-only-Regeln) führen zu einem **klaren Exportfehler statt einer unvollständigen `.backup`-Datei**. Die bisherige erfolgreiche Datei bleibt erhalten, die unabhängige SQLite-Sicherung läuft weiter. Originale Financisto-Vorlagen, die nur im Web pausiert wurden, behalten im Financisto-Export ihre originale Definition: Das Pause-Flag lässt sich nicht verlustfrei übertragen und ist bei Android-Rückimport zu prüfen.

## Sicherheit und Prüfung

Die Quelle liegt in SQLite als originaler gzip-BLOB (keine zusätzliche Verschlüsselung). Die Verzeichnisse und heruntergeladenen Dateien sind vertraulich zu behandeln. Die Statusdatei `data/financisto-backups/status.json` enthält Erfolg/Fehler, Zeit und Vorlagenanzahl, keine Schlüssel. Ein Export greift nicht schreibend auf Buchungen oder Kontostände zu.

Struktur, Pflichtfelder, Datensatz- und Wiederholungsvorlagenanzahl werden geprüft. Ein produktiver Android-Restore ist damit **nicht nachgewiesen**. Neue `.backup`-Dateien deshalb zuerst in einer separaten Financisto-Testinstallation importieren, Konten, Buchungen, Terminregeln und deren nächste Fälligkeiten kontrollieren und keinesfalls ungeprüft die einzige produktive Handy-Datenbank überschreiben.
