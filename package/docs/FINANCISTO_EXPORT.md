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

## Begrenzungen von wiederkehrenden Regeln (ab 1.9.58-dev.19)

Financisto kennt `EXACTLY_TIMES:count@N#` für eine maximale Anzahl sowie `STOPS_ON_DATE:date@yyyyMMddT000000#` für ein Enddatum. Für Web-Monats-, Quartals- und Jahresregeln wird das jeweils zutreffende Format geschrieben; bei zwei Grenzen wird die **früher wirksame** Grenze verwendet. Das Schema wurde anhand der nativen Financisto-Java-Klassen `RecurrencePeriod` und `RecurrenceViewFactory` geprüft.

**Achtung:** Web-Regeln für den 29., 30. oder 31. können nicht ohne Termindifferenz in das native `BYMONTHDAY`-Muster übertragen werden, da das Web die Termine in kurzen Monaten auf den letzten Tag verschiebt, Financisto aber überspringt. Ein solcher Export wird ausdrücklich abgebrochen. Andere noch nicht kompatible Intervalle bleiben ebenso blockiert. Die SQLite-Sicherung enthält sämtliche Web-Regeln vollständig. Der Rückimport der erzeugten Datei muss separat auf Android getestet werden.

## Monatstag 29–31 (ab 1.9.58-dev.20)

Wenn im Web eine Monatsregel bei kürzeren Monaten auf den letzten Kalendertag fällt, wird für den Financisto-Rückexport statt `MONTHLY:EVERY_NTH_DAY` das native `GEEKY`-Muster mit einer iCalendar-RRULE verwendet. Für den 30. wird beispielsweise `FREQ=MONTHLY;INTERVAL=1;BYMONTHDAY=30,-1;BYSETPOS=1` verwendet. Für den 29. gilt das entsprechende Muster, für den 31. `BYMONTHDAY=-1`. Bei Regeln mit Enddatum und/oder Wiederholungsanzahl wird die exakte Anzahl der zulässigen Termine als `COUNT` in der RRULE codiert, weil der GEEKY-Modus den normalen Financisto-Wiederholungszeitraum nicht verarbeitet.

Das Muster wurde anhand des Original-Quellcodes von Financisto verifiziert und die generierten Termine mit einem iCalendar-Iterator gegenüber dem Web-Planungsalgorithmus getestet. Die tatsächliche Ausführung in der Original-Android-App muss vor produktiver Wiederherstellung in einer Testinstallation geprüft werden.
