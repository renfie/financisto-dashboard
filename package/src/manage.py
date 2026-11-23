#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2026 René Fieler (RenFie)
# See LICENSE and NOTICE.md for terms and third-party notices.

"""Local recovery actions for the owner of the SQLite database.

Run inside the dashboard container as the project owner. No web endpoint exposes
this privileged recovery interface. Never print a TOTP seed or a password hash.
"""
import argparse
import ipaddress
import os
import sqlite3

p = argparse.ArgumentParser(description='Financisto: lokale Notfallverwaltung')
sub = p.add_subparsers(dest='cmd', required=True)
add = sub.add_parser('add-ip', help='Eine IP-Adresse freigeben')
add.add_argument('ip')
add.add_argument('label', nargs='?', default='Notfallfreigabe')
sub.add_parser('list-ips', help='Freigegebene IPs anzeigen')
reset = sub.add_parser('reset-totp', help='2FA eines Benutzers bei Geräteverlust zurücksetzen')
reset.add_argument('username')
reset.add_argument('--yes', action='store_true', help='Rücksetzung ausdrücklich bestätigen')
args = p.parse_args()
path = os.environ.get('DATABASE_PATH', '/data/finanzen.sqlite3')
with sqlite3.connect(path) as db:
    if args.cmd == 'add-ip':
        value = str(ipaddress.ip_address(args.ip))
        db.execute('INSERT OR IGNORE INTO allowed_clients(ip,label) VALUES (?,?)', (value,args.label[:100]))
        print('Freigabe geprüft/angelegt für:', value)
    elif args.cmd == 'list-ips':
        for row in db.execute('SELECT ip,label FROM allowed_clients ORDER BY id'):
            print(*row, sep='  |  ')
    elif args.cmd == 'reset-totp':
        if not args.yes:
            raise SystemExit('Keine Änderungen. Zum Bestätigen --yes ergänzen.')
        row = db.execute('SELECT id FROM users WHERE username=?', (args.username,)).fetchone()
        if not row:
            raise SystemExit('Benutzer nicht gefunden; nichts geändert.')
        db.execute('''UPDATE users SET totp_seed_enc=NULL,totp_enabled=0,last_totp_step=-1,
                      version=version+1 WHERE id=?''', (row[0],))
        db.execute('DELETE FROM recovery_codes WHERE user_id=?', (row[0],))
        db.execute('INSERT INTO audit_events(actor_id,event,detail) VALUES(NULL,?,?)',
                   ('2fa_emergency_reset_local', args.username))
        print('2FA zurückgesetzt; nächster Login mit bestehendem Passwort erfordert erneute TOTP-Einrichtung.')
