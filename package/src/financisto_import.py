"""Reader for Financisto gzip backups (legacy and modern Android package IDs)."""
from __future__ import annotations
import gzip
import io
from datetime import datetime
from zoneinfo import ZoneInfo

MAX_EXPANDED = 65 * 1024 * 1024
TZ = ZoneInfo('Europe/Berlin')

class BackupError(ValueError):
    pass

class ImportPaused(RuntimeError):
    """Import intentionally halted by dashboard settings; never archive or reject."""


def parse_backup(raw: bytes):
    if not raw.startswith(b'\x1f\x8b'):
        raise BackupError('Keine gültige komprimierte Financisto-Sicherung (.backup).')
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as f:
            data = f.read(MAX_EXPANDED + 1)
    except (OSError, EOFError, ValueError) as e:
        raise BackupError('Die Sicherungsdatei ist beschädigt oder unvollständig.') from e
    if len(data) > MAX_EXPANDED:
        raise BackupError('Die entpackte Sicherung überschreitet 65 MiB.')
    text = data.decode('utf-8-sig', errors='replace')
    lines = text.splitlines()
    # Legacy Financisto and the current Android fork use the same backup
    # container, but a different package ID. Unknown apps stay rejected.
    allowed = {'PACKAGE:ru.orangesoftware.financisto', 'PACKAGE:tw.tib.financisto'}
    if not lines or lines[0] not in allowed or '#START' not in lines or not lines or lines[-1] != '#END':
        raise BackupError('Die Datei hat kein unterstütztes Financisto-Format.')
    result = {'account': [], 'category': [], 'currency': [], 'payee': [], 'transactions': []}
    entity = None
    row = None
    for ln in lines:
        if ln.startswith('$ENTITY:'):
            entity = ln[len('$ENTITY:'):]
            row = {}
        elif ln == '$$':
            if entity in result and row is not None:
                result[entity].append(row)
            entity = None
            row = None
        elif entity is not None and row is not None and ':' in ln:
            key, val = ln.split(':', 1)
            row[key] = val
    if not result['transactions'] or not result['account']:
        raise BackupError('In der Sicherung fehlen Konten oder Buchungen.')
    # Do not silently replace imported values with zero if a future Android
    # version renames the underlying fields. New optional fields are allowed.
    required = {
        'account': ('_id', 'title', 'currency_id'),
        'transactions': ('_id', 'datetime', 'from_account_id', 'from_amount'),
        'category': ('_id', 'title'),
        'currency': ('_id', 'name', 'decimals'),
    }
    for kind, fields in required.items():
        for pos, item in enumerate(result[kind], 1):
            missing = [field for field in fields if field not in item]
            if missing:
                raise BackupError(f'Unbekannte Feldstruktur in {kind} (Datensatz {pos}): {", ".join(missing)}')
    for t in result['transactions']:
        for key in ('_id', 'datetime', 'from_account_id', 'from_amount'):
            try:
                int(t[key])
            except (ValueError, TypeError):
                raise BackupError(f'Ungueltiges Zahlenfeld {key} in Transaktion.') from None
    return result


def as_int(value, default=0):
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def normalized_backup(records):
    """Return table rows. Amounts are kept in original minor currency units."""
    accounts = [(as_int(a.get('_id')), a.get('title', '')[:250], as_int(a.get('currency_id')), a.get('type', '')[:50]) for a in records['account']]
    currencies = [(as_int(a.get('_id')), a.get('name','')[:20], a.get('symbol','')[:10], as_int(a.get('decimals'), 2)) for a in records['currency']]
    cats = [(as_int(c.get('_id')), c.get('title','')[:250], as_int(c.get('left')), as_int(c.get('right')), as_int(c.get('type'))) for c in records['category']]
    payees = [(as_int(p.get('_id')), p.get('title','')[:250]) for p in records['payee']]
    tx = []
    for t in records['transactions']:
        millis = as_int(t.get('datetime'))
        try:
            date = datetime.fromtimestamp(millis / 1000, TZ).date().isoformat()
        except (ValueError, OSError, OverflowError):
            continue
        tx.append((as_int(t.get('_id')), date, as_int(t.get('from_account_id')),
                   as_int(t.get('to_account_id')), as_int(t.get('category_id')),
                   as_int(t.get('payee_id')), as_int(t.get('from_amount')),
                   t.get('note','')[:5000], as_int(t.get('is_template'))))
    return accounts, currencies, cats, payees, tx



def ensure_account_snapshots(db):
    """Independent ledger totals from Financisto's own account snapshot.

    This table contains no manually maintained balances. Older databases are
    extended in place and existing Financisto tables are not restructured.
    """
    db.execute('''CREATE TABLE IF NOT EXISTS account_snapshots (
        account_id INTEGER PRIMARY KEY,
        balance_minor INTEGER,
        include_in_totals INTEGER,
        is_active INTEGER
    )''')


def account_snapshot_rows(records):
    """Return account balance/flags, retaining NULL for unknown values.

    Never infer an opening balance from transaction history: Financisto's
    total_amount is already the authoritative current account balance.
    """
    def optional_integer(value):
        if value is None or value == '':
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            raise BackupError('Financisto enthält einen ungültigen Kontostand oder Kontostatus.') from None

    result = []
    for account in records['account']:
        account_id = as_int(account.get('_id'))
        result.append((account_id,
                       optional_integer(account.get('total_amount')),
                       optional_integer(account.get('is_include_into_totals')),
                       optional_integer(account.get('is_active'))))
    return result



def save_snapshot(db, raw: bytes, *, source: str, source_mtime_ns: int | None = None, allow_destructive: bool = False):
    """Atomically replace Financisto snapshot, never touching household/auth/allowlist.

    Must be called with a SQLite connection whose context manager commits/rolls back.
    Manual uploads use a wall-clock barrier; automatic imports use preserved file mtime.
    """
    import hashlib
    import time
    from datetime import datetime

    # Checked INSIDE the SQLite write transaction so a running worker cannot
    # race with turning off auto-import or switching the source of truth.
    mode = db.execute("SELECT value FROM meta WHERE key='finance_mode'").fetchone()
    enabled = db.execute("SELECT value FROM meta WHERE key='auto_import_enabled'").fetchone()
    writes = db.execute("SELECT value FROM meta WHERE key='ledger_web_writes'").fetchone()
    if mode and mode[0] != 'import':
        raise ImportPaused('Web-Finanzverwaltung ist führend; Import nur als Vorschau möglich.')
    pending = db.execute("SELECT value FROM meta WHERE key='import_overwrite_pending'").fetchone()
    approved = db.execute("SELECT value FROM meta WHERE key='import_overwrite_approved'").fetchone()
    has_edits = (writes and int(writes[0]) > 0) or (pending and pending[0] == '1')
    may_replace = (source == 'manual' and allow_destructive) or (source == 'automatic' and approved and approved[0] == '1')
    if has_edits and not may_replace:
        raise ImportPaused('Web-Änderungen vorhanden; Überschreiben erfordert ausdrückliche Zustimmung.')
    if source == 'automatic' and enabled and enabled[0] != '1':
        raise ImportPaused('Auto-Import in der Weboberfläche deaktiviert.')
    records = parse_backup(raw)
    accounts, currencies, cats, payees, tx = normalized_backup(records)
    balances = account_snapshot_rows(records)
    # Keep the exact source as a DB BLOB so future SQLite backups contain the
    # required legacy/fork-specific attributes for a non-lossy return export.
    # Refuse unexpected/empty snapshots before touching any existing financial records.
    if not accounts or not tx:
        raise BackupError('Sicherung enthält keine vollständigen Konten/Buchungen.')
    if len({r[0] for r in accounts}) != len(accounts) or len({r[0] for r in tx}) != len(tx):
        raise BackupError('Sicherung enthält doppelte IDs; keine Daten verändert.')
    digest = hashlib.sha256(raw).hexdigest()
    now_ns = time.time_ns()
    # Use source file timestamp for automatic imports so an old backup cannot
    # override a newer imported snapshot. Manual uploads set a freshness barrier.
    marker = now_ns if source == 'manual' else source_mtime_ns
    if not isinstance(marker, int) or marker <= 0:
        raise BackupError('Ungültiger Sicherungs-Zeitstempel.')
    existing = db.execute("SELECT value FROM meta WHERE key='last_import_source_mtime_ns'").fetchone()
    if source == 'automatic' and existing and int(existing[0]) >= marker:
        return {'status':'older','count':len(tx),'sha256':digest}
    same = db.execute("SELECT value FROM meta WHERE key='last_import_sha256'").fetchone()
    if source == 'automatic' and same and same[0] == digest and not has_edits:
        # Still advance file timestamp to avoid rechecking copies of same content.
        db.execute("INSERT OR REPLACE INTO meta VALUES ('last_import_source_mtime_ns',?)",(str(marker),))
        return {'status':'unchanged','count':len(tx),'sha256':digest}
    # All replacement statements share the caller's SQLite transaction.
    ensure_account_snapshots(db)
    db.execute('DELETE FROM account_snapshots')
    from financisto_export import store_matching_source
    store_matching_source(db, raw, sha256=digest)
    for table in ('transactions', 'payees', 'categories', 'accounts', 'currencies'):
        db.execute(f'DELETE FROM {table}')
    db.executemany('INSERT INTO accounts VALUES (?,?,?,?)', accounts)
    db.executemany('INSERT INTO currencies VALUES (?,?,?,?)', currencies)
    db.executemany('INSERT INTO categories VALUES (?,?,?,?,?)', cats)
    db.executemany('INSERT INTO payees VALUES (?,?)', payees)
    db.executemany('''INSERT INTO transactions
        (id,day,account_id,to_account_id,category_id,payee_id,amount,note,is_template)
        VALUES (?,?,?,?,?,?,?,?,?)''', tx)
    db.executemany('''INSERT INTO account_snapshots
                      (account_id,balance_minor,include_in_totals,is_active)
                      VALUES (?,?,?,?)''', balances)
    properties = {
        'last_import':datetime.now().strftime('%d.%m.%Y %H:%M'),
        'tx_count':str(len(tx)),
        'last_import_source':'Automatisch (Android)' if source == 'automatic' else 'Manuell',
        'last_import_sha256':digest,
        'last_import_source_mtime_ns':str(marker)
    }
    db.executemany('INSERT OR REPLACE INTO meta(key,value) VALUES (?,?)',properties.items())
    if has_edits:
        db.execute("INSERT OR REPLACE INTO meta(key,value) VALUES ('ledger_web_writes','0')")
        db.execute("INSERT OR REPLACE INTO meta(key,value) VALUES ('import_overwrite_pending','0')")
        db.execute("INSERT OR REPLACE INTO meta(key,value) VALUES ('import_overwrite_approved','0')")
    return {'status':'imported','count':len(tx),'sha256':digest}
