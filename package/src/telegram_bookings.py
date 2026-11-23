# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2026 René Fieler (RenFie)
# See LICENSE and NOTICE.md for terms and third-party notices.

"""FieLanzen Telegram booking logic: validated, idempotent drafts and approvals."""
from __future__ import annotations
import re
import secrets
import time
from decimal import Decimal

PREFIX = 'fl25'
EXPIRY = 30 * 60


def ensure_schema(db):
    db.execute('''CREATE TABLE IF NOT EXISTS telegram_booking_settings (
        id INTEGER PRIMARY KEY CHECK(id=1),
        enabled INTEGER NOT NULL DEFAULT 0 CHECK(enabled IN (0,1)),
        secret_enc TEXT NOT NULL DEFAULT '',
        permitted_user_ids TEXT NOT NULL DEFAULT '',
        default_account_id INTEGER NOT NULL DEFAULT 0,
        default_category_id INTEGER NOT NULL DEFAULT 0,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )''')
    db.execute('INSERT OR IGNORE INTO telegram_booking_settings(id) VALUES (1)')
    db.execute('''CREATE TABLE IF NOT EXISTS telegram_booking_drafts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        token TEXT NOT NULL UNIQUE,
        chat_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        source_message_id TEXT NOT NULL,
        day TEXT NOT NULL,
        account_id INTEGER NOT NULL,
        category_id INTEGER NOT NULL DEFAULT 0,
        kind TEXT NOT NULL CHECK(kind IN ('expense','income')),
        amount_text TEXT NOT NULL,
        payee TEXT NOT NULL,
        note TEXT NOT NULL DEFAULT '',
        created_epoch INTEGER NOT NULL,
        expires_epoch INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','posted','cancelled')),
        transaction_id INTEGER,
        UNIQUE(chat_id,source_message_id)
    )''')
    db.execute('CREATE INDEX IF NOT EXISTS telegram_drafts_expiry_idx ON telegram_booking_drafts(status,expires_epoch)')
    # Safe additive migration from the Node-RED bridge in 1.9.25.
    cols = {r['name'] for r in db.execute('PRAGMA table_info(telegram_booking_settings)')}
    additions = {
        'receive_mode': "TEXT NOT NULL DEFAULT 'bridge'",
        'bot_token_enc': "TEXT NOT NULL DEFAULT ''",
        'allowed_chat_id': "TEXT NOT NULL DEFAULT ''",
        'auto_confirm': "INTEGER NOT NULL DEFAULT 0 CHECK(auto_confirm IN (0,1))",
        'activation_epoch': "INTEGER NOT NULL DEFAULT 0",
        'poll_offset': "INTEGER NOT NULL DEFAULT 0",
    }
    for column, definition in additions.items():
        if column not in cols:
            db.execute(f'ALTER TABLE telegram_booking_settings ADD COLUMN {column} {definition}')


def config(db):
    return db.execute('SELECT * FROM telegram_booking_settings WHERE id=1').fetchone()


def check_ids(value):
    items = [i.strip() for i in re.split(r'[,;\s]+', value or '') if i.strip()]
    if not items or len(items)>12 or any(not re.fullmatch(r'[1-9][0-9]{3,19}',i) for i in items):
        raise ValueError('Bitte 1 bis 12 numerische Telegram-Benutzer-IDs eintragen.')
    return ','.join(dict.fromkeys(items))


def response(text, buttons=None):
    return {'text':text[:1800], 'buttons':buttons or []}


def available_accounts(db):
    return db.execute('''SELECT a.id,a.title,c.code,c.decimals FROM accounts a
        JOIN account_snapshots s ON s.account_id=a.id JOIN currencies c ON c.id=a.currency_id
        WHERE s.is_active<>0 AND s.balance_minor IS NOT NULL ORDER BY a.title COLLATE NOCASE''').fetchall()


def amount_to_minor(s, decimals):
    raw=(s or '').strip().replace(',','.')
    if not re.fullmatch(r'\d{1,9}(?:\.\d{1,6})?',raw):
        raise ValueError('Betrag: zum Beispiel 24,90.')
    amount=Decimal(raw)*(10**decimals)
    if amount != amount.to_integral_value() or amount<=0 or amount>10**13:
        raise ValueError('Betrag ungültig für diese Währung.')
    return int(amount)


def _category_names(db):
    rows=db.execute('SELECT id,title,lft,rgt FROM categories ORDER BY lft,title').fetchall()
    stack=[];result={}
    for r in rows:
        while stack and stack[-1]['rgt']<r['lft']:
            stack.pop()
        result[r['id']]=' / '.join([p['title'] for p in stack]+[r['title']])
        stack.append(r)
    return result


def _selected_account(db, chosen, default_id):
    accounts=available_accounts(db)
    if chosen:
        matched=[a for a in accounts if a['title'].casefold()==chosen.casefold() or str(a['id'])==chosen]
        if len(matched)!=1:
            raise ValueError('Konto nicht gefunden. Bitte den Namen exakt hinter | eintragen.')
        return matched[0]
    for a in accounts:
        if str(a['id'])==str(default_id):
            return a
    raise ValueError('Bitte zuerst ein Standardkonto unter Einstellungen → Telegram-Buchungen festlegen.')


def _selected_category(db, chosen, default_id, payee, kind):
    """Expense: configured default, otherwise Einkauf; income: no forced expense tag."""
    names=_category_names(db)
    expected_kind=0 if kind=='expense' else 1
    kinds={r['id']:int(r['kind']) for r in db.execute('SELECT id,kind FROM categories')}
    if chosen:
        matched=[i for i,n in names.items() if kinds.get(i)==expected_kind and
                 (str(i)==chosen or n.casefold()==chosen.casefold())]
        if not matched:
            matched=[i for i,n in names.items() if kinds.get(i)==expected_kind and
                     n.rsplit(' / ',1)[-1].casefold()==chosen.casefold()]
        if len(matched)!=1:
            raise ValueError('Kategorie nicht eindeutig oder falscher Buchungstyp. Bitte genauen Namen hinter | angeben.')
        return matched[0]
    if int(default_id or 0) in names and kinds.get(int(default_id))==expected_kind:
        return int(default_id)
    if kind=='income':
        return 0
    # No independent Telegram fallback: the shared administrator setting is
    # authoritative. No category is created as a side effect of a bot message.
    return 0


def help_text():
    return ('📘 FieLanzen · Buchungen per Telegram\n'
            'Ausgabe: /finanz 24,90 Edeka\n'
            'Ausgabe mit Kategorie und Konto:\n'
            '/finanz 24,90 Edeka | Einkauf | Comdirect\n'
            'Einnahme auf Konto mit Notiz:\n'
            '/finanz +150 Taschengeld | Ebay Direkteinzahlung\n'
            'Bei Ausgaben: ohne Kategorie gilt die gemeinsame Standardkategorie '
            'aus Einstellungen → Standardkonto für neue Buchungen; '
            'ohne Konto das Telegram-Standardkonto.\n' 
            'Bei Einnahmen: +Betrag KONTO | optionale Notiz.\n'
            'Ohne Sofortbuchung erst bestätigen; /finanzid zeigt die IDs.')


def _draft_text(db, d):
    a=db.execute('''SELECT a.title,c.code,c.decimals FROM accounts a JOIN currencies c
        ON c.id=a.currency_id WHERE a.id=?''',(d['account_id'],)).fetchone()
    names=_category_names(db)
    if not a:
        raise ValueError('Das gewählte Konto existiert nicht mehr.')
    amount=amount_to_minor(d['amount_text'],a['decimals'])
    txt=f'{Decimal(amount)/(10**a["decimals"]):.{a["decimals"]}f}'.replace('.',',')
    details = (f'Empfänger: {d["payee"]}\n' if d['kind']=='expense' else '')
    details+=f'Konto: {a["title"]}\n'
    details+=f'Kategorie: {names.get(d["category_id"],"Ohne Kategorie")}\n'
    if d['note']:
        details+=f'Notiz: {d["note"]}\n'
    return ('🧾 FieLanzen · Buchungsvorschlag\n'
            f'{"Ausgabe" if d["kind"]=="expense" else "Einnahme"}: {txt} {a["code"]}\n'
            +details+f'Datum: {d["day"]}\n'
            'Noch nicht gebucht – bitte bestätigen.')


def _buttons(token):
    return [[{'text':'✅ Buchen','callback_data':f'{PREFIX}:ok:{token}'},
             {'text':'❌ Abbrechen','callback_data':f'{PREFIX}:no:{token}'}],
            [{'text':'🏦 Konto ändern','callback_data':f'{PREFIX}:accounts:{token}:0'},
             {'text':'🏷 Kategorie ändern','callback_data':f'{PREFIX}:categories:{token}:0'}]]


def _draft_controls(db, d):
    return response(_draft_text(db,d), _buttons(d['token']))


def create(db, message, chat_id, user_id, message_id, today, default_account, default_category):
    command=(message or '').strip()
    m=re.match(r'^/finanz(?:@[A-Za-z0-9_]+)?(?:\s+(.*))?$',command,re.I|re.S)
    if not m:
        return response(help_text())
    content=(m.group(1) or '').strip()
    if not content:
        return response(help_text())
    parts=[p.strip() for p in content.split('|')]
    match=re.fullmatch(r'([+-]?\d{1,9}(?:[,.]\d{1,6})?)\s+(.{1,120})',parts[0],re.S)
    if not match:
        raise ValueError('Bitte Betrag und Empfänger oder Einnahmekonto angeben.\n'+help_text())
    raw=match.group(1)
    kind='income' if raw.startswith('+') else 'expense'
    amount_text=raw.lstrip('+-')
    label=match.group(2).strip()
    if not label or any(ord(c)<32 for c in label):
        raise ValueError('Ungültiger Name.')
    if kind=='income':
        if len(parts)>2:
            raise ValueError('Einnahme: /finanz +150 Taschengeld | Ebay Direkteinzahlung')
        account=_selected_account(db,label,default_account)
        note=parts[1] if len(parts)>1 else ''
        payee=''
        category=_selected_category(db,'',default_category,payee,kind)
    else:
        if len(parts)>4:
            raise ValueError('Ausgabe: /finanz 24,90 Edeka | Einkauf | Comdirect | optionale Notiz')
        payee=label
        category_name=parts[1] if len(parts)>1 else ''
        account_name=parts[2] if len(parts)>2 else ''
        note=parts[3] if len(parts)>3 else ''
        account=_selected_account(db,account_name,default_account)
        category=_selected_category(db,category_name,default_category,payee,kind)
    if len(note)>1000 or any(ord(c)<32 for c in note):
        raise ValueError('Notiz darf höchstens 1000 Zeichen enthalten.')
    amount_to_minor(amount_text,account['decimals'])
    # Identical Telegram message ID is never prepared twice.
    old=db.execute('SELECT * FROM telegram_booking_drafts WHERE chat_id=? AND source_message_id=?',
                   (chat_id,message_id)).fetchone()
    if old:
        if old['status']=='posted':
            return response('Diese Nachricht wurde bereits verbucht. Keine Doppelbuchung.')
        if old['status']=='cancelled':
            return response('Dieser Buchungsvorschlag wurde bereits abgebrochen.')
        if old['expires_epoch']<int(time.time()):
            return response('Dieser Buchungsvorschlag ist abgelaufen. Bitte eine neue Nachricht senden.')
        return _draft_controls(db,old)
    now=int(time.time())
    count=db.execute('SELECT COUNT(*) FROM telegram_booking_drafts WHERE user_id=? AND created_epoch>?',
                     (user_id,now-600)).fetchone()[0]
    if count>=20:
        raise ValueError('Zu viele Buchungsvorschläge. Bitte später erneut versuchen.')
    token=secrets.token_urlsafe(16)
    db.execute('''INSERT INTO telegram_booking_drafts
        (token,chat_id,user_id,source_message_id,day,account_id,category_id,kind,amount_text,payee,note,
         created_epoch,expires_epoch) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''',
         (token,chat_id,user_id,message_id,today,account['id'],category,kind,amount_text,payee,note,now,now+EXPIRY))
    return _draft_controls(db,db.execute('SELECT * FROM telegram_booking_drafts WHERE token=?',(token,)).fetchone())


def callback(db, callback, chat_id, user_id, mark_edit, entry_payee, apply_balance_delta,
             notifications, actor_name, neutral_category_ids):
    parts=(callback or '').split(':')
    if len(parts)<3 or parts[0]!=PREFIX:
        raise ValueError('Kein FieLanzen-Rückruf.')
    op=parts[1];token=parts[2]
    if not re.fullmatch(r'[a-zA-Z0-9_-]{20,40}',token):
        raise ValueError('Ungültiger Buchungscode.')
    d=db.execute('SELECT * FROM telegram_booking_drafts WHERE token=?',(token,)).fetchone()
    if not d or d['chat_id']!=chat_id or d['user_id']!=user_id:
        raise ValueError('Buchungsvorschlag nicht gefunden oder nicht freigegeben.')
    if d['status']=='posted':
        return response('✅ Diese Buchung wurde bereits gespeichert. Keine Doppelbuchung.')
    if d['status']=='cancelled':
        return response('Der Vorschlag wurde bereits abgebrochen.')
    if d['expires_epoch']<int(time.time()):
        return response('Der Vorschlag ist abgelaufen. Bitte /finanz erneut senden.')
    if op=='no':
        db.execute("UPDATE telegram_booking_drafts SET status='cancelled' WHERE id=?",(d['id'],))
        return response('❌ Buchung verworfen. Kein Kontostand verändert.')
    if op in ('accounts','categories'):
        page=int(parts[3]) if len(parts)==4 and parts[3].isdigit() else 0
        if page>100: raise ValueError('Ungültige Seite.')
        if op=='accounts':
            options=[(a['id'],f'{a["title"]} ({a["code"]})') for a in available_accounts(db)]
            prefix='setaccount'
        else:
            expected=1 if d['kind']=='income' else 0
            types={r['id']:r['kind'] for r in db.execute('SELECT id,kind FROM categories')}
            options=[(0,'Ohne Kategorie')]+[(i,n) for i,n in _category_names(db).items() if types.get(i)==expected]
            options.sort(key=lambda x:x[1].casefold())
            prefix='setcategory'
        page_size=8
        start=page*page_size
        buttons=[[{'text':str(name)[:55], 'callback_data':f'{PREFIX}:{prefix}:{token}:{num}'}]
                 for num,name in options[start:start+page_size]]
        nav=[]
        if page: nav.append({'text':'◀️ Zurück','callback_data':f'{PREFIX}:{op}:{token}:{page-1}'})
        if start+page_size<len(options): nav.append({'text':'Weiter ▶️','callback_data':f'{PREFIX}:{op}:{token}:{page+1}'})
        if nav:buttons.append(nav)
        buttons.append([{'text':'↩️ Zum Vorschlag','callback_data':f'{PREFIX}:back:{token}'}])
        return response('Bitte '+('Konto' if op=='accounts' else 'Kategorie')+' auswählen:',buttons)
    if op=='setaccount':
        n=int(parts[3]) if len(parts)==4 and parts[3].isdigit() else -1
        if n not in {a['id'] for a in available_accounts(db)}:
            raise ValueError('Konto ist nicht mehr verfügbar.')
        amount_to_minor(d['amount_text'], db.execute('''SELECT c.decimals FROM accounts a JOIN currencies c
                                                    ON c.id=a.currency_id WHERE a.id=?''',(n,)).fetchone()[0])
        db.execute('UPDATE telegram_booking_drafts SET account_id=? WHERE id=?',(n,d['id']))
    elif op=='setcategory':
        n=int(parts[3]) if len(parts)==4 and parts[3].isdigit() else -1
        if n!=0 and n not in {r['id'] for r in db.execute('SELECT id FROM categories WHERE kind=?',
                (1 if d['kind']=='income' else 0,))}:
            raise ValueError('Kategorie existiert nicht.')
        db.execute('UPDATE telegram_booking_drafts SET category_id=? WHERE id=?',(n,d['id']))
    elif op=='ok':
        a=_selected_account(db,str(d['account_id']),0)
        amount=amount_to_minor(d['amount_text'],a['decimals'])
        if d['category_id'] and d['category_id'] not in {r['id'] for r in db.execute('SELECT id FROM categories WHERE kind=?',
                (1 if d['kind']=='income' else 0,))}:
            raise ValueError('Kategorie nicht mehr verfügbar.')
        payee_id=entry_payee(db,d['payee'])
        row=dict(day=d['day'],account_id=a['id'],to_account_id=0,category_id=d['category_id'],
                 payee_id=payee_id,amount=(-amount if d['kind']=='expense' else amount),note=d['note'],is_template=0)
        inserted=db.execute('''INSERT INTO transactions
            (day,account_id,to_account_id,category_id,payee_id,amount,note,is_template,origin)
            VALUES (:day,:account_id,:to_account_id,:category_id,:payee_id,:amount,:note,:is_template,'web')''',row)
        apply_balance_delta(db,row,+1)
        db.execute("UPDATE telegram_booking_drafts SET status='posted',transaction_id=? WHERE id=?",
                   (inserted.lastrowid,d['id']))
        mark_edit(db,'booking_created_telegram',f'Telegram {user_id} TX {inserted.lastrowid}')
        notifications.queue_booking(db,{**row,'notification_tx_id':inserted.lastrowid},actor_name)
        return response(f'✅ Buchung #{inserted.lastrowid} gespeichert und Kontostand aktualisiert.')
    elif op!='back':
        raise ValueError('Unbekannte Aktion.')
    d=db.execute('SELECT * FROM telegram_booking_drafts WHERE id=?',(d['id'],)).fetchone()
    return _draft_controls(db,d)
