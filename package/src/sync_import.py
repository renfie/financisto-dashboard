# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2026 René Fieler (RenFie)
# See LICENSE and NOTICE.md for terms and third-party notices.

"""Offline importer with bounded, post-commit retention of uploaded Financisto files.

Only /data/inbox/*.backup are considered. No files on an Android device are touched.
"""
from __future__ import annotations
import logging
import re
from datetime import datetime
from zoneinfo import ZoneInfo
import os
import sqlite3
import time
import uuid
from pathlib import Path
from financisto_import import BackupError, ImportPaused, save_snapshot, parse_backup, normalized_backup

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
LOG = logging.getLogger('financisto-sync')
DB = Path(os.getenv('DATABASE_PATH', '/data/finanzen.sqlite3'))
INBOX = Path(os.getenv('SYNC_INBOX_PATH', '/data/inbox'))
ARCHIVE = INBOX.parent / 'import-archive'
REJECTED = INBOX.parent / 'import-errors'
MAX_FILE = 30 * 1024 * 1024
INTERVAL = 60
MIN_AGE = 120  # Finished uploads, never active transfers
RETAIN_GOOD = 3
RETAIN_BAD = 5
BAD_MAX_AGE = 14 * 86400

BACKUP_NAME = re.compile(r'^(\d{8})_(\d{6})_\d+\.backup$', re.I)
BACKUP_SUFFIX = re.compile(r'(\d{8})_(\d{6})_\d+\.backup$', re.I)
LOCAL_TZ = ZoneInfo('Europe/Berlin')


def backup_marker(path: Path, stat, now: float) -> int:
    """Use the real Financisto backup date, not the FolderSync upload date.

    This prevents a recently uploaded *old* backup from replacing the newest
    database. Fall back to mtime for nonstandard filenames.
    """
    match = BACKUP_SUFFIX.search(path.name)
    if match:
        try:
            instant = datetime.strptime(''.join(match.groups()), '%Y%m%d%H%M%S')
            stamp = instant.replace(tzinfo=LOCAL_TZ).timestamp()
            if 946684800 <= stamp <= now + 86400:
                return round(stamp * 1_000_000_000)
        except (ValueError, OverflowError):
            pass
    return stat.st_mtime_ns


def stable(entry, original, now):
    """Only ordinary, sufficiently old files unchanged since the initial scan."""
    try:
        return (not entry.is_symlink() and entry.is_file()
                and (now - entry.stat().st_mtime >= MIN_AGE)
                and entry.stat().st_size == original.st_size
                and entry.stat().st_mtime_ns == original.st_mtime_ns)
    except OSError:
        return False


def bounded_cleanup(directory: Path, keep: int, now: float, max_age=None):
    """Never touch unrecognized files or symlinks; only app-managed .backup files."""
    try:
        records = [(backup_marker(p, p.stat(), now), p) for p in directory.glob('*.backup')
                   if p.is_file() and not p.is_symlink()]
    except OSError as exc:
        LOG.warning('Archiv nicht lesbar %s: %s', directory, exc)
        return
    records.sort(key=lambda pair: pair[0], reverse=True)
    for pos, (_, path) in enumerate(records):
        try:
            # Retain last three successful backups regardless of age.
            expired = max_age is not None and now - path.stat().st_mtime > max_age
            if pos >= keep or expired:
                path.unlink()
                LOG.info('Alte Sicherung bereinigt: %s/%s', directory.name, path.name)
        except OSError as exc:
            LOG.warning('Bereinigung fehlgeschlagen %s: %s', path.name, exc)


def move_managed(source: Path, original, destination: Path, now: float):
    """Move (not copy) after import / validation; never move a changing upload."""
    if not stable(source, original, now):
        LOG.warning('Datei vor Verschieben verändert; bleibt in Inbox: %s', source.name)
        return False
    try:
        destination.mkdir(parents=True, exist_ok=True)
        unique = f'{time.time_ns()}-{uuid.uuid4().hex[:8]}-{source.name}'
        source.rename(destination / unique)
        LOG.info('Sicherung verschoben: %s -> %s', source.name, destination.name)
        return True
    except OSError as exc:
        LOG.warning('Datei konnte nicht verschoben werden: %s: %s', source.name, exc)
        return False


def scan_once(now=None):
    now = time.time() if now is None else now
    if not INBOX.is_dir() or not DB.is_file():
        LOG.info('Datenbank oder Inbox fehlt; neuer Versuch später.')
        return 'not_ready'

    # When paused, do not even run file retention/validation: incoming
    # backups remain untouched and can be processed if later re-enabled.
    try:
        with sqlite3.connect(DB, timeout=10) as db:
            db.execute('PRAGMA busy_timeout=10000')
            mode = db.execute("SELECT value FROM meta WHERE key='finance_mode'").fetchone()
            enabled = db.execute("SELECT value FROM meta WHERE key='auto_import_enabled'").fetchone()
        if (mode and mode[0] != 'import') or (enabled and enabled[0] != '1'):
            return 'paused'
    except sqlite3.Error as exc:
        LOG.warning('Importsteuerung nicht lesbar: %s', exc)
        return 'error'
    candidates=[]
    try:
        for entry in INBOX.iterdir():
            if entry.suffix.lower() != '.backup' or entry.is_symlink() or not entry.is_file():
                continue
            try:
                st=entry.stat()
            except OSError:
                continue
            if now-st.st_mtime < MIN_AGE:
                continue
            candidates.append((backup_marker(entry, st, now), entry.name, entry, st))
    except OSError as exc:
        LOG.error('Inbox nicht lesbar: %s',exc)
        return 'error'
    if not candidates:
        bounded_cleanup(REJECTED, RETAIN_BAD, now, max_age=BAD_MAX_AGE)
        return 'no_new_files'
    candidates.sort(reverse=True)
    # Retention is also checked on quiet days, without waiting for another failed upload.
    bounded_cleanup(REJECTED, RETAIN_BAD, now, max_age=BAD_MAX_AGE)
    result='no_new_files'
    for marker, _, source, original in candidates:
        if not stable(source,original,now):
            continue
        if original.st_size <= 0 or original.st_size > MAX_FILE:
            LOG.warning('Sicherung hat ungültige Größe: %s', source.name)
            if move_managed(source,original,REJECTED,now):
                bounded_cleanup(REJECTED,RETAIN_BAD,now,max_age=BAD_MAX_AGE)
            result='invalid'
            continue
        try:
            with sqlite3.connect(DB, timeout=20) as db:
                db.execute('PRAGMA busy_timeout=20000')
                latest=db.execute("SELECT value FROM meta WHERE key='last_import_source_mtime_ns'").fetchone()
            if latest and int(latest[0]) >= marker:
                # Older than our last snapshot. Validate before archiving it, too.
                with source.open('rb') as file:
                    old_raw = file.read(MAX_FILE + 1)
                if not stable(source,original,now) or len(old_raw) != original.st_size:
                    result = 'still_copying'
                    continue
                old_accounts, _, _, _, old_tx = normalized_backup(parse_backup(old_raw))
                if not old_accounts or not old_tx:
                    raise BackupError('Alte Sicherung unvollständig.')
                if move_managed(source,original,ARCHIVE,now):
                    bounded_cleanup(ARCHIVE,RETAIN_GOOD,now)
                continue
            with source.open('rb') as file:
                raw=file.read(MAX_FILE+1)
            if not stable(source,original,now) or len(raw) != original.st_size:
                LOG.warning('Datei während des Lesens verändert: %s',source.name)
                result='still_copying'
                continue
            with sqlite3.connect(DB, timeout=20) as db:
                db.execute('PRAGMA busy_timeout=20000')
                db.execute('BEGIN IMMEDIATE')
                imported=save_snapshot(db,raw,source='automatic',source_mtime_ns=marker)
                # SQLite context commits only after successful save_snapshot.
            result=imported['status']
            if result == 'imported':
                LOG.info('Sicherung %s importiert: %d Buchungen',source.name,imported['count'])
            if result in ('imported','unchanged','older'):
                if move_managed(source,original,ARCHIVE,now):
                    bounded_cleanup(ARCHIVE,RETAIN_GOOD,now)
            # A valid latest snapshot supersedes older inbox files, processed next loop.
            if result in ('imported','unchanged'):
                return result
        except ImportPaused:
            LOG.info('Automatischer Import inzwischen deaktiviert; Dateien bleiben erhalten.')
            return 'paused'
        except BackupError as exc:
            LOG.error('Sicherung %s ungültig (Daten unverändert): %s',source.name,exc)
            if move_managed(source,original,REJECTED,now):
                bounded_cleanup(REJECTED,RETAIN_BAD,now,max_age=BAD_MAX_AGE)
            result='invalid'
        except (sqlite3.Error, OSError, ValueError) as exc:
            # Transient SQLite / filesystem errors are not grounds for deleting files.
            LOG.error('Sicherung %s derzeit nicht importierbar: %s',source.name,exc)
            return 'error'
    return result


def main():
    LOG.info('Auto-Import-Dienst gestartet. Ordner=%s, Intervall=%ss, Mindestalter=%ss; Archiv=%d, Fehler=%d',
             INBOX,INTERVAL,MIN_AGE,RETAIN_GOOD,RETAIN_BAD)
    previous = None
    while True:
        try:
            status = scan_once()
            if status == 'paused' and previous != 'paused':
                LOG.info('Automatischer Import in den Webeinstellungen ausgeschaltet; eingehende Dateien bleiben liegen.')
            if previous == 'paused' and status != 'paused':
                LOG.info('Automatischer Import wieder freigegeben.')
            previous = status
        except Exception:
            LOG.exception('Unerwarteter Importfehler; Finanzdaten bleiben erhalten')
        time.sleep(INTERVAL)

if __name__ == '__main__':
    main()
