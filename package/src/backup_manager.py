"""Daily SQLite snapshots. Only automatic snapshots are pruned.

Each backup is created through SQLite's backup API, validated, then atomically
published. Never expose this directory via Caddy or import it as Financisto.
"""
from __future__ import annotations
import logging
import json
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
FINANCISTO_FORMAT_REV = 18


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


def _financisto_status_file(db_path: Path) -> Path:
    return export_dir(db_path) / 'status.json'


def financisto_status(db_path: Path = DB) -> dict:
    """Persist separately from SQLite: the UI must never confuse old .backup files
    with a successfully created CURRENT backup. No financial data is stored here.
    """
    default = dict(last_attempt='', last_success='', last_filename='', last_day='',
                   error='', ok=None, format_revision=0, recurring_templates=None,
                   transaction_count=None)
    directory = export_dir(db_path, create=False)
    if directory is None:
        return default
    path = directory / 'status.json'
    if path.is_symlink() or not path.is_file():
        return default
    try:
        with path.open('r', encoding='utf-8') as stream:
            value = json.load(stream)
        if isinstance(value, dict):
            for name in default:
                if name in value and isinstance(value[name], type(default[name])):
                    default[name] = value[name]
                elif name in value and default[name] is None:
                    default[name] = value[name]
    except (OSError, ValueError, TypeError):
        pass
    return default


def _save_financisto_status(db_path: Path, data: dict) -> None:
    directory = export_dir(db_path)
    fd, temp = tempfile.mkstemp(prefix='.status-', suffix='.tmp', dir=directory)
    os.fchmod(fd, 0o600)
    tmp = Path(temp)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(data, stream, ensure_ascii=False, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
        tmp.replace(directory / 'status.json')
    finally:
        tmp.unlink(missing_ok=True)


def export_current_financisto(db_path: Path = DB, *, day=None, force=False) -> str:
    """Create and validate a current-data Financisto backup including scheduled
    templates. On failure keep older files but publish the failure prominently.
    SQLite backups remain independent and are never touched here.
    """
    directory = export_dir(db_path)
    now = datetime.now(TZ)
    day = day or now.strftime('%Y%m%d')
    former = financisto_status(db_path)
    # Version migration: old .backup files from dev.17 can be incomplete.
    # A new dev.18 process must re-export even when such a file exists today.
    if (not force and former.get('format_revision') == FINANCISTO_FORMAT_REV
            and former.get('last_day') == day and former.get('last_filename')
            and (directory / former['last_filename']).is_file()):
        return 'already_backed_up'
    attempt = now.isoformat(timespec='seconds')
    try:
        with sqlite3.connect(db_path, timeout=30) as db:
            db.row_factory = sqlite3.Row
            db.execute('BEGIN')
            try:
                raw, stats = make_export(db)
                raw, stats = merge_recurring_export(db, raw, stats)
            finally:
                db.rollback()
        if not 0 < len(raw) <= FINANCISTO_MAX_BYTES:
            raise RuntimeError('Financisto-Export größer als 30 MiB oder leer')
        parsed = parse_backup(raw)
        if not parsed.get('transactions') or not parsed.get('account'):
            raise RuntimeError('Financisto-Export ohne Konten oder Buchungen')
        # All scheduled, exportable rules must have become native templates.
        expected_templates = stats.get('recurring_exported')
        actual_templates = sum(1 for row in parsed['transactions']
                               if row.get('is_template') == '2' and row.get('recurrence'))
        if expected_templates is None or actual_templates != expected_templates:
            raise RuntimeError('Wiederholungsvorlagen unvollständig: '
                               f'{actual_templates}/{expected_templates}')
        name = f'financisto-aktuell-{day}-{now:%H%M%S}-{secrets.token_hex(3)}.backup'
        fd, temp = tempfile.mkstemp(prefix='.financisto-', suffix='.backup', dir=directory)
        os.fchmod(fd, 0o600)
        tmp = Path(temp)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            dest = directory / name
            if dest.exists() or dest.is_symlink():
                raise RuntimeError('Financisto-Dateiname bereits vorhanden')
            tmp.replace(dest)
        finally:
            tmp.unlink(missing_ok=True)
        success = dict(former, last_attempt=attempt, last_success=attempt,
                       last_filename=name, last_day=day, ok=True, error='',
                       format_revision=FINANCISTO_FORMAT_REV,
                       recurring_templates=actual_templates,
                       transaction_count=len(parsed['transactions']))
        _save_financisto_status(db_path, success)
        # Prune only successfully published automatic Financisto files.
        files = sorted((p for p in directory.iterdir() if FINANCISTO_NAME.fullmatch(p.name)
                        and p.is_file() and not p.is_symlink()),
                       key=lambda p: p.name, reverse=True)
        for old in files[FINANCISTO_KEEP:]:
            old.unlink()
        LOG.info('Financisto-Sicherung erstellt: %s, Buchungen inkl. Vorlagen: %d, Vorlagen: %d',
                 name, len(parsed['transactions']), actual_templates)
        return 'created'
    except (ExportError, BackupError, sqlite3.Error, OSError, RuntimeError,
            ValueError, KeyError, TypeError) as exc:
        error = str(exc)[:600] or type(exc).__name__
        failed = dict(former, last_attempt=attempt, ok=False, error=error)
        try:
            _save_financisto_status(db_path, failed)
        except OSError as status_exc:
            LOG.error('Financisto-Status konnte nicht gespeichert werden: %s', status_exc)
        LOG.warning('Kein frisches Financisto-Backup erstellt: %s', error)
        raise


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
