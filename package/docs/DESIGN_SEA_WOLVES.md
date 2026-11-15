# Financisto Dashboard – Sea-Wolves-Design v1.9.17

Dieses Theme verwendet die Originalgrafiken `wolf-logo.webp` und `favicon.png` aus dem
vorherigen benutzereigenen Projekt `NPM_Fehlerseiten_Responsive_v3.zip`.
Die Grafiken werden lokal vom eigenen Dashboard ausgeliefert; keine externen Abrufe/Tracker.

## Dateien
- `static/sea-wolves-logo.webp`: Logo in der Navigation
- `static/sea-wolves-favicon.png`: Browser-Favicon
- `static/sea-wolves-watermark.webp`: aus Logo abgeleitete, entfärbte Version mit Transparenz
- `static/wolves-theme.css`: visuelle Anpassungen (wird nach der bisherigen `style.css` geladen)

## Darstellung
- Desktop: helle Seitenleiste, aktiver Menüpunkt mit goldener Linie
- Mobil: weiße Kopfzeile, aufklappbares Menü
- Hintergrund: schwach sichtbares Wolf-Logo ohne Beeinträchtigung der Inhalte
- Druck: keine Seitennavigation oder Wasserzeichen; Finanzberichte bleiben lesbar

## Update
`cd /home/pi/docker-files && unzip -o financisto-dashboard-v1.9.17.zip && ./financisto-release-1.9.17/update.sh`

Bei Anzeige des vorherigen Designs Browser mit Strg+F5 neu laden.
Dieses Update ändert keine Datensätze, Zugriffsrechte, Importlogik oder Finanzfunktionen.
