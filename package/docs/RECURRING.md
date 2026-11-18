# Wiederkehrende Buchungen

**Import:** Nur Financisto-Transaktionen mit `is_template=2` und `recurrence` werden als Vorlagen übernommen. Andere Buchungen sind nicht betroffen.

**Wiederholungsregeln:** Gewöhnliche monatliche Regeln mit Datum und Monatsintervall werden verarbeitet. Das erweiterte vierteljährliche Sonderformat ist nicht automatisch eindeutig; die Regel bleibt deaktiviert und muss auf ein bestätigtes Standardintervall umgestellt werden. Für einen nicht vorhandenen Monatstag wird der letzte Tag verwendet. Der automatische Ausführungszeitpunkt kann über „Ausführen ab“ festgelegt werden.

**Neue Regeln:** Der Tag im Monat wird aus dem Startdatum vorbelegt und bei dessen Änderung angepasst, solange kein eigener Monatstag eingestellt wurde. Bei täglich und wöchentlich wird das nicht relevante Monatstagsfeld ausgeblendet. Gespeicherte Regeln behalten ihre bisherigen Werte.

**Erstaktivierung:** Termine werden ab dem Tag der Aktivierung berechnet, nicht rückwirkend seit den ursprünglichen Jahren. Die automatische Ausführung benötigt eine gesonderte Admin-Freigabe. Der `recurring`-Dienst benötigt keine Netzwerkverbindung.

**Sicherheit:** Nur im Web-Finanzmodus; Transaktion, laufende Kontostandsänderung und eindeutiger Ausführungsnachweis erfolgen atomar in SQLite. Manuelle Wiederholungen können nur für bereits fällige Termine bestätigt werden. Bei fehlendem Konto, unbekanntem Saldo oder unbekannter Kategorie wird nicht gebucht.

**Daten:** Die drei neuen SQLite-Tabellen werden in den bestehenden täglichen Datenbankbackups mitgesichert. Ein vollständiger Import oder Rückimport aus Financisto löscht sie nicht. Änderungen an einer Regel deaktivieren diese zur erneuten Prüfung.

**Einschränkung:** Der Rückexport nach Financisto bildet die erzeugten Einzelbuchungen ab. Die Web-Wiederholungsregel selbst wird aktuell nicht zusätzlich als Financisto-Scheduler-Vorlage exportiert.

## 1.9.10 – Ausführungsmodi

**Pausiert:** Keine neue Buchung.
**Manuelle Buchung:** Bei Fälligkeit muss man die Einzelbuchung bewusst auslösen und mit `BUCHEN` bestätigen.
**Automatische Buchung:** Nur durch Administrator freizugeben; der Hintergrunddienst trägt die fällige Buchung in der Finanzdatenbank ein, keine echte Banküberweisung.

Die Auswahl erfolgt pro Regel über ein einziges Dropdown mit „Übernehmen“. Das Bearbeiten der Regelinhalte deaktiviert die Regel wie bisher zur erneuten Prüfung.

## 1.9.11 – Bearbeiten und Löschen

**Bearbeiten:** Das Formular öffnet sich im Dialog direkt über der Regelliste. Es wird nicht mehr zum Seitenende gesprungen. Die Änderung deaktiviert die Regel wie bisher zur erneuten Prüfung.

**Löschen:** Administratoren und Bearbeiter dürfen mit CSRF-Schutz und vollständiger Eingabe des Vorlagennamens eine Regel entfernen. Es handelt sich um eine Archivierung (`deleted_on`) – die Regel verschwindet aus der aktiven Liste, wird für automatische/manuelle Ausführung gesperrt und kann bei erneuten Imports derselben Financisto-Vorlage nicht ungewollt neu angelegt werden.

**Bereits gebuchte Umsätze und Kontostände bleiben erhalten.** Auch die Ausführungshistorie bleibt für die Auditierung nachvollziehbar.

**Docker:** Dashboard, Import, Sicherung und Wiederkehrend verwenden ein einziges Python-Image. Caddy bleibt separat. Das Update baut nur dieses Image und erzwingt nicht mehr den Neustart unveränderter Dienste. Alte Docker-Images werden für Rückfalloptionen nicht automatisch gelöscht.


**Rückwechsel:** Die SQLite-Regeln werden bei Wechsel zu Financisto deaktiviert. Sie werden nicht in Android zurücksynchronisiert. Der vorhandene Financisto-Testexport bewahrt die Original-Vorlagen, enthält aber keine späteren Web-Änderungen an deren Wiederholungslogik.

### Financisto-Rückexport (1.9.14)

Unter Einstellungen → Rückexport nach Financisto können im Testmodus automatisch aktive Monats-/Quartals-/Jahresregeln exportiert werden. Aus Sicherheitsgründen werden manuell aktive Regeln nicht als Android-Automatik exportiert. Pausierte und gelöschte Regeln entfallen aus der exportierten Android-Datei, bleiben aber in der Web-Datenbank inklusive Ausführungshistorie gespeichert. Unmodellierte Originalbuchungen werden nicht angetastet. Das Umschalten der Datenführung allein überträgt nichts.
