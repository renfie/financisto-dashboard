# Zeitraum-Schnellfilter und Cashflow (v1.9.45)

**Sprache / Language:** [English](CASHFLOW.en.md) | Deutsch

## Schnellfilter

Die Buchungsliste bietet 1W (letzte sieben Tage einschließlich heute), 1M (laufender Kalendermonat), 3M (laufender und zwei vorangegangene Kalendermonate) sowie 6M (laufender und fünf vorangegangene Kalendermonate). Mit **Monatsauswahl** wird der bisherige Zeitraum zwischen den beiden Vergleichsmonaten wiederhergestellt. Die Monatskarten und der Kategorienvergleich behalten ihren bisher unabhängig gewählten Zeitraum.

Das erweiterte Suchfeld ist über **Filter** erreichbar; darüber hinaus führen die **Erweiterten Monats-, Konto- und Kategoriefilter** zu den bisherigen Diagramm- und Listenfiltern. Der schnelle Textfilter beschränkt nur die Buchungsliste, nicht die Diagramme oder Monatssummen. Auswahl und Sortierung können über die URL geteilt werden; es werden keine Einstellungen dauerhaft geändert.

## Cashflow-Diagramm

Das neue Diagramm zeigt Einnahmen, Ausgaben und den Netto-Cashflow je Tag (1W), Wochenabschnitt (1M) oder Monat (3M, 6M und Monatsauswahl). Die Balken zeigen Einnahmen und Ausgaben, die dunkel gestrichelte Linie den Netto-Wert je Zeitraum (Überschuss oberhalb, Defizit unterhalb der mittleren Nulllinie, eigene Skala). Daten werden ausschließlich auf deinem Server aggregiert. Kein Tracking, keine externen Diagrammbibliotheken.

**Abgrenzung:** Umbuchungen zwischen eigenen Konten, durchlaufende Posten, Konto-/Depotwert-Korrekturen und zukünftige Buchungsdaten gelten nicht als realisierter Cashflow. Die Cashflow-Auswertung verändert keine Buchungsdaten oder Kontostände. Bei künftigen Buchungsdaten bleibt die gelbe Kennzeichnung in der Liste erhalten, auch wenn die Cashflow-Zahlen sie nicht mitzählen.

Es werden nur Buchungen in der gewählten Währung berücksichtigt; ohne Währungsumrechnung. Konto-, Kategorie- und erweiterte Suchfilter gelten für die Chart-Daten. Der separate Buchungslisten-Schnellfilter verändert das Cashflow-Diagramm nicht.

## Dashboard-Reihenfolge und Seitennavigation

Die aufklappbare **Buchungsliste** befindet sich direkt unter den Kontoständen und vor Ausgaben nach Kategorien und Cashflow. Sie ist normalerweise eingeklappt. Über **Zu den Buchungen**, Seitenzahlen oder einen Sortier-/Filterlink öffnet sich der Bereich automatisch. Die Seitenzahlen ermöglichen den direkten Sprung zu einer bestimmten Seite, inklusive Auslassungszeichen bei vielen Seiten.

Die Farben des Cashflow-Diagramms folgen der Farbpalette der monatlichen Kategorie-Auswertung: türkis für Einnahmen, orange für Ausgaben. Die Linie hat eine eigene Skala um null und ist daher nicht als Kontostand oder unmittelbar gleich skalierter Balkenwert zu lesen. Alle Diagramme entstehen offline.

## Buchungsaktionen

Auf PC und ausreichend breiten Fenstern stehen **Klonen**, **Bearbeiten** und **Löschen** ohne Umbruch nebeneinander. Auf Tablets und Smartphones bleibt die größere, berührungsfreundliche Kartenansicht erhalten.

## Anzeige ab 1.9.47
Der Cashflow ist beim Laden der Dashboard-Startseite zugeklappt, kann aber jederzeit manuell oder per Link `#cashflow` geöffnet werden. Die Buchungsliste ist dagegen beim Laden geöffnet.
