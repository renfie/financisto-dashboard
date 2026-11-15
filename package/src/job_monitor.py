"""Persist only operational metadata about the single background worker.

No financial contents, file payloads, secrets or login details are stored.
The dashboard reads these markers and independently inspects backup metadata.
"""
from __future__ import annotations
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import sqlite3
import time

TZ = ZoneInfo('Europe/Berlin')
PERIODS = {'auto-import': 60, 'recurring': 900, 'backup': 3600}
LABELS = {'auto-import': 'Financisto-Import',
          'recurring': 'Wiederkehrende Buchungen',
          'backup': 'SQLite-Datensicherung'}
RESULT_LABELS = {
    'imported': 'Neue Sicherung importiert',
    'unchanged': 'Sicherung bereits vorhanden',
    'older': 'Ältere Sicherung geprüft',
    'no_new_files': 'Keine neue Sicherung',
    'not_ready': 'Datenbank oder Inbox noch nicht bereit',
    'still_copying': 'Datei wird noch übertragen',
    'invalid': 'Ungültige Sicherung erkannt',
    'paused': 'Ausführung pausiert',
    'created': 'Sicherung erstellt',
    'already_backed_up': 'Tagessicherung bereits vorhanden',
    'error': 'Fehler bei der Prüfung',
    'ok': 'Prüfung erfolgreich',
    'posted': 'Fällige Buchung eingetragen',
    'no_due': 'Keine fällige Buchung',
}


def ensure_schema(db):
    db.execute('''CREATE TABLE IF NOT EXISTS background_job_status(
      job TEXT PRIMARY KEY CHECK(job IN ('auto-import','recurring','backup')),
      last_check_ts INTEGER NOT NULL,
      next_check_ts INTEGER NOT NULL,
      last_result TEXT NOT NULL,
      last_success_ts INTEGER,
      last_action_ts INTEGER,
      last_error TEXT NOT NULL DEFAULT ''
    )''')


def record(db_path, name, result, next_at, error='', now=None):
    if name not in PERIODS:
        raise ValueError('Unbekannter Hintergrunddienst')
    if not Path(db_path).is_file():
        return False
    now = int(time.time() if now is None else now)
    result = str(result)[:40]
    fault = result in ('error', 'invalid', 'not_ready')
    acted = (name == 'auto-import' and result == 'imported'
             or name == 'backup' and result == 'created'
             or name == 'recurring' and result == 'posted')
    with sqlite3.connect(db_path, timeout=15) as db:
        db.execute('PRAGMA busy_timeout=15000')
        ensure_schema(db)
        db.execute('''INSERT INTO background_job_status
          (job,last_check_ts,next_check_ts,last_result,last_success_ts,last_action_ts,last_error)
          VALUES(?,?,?,?,?,?,?)
          ON CONFLICT(job) DO UPDATE SET
            last_check_ts=excluded.last_check_ts,
            next_check_ts=excluded.next_check_ts,
            last_result=excluded.last_result,
            last_success_ts=COALESCE(excluded.last_success_ts,background_job_status.last_success_ts),
            last_action_ts=COALESCE(excluded.last_action_ts,background_job_status.last_action_ts),
            last_error=excluded.last_error''',
          (name, now, int(next_at), result,
           None if fault else now, now if acted else None,
           str(error)[:280] if fault else ''))
    return True


def clock(value):
    if value is None:
        return 'Noch nicht erfasst'
    return datetime.fromtimestamp(int(value), TZ).strftime('%d.%m.%Y %H:%M:%S')


def dashboard_status(db, db_path, now=None):
    """Pure read with safe fallback if no worker marker exists after upgrade."""
    now = int(time.time() if now is None else now)
    rows={}
    if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='background_job_status'").fetchone():
        rows={r['job']:dict(r) for r in db.execute('SELECT * FROM background_job_status')}
    meta=dict(db.execute("SELECT key,value FROM meta WHERE key IN ('finance_mode','auto_import_enabled','daily_backup_enabled','last_import','last_import_source')").fetchall())
    web_mode=meta.get('finance_mode','import')=='web'
    import_enabled=(not web_mode and meta.get('auto_import_enabled','1')=='1')
    backup_enabled=(meta.get('daily_backup_enabled','1')=='1')
    jobs=[]
    for name in ('auto-import','recurring','backup'):
        rec=rows.get(name)
        enabled={'auto-import':import_enabled,'recurring':web_mode,'backup':backup_enabled}[name]
        if rec:
            check=int(rec['last_check_ts'])
            nxt=int(rec['next_check_ts'])
            stale=now-check > max(180, PERIODS[name]*2+120)
            # A worker can have stopped right after scheduling a future check.
            # The one-minute import heartbeat below also guards long-period jobs.
            heartbeat=rows.get('auto-import')
            if heartbeat and now-int(heartbeat['last_check_ts']) > 180:
                stale=True
            if nxt < now-90: stale=True
            problem=rec['last_result'] in ('error','invalid','not_ready')
            tone='warning' if (stale or problem) else 'neutral' if not enabled else 'ok'
            if stale:
                status='Keine aktuelle Rückmeldung'
            elif not enabled:
                status='Pausiert'
            elif problem:
                status='Prüfung mit Warnung'
            else:
                status=RESULT_LABELS.get(rec['last_result'],'Prüfung durchgeführt')
            next_display='Überfällig – Dienst prüfen' if nxt < now-90 else clock(nxt)
            item={'id':name,'label':LABELS[name], 'enabled':enabled, 'tone':tone,
                  'status':status,'last_check':clock(check), 'next_check':next_display,
                  'last_action':clock(rec['last_action_ts']) if rec['last_action_ts'] else '',
                  'error':rec['last_error'] if problem else '', 'stale':stale}
        else:
            item={'id':name,'label':LABELS[name], 'enabled':enabled,'tone':'neutral',
                  'status':'Noch keine Prüfung protokolliert', 'last_check':'Noch nicht erfasst',
                  'next_check':'Noch nicht bekannt','last_action':'','error':'','stale':True}
        jobs.append(item)
    heartbeat=rows.get('auto-import')
    heartbeat_ok=bool(heartbeat and now-int(heartbeat['last_check_ts']) <= 180)
    # This is a worker heartbeat, not a claim about Docker health.
    backup_dir=Path(db_path).parent/'web-backups'
    latest_backup=None
    latest_daily=None
    if backup_dir.is_dir() and not backup_dir.is_symlink():
        for candidate in backup_dir.glob('*.sqlite3'):
            if not candidate.is_file() or candidate.is_symlink() or candidate.name.startswith('.'):
                continue
            try:
                stamp=candidate.stat().st_mtime
            except OSError:
                continue
            if not latest_backup or stamp > latest_backup[0]:
                latest_backup=(stamp,candidate.name)
            if candidate.name.startswith('automatisch-') and (not latest_daily or stamp>latest_daily[0]):
                latest_daily=(stamp,candidate.name)
    return {
        'jobs':jobs,'heartbeat_ok':heartbeat_ok,'heartbeat_seen':clock(heartbeat['last_check_ts']) if heartbeat else 'Noch nicht erfasst',
        'finance_mode':'web' if web_mode else 'import',
        'last_import':meta.get('last_import') or 'Noch kein Import',
        'last_import_source':meta.get('last_import_source') or '—',
        'last_backup':clock(latest_backup[0]) if latest_backup else 'Noch keine Sicherung gefunden',
        'last_backup_type':('Automatisch' if latest_backup and latest_backup[1].startswith('automatisch-') else 'Manuell / anlassbezogen') if latest_backup else '',
        'last_daily':clock(latest_daily[0]) if latest_daily else 'Noch keine Tagessicherung',
    }
