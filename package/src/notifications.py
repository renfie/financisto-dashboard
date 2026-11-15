"""Private, opt-in expense notifications via a durable SQLite outbox.

Sender has outbound network access, but never receives an HTTP port or user login.
Existing Node-RED/Telegram update reception remains entirely untouched.
"""
from __future__ import annotations

import base64
import hashlib
import json
import webpush
import logging
import re
import sqlite3
import time
from decimal import Decimal
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from cryptography.fernet import Fernet

LOG = logging.getLogger('finance-notifications')


def ensure_schema(db):
    script = '''
    CREATE TABLE IF NOT EXISTS notification_settings (
        id INTEGER PRIMARY KEY CHECK(id=1),
        enabled INTEGER NOT NULL DEFAULT 0 CHECK(enabled IN (0,1)),
        min_amount_cents INTEGER NOT NULL DEFAULT 10000 CHECK(min_amount_cents>0),
        gotify_enabled INTEGER NOT NULL DEFAULT 0 CHECK(gotify_enabled IN (0,1)),
        gotify_url TEXT NOT NULL DEFAULT '',
        gotify_token_enc TEXT NOT NULL DEFAULT '',
        gotify_priority INTEGER NOT NULL DEFAULT 5 CHECK(gotify_priority BETWEEN 0 AND 10),
        telegram_enabled INTEGER NOT NULL DEFAULT 0 CHECK(telegram_enabled IN (0,1)),
        telegram_token_enc TEXT NOT NULL DEFAULT '',
        telegram_chat_id TEXT NOT NULL DEFAULT '',
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    INSERT OR IGNORE INTO notification_settings(id) VALUES (1);
    CREATE TABLE IF NOT EXISTS notification_outbox (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT NOT NULL,
        reference TEXT NOT NULL,
        channel TEXT NOT NULL CHECK(channel IN ('gotify','telegram')),
        body TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','sending','sent','failed')),
        attempts INTEGER NOT NULL DEFAULT 0,
        next_attempt_epoch INTEGER NOT NULL DEFAULT 0,
        claimed_epoch INTEGER NOT NULL DEFAULT 0,
        last_error TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        sent_at TEXT,
        UNIQUE(source,reference,channel)
    );
    CREATE INDEX IF NOT EXISTS notify_pending_idx ON notification_outbox(status,next_attempt_epoch);
    '''
    for statement in script.split(';'):
        if statement.strip():
            db.execute(statement)


def key_for(secret):
    digest = hashlib.sha256(('financisto-notify-v1:' + secret).encode('utf-8')).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt(token, secret):
    return Fernet(key_for(secret)).encrypt(token.encode('utf-8')).decode('ascii')


def decrypt(token_enc, secret):
    return Fernet(key_for(secret)).decrypt(token_enc.encode('ascii')).decode('utf-8')


def settings(db):
    return db.execute('SELECT * FROM notification_settings WHERE id=1').fetchone()


def summary(db):
    config = settings(db)
    status = {r['status']: r['n'] for r in db.execute(
        'SELECT status,COUNT(*) n FROM notification_outbox GROUP BY status')}
    last = db.execute('SELECT sent_at FROM notification_outbox WHERE status=? ORDER BY id DESC LIMIT 1', ('sent',)).fetchone()
    return dict(config), status, (last['sent_at'] if last else None)


def check_gotify_url(raw):
    url = (raw or '').strip().rstrip('/')
    if not url or len(url) > 350:
        raise ValueError('Bitte eine vollständige Gotify-URL eingeben.')
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('Für Gotify eine HTTPS-Adresse ohne Zugangsdaten/Parameter angeben.')
    if parsed.path not in ('','/'):
        raise ValueError('Bitte nur die Basisadresse der Gotify-Instanz angeben (ohne /message).')
    return url


def check_telegram_token(value):
    token = (value or '').strip()
    if not re.fullmatch(r'[0-9]{5,15}:[A-Za-z0-9_-]{25,}', token):
        raise ValueError('Das Telegram-Bot-Token hat ein ungültiges Format.')
    return token


def check_telegram_chat_id(value):
    raw = (value or '').strip()
    if not re.fullmatch(r'-?[0-9]{4,22}', raw):
        raise ValueError('Bitte eine numerische Telegram-Chat-ID angeben.')
    return raw


NEUTRAL_CATEGORY_NAMES = {
    'Durchlaufender Posten (Ausgabe)', 'Durchlaufender Posten (Eingang)',
    'Kontostandskorrektur (Zugang)', 'Kontostandskorrektur (Abgang)',
    'Depot-Wertanpassung (Zugang)', 'Depot-Wertanpassung (Abgang)',
}


def neutral_category(db, category_id):
    if not category_id:
        return False
    rows = db.execute('SELECT id,title,lft,rgt FROM categories').fetchall()
    roots = [r for r in rows if r['title'].strip().casefold() in
             {n.casefold() for n in NEUTRAL_CATEGORY_NAMES}]
    return any(r['id']==category_id and any(
        r['lft'] is not None and r['rgt'] is not None and
        root['lft'] is not None and root['rgt'] is not None and
        r['lft']>=root['lft'] and r['rgt']<=root['rgt'] for root in roots)
        for r in rows)


def expense_decision(db, row):
    """Return (human-readable reason, eligible account row) without side effects."""
    cfg=settings(db)
    if not cfg or not cfg['enabled']:
        return 'Ausgabenwarnungen sind deaktiviert.', None
    if row['amount'] >= 0:
        return 'Keine Ausgabe.', None
    if row['to_account_id']:
        return 'Umbuchungen lösen keine Warnung aus.', None
    if neutral_category(db,row['category_id']):
        return 'Durchlaufende Posten und Kontostandskorrekturen lösen keine Warnung aus.', None
    account=db.execute('''SELECT a.title,c.code,c.decimals FROM accounts a
                          JOIN currencies c ON c.id=a.currency_id WHERE a.id=?''',
                       (row['account_id'],)).fetchone()
    if not account or account['code']!='EUR' or account['decimals']!=2:
        return 'Keine Benachrichtigung: Ausgabenkonto ist nicht in EUR.', account
    if abs(int(row['amount'])) < int(cfg['min_amount_cents']):
        return 'Unterhalb des eingestellten Grenzbetrags.', account
    if not (cfg['gotify_enabled'] or cfg['telegram_enabled']):
        return 'Kein Gotify-/Telegram-Warnkanal aktiviert.', account
    return '', account


def queue_booking(db, row, actor_name=''):
    """Called INSIDE the existing booking transaction. No network operations here."""
    ref=str(row['notification_tx_id'])
    n=webpush.queue_booking(db,row,ref)
    # Gotify/Telegram retain their independent, administrator-defined expense threshold.
    if int(row['amount'])>=0:
        return n
    reason,account=expense_decision(db,row)
    if reason:
        return n
    cfg=settings(db)
    payee=db.execute('SELECT title FROM payees WHERE id=?',(row['payee_id'],)).fetchone()
    category=db.execute('SELECT title FROM categories WHERE id=?',(row['category_id'],)).fetchone()
    amount_text=f"{Decimal(-row['amount']) / 100:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    lines=['FieLanzen · Ausgabe über Grenzbetrag',
           f'Betrag: {amount_text} EUR',
           f'Empfänger: {payee["title"] if payee else "–"}',
           f'Kategorie: {category["title"] if category else "–"}',
           f'Konto: {account["title"]}',f'Datum: {row["day"]}']
    if actor_name:
        lines.append(f'Erfasst von: {actor_name[:70]}')
    if row['note']:
        lines.append('Notiz: '+str(row['note'])[:160])
    body='\n'.join(lines)
    for channel in ('gotify','telegram'):
        if cfg[channel+'_enabled']:
            cur=db.execute('''INSERT OR IGNORE INTO notification_outbox(source,reference,channel,body)
                          VALUES ('expense',?,?,?)''',(ref,channel,body))
            n+=max(0,cur.rowcount)
    return n


def queue_test(db):
    cfg = settings(db)
    if not cfg or not cfg['enabled']:
        raise ValueError('Benachrichtigungen sind noch deaktiviert.')
    channels = [c for c in ('gotify','telegram') if cfg[c+'_enabled']]
    if not channels:
        raise ValueError('Mindestens einen Benachrichtigungskanal auswählen.')
    import secrets
    ref = secrets.token_hex(12)
    for channel in channels:
        db.execute('''INSERT INTO notification_outbox(source,reference,channel,body)
                      VALUES ('test',?,?,?)''', (ref,channel,
                      'FieLanzen · Testbenachrichtigung\nDer Versandkanal wurde erfolgreich angesprochen.'))
    return len(channels)


def _post_json(url, headers, data):
    request = Request(url, data=json.dumps(data).encode('utf-8'), headers={
        'Content-Type': 'application/json; charset=utf-8', **headers}, method='POST')
    try:
        with urlopen(request, timeout=8) as response:
            if not 200 <= response.status < 300:
                raise RuntimeError(f'HTTP {response.status}')
            if url.startswith('https://api.telegram.org/'):
                parsed = json.loads(response.read(16*1024).decode('utf-8'))
                if not parsed.get('ok'):
                    raise RuntimeError('Telegram hat den Versand abgelehnt.')
    except HTTPError as exc:
        # Never leak the Telegram bot token embedded in the URL.
        raise RuntimeError(f'HTTP {exc.code} vom Versanddienst') from None
    except (URLError, TimeoutError, OSError) as exc:
        raise RuntimeError('Netzwerkfehler beim Versand (' + type(exc).__name__ + ')') from None


def send(channel, body, cfg, secret):
    if not cfg['enabled'] or not cfg[channel+'_enabled']:
        raise RuntimeError('Versandkanal inzwischen deaktiviert')
    if channel == 'gotify':
        url = check_gotify_url(cfg['gotify_url']) + '/message'
        token = decrypt(cfg['gotify_token_enc'], secret)
        _post_json(url, {'X-Gotify-Key': token},
                   dict(title='FieLanzen', message=body, priority=int(cfg['gotify_priority'])))
    elif channel == 'telegram':
        token = decrypt(cfg['telegram_token_enc'], secret)
        chat_id = check_telegram_chat_id(cfg['telegram_chat_id'])
        # sendMessage is independent of Node-RED receiving incoming updates.
        _post_json(f'https://api.telegram.org/bot{token}/sendMessage', {},
                   dict(chat_id=chat_id, text=body))
    else:
        raise RuntimeError('Unbekannter Kanal')


def drain_one(db_path, secret):
    """At-least-once delivery; resilient across restarts, bounded retries."""
    now = int(time.time())
    with sqlite3.connect(db_path, timeout=10) as db:
        db.row_factory = sqlite3.Row
        db.execute('BEGIN IMMEDIATE')
        # Recover jobs held by a dead sender. Might resend after a process crash.
        db.execute("UPDATE notification_outbox SET status='pending' WHERE status='sending' AND claimed_epoch<?",
                   (now-120,))
        job = db.execute('''SELECT * FROM notification_outbox WHERE status='pending'
                           AND next_attempt_epoch<=? ORDER BY id LIMIT 1''', (now,)).fetchone()
        if not job:
            return False
        db.execute("UPDATE notification_outbox SET status='sending',claimed_epoch=?,attempts=attempts+1 WHERE id=?",
                   (now,job['id']))
        cfg = settings(db)
    try:
        if not cfg:
            raise RuntimeError('Versand nicht eingerichtet')
        send(job['channel'], job['body'], cfg, secret)
    except Exception as exc:
        # No exception details containing URLs, header values or credentials.
        safe = str(exc)[:150] if isinstance(exc, RuntimeError) else type(exc).__name__
        fail = int(job['attempts']) >= 4
        delay = min(3600, 60 * (2 ** min(int(job['attempts']), 6)))
        with sqlite3.connect(db_path, timeout=10) as db:
            db.execute('''UPDATE notification_outbox SET status=?,last_error=?,next_attempt_epoch=?
                          WHERE id=? AND status='sending' ''',
                       ('failed' if fail else 'pending',safe,now+delay,job['id']))
        LOG.warning('Versand %s ID %s: %s',job['channel'],job['id'],safe)
    else:
        with sqlite3.connect(db_path, timeout=10) as db:
            db.execute('''UPDATE notification_outbox SET status='sent',sent_at=CURRENT_TIMESTAMP,last_error=''
                          WHERE id=? AND status='sending' ''',(job['id'],))
        LOG.info('Versand %s ID %s abgeschlossen',job['channel'],job['id'])
    return True


def main():
    import os
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
    db = os.getenv('DATABASE_PATH','/data/finanzen.sqlite3')
    secret = Path(os.getenv('APP_SECRET_FILE','/run/finance-secrets/app_secret')).read_text().strip()
    LOG.info('Benachrichtigungsdienst gestartet (Ausgabenwarnungen und eigener Telegram-Buchungsbot)')
    import threading
    import telegram_receiver
    threading.Thread(target=telegram_receiver.loop, args=(db,secret),
                     name='finance-telegram-direct',daemon=True).start()
    while True:
        try:
            regular=drain_one(db,secret)
            pushed=webpush.drain_one(db,secret,os.getenv('VAPID_SUBJECT','https://finance.example.org'))
            if not regular and not pushed:
                time.sleep(10)
        except (sqlite3.Error,OSError) as exc:
            LOG.warning('Ausgangswarteschlange vorübergehend nicht verfügbar (%s)',type(exc).__name__)
            time.sleep(20)


if __name__ == '__main__':
    main()
