# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2026 René Fieler (RenFie)
"""Contract and transactional integration tests for Mobile recurring API (stdlib)."""
import ast
import hashlib
import importlib
import json
import re
import sqlite3
import sys
import tempfile
import time
import types
import unittest
import uuid
from datetime import date
from pathlib import Path
from types import SimpleNamespace

BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE/'src'))
sys.modules.setdefault('notifications',types.SimpleNamespace(queue_booking=lambda *a,**k:None))
import recurring
import mobile_recurring_api as api


def stub_app():
    source=(BASE/'src'/'app.py').read_text(encoding='utf-8')
    tree=ast.parse(source)
    names={'_mobile_receipt','_mobile_save_receipt','_mobile_body_and_request_id','_mobile_recurring_mutate',
           'mobile_api_recurring_list'}
    nodes=[]
    for node in tree.body:
        if isinstance(node,ast.FunctionDef) and node.name in names:
            node.decorator_list=[]
            nodes.append(node)
    assert len(nodes)==len(names)
    scope=dict(sqlite3=sqlite3,re=re,hashlib=hashlib,time=time,_mobile_json=json,
               _mobile_rule_read=api.read_rule,_mobile_rule_json=api.serialize,
               _mobile_rule_revision=api.revision,_mobile_rule_payload=api.parse_payload,
               entry_payee=lambda db,title: get_payee(db,title),
               _MobileUUID=uuid.UUID,
               recurring_today=lambda:date(2026,11,26),date=date,
               on_or_after=recurring.on_or_after,validate_rule=recurring.validate_rule,
               post_one=recurring.post_one,
               _mobile_json_response=lambda body,status=200:dict(body,status=status),
               _mobile_denied=lambda status,message:dict(status=status,error=message),
               audit=lambda db,event,detail,actor_id=None:db.execute(
                   'INSERT INTO audit_events(actor_id,event,detail,client_ip) VALUES(?,?,?,?)',
                   (actor_id,event,detail,'test')))
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),
                 str(BASE/'src'/'app.py'),'exec'),scope)
    return scope


def get_payee(db,title):
    title=title.strip()
    if not title:return 0
    row=db.execute('SELECT id FROM payees WHERE title=? COLLATE NOCASE',(title,)).fetchone()
    if row:return row['id']
    return db.execute('INSERT INTO payees(title) VALUES(?)',(title,)).lastrowid


class MobileRecurringContract(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path=Path(temp.name)/'test.sqlite3'
        with self.connection() as db:
            db.executescript("""
                CREATE TABLE accounts(id INTEGER PRIMARY KEY,title TEXT,currency_id INTEGER);
                CREATE TABLE currencies(id INTEGER PRIMARY KEY,decimals INTEGER);
                CREATE TABLE account_snapshots(account_id INTEGER PRIMARY KEY,balance_minor INTEGER,is_active INTEGER);
                CREATE TABLE payees(id INTEGER PRIMARY KEY,title TEXT);
                CREATE TABLE categories(id INTEGER PRIMARY KEY,title TEXT);
                CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT);
                CREATE TABLE transactions(id INTEGER PRIMARY KEY,day TEXT,account_id INTEGER,
                    to_account_id INTEGER,category_id INTEGER,payee_id INTEGER,
                    amount INTEGER,note TEXT,is_template INTEGER,origin TEXT);
                CREATE TABLE audit_events(actor_id INTEGER,event TEXT,detail TEXT,client_ip TEXT);
                CREATE TABLE mobile_api_receipts(key_id INTEGER,request_id TEXT,operation TEXT,
                    fingerprint TEXT,response_json TEXT,created_on INTEGER,
                    UNIQUE(key_id,request_id));
                INSERT INTO accounts VALUES(1,'Konto',1),(2,'Ziel',1);
                INSERT INTO currencies VALUES(1,2);
                INSERT INTO account_snapshots VALUES(1,200000,1),(2,0,1);
                INSERT INTO categories VALUES(2,'Wohnen');
                INSERT INTO meta VALUES('finance_mode','web'),('ledger_web_writes','0');
            """)
            recurring.ensure_schema(db)
        self.scope=stub_app()
        self.request=SimpleNamespace(headers={},args={},get_json=lambda silent=False:self.payload)
        self.scope['request']=self.request
        self.role='admin'
        self.access='write'
        self.scope['_mobile_require']=lambda: (dict(key_id=5,user_id=3,role=self.role,access=self.access),None)
        self.scope['_mobile_recurring_writer']=lambda: self.writer()
        self.scope['get_db']=self.connection
        self.payload={}
        self.headers('create')

    def connection(self):
        db=sqlite3.connect(self.path)
        db.row_factory=sqlite3.Row
        return db

    def writer(self):
        if self.access!='write' or self.role not in ('admin','editor'):
            return None,dict(status=403,error='Forbidden')
        with self.connection() as db:
            if db.execute("SELECT value FROM meta WHERE key='finance_mode'").fetchone()[0]!='web':
                return None,dict(status=409,error='Not authoritative')
        return dict(key_id=5,user_id=3,role=self.role,access=self.access),None

    def headers(self,action,revision=None,rid=None):
        self.request.headers={'Idempotency-Key':rid or str(uuid.uuid4())}
        if revision is not None:self.request.headers['If-Match']=revision

    def draft(self,**overrides):
        item=dict(title='Miete',kind='expense',account_id=1,to_account_id=0,
                  category_id=2,payee_title='Vermieter',amount_minor=95000,note='',
                  frequency='monthly',interval_count=1,day_of_month=25,
                  start_on='2026-11-01',run_at='09:30',end_on=None,max_occurrences=12)
        item.update(overrides)
        return item

    def mutation(self,op,ident=None,body=None):
        self.payload={} if body is None else body
        return self.scope['_mobile_recurring_mutate'](op,ident)

    def create(self,**overrides):
        self.headers('create')
        out=self.mutation('create',body=self.draft(**overrides))
        self.assertEqual(out['status'],201,out)
        return out['rule']

    def test_create_read_positive_amount_revision_and_paused(self):
        item=self.create()
        self.assertEqual(item['mode'],'paused')
        self.assertEqual(item['amount_minor'],95000)
        self.assertRegex(item['revision'],r'^[0-9a-f]{32}$')
        with self.connection() as db:
            stored=db.execute('SELECT * FROM recurring_rules').fetchone()
            self.assertEqual(stored['amount_minor'],-95000)
        self.assertEqual(self.scope['mobile_api_recurring_list']()['items'][0]['id'],item['id'])

    def test_permissions_mode_and_expiration(self):
        item=self.create()
        self.access='read'
        self.headers('mode',item['revision'])
        self.assertEqual(self.mutation('mode',item['id'],{'mode':'manual'})['status'],403)
        self.access='write';self.role='editor'
        self.headers('mode',item['revision'])
        self.assertEqual(self.mutation('mode',item['id'],{'mode':'auto'})['status'],403)
        self.headers('mode',item['revision'])
        manual=self.mutation('mode',item['id'],{'mode':'manual'})
        self.assertEqual(manual['rule']['mode'],'manual')
        self.role='admin'
        self.headers('mode',manual['rule']['revision'])
        auto=self.mutation('mode',item['id'],{'mode':'auto'})
        self.assertEqual(auto['rule']['mode'],'auto')
        with self.connection() as db:db.execute("UPDATE meta SET value='import' WHERE key='finance_mode'")
        self.headers('mode',auto['rule']['revision'])
        self.assertEqual(self.mutation('mode',item['id'],{'mode':'paused'})['status'],409)

    def test_conflicts_edit_pauses_and_soft_delete(self):
        item=self.create()
        self.headers('update')
        self.assertEqual(self.mutation('update',item['id'],self.draft())['status'],428)
        self.headers('update','a'*32)
        self.assertEqual(self.mutation('update',item['id'],self.draft())['status'],409)
        self.headers('update',item['revision'])
        change=self.mutation('update',item['id'],self.draft(title='Neue Miete'))
        self.assertEqual(change['rule']['mode'],'paused')
        self.assertNotEqual(change['rule']['revision'],item['revision'])
        self.headers('delete',change['rule']['revision'])
        self.assertEqual(self.mutation('delete',item['id'],{'confirm_title':'Falsch'})['status'],400)
        self.headers('delete',change['rule']['revision'])
        self.assertTrue(self.mutation('delete',item['id'],{'confirm_title':'Neue Miete'})['archived'])
        self.assertEqual(self.scope['mobile_api_recurring_list']()['items'],[])

    def test_receipt_key_replay_and_body_conflict(self):
        key=str(uuid.uuid4())
        self.headers('create',rid=key)
        data=self.draft()
        first=self.mutation('create',body=data)
        self.headers('create',rid=key)
        second=self.mutation('create',body=data)
        self.assertEqual(first,second)
        with self.connection() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM recurring_rules').fetchone()[0],1)
        self.headers('create',rid=key)
        self.assertEqual(self.mutation('create',body=self.draft(title='Andere'))['status'],400)

    def test_manual_post_and_no_duplicates_on_new_key(self):
        item=self.create()
        self.headers('mode',item['revision'])
        active=self.mutation('mode',item['id'],{'mode':'manual'})['rule']
        self.headers('post',active['revision'])
        self.assertEqual(self.mutation('post',item['id'],{'confirm':'falsch'})['status'],400)
        self.headers('post',active['revision'])
        first=self.mutation('post',item['id'],{'confirm':'BUCHEN'})
        self.assertEqual(first['status'],200,first)
        self.assertGreater(first['booking_id'],0)
        with self.connection() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM recurring_runs').fetchone()[0],1)
            before=db.execute('SELECT balance_minor FROM account_snapshots WHERE account_id=1').fetchone()[0]
        self.headers('post',first['rule']['revision'])
        repeat=self.mutation('post',item['id'],{'confirm':'BUCHEN'})
        self.assertEqual(repeat['status'],409,repeat)
        with self.connection() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM recurring_runs').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT balance_minor FROM account_snapshots WHERE account_id=1').fetchone()[0],before)

    def test_invalid_drafts_and_limits(self):
        for changes in (dict(interval_count=121),dict(day_of_month=32),
                        dict(amount_minor=-1),dict(run_at='25:99'),
                        dict(end_on='2026-10-01'),dict(max_occurrences=10001)):
            self.headers('create')
            self.assertEqual(self.mutation('create',body=self.draft(**changes))['status'],400)
        expired=self.create(end_on='2026-11-05')
        self.headers('mode',expired['revision'])
        self.assertEqual(self.mutation('mode',expired['id'],{'mode':'manual'})['status'],409)

if __name__=='__main__':
    unittest.main()
