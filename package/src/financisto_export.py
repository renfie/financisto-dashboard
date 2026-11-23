# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2026 René Fieler (RenFie)
# See LICENSE and NOTICE.md for terms and third-party notices.

"""Conservative, experimental Financisto backup writer.

Uses an original, SHA256-matched backup as a preservation template; unmodelled
entities and attributes are copied byte-for-byte as UTF-8 text. No write back
to Financisto or ledger happens here. Android restore remains unverified.
"""
from __future__ import annotations

import gzip
import hashlib
import io
import sqlite3
from datetime import datetime, time
from zoneinfo import ZoneInfo

from financisto_import import parse_backup, normalized_backup, BackupError

class ExportError(ValueError):
    pass

TZ = ZoneInfo('Europe/Berlin')
SOURCE_TABLE = 'financisto_export_source'


def ensure_source_table(db: sqlite3.Connection):
    db.execute("""CREATE TABLE IF NOT EXISTS financisto_export_source (
        sha256 TEXT PRIMARY KEY,
        package_id TEXT NOT NULL,
        raw BLOB NOT NULL,
        retained_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""")


def store_matching_source(db, raw: bytes, *, sha256: str | None = None):
    digest = hashlib.sha256(raw).hexdigest()
    if sha256 is not None and digest != sha256:
        raise ExportError('Originaldatei stimmt nicht mit dem importierten Stand überein.')
    try:
        parse_backup(raw)
    except BackupError as exc:
        raise ExportError('Sicherung wurde nicht als gültige Financisto-Datei erkannt.') from exc
    ensure_source_table(db)
    package = gzip.decompress(raw).splitlines()[0].decode('ascii')
    db.execute('DELETE FROM financisto_export_source')
    db.execute("""INSERT INTO financisto_export_source (sha256,package_id,raw)
                  VALUES (?,?,?)""", (digest,package,raw))
    return digest


def matching_source(db):
    ensure_source_table(db)
    row = db.execute("SELECT value FROM meta WHERE key='last_import_sha256'").fetchone()
    if not row or not row[0]:
        raise ExportError('Noch kein ursprünglicher Financisto-Import dokumentiert.')
    digest = str(row[0])
    stored = db.execute('SELECT raw FROM financisto_export_source WHERE sha256=?', (digest,)).fetchone()
    if not stored or not stored[0]:
        raise ExportError('Passende Original-Sicherung fehlt. Bitte erst die exakt zuletzt importierte .backup-Datei als Exportgrundlage hinterlegen.')
    raw = bytes(stored[0])
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ExportError('Gespeicherte Original-Sicherung stimmt nicht mit dem importierten Stand überein.')
    return raw


def safe_text(value):
    s = str(value if value is not None else '')
    if any(ch in s for ch in ('\r','\n','\x00')):
        raise ExportError('Neue Namen/Notizen mit Zeilenumbrüchen können noch nicht sicher exportiert werden.')
    return s


def template(kind, existing, *, now):
    # Original app-schema fields used by standard Financisto backups. Preserve
    # any fork-specific field names but DO NOT duplicate user-specific values.
    defaults = {
        'account': dict(_id='0',title='',creation_date=str(now),currency_id='1',total_amount='0',
                        type='CASH',sort_order='0',is_active='1',is_include_into_totals='1',
                        last_category_id='0',last_account_id='0',total_limit='0',card_issuer='VISA',
                        closing_day='0',payment_day='0',last_transaction_date='0',updated_on='0'),
        'category': dict(_id='0',title='',left='0',right='0',last_location_id='0',
                         last_project_id='0',type='0',updated_on='0',is_active='1'),
        'payee': dict(_id='0',title='',last_category_id='0',updated_on='0',is_active='1'),
        'currency': dict(_id='0',name='EUR',symbol='€',decimals='2',updated_on='0'),
        'transactions': dict(_id='0',from_account_id='0',to_account_id='0',category_id='0',
                             project_id='0',location_id='0',note='',from_amount='0',to_amount='0',
                             datetime=str(now),accuracy='0',latitude='0',longitude='0',
                             is_template='0',status='UR',is_ccard_payment='0',
                             last_recurrence='0',payee_id='0',parent_id='0',updated_on='0',
                             original_currency_id='0',original_from_amount='0'),
    }
    base = defaults[kind].copy()
    # If newer Financisto supplied additional fields, include their field
    # names without copying personal content from another record.
    for key, val in existing.items():
        if key not in base:
            base[key] = '0' if val and val.lstrip('-').isdigit() else ''
    return base


def parse_raw_blocks(raw):
    """Keep unknown entities & every original block unchanged."""
    try:
        source = gzip.decompress(raw).decode('utf-8-sig')
    except (ValueError, UnicodeDecodeError, OSError) as exc:
        raise ExportError('Originaldatei kann nicht gelesen werden.') from exc
    lines = source.splitlines(keepends=True)
    if not lines or lines[-1].strip() != '#END':
        raise ExportError('Unvollständige Originaldatei.')
    chunks=[]
    i=0
    while i<len(lines):
        ln=lines[i]
        if ln.startswith('$ENTITY:'):
            entity=ln[8:].strip()
            j=i+1
            while j<len(lines) and lines[j].strip()!='$$': j+=1
            if j==len(lines): raise ExportError('Fehlender Datensatzabschluss in der Originaldatei.')
            rawblock=''.join(lines[i:j+1])
            content={}
            for row in lines[i+1:j]:
                if ':' in row:
                    k,v=row.rstrip('\r\n').split(':',1)
                    content[k]=v
            chunks.append((entity,content,rawblock))
            i=j+1
        else:
            chunks.append((None,None,ln))
            i+=1
    return chunks


def render_block(entity, item):
    # Must preserve schema field names without accidentally introducing line
    # separators or '$$' entity terminators.
    chunks=[f'$ENTITY:{entity}\n']
    for k, v in item.items():
        if '\n' in k or ':' in k or k.startswith('$'):
            raise ExportError('Unbekannter Feldname im Backup.')
        chunks.append(f'{k}:{safe_text(v)}\n')
    chunks.append('$$\n')
    return ''.join(chunks)


def make_export(db: sqlite3.Connection):
    """Return gzip bytes and stats. No database modification."""
    raw=matching_source(db)
    source=parse_backup(raw)
    normalized=normalized_backup(source)
    # Read one SQLite transaction externally for a stable multi-table snapshot.
    all_accounts={r['id']:r for r in db.execute("""SELECT a.*,s.balance_minor,s.is_active,s.include_in_totals
        FROM accounts a LEFT JOIN account_snapshots s ON s.account_id=a.id""")}
    all_categories={r['id']:r for r in db.execute('SELECT * FROM categories')}
    all_payees={r['id']:r for r in db.execute('SELECT * FROM payees')}
    all_currencies={r['id']:r for r in db.execute('SELECT * FROM currencies')}
    all_tx={r['id']:r for r in db.execute('SELECT * FROM transactions')}
    if not all_accounts or not all_tx:
        raise ExportError('Konten oder Buchungen fehlen. Export abgebrochen.')
    source_currency_ids={int(c['_id']) for c in source['currency']}
    missing_original=source_currency_ids-set(all_currencies)
    if missing_original:
        raise ExportError('Ursprüngliche Währungen fehlen; Rückexport abgebrochen.')
    for c in all_currencies.values():
        if not c['code'] or not (0<=int(c['decimals'])<=6):
            raise ExportError('Ungültige Währung; Rückexport abgebrochen.')
    for account in all_accounts.values():
        if account['balance_minor'] is None or account['currency_id'] not in all_currencies:
            raise ExportError('Unbekannter Kontostand oder Währung; Export abgebrochen.')
    original_tx={int(t['_id']):t for t in source['transactions']}
    for t in all_tx.values():
        # Historical original rows may refer to soft-deleted payees/categories.
        # Preserve them untouched; apply strict reference checks to new web rows.
        if t['origin'] not in ('web','financisto_edited'):
            continue
        if t['account_id'] not in all_accounts or t['to_account_id'] and t['to_account_id'] not in all_accounts:
            raise ExportError('Buchung verweist auf ein fehlendes Konto.')
        source_old=original_tx.get(t['id']) if t['origin']=='financisto_edited' else None
        if t['category_id'] and t['category_id'] not in all_categories:
            if not source_old or t['category_id']!=int(source_old.get('category_id','0')):
                raise ExportError('Buchung verweist auf eine fehlende Kategorie.')
        if t['payee_id'] and t['payee_id'] not in all_payees:
            if not source_old or t['payee_id']!=int(source_old.get('payee_id','0')):
                raise ExportError('Buchung verweist auf einen fehlenden Empfänger.')
        if t['to_account_id'] and all_accounts[t['account_id']]['currency_id'] != all_accounts[t['to_account_id']]['currency_id']:
            raise ExportError('Buchung zwischen unterschiedlichen Währungen benötigt gesonderte Umrechnung.')

    # Untouched original transactions retain all original extension fields.
    # Edited original transactions preserve those fields but update explicitly
    # modeled attributes. Deleted originals are deliberately omitted from the
    # exported set, never silently restored from the source backup.
    original_tx={int(t['_id']):t for t in source['transactions']}
    original_norm={v[0]:v for v in normalized[4]}
    for ident,tx in all_tx.items():
        if tx['origin']=='financisto':
            original=original_norm.get(ident)
            if not original: raise ExportError(f'Original zur Buchung {ident} fehlt.')
            current=(tx['id'],tx['day'],tx['account_id'],tx['to_account_id'],
                     tx['category_id'],tx['payee_id'],tx['amount'],tx['note'],tx['is_template'])
            if current != tuple(original):
                raise ExportError(f'Importierte Buchung {ident} weicht ohne Bearbeitungsmarkierung ab.')
        elif tx['origin']=='financisto_edited':
            if ident not in original_tx:
                raise ExportError(f'Original zur bearbeiteten Buchung {ident} fehlt.')
        elif tx['origin']=='web':
            if ident in original_tx:
                raise ExportError(f'Web-Buchungs-ID {ident} kollidiert mit Originaldaten.')
        else:
            raise ExportError(f'Unbekannte Buchungsherkunft {ident}.')

    # A bounded snapshot of all current (not only selected month) web data.
    items={
        'account':{}, 'category':{}, 'payee':{}, 'currency':{}, 'transactions':{},
    }
    now=int(datetime.now(tz=TZ).timestamp()*1000)
    samples={kind:source[kind][0] if source[kind] else {} for kind in items}
    for ident,r in all_accounts.items():
        base=next((dict(a) for a in source['account'] if int(a['_id'])==ident), None)
        it=base or template('account', samples['account'],now=now)
        it.update(_id=str(ident),title=safe_text(r['title']),currency_id=str(r['currency_id']),
                  type=safe_text(r['kind'] or 'CASH'),total_amount=str(r['balance_minor']),
                  is_active=str(1 if r['is_active'] is None else r['is_active']),
                  is_include_into_totals=str(1 if r['include_in_totals'] is None else r['include_in_totals']))
        items['account'][ident]=it
    for ident,r in all_categories.items():
        base=next((dict(a) for a in source['category'] if int(a['_id'])==ident), None)
        it=base or template('category',samples['category'],now=now)
        it.update(_id=str(ident),title=safe_text(r['title']),left=str(r['lft']),
                  right=str(r['rgt']),type=str(r['kind']))
        items['category'][ident]=it
    for ident,r in all_payees.items():
        base=next((dict(a) for a in source['payee'] if int(a['_id'])==ident), None)
        it=base or template('payee',samples['payee'],now=now)
        it.update(_id=str(ident),title=safe_text(r['title']))
        items['payee'][ident]=it
    for ident,r in all_currencies.items():
        base=next((dict(a) for a in source['currency'] if int(a['_id'])==ident), None)
        it=base or template('currency', source['currency'][0] if source['currency'] else {},now=now)
        it.update(_id=str(ident),name=safe_text(r['code']),symbol=safe_text(r['symbol'] or r['code']),
                  decimals=str(int(r['decimals'])))
        items['currency'][ident]=it
    for ident,r in all_tx.items():
        if r['origin']=='financisto':
            items['transactions'][ident]=original_tx[ident]
        else:
            it=(dict(original_tx[ident]) if r['origin']=='financisto_edited'
                else template('transactions',samples['transactions'],now=now))
            # Local noon avoids daylight-saving boundary date shifts.
            stamp=int(datetime.combine(datetime.fromisoformat(r['day']).date(),time(12),TZ).timestamp()*1000)
            it.update(_id=str(ident),from_account_id=str(r['account_id']),
                      to_account_id=str(r['to_account_id']),category_id=str(r['category_id']),
                      payee_id=str(r['payee_id']),from_amount=str(r['amount']),
                      to_amount=str(-r['amount']) if r['to_account_id'] else '0',
                      datetime=str(stamp),
                      is_template=str(r['is_template']),note=safe_text(r['note']))
            if r['origin']=='web':
                it['last_recurrence']=str(stamp)
            items['transactions'][ident]=it

    original_ids={kind:{int(row['_id']) for row in source[kind]} for kind in items}
    emitted={kind:set() for kind in items}
    # Read original blocks and replace only the four known entity groups,
    # preserving every unrecognized entity and all its fields exactly.
    chunks=parse_raw_blocks(raw)
    last_position={kind:max((i for i,c in enumerate(chunks) if c[0]==kind),default=-1) for kind in items}
    replacement=[]
    for i,(entity, content, rawchunk) in enumerate(chunks):
        if entity not in items:
            replacement.append(rawchunk)
            continue
        ident=int(content.get('_id','0'))
        if ident in items[entity]:
            if entity=='transactions' and all_tx[ident]['origin']=='financisto':
                # Exact original block: retain all unmodelled extension fields.
                replacement.append(rawchunk)
            else:
                replacement.append(render_block(entity,items[entity][ident]))
            emitted[entity].add(ident)
        # omit only deliberately deleted, unreferenced master data
        if i == last_position[entity]:
            for new_id in sorted(items[entity].keys()-emitted[entity]):
                replacement.append(render_block(entity,items[entity][new_id]))
                emitted[entity].add(new_id)
    # Some historical files have no payees/categories: append before #END.
    for entity in items:
        if not emitted[entity]:
            pending=[render_block(entity,items[entity][ident]) for ident in sorted(items[entity])]
            if pending:
                idx=len(replacement)-1
                while idx>=0 and replacement[idx].strip()!='#END': idx-=1
                if idx<0: raise ExportError('Fehlende Abschlussmarkierung.')
                replacement[idx:idx]=pending
    plain=''.join(replacement).encode('utf-8')
    buf=io.BytesIO()
    with gzip.GzipFile(fileobj=buf,mode='wb',mtime=0) as fout:
        fout.write(plain)
    exported=buf.getvalue()
    # Independent structural round trip through the currently deployed parser.
    verify=parse_backup(exported)
    norm=normalized_backup(verify)
    if len(norm[0])!=len(all_accounts) or len(norm[1])!=len(all_currencies) or len(norm[2])!=len(all_categories) or len(norm[3])!=len(all_payees) or len(norm[4])!=len(all_tx):
        raise ExportError('Plausibilitätsprüfung fehlgeschlagen: Datensatzanzahl weicht ab.')
    actual={t[0]:t for t in norm[4]}
    for ident,r in all_tx.items():
        expected=(ident,r['day'],r['account_id'],r['to_account_id'],r['category_id'],r['payee_id'],r['amount'],r['note'][:5000] if r['note'] else '',r['is_template'])
        if tuple(actual[ident])!=tuple(expected):
            raise ExportError(f'Plausibilitätsprüfung für Buchung {ident} fehlgeschlagen.')
    return exported, {'transactions':len(all_tx),'web':sum(1 for t in all_tx.values() if t['origin']=='web'),
                      'accounts':len(all_accounts),'categories':len(all_categories),'payees':len(all_payees)}
