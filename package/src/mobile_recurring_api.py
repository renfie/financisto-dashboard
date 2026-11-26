# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2026 René Fieler (RenFie)
"""Mobile recurring-rule serialization and input validation.

All SQL writes are performed by the authenticated Flask adapter in app.py.
The existing recurring module remains the only scheduler/posting engine.
"""
import hashlib
import json
import re
from datetime import date
from recurring import validate_rule, completed_runs

_FIELDS = ('title','kind','account_id','to_account_id','category_id','payee_title',
           'amount_minor','note','frequency','interval_count','day_of_month',
           'start_on','run_at','end_on','max_occurrences')
_HASH_FIELDS = ('id','title','kind','account_id','to_account_id','category_id',
                'payee_id','amount_minor','note','frequency','interval_count',
                'day_of_month','start_on','run_at','end_on','max_occurrences',
                'completed_on','next_on','active','auto_post','needs_review','updated_on','deleted_on')


def revision(row, count):
    payload=[row[key] for key in _HASH_FIELDS]+[count]
    return hashlib.sha256(json.dumps(payload,ensure_ascii=False,default=str,
                                     separators=(',',':')).encode()).hexdigest()[:32]


def read_rule(db, rule_id):
    return db.execute("""SELECT r.*,p.title payee_title,
         (SELECT COUNT(*) FROM recurring_runs x WHERE x.rule_id=r.id) completed_count
         FROM recurring_rules r LEFT JOIN payees p ON p.id=r.payee_id
         WHERE r.id=? AND r.deleted_on IS NULL""",(rule_id,)).fetchone()


def serialize(row):
    count=int(row['completed_count'])
    mode='paused' if not row['active'] else 'auto' if row['auto_post'] else 'manual'
    result={key:row[key] for key in ('id','title','kind','account_id','to_account_id',
            'category_id','payee_id','payee_title','note','frequency','interval_count',
            'day_of_month','start_on','run_at','end_on','max_occurrences',
            'next_on','needs_review')}
    result['revision']=revision(row,count)
    result['amount_minor']=abs(int(row['amount_minor']))
    result['mode']=mode
    result['completed_count']=count
    result['payee_title']=result['payee_title'] or ''
    result['needs_review']=result['needs_review'] or ''
    result['to_account_id']=int(result['to_account_id'] or 0)
    result['category_id']=int(result['category_id'] or 0)
    result['payee_id']=int(result['payee_id'] or 0)
    return result


def _positive_int(value, label, lower, upper):
    if type(value) is not int or not lower<=value<=upper:
        raise ValueError(label+' außerhalb des erlaubten Bereichs.')
    return value


def parse_payload(db, data, resolve_payee):
    if set(data)!=set(_FIELDS):
        raise ValueError('Regelentwurf muss genau die vereinbarten Felder enthalten.')
    title=data['title']
    if not isinstance(title,str) or not title.strip() or len(title.strip())>160:
        raise ValueError('Ungültiger Regelname.')
    kind=data['kind']
    if kind not in ('expense','income','transfer'):
        raise ValueError('Ungültige Buchungsart.')
    frequency=data['frequency']
    if frequency not in ('daily','weekly','monthly','quarterly','yearly'):
        raise ValueError('Ungültiges Wiederholungsintervall.')
    period=_positive_int(data['interval_count'],'Intervall',1,120)
    dom=_positive_int(data['day_of_month'],'Monatstag',1,31)
    source=_positive_int(data['account_id'],'Quellkonto',1,2147483647)
    target=_positive_int(data['to_account_id'],'Zielkonto',0,2147483647)
    category=_positive_int(data['category_id'],'Kategorie',0,2147483647)
    if kind=='transfer':
        if target==0 or category!=0: raise ValueError('Umbuchung benötigt Zielkonto, aber keine Kategorie.')
    elif target: raise ValueError('Zielkonto nur bei Umbuchungen erlaubt.')
    amount=_positive_int(data['amount_minor'],'Betrag',1,9223372036854775807)
    note=data['note']
    if not isinstance(note,str) or len(note)>1000: raise ValueError('Ungültige Notiz.')
    payee_title=data['payee_title']
    if not isinstance(payee_title,str) or len(payee_title.strip())>120:
        raise ValueError('Ungültiger Empfängername.')
    start=data['start_on']
    end=data['end_on']
    if not isinstance(start,str):
        raise ValueError('Startdatum erforderlich.')
    try:
        start_date=date.fromisoformat(start)
        if start_date.isoformat()!=start or not 2000<=start_date.year<=2100:
            raise ValueError()
        if end is not None:
            if not isinstance(end,str): raise ValueError()
            end_date=date.fromisoformat(end)
            if end_date.isoformat()!=end or end_date<start_date or end_date.year>2100:
                raise ValueError()
    except ValueError:
        raise ValueError('Ungültiges Start- oder Enddatum.') from None
    clock=data['run_at']
    if not isinstance(clock,str) or not re.fullmatch(r'(?:[01][0-9]|2[0-3]):[0-5][0-9]',clock):
        raise ValueError('Ausführungszeit muss HH:MM sein.')
    maximum=data['max_occurrences']
    if maximum is not None: _positive_int(maximum,'Maximale Ausführungen',1,10000)
    account=db.execute("""SELECT c.decimals FROM accounts a JOIN currencies c
         ON a.currency_id=c.id WHERE a.id=?""",(source,)).fetchone()
    if account is None: raise ValueError('Quellkonto unbekannt.')
    # Resolve inside the same transaction; rollback also removes newly created payees.
    payee=resolve_payee(db,payee_title)
    row=dict(title=title.strip(),kind=kind,account_id=source,to_account_id=target,
             category_id=category,payee_id=payee,
             amount_minor=amount if kind=='income' else -amount,note=note,
             frequency=frequency,interval_count=period,day_of_month=dom,
             start_on=start,run_at=clock,end_on=end,max_occurrences=maximum)
    validate_rule(db,row)
    return row
