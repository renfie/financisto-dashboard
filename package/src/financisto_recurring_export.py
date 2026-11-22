"""Conservative export of enabled Web recurring rules to a Financisto .backup.

This module consumes a *fully validated* export from financisto_export.make_export,
never writes to SQLite, never alters recorded transactions, and refuses formats
with ambiguous execution semantics. It reuses the existing Android row schema.
"""
from __future__ import annotations

import datetime as dt
import gzip
import io
import sqlite3
from zoneinfo import ZoneInfo

from financisto_export import ExportError, parse_raw_blocks, render_block, template
from financisto_import import parse_backup

TZ = ZoneInfo('Europe/Berlin')


def recurrence_for(rule):
    """The precise EVERY_NTH_DAY monthly dialect found in the 2026-11-02 backup."""
    freq = rule['frequency']
    distance = int(rule['interval_count'])
    day = int(rule['day_of_month'])
    if not (1 <= distance <= 120 and 1 <= day <= 31):
        raise ExportError(f'Regel {rule["title"]}: ungültiger Abstand bzw. Monatstag.')
    if freq not in ('monthly', 'quarterly', 'yearly'):
        raise ExportError(f'Regel {rule["title"]}: {freq} kann noch nicht sicher nach Financisto exportiert werden. Bitte zuerst pausieren.')
    distance *= {'monthly': 1, 'quarterly': 3, 'yearly': 12}[freq]
    if distance > 120:
        raise ExportError(f'Regel {rule["title"]}: Abstand über 120 Monaten wird nicht unterstützt.')
    try:
        date = dt.date.fromisoformat(rule['start_on'])
    except ValueError as exc:
        raise ExportError(f'Regel {rule["title"]}: ungültiges Startdatum.') from exc
    if date.year < 2000 or date.year > 2100:
        raise ExportError(f'Regel {rule["title"]}: Startdatum außerhalb 2000–2100.')
    return (f'{date.isoformat()}T12:00:00~MONTHLY:'
            f'monthly_pattern_0@EVERY_NTH_DAY#count@1#interval@{distance}#'
            f'monthly_pattern_params_0@{day}#~INDEFINETELY:null')


def preview_summary(db):
    """Lightweight counts only: safe to display in admin settings."""
    try:
        rows = db.execute("""SELECT active,auto_post,deleted_on,source_kind,frequency
          FROM recurring_rules""").fetchall()
    except sqlite3.OperationalError:
        return dict(total=0,automatic=0,manual=0,paused=0,removed=0,unsupported=0)
    live = [r for r in rows if not r['deleted_on']]
    return dict(total=len(rows),automatic=sum(int(r['active'])==1 and int(r['auto_post'])==1 for r in live),
                manual=sum(int(r['active'])==1 and int(r['auto_post'])==0 for r in live),
                paused=sum(not int(r['active']) for r in live),
                removed=len(rows)-len(live),
                unsupported=sum(int(r['active'])==1 and r['frequency'] not in ('monthly','quarterly','yearly') for r in live))


def merge_recurring_export(db, base_raw: bytes, stats: dict):
    """Build an offline file with current automatic rules, never post anything.

    Original transaction blocks are overwritten only if their matching imported
    template is explicitly active/automatic. Manually enabled rules are rejected:
    Android's automatic-scheduling semantics cannot be guaranteed to match.
    Paused/soft-deleted rules are absent from the new file (never reactivated).
    """
    current = parse_backup(base_raw)
    prior_tx = {int(t['_id']): t for t in current['transactions']}
    prior_template_ids = {i for i, row in prior_tx.items() if row.get('is_template')=='2' and row.get('recurrence')}
    try:
        rows = [dict(r) for r in db.execute('SELECT * FROM recurring_rules ORDER BY id')]
    except sqlite3.OperationalError as exc:
        raise ExportError('Wiederkehrende Buchungen sind noch nicht eingerichtet.') from exc
    by_source = {}
    for rule in rows:
        if rule['source_kind']=='financisto':
            source_id = rule['source_id']
            if source_id in by_source:
                raise ExportError('Doppelte Financisto-Vorlagenkennung in SQLite.')
            by_source[source_id] = rule
            if source_id not in prior_template_ids:
                raise ExportError(f'Die Vorlage {rule["title"]} stammt nicht aus der verwendeten Originalsicherung. Bitte Importstand prüfen.')
    # Templates not imported into Web recurring_rules remain unchanged in the
    # exact original Financisto backup. Do not require a second manual import.
    untracked = prior_template_ids-set(by_source)

    for rule in rows:
        if rule['deleted_on'] or not int(rule['active']):
            continue
        if not int(rule['auto_post']):
            raise ExportError(f'Regel {rule["title"]}: manuell aktive Regeln können in Financisto unbeabsichtigt automatisch laufen. Bitte vor dem Export pausieren oder ausdrücklich auf Automatisch umstellen.')
        if rule['needs_review']:
            raise ExportError(f'Regel {rule["title"]}: noch nicht abgeschlossene Regelprüfung. Bitte bearbeiten.')
        if (rule.get('run_at') or '00:00') != '00:00':
            raise ExportError(f'Regel {rule["title"]}: individuelle Ausführungsuhrzeit kann in Financisto nicht sicher übernommen werden.')
        if rule.get('end_on') or rule.get('max_occurrences') is not None:
            raise ExportError(f'Regel {rule["title"]}: Begrenzte Wiederholungen (Enddatum/Anzahl) können nicht zuverlässig in das Android-Format exportiert werden. Bitte die Regel vor dem Export deaktivieren.')
        from recurring import validate_rule
        try:
            validate_rule(db,rule)
        except (ValueError, sqlite3.Error) as exc:
            raise ExportError(f'Regel {rule["title"]}: {exc}') from exc
        recurrence_for(rule)

    now = int(dt.datetime.now(TZ).timestamp()*1000)
    account_ids = {row['id'] for row in db.execute('SELECT id FROM accounts')}
    categories = {row['id'] for row in db.execute('SELECT id FROM categories')}
    payees = {row['id'] for row in db.execute('SELECT id FROM payees')}
    chunks = parse_raw_blocks(base_raw)
    max_ident = max(prior_tx, default=0)
    # Web-origin transaction IDs are part of the baseline and must stay free.
    inserts = []
    replacements = {}
    removed = set()
    updated_count = new_count = 0
    seen_source_ids = set()
    for rule in rows:
        is_original = rule['source_kind']=='financisto'
        orig_id = rule['source_id'] if is_original else None
        if is_original:
            seen_source_ids.add(orig_id)
        if rule['deleted_on'] or not int(rule['active']):
            if is_original:
                removed.add(orig_id)
            continue
        if int(rule['account_id']) not in account_ids or (rule['to_account_id'] and int(rule['to_account_id']) not in account_ids):
            raise ExportError(f'Regel {rule["title"]}: fehlendes Konto.')
        if rule['category_id'] and int(rule['category_id']) not in categories:
            raise ExportError(f'Regel {rule["title"]}: fehlende Kategorie.')
        if rule['payee_id'] and int(rule['payee_id']) not in payees:
            raise ExportError(f'Regel {rule["title"]}: fehlender Empfänger.')
        if is_original:
            result = dict(prior_tx[orig_id])
            ident = orig_id
            updated_count += 1
        else:
            max_ident += 1
            ident = max_ident
            result = template('transactions',next(iter(prior_tx.values())),now=now)
            new_count += 1
        start_date=dt.date.fromisoformat(rule['start_on'])
        start_millis=int(dt.datetime.combine(start_date,dt.time(12,0),TZ).timestamp()*1000)
        old_last = int(result.get('last_recurrence') or 0)
        result.update(_id=str(ident),from_account_id=str(rule['account_id']),
             to_account_id=str(rule['to_account_id']),category_id=str(rule['category_id']),
             payee_id=str(rule['payee_id']),from_amount=str(rule['amount_minor']),
             to_amount=str(-int(rule['amount_minor'])) if rule['to_account_id'] else '0',
             note=(rule['note'] or rule['title']),datetime=str(start_millis),
             is_template='2',status='PN',last_recurrence=str(max(now,old_last)),
             recurrence=recurrence_for(rule))
        if is_original:
            replacements[ident] = result
        else:
            inserts.append(result)
    # Preserve untracked original templates instead of dropping or rewriting them.
    if not seen_source_ids.issubset(prior_template_ids):
        raise ExportError('Regelverweise auf unbekannte Financisto-Vorlagen gefunden.')

    outgoing=[]
    last_transaction_pos=max((idx for idx,c in enumerate(chunks) if c[0]=='transactions'), default=-1)
    if last_transaction_pos<0:
        raise ExportError('Keine Transaktionsdaten in der Originaldatei gefunden.')
    for pos,(kind, row, chunk) in enumerate(chunks):
        if kind=='transactions':
            ident=int(row['_id'])
            if ident in removed:
                pass
            elif ident in replacements:
                outgoing.append(render_block(kind,replacements[ident]))
            else:
                outgoing.append(chunk)
        else:
            outgoing.append(chunk)
        if pos==last_transaction_pos:
            for item in inserts:
                outgoing.append(render_block('transactions',item))
    raw_text=''.join(outgoing).encode('utf-8')
    buffer=io.BytesIO()
    with gzip.GzipFile(fileobj=buffer,mode='wb',mtime=0) as f:
        f.write(raw_text)
    exported=buffer.getvalue()
    actual=parse_backup(exported)
    out_tx={int(r['_id']):r for r in actual['transactions']}
    if len(out_tx)!=len(actual['transactions']):
        raise ExportError('Doppelte Transaktions-ID im Rückexport.')
    expected_ids=(set(prior_tx)-removed)|set(int(x['_id']) for x in inserts)
    if set(out_tx)!=expected_ids:
        raise ExportError('Transaktionsanzahl/IDs im Rückexport weichen ab.')
    for ident, before in prior_tx.items():
        if ident in removed: continue
        after=out_tx[ident]
        if ident not in replacements and before!=after:
            raise ExportError(f'Unveränderte Buchung {ident} wurde beim Export verändert.')
        if ident in replacements and after!=replacements[ident]:
            raise ExportError(f'Wiederkehrende Vorlage {ident} konnte nicht korrekt übertragen werden.')
    for added in inserts:
        if out_tx[int(added['_id'])]!=added:
            raise ExportError('Neue Wiederholungsvorlage wurde unvollständig gespeichert.')
    for entity in ('account','currency','category','payee'):
        if current[entity]!=actual[entity]:
            raise ExportError(f'Stammdaten {entity} wurden beim Wiederholungsexport unerwartet verändert.')
    copy_stats = dict(stats)
    copy_stats.update({'recurring_updated':updated_count,'recurring_new':new_count,
                       'recurring_preserved_original':len(untracked),
                       'recurring_excluded':len(removed), 'recurring_exported':updated_count+new_count+len(untracked),
                       'transactions_with_templates':len(out_tx)})
    return exported,copy_stats
