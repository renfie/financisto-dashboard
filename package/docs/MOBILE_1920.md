# Mobile-Feintuning in Version 1.9.20

Die zusätzliche Datei `static/mobile.css` setzt nur bei `@media screen and (max-width:760px)` an und verändert keine Druckansichten. `static/mobile.js` synchronisiert den neuen Menüknopf „Mehr“ mit dem vorhandenen oberen Menü; die bestehenden serverseitigen Benutzerrechte steuern weiterhin, welche Schnellziele angeboten werden.

Die Buchungsansicht verwendet auf Smartphones Karten mit identischen Daten und Server-Filtern wie die Desktop-Tabelle. Für die Sortierung gibt es auf mobilen Geräten ein eigenes aufklappbares Menü, während die Desktop-Tabelle ihre klickbaren Spaltenköpfe behält.

Das Dashboard hat weiterhin die gemeinsamen Filter der historischen Auswertung und den 30er-Seitenumfang, sofern nicht durch den Administrator verändert. Im Designer sind keine Datenbanktabellen oder Container ergänzt worden.
