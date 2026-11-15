# Rückexport in Financisto (`.backup`): Testfunktion 1.9.5

## Voraussetzungen

1. Administrator mit eingerichteter TOTP-2FA.
2. Die zuletzt tatsächlich importierte Original-Sicherung muss als exportierbare Grundlage in SQLite gespeichert sein. Das Upgrade übernimmt sie automatisch aus `data/import-archive` oder `data/inbox`, wenn SHA256 exakt übereinstimmt. Falls nicht, kann sie über Einstellungen hochgeladen werden, ohne Finanzdaten zu überschreiben.
3. Der Export rekonstruiert heutige Web-Buchungen und Stammdaten und kopiert alle übrigen Datenfelder und Entitäten der Originaldatei. Der Export ist **experimentell**.

## Datenschutz

Die SQLite-Datenbank enthält die exportierte Originaldatei als unveränderten gzip-BLOB. Dies ist **keine Verschlüsselung**. DB, Backups und heruntergeladene Dateien vertraulich behandeln. Die DB-Sicherungen enthalten diese Datei vollständig.

## Tests

Lokale Tests prüfen die GZIP-Struktur, Paketkennung, Pflichtfelder, IDs, Gesamtanzahl, historische Buchungen und Web-Buchungen. Eine **echte Rücksicherung auf Android** wurde nicht durchgeführt, insbesondere nicht mit der aktuellen Android-Version DB 257. Der Export ist noch nicht als voll kompatibler Rückweg freigegeben.

Nicht die produktive Handyinstallation damit überschreiben! Nur auf einem zweiten Testgerät/-profil mit dortiger Testdatenbank prüfen, ob Konten, Kategorien, Empfänger, Umbuchungen, Buchungsbeträge und Kontostände korrekt sind.


### Kontrollierter Rückexport wiederkehrender Buchungen (1.9.14)

Auf **Einstellungen → Rückexport nach Financisto** die Option für Wiederholungen aktivieren. Nur explizit freigegebene **automatische Monats-/Quartals-/Jahresregeln** werden in das exakte bekannte `MONTHLY:EVERY_NTH_DAY`-Format umgewandelt. Importierte Vorlagen werden aktualisiert; neue Web-Vorlagen erhalten neue, kollisionsfreie IDs. Pausierte und archivierte Vorlagen erscheinen nicht in der Android-Datei. Manuell aktive und nicht sicher unterstützte Intervallformate werden **nicht** stillschweigend übertragen: Der Export wird mit einer Fehlermeldung abgebrochen.

Unveränderte Transaktionen und alle Stammdaten bleiben erhalten. Durch das Exportieren oder durch den Wechsel des führenden Systems wird **nichts auf das Smartphone übertragen**; hierfür die resultierende `.backup` bewusst in Financisto importieren. `last_recurrence` wird vorsorglich auf mindestens den Exportzeitpunkt gesetzt; ob die Android-App damit alte Termine tatsächlich nicht nachholt, muss auf einem getrennten Testprofil geprüft werden. Der Android-Import von Wiederholungsregeln ist weiterhin experimentell.

Ohne aktivierte Option verhält sich der Testexport unverändert wie in 1.9.13.

