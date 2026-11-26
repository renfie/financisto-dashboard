# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2026 René Fieler (RenFie)
"""Shared, read-only monthly ledger aggregation for web and Mobile API.

The caller supplies the dashboard's existing neutral-category definitions and
category hierarchy. The single SQL query aggregates the full selected ledger;
mobile booking pagination never contributes to these figures.
"""
from collections import defaultdict
from datetime import date


def months_between(first, last):
    start_y, start_m = map(int, first.split('-'))
    end_y, end_m = map(int, last.split('-'))
    start, end = start_y * 12 + start_m - 1, end_y * 12 + end_m - 1
    return [f'{i // 12:04d}-{i % 12 + 1:02d}' for i in range(start, end+1)]


def summarize_months(db, *, first, last, currency_id, today, neutral_ids,
                     categories, account_id=None, category_id=None, search=None):
    """Calculate booked totals and (separately) all-dated projected totals.

    Income and expenses match the dashboard comparison: internal transfers and
    neutral/pass-through/adjustment categories are excluded. Booking counts
    count only non-neutral, non-transfer, nonzero-value bookings. Transfers
    have their own absolute source amount and count, and never affect balance.
    A filtered transfer is visible if the account is source OR destination.
    """
    months=months_between(first,last)
    selected=set()
    if category_id is not None:
        parent=next(c for c in categories if int(c['id'])==int(category_id))
        selected={int(c['id']) for c in categories
                  if c['lft'] is not None and c['rgt'] is not None
                  and parent['lft'] is not None and parent['rgt'] is not None
                  and c['lft']>=parent['lft'] and c['rgt']<=parent['rgt']}
        selected.add(int(category_id))
    conditions=['t.day >= ?', 't.day < ?', 'a.currency_id=?', 't.is_template=0']
    last_y,last_m=map(int,last.split('-'))
    next_month=f'{last_y+int(last_m==12):04d}-{last_m%12+1:02d}-01'
    params=[first+'-01',next_month,currency_id]
    if account_id is not None:
        conditions.append('(t.account_id=? OR t.to_account_id=?)')
        params.extend([account_id,account_id])
    if category_id is not None:
        conditions.append('t.category_id IN ('+','.join('?' for _ in selected)+')')
        params.extend(sorted(selected))
    if search:
        escaped=search.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')
        pattern='%'+escaped+'%'
        conditions.append("(p.title LIKE ? ESCAPE '\\' OR t.note LIKE ? ESCAPE '\\' OR c.title LIKE ? ESCAPE '\\')")
        params.extend([pattern]*3)
    # Aggregation stays inside SQLite: at most a few thousand month/category
    # groups cross into Python even for very large transaction histories.
    sql='''SELECT substr(t.day,1,7) AS month,t.category_id AS category_id,
         CASE WHEN COALESCE(t.to_account_id,0)<>0 THEN 1 ELSE 0 END AS transfer,
         CASE WHEN t.day<=? THEN 1 ELSE 0 END AS booked,
         CASE WHEN t.amount<0 THEN -1 WHEN t.amount>0 THEN 1 ELSE 0 END AS sign,
         COUNT(*) AS booking_count,
         COALESCE(SUM(ABS(t.amount)),0) AS amount_minor
         FROM transactions t JOIN accounts a ON a.id=t.account_id
         LEFT JOIN payees p ON p.id=t.payee_id
         LEFT JOIN categories c ON c.id=t.category_id
         WHERE '''+' AND '.join(conditions)+'''
         GROUP BY month,t.category_id,transfer,booked,sign'''
    grouped=db.execute(sql,[today,*params]).fetchall()
    results={m:{'month':m,'income_minor':0,'expense_minor':0,'balance_minor':0,
                'booking_count':0,'transfer_count':0,'transfer_minor':0,
                'categories':{'income':[],'expense':[]}} for m in months}
    projected={m:{'income':0,'expenses':0,'balance':0} for m in months}
    category_totals=defaultdict(lambda:[0,0])
    for r in grouped:
        m=r['month']
        if m not in results:continue
        category=r['category_id']
        if int(r['transfer']):
            if int(r['booked']):
                results[m]['transfer_count']+=int(r['booking_count'])
                results[m]['transfer_minor']+=int(r['amount_minor'])
            continue
        if category in neutral_ids or not r['sign']:
            continue
        kind='income' if r['sign']>0 else 'expense'
        amount=int(r['amount_minor'])
        projected[m][('income' if kind=='income' else 'expenses')]+=amount
        if not r['booked']:continue
        results[m][kind+'_minor']+=amount
        results[m]['booking_count']+=int(r['booking_count'])
        category_totals[(m,kind,int(category or 0))][0]+=amount
        category_totals[(m,kind,int(category or 0))][1]+=int(r['booking_count'])
    for m,entry in results.items():
        entry['balance_minor']=entry['income_minor']-entry['expense_minor']
        projected[m]['balance']=projected[m]['income']-projected[m]['expenses']
    return results,projected,category_totals


def attach_categories(results, category_totals, names):
    """Include full descendant paths, never merge distinct leaf categories."""
    for (month,kind,category_id),(amount,count) in category_totals.items():
        results[month]['categories'][kind].append(dict(
            category_id=category_id,
            category=names.get(category_id,'Ohne Kategorie'),
            amount_minor=amount,booking_count=count))
    for row in results.values():
        for group in ('income','expense'):
            row['categories'][group].sort(key=lambda x:(x['category'].casefold(),x['category_id']))
    return results
