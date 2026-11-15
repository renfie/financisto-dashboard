"""Direct Telegram group receiver for FieLanzen, using the existing notifications worker.

One dedicated bot token, one getUpdates consumer. No public webhook and no Node-RED.
Bookkeeping shares the same SQLite transactions as web bookings but does not need
Flask credentials or additional inbound network access.
"""
from __future__ import annotations

import json
import logging
import re
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

import notifications
import telegram_bookings

LOG = logging.getLogger('finance-telegram-receiver')
TZ = ZoneInfo('Europe/Berlin')
FINANCE_COMMAND = re.compile(r'^/(finanz|finanzid)(?:@([A-Za-z0-9_]+))?(?=\s|$)', re.I)
NEUTRAL_NAMES = {
    'Durchlaufender Posten (Ausgabe)', 'Durchlaufender Posten (Eingang)',
    'Kontostandskorrektur (Zugang)', 'Kontostandskorrektur (Abgang)',
    'Depot-Wertanpassung (Zugang)', 'Depot-Wertanpassung (Abgang)',
}


def api(token, method, payload=None, timeout=25):
    """Telegram POST request. Never log or re-raise the URL containing the token."""
    request = Request('https://api.telegram.org/bot' + token + '/' + method,
                      data=json.dumps(payload or {}).encode('utf-8'),
                      headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with urlopen(request, timeout=timeout) as response:
            result = json.load(response)
    except Exception as exc:
        raise RuntimeError('Telegram-' + method + ': ' + type(exc).__name__) from None
    if not isinstance(result, dict) or result.get('ok') is not True:
        code = result.get('error_code') if isinstance(result, dict) else 'unbekannt'
        raise RuntimeError(f'Telegram-{method}: API-Fehler {code}')
    return result.get('result')


def connection(path):
    db = sqlite3.connect(path, timeout=15)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA busy_timeout=15000')
    return db


def shared_default_expense_category(db):
    """Read the single shared Web/Telegram default; reject stale IDs."""
    row = db.execute("SELECT value FROM meta WHERE key='default_expense_category_id'").fetchone()
    raw = row['value'] if row else ''
    if not raw or not raw.isdigit():
        return 0
    valid = db.execute('SELECT id FROM categories WHERE id=? AND kind=0', (int(raw),)).fetchone()
    return int(valid['id']) if valid else 0


def neutral_ids(db):
    rows = db.execute('SELECT id,title,lft,rgt FROM categories').fetchall()
    roots = [r for r in rows if r['title'].strip().casefold() in {s.casefold() for s in NEUTRAL_NAMES}]
    return {r['id'] for r in rows if any(root['lft'] is not None and root['rgt'] is not None
        and r['lft'] is not None and r['rgt'] is not None
        and r['lft'] >= root['lft'] and r['rgt'] <= root['rgt'] for root in roots)}


def entry_payee(db, title):
    title = (title or '').strip()
    if not title:
        return 0
    if len(title) > 120:
        raise ValueError('Empfängername zu lang.')
    row = db.execute('SELECT id FROM payees WHERE title=? COLLATE NOCASE', (title,)).fetchone()
    return row['id'] if row else db.execute('INSERT INTO payees(title) VALUES (?)',(title,)).lastrowid


def apply_balance_delta(db, entry, direction):
    amount = int(direction) * int(entry['amount'])
    transfers = [(entry['account_id'],amount)]
    if entry['to_account_id']:
        transfers.append((entry['to_account_id'],-amount))
    for account_id, delta in transfers:
        if db.execute('''UPDATE account_snapshots SET balance_minor=balance_minor+?
                      WHERE account_id=? AND balance_minor IS NOT NULL''',(delta,account_id)).rowcount != 1:
            raise ValueError('Kontostand nicht bekannt. Buchung abgebrochen.')


def mark_edit(db, event, detail):
    db.execute("UPDATE meta SET value=CAST(value AS INTEGER)+1 WHERE key='ledger_web_writes'")
    db.execute('''INSERT INTO audit_events(actor_id,event,detail,client_ip)
                  VALUES(NULL,?,?,?)''',(event,detail[:250],'telegram'))


def is_web_mode(db):
    r = db.execute("SELECT value FROM meta WHERE key='finance_mode'").fetchone()
    return bool(r and r['value'] == 'web')


def response_to_group(token, chat_id, outcome, *, message_id=None, edit=False):
    data = dict(chat_id=chat_id, text=outcome['text'])
    if outcome.get('buttons'):
        data['reply_markup'] = {'inline_keyboard':outcome['buttons']}
    if edit and message_id:
        data['message_id'] = message_id
        try:
            return api(token, 'editMessageText', data, timeout=12)
        except RuntimeError:
            data.pop('message_id', None)
    if message_id:
        data['reply_parameters'] = dict(message_id=message_id, allow_sending_without_reply=True)
    return api(token,'sendMessage',data,timeout=12)


def command_for_bot(message, username):
    match=FINANCE_COMMAND.match(message)
    if not match:
        return None
    mentioned=match.group(2)
    if mentioned and (not username or mentioned.casefold()!=username.casefold()):
        return None
    return match.group(1).casefold()


def handle_message(db, token, cfg, msg, username):
    text = msg.get('text')
    sender = msg.get('from') or {}
    chat = msg.get('chat') or {}
    if not isinstance(text,str) or len(text)>400 or sender.get('is_bot'):
        return
    cmd = command_for_bot(text,username)
    if cmd is None:
        return
    user_id = str(sender.get('id',''))
    chat_id = str(chat.get('id',''))
    if not re.fullmatch(r'[1-9]\d{3,19}',user_id):
        return
    # /finanzid is intentionally safe during first-time setup, before activation.
    if cmd == 'finanzid':
        msg_text = (f'FieLanzen Telegram-Einrichtung\n'
                    f'Gruppen-Chat-ID: {chat_id}\nDeine Benutzer-ID: {user_id}\n'
                    'Die Werte bitte nur im Administratorbereich von FieLanzen eintragen.')
        response_to_group(token,chat_id,telegram_bookings.response(msg_text),
                          message_id=msg.get('message_id'))
        return
    if not (cfg['enabled'] and cfg['receive_mode']=='direct' and
            chat.get('type') in ('group','supergroup') and
            chat_id == cfg['allowed_chat_id'] and
            user_id in (cfg['permitted_user_ids'] or '').split(',')):
        return
    if int(msg.get('date') or 0) < int(cfg['activation_epoch'] or 0):
        return
    msg_id = str(msg.get('message_id',''))
    if not re.fullmatch(r'[1-9]\d{0,19}',msg_id):
        return
    try:
        db.execute('BEGIN IMMEDIATE')
        if not is_web_mode(db):
            result = telegram_bookings.response('Bitte zuerst die Web-Finanzverwaltung in FieLanzen aktivieren.')
        else:
            result = telegram_bookings.create(db,text,chat_id,user_id,msg_id,
                datetime.now(TZ).date().isoformat(),cfg['default_account_id'],
                shared_default_expense_category(db))
            if cfg['auto_confirm']:
                draft = db.execute('''SELECT token,status FROM telegram_booking_drafts
                       WHERE chat_id=? AND source_message_id=?''',(chat_id,msg_id)).fetchone()
                if draft and draft['status']=='pending':
                    result = telegram_bookings.callback(db,'fl25:ok:'+draft['token'],chat_id,user_id,
                        mark_edit,entry_payee,apply_balance_delta,notifications,
                        'Telegram '+user_id,neutral_ids)
        db.commit()
    except (ValueError,sqlite3.Error) as exc:
        db.rollback()
        result = telegram_bookings.response('⚠️ '+(str(exc) if isinstance(exc,ValueError) else 'Speichern vorübergehend nicht möglich.'))
    response_to_group(token,chat_id,result,message_id=msg.get('message_id'))


def handle_callback(db, token, cfg, query):
    sender = query.get('from') or {}
    message = query.get('message') or {}
    chat = message.get('chat') or {}
    chat_id = str(chat.get('id',''))
    user_id = str(sender.get('id',''))
    callback = str(query.get('data') or '')
    if not callback.startswith('fl25:'):
        return
    valid = bool(cfg['enabled'] and cfg['receive_mode']=='direct' and
                 chat_id == cfg['allowed_chat_id'] and
                 user_id in (cfg['permitted_user_ids'] or '').split(','))
    if not valid:
        try:
            api(token,'answerCallbackQuery',dict(callback_query_id=query['id'],
                       text='Für diese Buchung nicht freigegeben.',show_alert=True),timeout=10)
        except RuntimeError:
            pass
        return
    try:
        db.execute('BEGIN IMMEDIATE')
        if not is_web_mode(db):
            result = telegram_bookings.response('Web-Finanzverwaltung ist nicht aktiviert.')
        else:
            result = telegram_bookings.callback(db,callback,chat_id,user_id,mark_edit,
                    entry_payee,apply_balance_delta,notifications,'Telegram '+user_id,neutral_ids)
        db.commit()
    except (ValueError,sqlite3.Error) as exc:
        db.rollback()
        result = telegram_bookings.response('⚠️ '+(str(exc) if isinstance(exc,ValueError) else 'Speichern nicht möglich.'))
    try:
        api(token,'answerCallbackQuery',dict(callback_query_id=query['id']),timeout=10)
    except RuntimeError:
        pass
    response_to_group(token,chat_id,result,message_id=message.get('message_id'),edit=True)


def process_update(path, token, encrypted_token, update, username):
    db = connection(path)
    try:
        cfg = telegram_bookings.config(db)
        # Re-read settings after long polling: a newly activated bot must not
        # drop its first booking due to a stale pre-activation snapshot.
        if not cfg or cfg['receive_mode'] != 'direct' or cfg['bot_token_enc'] != encrypted_token:
            return
        if isinstance(update.get('message'),dict):
            handle_message(db,token,cfg,update['message'],username)
        elif isinstance(update.get('callback_query'),dict):
            handle_callback(db,token,cfg,update['callback_query'])
    finally:
        db.close()


def loop(path,secret):
    """Runs in one daemon thread of notifications; no extra Docker service."""
    token_cache='';username=''
    LOG.info('Direkter Telegram-Empfang bereit (getUpdates nur mit eigenem FieLanzen-Bot).')
    while True:
        try:
            with connection(path) as db:
                cfg=telegram_bookings.config(db)
                if not cfg or cfg['receive_mode']!='direct' or not cfg['bot_token_enc']:
                    time.sleep(5)
                    continue
                encrypted=cfg['bot_token_enc']
                token=notifications.decrypt(encrypted,secret)
                offset=int(cfg['poll_offset'] or 0)
            if token != token_cache:
                ident=api(token,'getMe',timeout=12)
                username=(ident or {}).get('username','')
                token_cache=token
                LOG.info('Telegram-Bot-Verbindung aktiv (Benutzername geprüft).')
            updates=api(token,'getUpdates',dict(offset=offset,timeout=15,
                    allowed_updates=['message','callback_query']),timeout=24)
            if not isinstance(updates,list):
                raise RuntimeError('Ungültige Telegram-Antwort.')
            for update in updates:
                uid=update.get('update_id')
                if not isinstance(uid,int) or uid < offset:
                    continue
                process_update(path,token,encrypted,update,username)
                with connection(path) as db:
                    db.execute('''UPDATE telegram_booking_settings SET poll_offset=?
                      WHERE id=1 AND receive_mode='direct' AND bot_token_enc=? AND poll_offset<?''',
                      (uid+1,encrypted,uid+1))
                    db.commit()
                offset=uid+1
        except Exception as exc:
            # Keep the daemon alive after unexpected API/DB failures. Never log
            # untrusted API URLs, tokens, finance texts, or exception repr.
            LOG.warning('Telegram-Empfang: %s',str(exc) if isinstance(exc,RuntimeError) else type(exc).__name__)
            time.sleep(6)


if __name__ == '__main__':
    import os
    logging.basicConfig(level=logging.INFO)
    loop(os.getenv('DATABASE_PATH','/data/finanzen.sqlite3'),
         Path(os.getenv('APP_SECRET_FILE','/run/finance-secrets/app_secret')).read_text().strip())
