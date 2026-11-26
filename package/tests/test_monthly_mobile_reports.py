# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2026 René Fieler (RenFie)
"""End-to-end SQLite monthly summary and API parameter/security regression tests."""
import ast
import calendar
import datetime
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace

BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE/'src'))
from monthly_reports import months_between, summarize_months, attach_categories


class MonthlyReportsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'finance.sqlite3'
        with self.db() as db:
            db.executescript('''
              CREATE TABLE currencies(id INTEGER PRIMARY KEY,code TEXT,decimals INTEGER);
              CREATE TABLE accounts(id INTEGER PRIMARY KEY,title TEXT,currency_id INTEGER);
              CREATE TABLE categories(id INTEGER PRIMARY KEY,title TEXT,lft INTEGER,rgt INTEGER);
              CREATE TABLE payees(id INTEGER PRIMARY KEY,title TEXT);
              CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT);
              CREATE TABLE transactions(id INTEGER PRIMARY KEY, day TEXT, account_id INTEGER,
                   to_account_id INTEGER, category_id INTEGER, payee_id INTEGER,
                   amount INTEGER, note TEXT,is_template INTEGER DEFAULT 0);
              CREATE INDEX tx_day_idx ON transactions(day);
              INSERT INTO currencies VALUES(1,'EUR',2),(2,'USD',2);
              INSERT INTO accounts VALUES(1,'Giro',1),(2,'Sparen',1),(3,'Dollar',2);
              INSERT INTO categories VALUES
                 (10,'Einkauf',1,6),(11,'Lebensmittel',2,3),(12,'Haus',4,5),
                 (20,'Gehalt',7,8),(30,'Durchlaufender Posten (Ausgang)',9,10),
                 (40,'Kontostandskorrektur (Abgang)',11,12);
              INSERT INTO payees VALUES(1,'Markt'),(2,'Arbeitgeber');
              INSERT INTO meta VALUES('default_currency_code','EUR');
              INSERT INTO transactions(id,day,account_id,to_account_id,category_id,payee_id,amount,note,is_template) VALUES
                (1,'2026-09-03',1,0,11,1,-5000,'Essen',0),
                (2,'2026-09-04',1,0,12,1,-2000,'Haus',0),
                (3,'2026-09-10',1,0,20,2,90000,'Lohn',0),
                (4,'2026-09-11',1,2,0,0,-15000,'Sparen',0),
                (5,'2026-09-12',1,0,30,0,-1800,'Durchlaufend',0),
                (6,'2026-09-13',1,0,40,0,-900,'Saldoabgleich',0),
                (7,'2026-10-03',1,0,11,1,-8000,'Essen',0),
                (8,'2026-10-04',3,0,11,1,-12345,'Dollar',0),
                (9,'2026-11-05',2,1,0,0,-700,'Transfer',0),
                (10,'2026-11-26',1,0,20,2,60000,'Heute',0),
                (11,'2026-11-27',1,0,11,1,-7777,'Zukunft',0),
                (12,'2026-09-20',1,0,11,1,-99999,'Vorlage',1),
                (13,'2026-11-12',2,0,11,1,-400,'Sparkonto',0);
            ''')
        self.cats=self.get_categories()
        self.names={10:'Einkauf',11:'Einkauf / Lebensmittel',12:'Einkauf / Haus',20:'Gehalt',30:'Durchlaufender Posten (Ausgang)',40:'Kontostandskorrektur (Abgang)'}

    def db(self):
        conn=sqlite3.connect(self.path)
        conn.row_factory=sqlite3.Row
        return closing(conn)

    def get_categories(self):
        with self.db() as db:
            return db.execute('SELECT * FROM categories ORDER BY lft').fetchall()

    def calculate(self,**kwargs):
        with self.db() as db:
            values,forecast,cat=summarize_months(db,first='2026-01',last='2026-12',currency_id=1,
                today='2026-11-26',neutral_ids={30,40},categories=self.cats,**kwargs)
            return attach_categories(values,cat,self.names),forecast

    def test_twelve_months_zero_months_history_and_actual_only(self):
        values,forecast=self.calculate()
        self.assertEqual(len(values),12)
        self.assertEqual((values['2026-08']['income_minor'],values['2026-08']['expense_minor'],values['2026-08']['booking_count']),(0,0,0))
        sept=values['2026-09']
        self.assertEqual((sept['income_minor'],sept['expense_minor'],sept['balance_minor'],sept['booking_count']),(90000,7000,83000,3))
        self.assertEqual((sept['transfer_count'],sept['transfer_minor']),(1,15000))
        self.assertEqual(values['2026-10']['expense_minor'],8000)
        self.assertEqual(values['2026-09']['categories']['income'][0]['category'], 'Gehalt')
        self.assertEqual(values['2026-09']['categories']['income'][0]['amount_minor'], 90000)
        self.assertEqual(values['2026-11']['expense_minor'],400)
        self.assertEqual(values['2026-11']['income_minor'],60000)
        self.assertEqual(forecast['2026-11']['expenses'],8177)
        self.assertEqual(values['2026-11']['transfer_minor'],700)
        self.assertEqual(values['2026-12']['income_minor'],0)

    def test_category_and_descendants_with_full_paths(self):
        result,_=self.calculate(category_id=10)
        september=result['2026-09']
        self.assertEqual(september['expense_minor'],7000)
        self.assertEqual([x['category'] for x in september['categories']['expense']],['Einkauf / Haus','Einkauf / Lebensmittel'])
        self.assertEqual(result['2026-10']['expense_minor'],8000)
        self.assertEqual(result['2026-11']['income_minor'],0)
        self.assertEqual(result['2026-09']['transfer_count'],0)
        single,_=self.calculate(category_id=11)
        self.assertEqual(single['2026-09']['expense_minor'],5000)

    def test_account_and_currency_no_double_count(self):
        account,_=self.calculate(account_id=2)
        self.assertEqual(account['2026-09']['transfer_count'],1)  # destination included
        self.assertEqual(account['2026-09']['income_minor'],0)
        self.assertEqual(account['2026-11']['expense_minor'],400)
        with self.db() as db:
            usd,_,_=summarize_months(db,first='2026-09',last='2026-11',currency_id=2,
                today='2026-11-26',neutral_ids={30,40},categories=self.cats)
        self.assertEqual(usd['2026-10']['expense_minor'],12345)
        self.assertEqual(usd['2026-09']['income_minor'],0)

    def test_sql_is_read_only(self):
        with self.db() as db:
            db.execute('PRAGMA query_only=ON')
            data,_,_=summarize_months(db,first='2026-09',last='2026-11',currency_id=1,
                today='2026-11-26',neutral_ids={30,40},categories=self.cats)
            self.assertEqual(data['2026-09']['balance_minor'],83000)

    def test_reference_dashboards_use_same_shared_calculation(self):
        text=(BASE/'src'/'app.py').read_text(encoding='utf-8')
        tree=ast.parse(text)
        for name in ('dashboard','historical_analysis','monthly_report_context','mobile_api_monthly_reports'):
            method=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
            self.assertTrue(any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name)
                                and n.func.id=='summarize_months' for n in ast.walk(method)),name)
        self.assertIn("'monthly_reports':True", text)
        # The categorised expense breakdown is the exact source for the
        # dashboard comparison chart; it has no second monetary aggregation.
        values,_=self.calculate()
        self.assertEqual(sum(r['amount_minor'] for r in values['2026-09']['categories']['expense']),values['2026-09']['expense_minor'])

    def test_api_auth_filters_and_json(self):
        source=ast.parse((BASE/'src'/'app.py').read_text(encoding='utf-8'))
        node=next(n for n in source.body if isinstance(n,ast.FunctionDef) and n.name=='mobile_api_monthly_reports')
        node.decorator_list=[]
        import re
        class FakeDateTime:
            @classmethod
            def now(cls,tz):return datetime.datetime(2026,11,26,12,0)
        class Query(dict):pass
        scope={'_mobile_require':lambda:(dict(access='read'),None),
               '_mobile_denied':lambda status,message:dict(status=status,error=message),
               '_mobile_json_response':lambda body:body,
               'request':SimpleNamespace(args=Query()),
               'datetime':FakeDateTime,'MONTH_TZ':None,'re':re,'sqlite3':sqlite3,
               'get_db':self.db,'finance_setting':lambda db,key,default:db.execute('SELECT value FROM meta WHERE key=?',(key,)).fetchone()[0],
               'category_tree':lambda db:(self.cats,self.names,{}),
               'pass_through_category_ids':lambda db:{30,40},
               'summarize_months':summarize_months,'attach_categories':attach_categories}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),'app.py','exec'),scope)
        run=scope['mobile_api_monthly_reports']
        scope['request'].args=Query({'from':'2026-09','to':'2026-11','currency':'EUR'})
        response=run()
        self.assertEqual(len(response['months']),3)
        self.assertTrue(response['complete'])
        scope['request'].args=Query()
        default=run()
        self.assertEqual((default['from'],default['to'],len(default['months'])),('2025-12','2026-11',12))
        scope['request'].args=Query({'from':'2024-01','to':'2026-12','currency':'EUR'})
        self.assertEqual(len(run()['months']),36)
        scope['request'].args=Query({'from':'2026-09','to':'2026-11','currency':'EUR'})
        self.assertEqual(response['months'][0]['income_minor'],90000)
        self.assertEqual(response['months'][2]['expense_minor'],400)
        self.assertNotIn('projected',response['months'][2])
        for args in ({'from':'2023-01','to':'2026-12','currency':'EUR'},
                     {'from':'2026-13','to':'2026-11','currency':'EUR'},
                     {'from':'2026-11','to':'2026-10','currency':'EUR'},
                     {'currency':'EUR','account_id':'999'},
                     {'currency':'EUR','category_id':'999'},
                     {'currency':'EUR','account_id':'3'},
                     {'currency':'EUR','account_id':'invalid'},
                     {'currency':'EUR','injection':'1'},
                     {'currency':'EUR','category_id':'11 OR 1=1'}):
            scope['request'].args=Query(args)
            self.assertEqual(run()['status'],400,args)
        scope['_mobile_require']=lambda:(None,dict(status=401,error='Unauthorized'))
        self.assertEqual(run()['status'],401)

    def test_large_ledger_and_query_plan_index(self):
        with self.db() as db:
            db.executemany('INSERT INTO transactions(day,account_id,to_account_id,category_id,payee_id,amount,note,is_template) VALUES(?,?,?,?,?,?,?,0)',
                [('2026-10-02',1,0,11,1,-1,'Bulk')]*30000)
            db.commit()
            query_plan=db.execute("EXPLAIN QUERY PLAN SELECT * FROM transactions WHERE day>='2026-10-01' AND day<'2026-11-01'").fetchall()
            self.assertIn('tx_day_idx',str([tuple(r) for r in query_plan]))
        res,_=self.calculate()
        self.assertEqual(res['2026-10']['expense_minor'],38000)
        self.assertEqual(res['2026-10']['booking_count'],30001)

if __name__=='__main__':unittest.main()
