"""One offline worker for safe, independently scheduled Financisto jobs.

Each task keeps its original DB checks and its own error boundary. Only one
worker should run per installation. No traffic, no background shell commands.
"""
from __future__ import annotations
import logging
import os
import signal
import time
from pathlib import Path

import backup_manager
import job_monitor
import recurring
import sync_import

LOG = logging.getLogger('finance-background')
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
STOP = False


def stop_handler(_signum, _frame):
    global STOP
    STOP = True


def task_specs():
    return [
        ('auto-import', sync_import.INTERVAL, sync_import.scan_once),
        ('recurring', 900, lambda: recurring.run_due(os.environ.get('DATABASE_PATH', '/data/finanzen.sqlite3'))),
        ('backup', backup_manager.INTERVAL, backup_manager.scan_once),
    ]


def run_one(name, call):
    try:
        result = call()
        if name == 'auto-import' and result not in ('paused','no_new_files','not_ready'):
            LOG.info('Auto-Import: %s', result)
        if name == 'recurring' and result:
            LOG.info('Wiederkehrend: %s Eintrag/Einträge verarbeitet', result)
        if name == 'backup' and result == 'created':
            LOG.info('SQLite-Tagesbackup erstellt')
        return result
    except Exception as exc:
        LOG.exception('%s fehlgeschlagen; andere Aufgaben laufen weiter', name)
        return ('error', type(exc).__name__ + ': ' + str(exc))


def main():
    import sys
    if sys.argv[1:] == ['--check']:
        for name, delay, _ in task_specs():
            print(f'{name}: Intervall={delay}s')
        return
    if sys.argv[1:] != ['--daemon']:
        raise SystemExit('Aufruf: python background_worker.py --daemon|--check')
    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, stop_handler)
    specs = task_specs()
    next_due = {name: 0.0 for name, _, _ in specs}
    LOG.info('Gemeinsamer Hintergrunddienst gestartet: Auto-Import %ss, Wiederkehrend 900s, Backup %ss',
             sync_import.INTERVAL, backup_manager.INTERVAL)
    while not STOP:
        now = time.monotonic()
        for name, period, call in specs:
            if STOP:
                break
            if now >= next_due[name]:
                # Schedule *before* invoking the job, so exceptions cannot create
                # a busy retry loop; next period is measured from completion.
                next_due[name] = float('inf')
                outcome = run_one(name, call)
                next_due[name] = time.monotonic() + period
                next_time = time.time() + period
                if isinstance(outcome, tuple):
                    result, message = outcome
                elif name == 'recurring':
                    result, message = ('posted' if outcome else 'no_due'), ''
                else:
                    result, message = str(outcome), ''
                try:
                    job_monitor.record(os.environ.get('DATABASE_PATH', '/data/finanzen.sqlite3'),
                                       name, result, next_time, message)
                except Exception:
                    LOG.exception('Statusprotokoll für %s konnte nicht geschrieben werden', name)
                now = time.monotonic()
        if not STOP:
            remaining = max(0.2, min(next_due.values())-time.monotonic())
            time.sleep(min(1.0,remaining))
    LOG.info('Gemeinsamer Hintergrunddienst sauber beendet')


if __name__ == '__main__':
    main()
