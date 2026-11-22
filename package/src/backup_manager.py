"""Daily SQLite snapshots. Only automatic snapshots are pruned.

Each backup is created through SQLite's backup API, validated, then atomically
published. Never expose this directory via Caddy or import it as Financisto.
"""
from __future__ import annotations
import logging
import os
import re
import secrets
import sqlite3
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from financisto_export import make_export, ExportError
from financisto_recurring_export import merge_recurring_export
from financisto_import import parse_backup, BackupError

LOG = logging.getLogger('finance-backup')
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
DB = Path(os.getenv('DATABASE_PATH', '/data/finanzen.sqlite3'))
TZ = ZoneInfo('Europe/Berlin')
KEEP = 14
INTERVAL = 3600
AUTO_NAME = re.compile(r'^automatisch-\d{8}-\d{6}-[0-9a-f]{6}\.sqlite3$')
FINANCISTO_KEEP = 2
FINANCISTO_NAME = re.compile(r'^financisto-aktuell-\d{8}-\d{6}-[0-9a-f]{6}\.backup$')
FINANCISTO_MAX_BYTES = 30 * 1024 * 1024


def target_dir(db_path: Path) -> Path:
    directory = db_path.parent / 'web-backups'
    if directory.is_symlink():
        raise RuntimeError('Unsicherer Sicherungsordner (Symlink)')
    directory.mkdir(mode=0o700, exist_ok=True)
    directory.chmod(0o700)
    return directory


def create_backup(db_path: Path = DB, label='automatisch') -> Path:
    if not re.fullmatch(r'[a-z0-9-]{1,45}', label):
        raise ValueError('Ungültige Sicherungsbezeichnung')
    if db_path.is_symlink() or not db_path.is_file():
        raise RuntimeError('Datenbank fehlt oder ist ein Symlink')
    directory = target_dir(db_path)
    now = datetime.now(TZ)
    name = f'{label}-{now:%Y%m%d-%H%M%S}-{secrets.token_hex(3)}.sqlite3'
    fd, tmp = tempfile.mkstemp(prefix='.backup-', suffix='.sqlite3', dir=directory)
    os.fchmod(fd, 0o600)
    os.close(fd)
    tmp_path = Path(tmp)
    try:
        with sqlite3.connect(f'file:{db_path}?mode=ro', uri=True, timeout=20) as src:
            with sqlite3.connect(tmp_path, timeout=20) as dest:
                src.backup(dest, pages=256, sleep=0.05)
                if dest.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise RuntimeError('SQLite integrity_check fehlgeschlagen')
                for table in ('users', 'transactions', 'accounts', 'meta'):
                    found = dest.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
                    if not found:
                        raise RuntimeError('Sicherung unvollständig: ' + table)
        # Ensure data is on disk before publishing.
        with tmp_path.open('rb') as handle:
            os.fsync(handle.fileno())
        final = directory / name
        if final.exists() or final.is_symlink():
            raise RuntimeError('Sicherungsname schon vorhanden')
        tmp_path.rename(final)
        dfd = os.open(directory, os.O_RDONLY | getattr(os,'O_DIRECTORY',0))
        try: os.fsync(dfd)
        finally: os.close(dfd)
        LOG.info('SQLite-Sicherung erstellt: %s', final.name)
        return final
    finally:
        tmp_path.unlink(missing_ok=True)


def prune_automatic(directory: Path, keep: int = KEEP) -> int:
    """Never delete manual, upgrade, pre-switch, or other backup families."""
    if directory.is_symlink() or not directory.is_dir():
        return 0
    candidates = []
    for path in directory.iterdir():
        if AUTO_NAME.fullmatch(path.name) and path.is_file() and not path.is_symlink():
            candidates.append(path)
    candidates.sort(key=lambda p: p.name, reverse=True)
    removed = 0
    for path in candidates[keep:]:
        path.unlink()
        removed += 1
    return removed


def status(db_path: Path = DB) -> dict:
    directory = target_dir(db_path)
    files = [p for p in directory.iterdir() if AUTO_NAME.fullmatch(p.name) and p.is_file() and not p.is_symlink()]
    files.sort(key=lambda p:p.name, reverse=True)
    return {'last': files[0].name if files else '', 'count':len(files)}


def enabled(db_path: Path = DB) -> bool:
    with sqlite3.connect(f'file:{db_path}?mode=ro', uri=True, timeout=10) as db:
        row = db.execute("SELECT value FROM meta WHERE key='daily_backup_enabled'").fetchone()
    return row is None or row[0] == '1'


def scan_once(db_path: Path = DB, today=None):
    if not db_path.is_file():
        return 'not_ready'
    if not enabled(db_path):
        return 'paused'
    now = datetime.now(TZ)
    day = today or now.strftime('%Y%m%d')
    directory = target_dir(db_path)
    prefix = f'automatisch-{day}-'
    sqlite_exists = any(p.is_file() and not p.is_symlink() and AUTO_NAME.fullmatch(p.name) and p.name.startswith(prefix) for p in directory.iterdir())
    if not sqlite_exists:
        create_backup(db_path, 'automatisch')
    prune_automatic(directory)
    try:
        export_current_financisto(db_path, day=day)
    except (ExportError, BackupError, sqlite3.Error, OSError, ValueError, RuntimeError) as exc:
        LOG.warning('Aktuelle Financisto-Sicherung nicht erstellt: %s', exc)
    return 'already_backed_up' if sqlite_exists else 'created'


def export_dir(db_path: Path, *, create=True) -> Path | None:
    directory = db_path.parent / 'financisto-backups'
    if directory.is_symlink():
        raise RuntimeError('Unsicherer Financisto-Sicherungsordner (Symlink)')
    if create:
        directory.mkdir(mode=0o700, exist_ok=True)
        directory.chmod(0o700)
    elif not directory.is_dir():
        return None
    return directory


def current_financisto_backups(db_path: Path = DB) -> tuple:
    """Only app-created current-data exports; never the old Android archive."""
    directory = export_dir(db_path, create=False)
    if directory is None:
        return ()
    result = []
    for path in directory.iterdir():
        if not FINANCISTO_NAME.fullmatch(path.name) or path.is_symlink() or not path.is_file():
            continue
        info = path.stat()
        if not 0 < info.st_size <= FINANCISTO_MAX_BYTES:
            continue
        result.append(dict(name=path.name, size=info.st_size, day=path.name[19:27]))
    result.sort(key=lambda item: item['name'], reverse=True)
    return tuple(result[:FINANCISTO_KEEP])


def export_current_financisto(db_path: Path = DB, *, day=None, force=False) -> str:
    """Create one immutable export per day from the live Web ledger.

    Requires a compatible original source; refuses unsupported recurring rules.
    There is no destructive import, no mutation to transactions, and no fallback
    to older Android backups when the current-data export fails.
    """
    directory = export_dir(db_path)
    now = datetime.now(TZ)
    day = day or now.strftime('%Y%m%d')
    prefix = 'financisto-aktuell-' + day + '-'
    if not force and any(item['name'].startswith(prefix) for item in current_financisto_backups(db_path)):
        return 'already_backed_up'
    with sqlite3.connect(db_path, timeout=30) as db:
        db.row_factory = sqlite3.Row
        db.execute('BEGIN')
        try:
            # The plain return exporter preserves original transaction rows
            # but does not materialize Web-created recurring rule templates.
            # Require the verified recurring pass for *all* automated backups.
            # Unsupported rule semantics raise an explicit error; never write
            # an apparently complete .backup with missing schedules.
            raw, stats = make_export(db)
            raw, stats = merge_recurring_export(db, raw, stats)
        finally:
            db.rollback()
    if not 0 < len(raw) <= FINANCISTO_MAX_BYTES:
        raise RuntimeError('Financisto-Export größer als 30 MiB oder leer')
    parsed = parse_backup(raw)
    if not parsed.get('transactions') or not parsed.get('account'):
        raise RuntimeError('Financisto-Export ohne Konten oder Buchungen')
    name = prefix + now.strftime('%H%M%S') + '-' + secrets.token_hex(3) + '.backup'
    fd, tmp = tempfile.mkstemp(prefix='.financisto-', suffix='.backup', dir=directory)
    os.fchmod(fd, 0o600)
    tmp_path = Path(tmp)
    try:
        with os.fdopen(fd,'wb') as writer:
            writer.write(raw)
            writer.flush()
            os.fsync(writer.fileno())
        final = directory / name
        if final.exists() or final.is_symlink():
            raise RuntimeError('Financisto-Dateiname schon vorhanden')
        tmp_path.rename(final)
        dir_fd = os.open(directory, os.O_RDONLY | getattr(os,'O_DIRECTORY',0))
        try: os.fsync(dir_fd)
        finally: os.close(dir_fd)
    finally:
        tmp_path.unlink(missing_ok=True)
    files = sorted((x for x in directory.iterdir()
                    if FINANCISTO_NAME.fullmatch(x.name) and x.is_file() and not x.is_symlink()),
                   key=lambda x:x.name, reverse=True)
    for old in files[FINANCISTO_KEEP:]:
        old.unlink()
    LOG.info('Aktueller Financisto-Rückexport gesichert: %s (%s Buchungen)', name, stats['transactions'])
    return 'created'



def main():
    if sys.argv[1:] != ['--daemon']:
        raise SystemExit('Aufruf: python backup_manager.py --daemon')
    LOG.info('SQLite-Tagesbackup aktiv: Prüfung alle %s Sekunden, %s automatische Sicherungen',INTERVAL, KEEP)
    while True:
        try:
            scan_once()
        except Exception:
            LOG.exception('Tagesbackup fehlgeschlagen; erneuter Versuch beim nächsten Intervall')
        time.sleep(INTERVAL)

if __name__ == '__main__':
    main()
