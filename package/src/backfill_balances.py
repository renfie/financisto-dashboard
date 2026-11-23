#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2026 René Fieler (RenFie)
# See LICENSE and NOTICE.md for terms and third-party notices.

"""One-time, safe balance extraction from an already imported archived backup.

Only a backup whose SHA-256 matches the transaction snapshot in SQLite is used.
No Financisto transaction or account row is replaced, and no archive is deleted.
"""
from __future__ import annotations
import hashlib
import os
import sqlite3
from pathlib import Path
from financisto_import import BackupError, account_snapshot_rows, ensure_account_snapshots, parse_backup


def restore(db_file: Path, archive: Path) -> str:
    if not db_file.exists():
        return 'Noch keine Datenbank – Kontostände folgen beim ersten Import.'
    with sqlite3.connect(db_file, timeout=20) as db:
        ensure_account_snapshots(db)
        already = db.execute('SELECT COUNT(*) FROM account_snapshots').fetchone()[0]
        if already:
            return 'Kontostände bereits gespeichert.'
        current = db.execute("SELECT value FROM meta WHERE key='last_import_sha256'").fetchone()
        expected = current[0] if current else ''
    if not expected:
        return 'Kein Import-Fingerabdruck vorhanden; Kontostände folgen beim nächsten Import.'
    for path in sorted(archive.glob('*.backup'), reverse=True) if archive.is_dir() else ():
        if path.is_symlink() or not path.is_file():
            continue
        try:
            if not 0 < path.stat().st_size <= 30*1024*1024:
                continue
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != expected:
                continue
            balances = account_snapshot_rows(parse_backup(raw))
            with sqlite3.connect(db_file, timeout=20) as db:
                db.execute('BEGIN IMMEDIATE')
                actual = db.execute("SELECT value FROM meta WHERE key='last_import_sha256'").fetchone()
                accounts = {a[0] for a in db.execute('SELECT id FROM accounts')}
                if not actual or actual[0] != expected or accounts != {a[0] for a in balances}:
                    db.rollback()
                    return 'Kontenbestand hat sich geändert; kein Abgleich durchgeführt.'
                existing = db.execute('SELECT COUNT(*) FROM account_snapshots').fetchone()[0]
                if existing:
                    db.rollback()
                    return 'Kontostände wurden inzwischen bereits importiert.'
                ensure_account_snapshots(db)
                db.executemany('''INSERT INTO account_snapshots
                    (account_id,balance_minor,include_in_totals,is_active)
                    VALUES (?,?,?,?)''', balances)
            return f'Kontostände aus passender Archiv-Sicherung ergänzt: {len(balances)} Konten.'
        except (OSError, sqlite3.Error, BackupError, ValueError) as exc:
            # Do not leak private backup contents in error logs.
            return f'Kontostand-Abgleich übersprungen: {type(exc).__name__}. Nächster Import aktualisiert die Konten.'
    return 'Keine zum aktuellen Import passende Archiv-Sicherung; Kontostände folgen beim nächsten Import.'


if __name__ == '__main__':
    project = Path(os.environ.get('FINANCISTO_PROJECT_DIR', Path(__file__).resolve().parent))
    print(restore(project / 'data/finanzen.sqlite3', project / 'data/import-archive'))
