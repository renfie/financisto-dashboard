# FieLanzen als Android-App installieren (v1.9.27)

1. Dashboard über die bestehende HTTPS-Domain auf dem Android-Telefon öffnen.
2. In Chrome oder Samsung Internet über das Browser-Menü „App installieren“ oder „Zum Startbildschirm hinzufügen“ wählen.
3. FieLanzen über das neue Wolfs-Icon starten. Login und 2FA erfolgen wie bisher.

## Sicherheit und Betrieb
- Installation setzt vom Telefon aus vertrauenswürdiges HTTPS voraus. Eine lokale Caddy-Zertifizierungsstelle muss dem Telefon vertrauenswürdig sein; über die öffentliche HTTPS-Domain ist dies einfacher.
- Kein Offline-Betrieb: alle Konto- und Buchungsdaten bleiben ausschließlich serverseitig. Der Service Worker speichert keinerlei Antwort.
- Bestehende Mobile-Navigation, Einstellungen, Telegram, Gotify, Importe und Sync bleiben unverändert.
- Eine PWA ist keine APK; sie wird direkt aus dem Browser installiert. Eine separat signierte APK kann später erstellt werden.
- Die Installation erteilt weder neue Benutzerrechte noch umgeht sie Netzwerkzugriffsschutz/2FA.

Siehe WEB_PUSH.md für die Benachrichtigungen in der PWA ab v1.9.31.
