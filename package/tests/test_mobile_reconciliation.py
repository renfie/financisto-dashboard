# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2026 René Fieler (RenFie)
"""Web/Mobile reconciliation parity and transactional security (stdlib)."""
import ast
import hashlib
import json
import re
import sqlite3
import tempfile
import time
import unittest
import uuid
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

SOURCE=Path(__file__).resolve().parents[1]/'src'/'app.py'
FUNCTIONS={'reconcile_account_balance','settings_reconcile_account','mobile_api_reconcile_account',
           'existing_account','future_account_deltas','apply_balance_delta','insert_category',
           'mark_finance_edit','_mobile_body_and_request_id','_mobile_receipt','_mobile_save_receipt',
           'pass_through_category_ids','adjustment_category_ids','opening_amount','minor_amount'}


def api_functions():
    tree=ast.parse(SOURCE.read_text())
    nodes=[]
    for node in tree.body:
        if isinstance(node,ast.FunctionDef) and node.name in FUNCTIONS:
            node.decorator_list=[]
            nodes.append(node)
    assert {node.name for node in nodes} == FUNCTIONS
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='ReconciliationConflict')
    namespace=dict(sqlite3=sqlite3,re=re,hashlib=hashlib,time=time,_MobileUUID=uuid.UUID,
        _mobile_json=json,Decimal=Decimal,defaultdict=defaultdict,datetime=datetime,
        MONTH_TZ=ZoneInfo('Europe/Berlin'),
        ADJUSTMENT_CATEGORIES={
            ('reconciliation','income'):('Kontostandskorrektur (Zugang)',1),
            ('reconciliation','expense'):('Kontostandskorrektur (Abgang)',0),
            ('valuation','income'):('Depot-Wertanpassung (Zugang)',1),
            ('valuation','expense'):('Depot-Wertanpassung (Abgang)',0)},
        PASS_THROUGH_CATEGORIES={
            'expense':('Durchlaufender Posten (Ausgabe)',0),
            'income':('Durchlaufender Posten (Eingang)',1)})
    exec(compile(ast.fix_missing_locations(ast.Module(body=[cls]+nodes,type_ignores=[])),
                 str(SOURCE),'exec'),namespace)
    return namespace


class ReconcileMobileTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.file=Path(tmp.name)/'finance.sqlite3'
        with self.db() as db:
            db.executescript("""
                CREATE TABLE currencies(id INTEGER PRIMARY KEY,code TEXT,decimals INT);
                CREATE TABLE accounts(id INTEGER PRIMARY KEY,title TEXT,currency_id INT);
                CREATE TABLE account_snapshots(account_id INTEGER PRIMARY KEY,balance_minor INT,is_active INT,include_in_totals INT);
                CREATE TABLE categories(id INTEGER PRIMARY KEY,title TEXT,lft INT,rgt INT,kind INT);
                CREATE TABLE transactions(id INTEGER PRIMARY KEY,day TEXT,account_id INT,to_account_id INT,
                   category_id INT,payee_id INT,amount INT,note TEXT,is_template INT,origin TEXT);
                CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT);
                CREATE TABLE audit_events(actor_id INT,event TEXT,detail TEXT,client_ip TEXT);
                CREATE TABLE mobile_api_receipts(key_id INT,request_id TEXT,operation TEXT,
                   fingerprint TEXT,response_json TEXT,created_on INT,UNIQUE(key_id,request_id));
                INSERT INTO currencies VALUES(1,'EUR',2),(2,'JPY',0),(3,'KWD',3);
                INSERT INTO accounts VALUES(1,'Giro',1),(2,'Yen',2),(3,'KWD',3),(4,'Inaktiv',1);
                INSERT INTO account_snapshots VALUES(1,125000,1,1),(2,1234,1,1),(3,56789,1,1),(4,500,0,1);
                INSERT INTO meta VALUES('finance_mode','web'),('ledger_web_writes','0');
            """)
        from types import SimpleNamespace
        self.api=api_functions()
        self.access='write';self.role='admin';self.payload={}
        self.request=SimpleNamespace(headers={},form={},get_json=lambda silent=True:self.payload)
        self.api.update(
            request=self.request,get_db=self.db,
            finance_setting=lambda db,k,default='':(db.execute('SELECT value FROM meta WHERE key=?',(k,)).fetchone() or (default,))[0],
            _mobile_require=self.authorize,
            _mobile_denied=lambda status,message:dict(status=status,error=message),
            _mobile_json_response=lambda data,status=200:dict(data,status=status),
            audit=lambda db,event,detail,actor_id=None:db.execute('INSERT INTO audit_events VALUES(?,?,?,?)',(actor_id,event,detail,'test')),
            csrf_ok=lambda:True,url_for=lambda name:'/settings',
            redirect=lambda location:dict(redirect=location),
            flash=lambda message,kind:None,
            abort=lambda code:(_ for _ in ()).throw(ValueError('HTTP '+str(code))),
            current_user=lambda:dict(id=19)
        )

    def db(self):
        db=sqlite3.connect(self.file)
        db.row_factory=sqlite3.Row
        return db

    def authorize(self,write=False):
        if write and (self.access!='write' or self.role not in ('admin','editor')):
            return None,dict(status=401,error='Unauthorized')
        with self.db() as db:
            mode=db.execute("SELECT value FROM meta WHERE key='finance_mode'").fetchone()[0]
        if write and mode!='web':return None,dict(status=409,error='Web mode required')
        return dict(key_id=7,user_id=19,role=self.role,access=self.access),None

    def call(self,account_id=1,actual=127500,expected=125000,note='',key=None,body=None):
        self.payload=body if body is not None else {
            'actual_balance_minor':actual,'expected_balance_minor':expected,'note':note}
        self.request.headers={'Idempotency-Key':key or str(uuid.uuid4())}
        return self.api['mobile_api_reconcile_account'](account_id)

    def state(self):
        with self.db() as db:
            return (db.execute('SELECT COUNT(*) FROM transactions').fetchone()[0],
                    db.execute('SELECT balance_minor FROM account_snapshots WHERE account_id=1').fetchone()[0],
                    db.execute('SELECT COUNT(*) FROM mobile_api_receipts').fetchone()[0])

    def test_income_expense_and_special_categories(self):
        plus=self.call()
        self.assertEqual((plus['status'],plus['change_minor'],plus['balance_minor']), (200,2500,127500))
        minus=self.call(actual=122000,expected=127500)
        self.assertEqual(minus['change_minor'],-5500)
        with self.db() as db:
            rows=db.execute('SELECT t.amount,c.title,c.kind FROM transactions t JOIN categories c ON c.id=t.category_id ORDER BY t.id').fetchall()
            self.assertEqual([(r['amount'],r['title'],r['kind']) for r in rows],
                [(2500,'Kontostandskorrektur (Zugang)',1),(-5500,'Kontostandskorrektur (Abgang)',0)])
            self.assertEqual(len(self.api['pass_through_category_ids'](db)),2)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM audit_events WHERE event='account_reconciled'").fetchone()[0],2)

    def test_zero_change_and_replay(self):
        key=str(uuid.uuid4())
        first=self.call(actual=125000,key=key)
        self.assertEqual((first['unchanged'],first['change_minor'],first['booking_id']),(True,0,None))
        self.assertEqual(first,self.call(actual=125000,key=key))
        self.assertEqual(self.state(),(0,125000,1))
        self.assertEqual(self.call(actual=127500,key=key)['status'],409)
        other=str(uuid.uuid4())
        one=self.call(key=other)
        self.assertEqual(one,self.call(key=other))
        self.assertEqual(self.state(),(1,127500,2))

    def test_stale_balance_and_rollback(self):
        result=self.call(expected=124999)
        self.assertEqual(result['status'],409)
        self.assertIn('inzwischen verändert',result['error'])
        self.assertEqual(self.state(),(0,125000,0))
        self.api['apply_balance_delta']=lambda db,row,direction:(_ for _ in ()).throw(ValueError('Failure'))
        self.assertEqual(self.call()['status'],409)
        self.assertEqual(self.state(),(0,125000,0))
        with self.db() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM categories').fetchone()[0],0)

    def test_future_and_negative_amount(self):
        future=str(datetime.now(ZoneInfo('Europe/Berlin')).year+1)+'-12-01'
        with self.db() as db:
            db.execute("INSERT INTO transactions VALUES(1,?,1,0,0,0,-5000,'Future',0,'web')",(future,))
            db.execute('UPDATE account_snapshots SET balance_minor=120000 WHERE account_id=1')
        r=self.call(actual=-500)
        self.assertEqual((r['status'],r['change_minor'],r['balance_minor'],r['projected_balance_minor']),
                         (200,-125500,-500,-5500))

    def test_currency_decimals_and_authorization(self):
        yen=self.call(account_id=2,actual=-80,expected=1234)
        self.assertEqual((yen['currency'],yen['decimals'],yen['change_minor']),('JPY',0,-1314))
        kwd=self.call(account_id=3,actual=57000,expected=56789)
        self.assertEqual((kwd['currency'],kwd['decimals'],kwd['change_minor']),('KWD',3,211))
        self.access='read';self.assertEqual(self.call()['status'],401)
        self.access='write';self.role='viewer';self.assertEqual(self.call()['status'],401)
        self.role='editor';self.assertEqual(self.call()['status'],200)
        with self.db() as db:db.execute("UPDATE meta SET value='import' WHERE key='finance_mode'")
        self.assertEqual(self.call(actual=130000,expected=127500)['status'],409)

    def test_invalid_inputs(self):
        for body in (
            {'actual_balance_minor':'100','expected_balance_minor':125000,'note':''},
            {'actual_balance_minor':True,'expected_balance_minor':125000,'note':''},
            {'actual_balance_minor':1,'expected_balance_minor':125000,'note':'x'*501},
            {'actual_balance_minor':0,'expected_balance_minor':125000,'note':None},
            {'actual_balance_minor':0,'expected_balance_minor':125000},
            {'actual_balance_minor':0,'expected_balance_minor':125000,'note':'','change_minor':8},
        ):
            self.assertEqual(self.call(body=body)['status'],400)
        self.assertEqual(self.call(account_id=999)['status'],404)
        self.assertEqual(self.call(account_id=4,actual=10,expected=500)['status'],409)
        self.assertEqual(self.call(key='not-a-uuid')['status'],400)

    def test_web_mobile_same_booking_and_snapshot(self):
        self.request.form={'return_to':'settings','account_id':'1','actual_balance':'1275,00','note':'Abgleich'}
        result=self.api['settings_reconcile_account']()
        self.assertEqual(result['redirect'],'/settings#kontostand-abgleichen')
        with self.db() as db:
            old=tuple(db.execute('SELECT day,amount,note,category_id,origin FROM transactions').fetchone())
            snapshot=db.execute('SELECT balance_minor FROM account_snapshots WHERE account_id=1').fetchone()[0]
            db.execute('DELETE FROM transactions')
            db.execute('DELETE FROM categories')
            db.execute('UPDATE account_snapshots SET balance_minor=125000 WHERE account_id=1')
        result=self.call(actual=127500,expected=125000,note='Abgleich')
        self.assertEqual(result['status'],200)
        with self.db() as db:
            new=tuple(db.execute('SELECT day,amount,note,category_id,origin FROM transactions').fetchone())
            self.assertEqual(new,old)
            self.assertEqual(db.execute('SELECT balance_minor FROM account_snapshots WHERE account_id=1').fetchone()[0],snapshot)

    def test_additive_capabilities_and_no_new_schema(self):
        source=SOURCE.read_text()
        for feature in ('account_reconciliation','monthly_reports','history_highlights','recurring_rules'):
            self.assertIn("'"+feature+"':True",source)
        self.assertIn("reconcile_account_balance(db,account_id,actual,note,",source)
        self.assertIn("result = reconcile_account_balance(db, int(account_id), actual, note)",source)


if __name__=='__main__':unittest.main()
