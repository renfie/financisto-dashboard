# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2026 René Fieler (RenFie)
# See LICENSE and NOTICE.md for terms and third-party notices.

"""Financisto recurring templates: read-only preview, controlled import and idempotent posting.

No original customer backup is shipped or stored in this module. The backup is
supplied through the authenticated admin web form and only its ten-ish template
records are staged. A scheduled worker posts only explicitly enabled rules,
and only when the Web ledger is authoritative.
"""
from __future__ import annotations

import calendar
import datetime as dt
import json
import os
import re
import sqlite3
import notifications
import sys
import time
import uuid
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo('Europe/Berlin')
MAX_FILE_SIZE = 30 * 1024 * 1024


def today():
    return dt.datetime.now(TZ).date()


def ensure_schema(db):
    db.executescript('''
    CREATE TABLE IF NOT EXISTS recurring_rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_kind TEXT NOT NULL DEFAULT 'web',
        source_id INTEGER,
        title TEXT NOT NULL,
        kind TEXT NOT NULL CHECK(kind IN ('expense','income','transfer')),
        account_id INTEGER NOT NULL,
        to_account_id INTEGER NOT NULL DEFAULT 0,
        category_id INTEGER NOT NULL DEFAULT 0,
        payee_id INTEGER NOT NULL DEFAULT 0,
        amount_minor INTEGER NOT NULL,
        note TEXT NOT NULL DEFAULT '',
        frequency TEXT NOT NULL DEFAULT 'monthly',
        interval_count INTEGER NOT NULL DEFAULT 1,
        day_of_month INTEGER NOT NULL DEFAULT 1,
        start_on TEXT NOT NULL,
        run_at TEXT NOT NULL DEFAULT '00:00',
        end_on TEXT,
        max_occurrences INTEGER,
        completed_on TEXT,
        next_on TEXT,
        active INTEGER NOT NULL DEFAULT 0,
        auto_post INTEGER NOT NULL DEFAULT 0,
        needs_review TEXT NOT NULL DEFAULT '',
        raw_recurrence TEXT NOT NULL DEFAULT '',
        created_on TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_on TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        deleted_on TEXT,
        UNIQUE(source_kind,source_id)
    );
    CREATE INDEX IF NOT EXISTS recurring_due_idx ON recurring_rules(active,auto_post,next_on);
    CREATE TABLE IF NOT EXISTS recurring_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rule_id INTEGER NOT NULL REFERENCES recurring_rules(id),
        due_on TEXT NOT NULL,
        booking_id INTEGER NOT NULL,
        created_on TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(rule_id,due_on)
    );
    CREATE TABLE IF NOT EXISTS recurring_import_previews (
        token TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        created_on TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        payload TEXT NOT NULL
    );
    ''')
    # Existing installations (1.9.9/1.9.10) require a single additive column.
    # Keep records that were booked already, including recurrence audit trail.
    cols={r[1] for r in db.execute('PRAGMA table_info(recurring_rules)')}
    if 'deleted_on' not in cols:
        try:
            db.execute('ALTER TABLE recurring_rules ADD COLUMN deleted_on TEXT')
        except sqlite3.OperationalError:
            if 'deleted_on' not in {r[1] for r in db.execute('PRAGMA table_info(recurring_rules)')}:
                raise
    # 1.9.35: Optional wall-clock earliest execution time, in Europe/Berlin.
    # Old rules keep their previous behavior (due from midnight onward).
    if 'run_at' not in cols:
        try:
            db.execute("ALTER TABLE recurring_rules ADD COLUMN run_at TEXT NOT NULL DEFAULT '00:00'")
        except sqlite3.OperationalError:
            if 'run_at' not in {r[1] for r in db.execute('PRAGMA table_info(recurring_rules)')}:
                raise
    # 1.9.40: optional, inclusive end date / number of actual occurrences.
    # NULL keeps pre-existing schedules unlimited. This migration is additive.
    for column, decl in [('end_on', 'TEXT'), ('max_occurrences', 'INTEGER'), ('completed_on', 'TEXT')]:
        if column not in cols:
            try:
                db.execute(f'ALTER TABLE recurring_rules ADD COLUMN {column} {decl}')
            except sqlite3.OperationalError:
                if column not in {r[1] for r in db.execute('PRAGMA table_info(recurring_rules)')}:
                    raise


def parse_rule(text):
    """Recognize precise monthly clauses; never guess complex GEEKY semantics."""
    text = text or ''
    head, sep, body = text.partition('~')
    try:
        anchor = dt.date.fromisoformat(head[:10])
    except ValueError:
        return dict(frequency='custom', interval_count=1, day_of_month=1,
                    start_on=today().isoformat(), needs_review='Startdatum nicht lesbar')
    if not sep or not body.startswith('MONTHLY:'):
        return dict(frequency='custom', interval_count=1, day_of_month=anchor.day,
                    start_on=anchor.isoformat(), needs_review='Komplexes Wiederholungsformat: zunächst manuell prüfen')
    sub = body.split('~',1)[0].split(':',1)[1]
    props = dict(re.findall(r'([A-Za-z_0-9]+)@([^#]+)', sub))
    if props.get('monthly_pattern_0') != 'EVERY_NTH_DAY':
        return dict(frequency='custom', interval_count=1, day_of_month=anchor.day,
                    start_on=anchor.isoformat(), needs_review='Monatliches Sondermuster noch nicht unterstützt')
    try:
        day = int(props['monthly_pattern_params_0'])
        months = int(props.get('interval', '1'))
        if not (1 <= day <= 31 and 1 <= months <= 120):
            raise ValueError()
    except (ValueError, KeyError):
        return dict(frequency='custom', interval_count=1, day_of_month=anchor.day,
                    start_on=anchor.isoformat(), needs_review='Wiederholungsintervall unvollständig')
    return dict(frequency='monthly', interval_count=months, day_of_month=day,
                start_on=anchor.isoformat(), needs_review='')


def planned_date(anchor, frequency, interval, day, step):
    if frequency == 'daily':
        return anchor + dt.timedelta(days=step * interval)
    if frequency == 'weekly':
        return anchor + dt.timedelta(weeks=step * interval)
    if frequency in ('monthly','quarterly','yearly'):
        months = interval * {'monthly':1,'quarterly':3,'yearly':12}[frequency]
        index = anchor.year * 12 + anchor.month - 1 + step * months
        y, m = divmod(index, 12)
        if y > 9999:
            raise ValueError('Termin liegt außerhalb des erlaubten Datumsbereichs')
        return dt.date(y, m + 1, min(day, calendar.monthrange(y, m+1)[1]))
    raise ValueError('Wiederholungsformat zunächst umstellen')


def on_or_after(anchor, frequency, interval, day, minimum):
    if interval < 1 or interval > 120:
        raise ValueError('Ungültiges Intervall')
    for step in range(0, 15000):
        d = planned_date(anchor, frequency, interval, day, step)
        if d >= minimum and d >= anchor:
            return d
    raise ValueError('Kein zukünftiger Termin gefunden')


def next_after(rule, minimum):
    anchor = dt.date.fromisoformat(rule['start_on'])
    return on_or_after(anchor, rule['frequency'], int(rule['interval_count']),
                       int(rule['day_of_month']), minimum).isoformat()


def preview_from_backup(raw, db):
    from financisto_import import parse_backup
    records = parse_backup(raw)
    names = {row['_id']: row.get('title','') for row in records['account']}
    account_currency = {row['_id']: int(row.get('currency_id') or 0) for row in records['account']}
    payees = {row['_id']: row.get('title','') for row in records['payee']}
    categories = {row['_id']: row.get('title','') for row in records['category']}
    current_accounts = {r['id']: dict(r) for r in db.execute('''SELECT a.id,a.title,a.currency_id,c.decimals,s.balance_minor,s.is_active
        FROM accounts a JOIN currencies c ON c.id=a.currency_id LEFT JOIN account_snapshots s ON s.account_id=a.id''')}
    current_cats = {r['id']: r['title'] for r in db.execute('SELECT id,title FROM categories')}
    current_payees = {r['id']: r['title'] for r in db.execute('SELECT id,title FROM payees')}
    results=[]
    for tx in records['transactions']:
        if tx.get('is_template') != '2' or not tx.get('recurrence'):
            continue
        template_id = int(tx['_id'])
        amount = int(tx.get('from_amount','0'))
        account_id=int(tx.get('from_account_id') or 0)
        target_id=int(tx.get('to_account_id') or 0)
        category_id=int(tx.get('category_id') or 0)
        payee_id=int(tx.get('payee_id') or 0)
        kind = 'transfer' if target_id else ('income' if amount > 0 else 'expense')
        schedule = parse_rule(tx['recurrence'])
        warnings = [schedule['needs_review']] if schedule['needs_review'] else []
        account=current_accounts.get(account_id)
        if not account or (account['title'] != names.get(str(account_id)) or account['currency_id'] != account_currency.get(str(account_id))) or account['is_active']==0 or account['balance_minor'] is None:
            warnings.append('Quellkonto stimmt nicht mit der Web-Datenbank überein')
            account_id=0
        if target_id:
            target=current_accounts.get(target_id)
            if not target or (target['title'] != names.get(str(target_id)) or target['currency_id'] != account_currency.get(str(target_id))) or target['balance_minor'] is None:
                warnings.append('Zielkonto stimmt nicht mit der Web-Datenbank überein')
                target_id=0
        if category_id and current_cats.get(category_id) != categories.get(str(category_id)):
            warnings.append('Kategorie muss neu zugeordnet werden')
            category_id=0
        if payee_id and current_payees.get(payee_id) != payees.get(str(payee_id)):
            warnings.append('Empfänger muss neu zugeordnet werden')
            payee_id=0
        title = (payees.get(tx.get('payee_id','')) or tx.get('note') or f'Vorlage {template_id}').strip()[:160]
        result={**schedule,'source_kind':'financisto','source_id':template_id,
                'title':title,'kind':kind,'account_id':account_id,'to_account_id':target_id,
                'category_id':category_id,'payee_id':payee_id,'amount_minor':amount,
                'note':(tx.get('note') or '')[:1000],
                'raw_recurrence':tx['recurrence'][:1000],
                'needs_review':'; '.join(filter(None,warnings))}
        results.append(result)
    return results, len(records['transactions'])


def save_import_preview(db, user_id, rules):
    token = uuid.uuid4().hex
    # Only parsed templates, never the full financial backup, are retained.
    db.execute("DELETE FROM recurring_import_previews WHERE created_on < datetime('now','-1 hour')")
    db.execute('INSERT INTO recurring_import_previews(token,user_id,payload) VALUES(?,?,?)',
               (token,user_id,json.dumps(rules,ensure_ascii=False)))
    return token


def confirm_import(db, token, user_id):
    row=db.execute('''SELECT payload FROM recurring_import_previews WHERE token=? AND user_id=?
        AND created_on >= datetime('now','-1 hour')''', (token,user_id)).fetchone()
    if not row:
        raise ValueError('Importvorschau abgelaufen; bitte Sicherung erneut prüfen.')
    records=json.loads(row[0]); count=0
    for r in records:
        if not isinstance(r.get('source_id'),int):
            raise ValueError('Ungültige Vorlage')
        exists=db.execute("SELECT 1 FROM recurring_rules WHERE source_kind='financisto' AND source_id=?",(r['source_id'],)).fetchone()
        if exists:
            continue  # preserve user modifications on repeated backup imports
        db.execute('''INSERT INTO recurring_rules(source_kind,source_id,title,kind,account_id,to_account_id,
                category_id,payee_id,amount_minor,note,frequency,interval_count,day_of_month,
                start_on,next_on,active,auto_post,needs_review,raw_recurrence)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,NULL,0,0,?,?)''',
            (r['source_kind'],r['source_id'],r['title'],r['kind'],r['account_id'],r['to_account_id'],
             r['category_id'],r['payee_id'],r['amount_minor'],r['note'],r['frequency'],
             r['interval_count'],r['day_of_month'],r['start_on'],r['needs_review'],r['raw_recurrence']))
        count+=1
    db.execute('DELETE FROM recurring_import_previews WHERE token=?',(token,))
    return count


def validate_rule(db, rule):
    if rule['frequency'] not in ('daily','weekly','monthly','quarterly','yearly'):
        raise ValueError('Sonderregel zuerst auf ein unterstütztes Intervall umstellen.')
    if not (1 <= int(rule['interval_count']) <= 120 and 1 <= int(rule['day_of_month']) <= 31):
        raise ValueError('Ungültiger Wiederholungsabstand.')
    account=db.execute('''SELECT a.currency_id,s.balance_minor,s.is_active FROM accounts a
        JOIN account_snapshots s ON s.account_id=a.id WHERE a.id=?''',(rule['account_id'],)).fetchone()
    if not account or account['balance_minor'] is None or account['is_active']==0:
        raise ValueError('Quellkonto ist nicht mehr aktiv oder hat keinen bekannten Saldo.')
    if rule['kind']=='transfer':
        target=db.execute('''SELECT a.currency_id,s.balance_minor,s.is_active FROM accounts a
            JOIN account_snapshots s ON s.account_id=a.id WHERE a.id=?''',(rule['to_account_id'],)).fetchone()
        if not target or target['balance_minor'] is None or target['is_active']==0 or target['currency_id']!=account['currency_id'] or rule['to_account_id']==rule['account_id']:
            raise ValueError('Ungültiges Umbuchungs-Zielkonto.')
    if rule['category_id'] and not db.execute('SELECT 1 FROM categories WHERE id=?',(rule['category_id'],)).fetchone():
        raise ValueError('Kategorie nicht gefunden.')
    if rule['payee_id'] and not db.execute('SELECT 1 FROM payees WHERE id=?',(rule['payee_id'],)).fetchone():
        raise ValueError('Empfänger nicht gefunden.')
    if not int(rule['amount_minor']):
        raise ValueError('Betrag darf nicht 0 sein.')
    if rule['kind']=='income' and int(rule['amount_minor']) <= 0:
        raise ValueError('Einnahme muss einen positiven Betrag besitzen.')
    if rule['kind']!='income' and int(rule['amount_minor']) >= 0:
        raise ValueError('Ausgabe/Umbuchung muss negativ gespeichert sein.')


def completed_runs(db, rule_id):
    """Count handled occurrences, including matching existing bookings."""
    return db.execute('SELECT COUNT(*) FROM recurring_runs WHERE rule_id=?', (rule_id,)).fetchone()[0]


def is_finished(rule, next_on, count):
    """Return true when the NEXT date is beyond either configured limit."""
    return (
        (rule['max_occurrences'] is not None and count >= int(rule['max_occurrences']))
        or (rule['end_on'] is not None and next_on is not None and next_on > rule['end_on'])
    )


def advance_or_complete(db, rule, rule_id, current):
    # Keep count, next date and enabled state in the same locked transaction.
    completed = completed_runs(db, rule_id)
    candidate = next_after(rule, current + dt.timedelta(days=1))
    if is_finished(rule, candidate, completed):
        db.execute('''UPDATE recurring_rules SET next_on=NULL,active=0,auto_post=0,
                   completed_on=CURRENT_TIMESTAMP,updated_on=CURRENT_TIMESTAMP WHERE id=?''', (rule_id,))
    else:
        db.execute('''UPDATE recurring_rules SET next_on=?,updated_on=CURRENT_TIMESTAMP
                   WHERE id=?''', (candidate, rule_id))


def post_one(db, rule_id, minimum=None, *, automatic=False):
    # Caller must hold BEGIN IMMEDIATE transaction. Recheck mode inside lock.
    mode=db.execute("SELECT value FROM meta WHERE key='finance_mode'").fetchone()
    if not mode or mode[0]!='web':
        raise ValueError('Nur bei Web-Finanzverwaltung als führendem System möglich.')
    rule=db.execute('SELECT * FROM recurring_rules WHERE id=? AND deleted_on IS NULL',(rule_id,)).fetchone()
    if not rule or not rule['active'] or (automatic and not rule['auto_post']):
        raise ValueError('Regel nicht aktiv.')
    if not rule['next_on']:
        raise ValueError('Kein nächster Termin festgelegt.')
    scheduled=dt.date.fromisoformat(rule['next_on'])
    if is_finished(rule, scheduled.isoformat(), completed_runs(db, rule_id)):
        raise ValueError('Wiederholung ist bereits beendet (Enddatum oder Anzahl erreicht).')
    current=minimum or today()
    if scheduled > current:
        raise ValueError('Regel ist noch nicht fällig.')
    # The manual "Jetzt buchen" action intentionally follows the calendar date,
    # while automatic jobs honor the optional earliest local wall-clock time.
    if automatic and scheduled == current and dt.datetime.now(TZ).strftime('%H:%M') < (rule['run_at'] or '00:00'):
        raise ValueError('Gewählte Ausführungsuhrzeit noch nicht erreicht.')
    validate_rule(db,rule)
    existing=db.execute('SELECT booking_id FROM recurring_runs WHERE rule_id=? AND due_on=?',(rule_id,scheduled.isoformat())).fetchone()
    if existing:
        raise ValueError('Dieser Termin wurde bereits gebucht.')
    # Avoid duplicating an existing manually entered/imported transaction at
    # the exact due date. Record the occurrence as handled without changing
    # balances; the entry can still be examined in the bookings table.
    same=db.execute('''SELECT id FROM transactions WHERE day=? AND account_id=?
          AND COALESCE(to_account_id,0)=? AND COALESCE(category_id,0)=?
          AND COALESCE(payee_id,0)=? AND amount=? LIMIT 1''',
          (scheduled.isoformat(),rule['account_id'],rule['to_account_id'],rule['category_id'],
           rule['payee_id'],rule['amount_minor'])).fetchone()
    if same:
        db.execute('INSERT INTO recurring_runs(rule_id,due_on,booking_id) VALUES(?,?,?)',
                   (rule_id,scheduled.isoformat(),same['id']))
        advance_or_complete(db, rule, rule_id, current)
        db.execute('''INSERT INTO audit_events(actor_id,event,detail,client_ip)
                      VALUES(NULL,'recurring_existing_booking',?,'system')''',
                   (f'{rule_id}:{scheduled.isoformat()}:{same["id"]}',))
        return 0
    # A maximum of one due transaction per invocation; missed cycles never
    # trigger a sudden backfill of many historical months.
    cur=db.execute('''INSERT INTO transactions(day,account_id,to_account_id,category_id,payee_id,
            amount,note,is_template,origin) VALUES(?,?,?,?,?,?,?,0,'web')''',
            (scheduled.isoformat(),rule['account_id'],rule['to_account_id'],rule['category_id'],rule['payee_id'],
             rule['amount_minor'],rule['note']))
    transaction_id=cur.lastrowid
    # Newly posted recurring income/expenses reach personal Push rules as well.
    # Existing/imported entries remain excluded.
    if int(rule['amount_minor']) and not rule['to_account_id']:
        row=dict(day=scheduled.isoformat(),account_id=rule['account_id'],
                 to_account_id=rule['to_account_id'],category_id=rule['category_id'],
                 payee_id=rule['payee_id'],amount=rule['amount_minor'],note=rule['note'],
                 notification_tx_id=transaction_id)
        notifications.queue_booking(db,row,'Wiederkehrend automatisch' if automatic else 'Wiederkehrend manuell')
    for account_id,delta in [(rule['account_id'],rule['amount_minor'])]+(
       [(rule['to_account_id'],-rule['amount_minor'])] if rule['to_account_id'] else []):
        if not db.execute('''UPDATE account_snapshots SET balance_minor=balance_minor+?
                     WHERE account_id=? AND balance_minor IS NOT NULL''',(delta,account_id)).rowcount:
            raise ValueError('Kontostand konnte nicht aktualisiert werden')
    db.execute('INSERT INTO recurring_runs(rule_id,due_on,booking_id) VALUES(?,?,?)',
               (rule_id,scheduled.isoformat(),transaction_id))
    advance_or_complete(db, rule, rule_id, current)
    db.execute('''UPDATE meta SET value=CAST(value AS INTEGER)+1 WHERE key='ledger_web_writes' ''')
    db.execute('''INSERT INTO audit_events(actor_id,event,detail,client_ip) VALUES(NULL,?,?,?)''',
               ('recurring_posted_auto' if automatic else 'recurring_posted_manual',
                f'{rule_id}:{scheduled.isoformat()}:{transaction_id}', 'system'))
    return transaction_id


def run_due(db_path):
    with sqlite3.connect(db_path,timeout=15) as db:
        db.row_factory=sqlite3.Row
        ensure_schema(db)
        current=dt.datetime.now(TZ)
        today_str=current.date().isoformat()
        clock_str=current.strftime('%H:%M')
        mode=db.execute("SELECT value FROM meta WHERE key='finance_mode'").fetchone()
        if not mode or mode[0]!='web':
            return 0
        matches=db.execute('''SELECT id FROM recurring_rules WHERE active=1 AND auto_post=1 AND deleted_on IS NULL
                AND next_on IS NOT NULL
                AND (end_on IS NULL OR next_on <= end_on)
                AND (max_occurrences IS NULL OR (SELECT COUNT(*) FROM recurring_runs
                        WHERE rule_id=recurring_rules.id) < max_occurrences)
                AND (next_on < ? OR (next_on = ? AND COALESCE(run_at,'00:00') <= ?))
                ORDER BY next_on,id LIMIT 40''',(today_str,today_str,clock_str)).fetchall()
        posted=0
        for (id_,) in matches:
            try:
                db.execute('BEGIN IMMEDIATE')
                post_one(db,id_,automatic=True)
                db.commit();posted+=1
            except (ValueError,sqlite3.Error) as exc:
                db.rollback()
                print(f'WARNUNG Wiederkehrend #{id_}: {exc}',flush=True)
        return posted


def main():
    if sys.argv[1:] != ['--daemon']:
        raise SystemExit('Bitte --daemon verwenden.')
    target=os.environ.get('DATABASE_PATH','/data/finanzen.sqlite3')
    print('Wiederkehrende Buchungen: Prüfung alle 15 Minuten; nur explizit aktivierte automatische Regeln',flush=True)
    while True:
        try:
            count=run_due(target)
            if count:
                print(f'{count} freigegebene wiederkehrende Buchungen erzeugt',flush=True)
        except Exception as exc:
            print(f'ERROR Wiederkehrend: {type(exc).__name__}: {exc}',flush=True)
        time.sleep(900)


if __name__=='__main__':
    main()
