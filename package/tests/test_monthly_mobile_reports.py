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
from monthly_reports import months_between, summarize_months, attach_categories, largest_bookings, serialize_highlights


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
        self.assertIn("'history_highlights':True", text)
        web=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='historical_analysis')
        self.assertTrue(any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name)
                            and n.func.id=='largest_bookings' for n in ast.walk(web)))
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
               'summarize_months':summarize_months,'attach_categories':attach_categories,
               'largest_bookings':largest_bookings,'serialize_highlights':serialize_highlights}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),'app.py','exec'),scope)
        run=scope['mobile_api_monthly_reports']
        scope['request'].args=Query({'from':'2026-09','to':'2026-11','currency':'EUR'})
        response=run()
        self.assertEqual(len(response['months']),3)
        self.assertTrue(response['complete'])
        self.assertEqual(response['highlights']['largest_expense'],dict(
            date='2026-10-03',amount_minor=8000,payee='Markt',category='Einkauf / Lebensmittel'))
        self.assertEqual(response['highlights']['largest_income']['amount_minor'],90000)
        scope['request'].args=Query()
        default=run()
        self.assertEqual((default['from'],default['to'],len(default['months'])),('2025-12','2026-11',12))
        scope['request'].args=Query({'from':'2024-01','to':'2026-12','currency':'EUR'})
        self.assertEqual(len(run()['months']),36)
        scope['request'].args=Query({'from':'2026-09','to':'2026-11','currency':'EUR'})
        self.assertEqual(response['months'][0]['income_minor'],90000)
        self.assertEqual(response['months'][2]['expense_minor'],400)
        self.assertNotIn('projected',response['months'][2])
        scope['request'].args=Query({'from':'2026-09','to':'2026-11','currency':'EUR','q':'Essen'})
        searched=run()
        self.assertEqual(searched['highlights']['largest_expense']['amount_minor'],8000)
        self.assertIsNone(searched['highlights']['largest_income'])
        self.assertEqual(searched['months'][0]['expense_minor'],5000)
        scope['request'].args=Query({'from':'2026-09','to':'2026-11','currency':'EUR','category_id':'12'})
        scoped=run()
        self.assertEqual(scoped['highlights']['largest_expense']['amount_minor'],2000)
        scope['request'].args=Query({'from':'2026-09','to':'2026-11','currency':'USD'})
        dollar=run()
        self.assertEqual(dollar['highlights']['largest_expense']['amount_minor'],12345)
        self.assertIsNone(dollar['highlights']['largest_income'])
        for args in ({'from':'2023-01','to':'2026-12','currency':'EUR'},
                     {'from':'2026-13','to':'2026-11','currency':'EUR'},
                     {'from':'2026-11','to':'2026-10','currency':'EUR'},
                     {'currency':'EUR','account_id':'999'},
                     {'currency':'EUR','category_id':'999'},
                     {'currency':'EUR','account_id':'3'},
                     {'currency':'EUR','account_id':'invalid'},
                     {'currency':'EUR','injection':'1'},
                     {'currency':'EUR','q':'a'*101},
                     {'currency':'EUR','q':'bad\nquery'},
                     {'currency':'EUR','category_id':'11 OR 1=1'}):
            scope['request'].args=Query(args)
            self.assertEqual(run()['status'],400,args)
        scope['_mobile_require']=lambda:(None,dict(status=401,error='Unauthorized'))
        self.assertEqual(run()['status'],401)

    def highlights(self,first='2026-09',last='2026-11',currency_id=1,**kwargs):
        with self.db() as db:
            raw=largest_bookings(db,first=first,last=last,currency_id=currency_id,
                today='2026-11-26',neutral_ids={30,40},categories=self.cats,**kwargs)
            return serialize_highlights(raw,self.names)

    def test_largest_income_expense_and_historical_web_parity(self):
        result=self.highlights()
        self.assertEqual(result['largest_income'],{
            'date':'2026-09-10','amount_minor':90000,'payee':'Arbeitgeber','category':'Gehalt'})
        self.assertEqual(result['largest_expense'],{
            'date':'2026-10-03','amount_minor':8000,'payee':'Markt',
            'category':'Einkauf / Lebensmittel'})
        # Same selection as the old web history scan with the historical filters.
        with self.db() as db:
            rows=db.execute("""SELECT t.day,t.amount,t.category_id,p.title payee_title
               FROM transactions t JOIN accounts a ON a.id=t.account_id
               LEFT JOIN payees p ON p.id=t.payee_id
               WHERE t.day>='2026-09-01' AND t.day<'2026-12-01'
                 AND a.currency_id=1 AND t.is_template=0 AND t.to_account_id=0
                 AND t.day<='2026-11-26' ORDER BY t.id""").fetchall()
        candidates=[r for r in rows if r['category_id'] not in {30,40}]
        expense=min((r for r in candidates if r['amount']<0),key=lambda r:r['amount'])
        income=max((r for r in candidates if r['amount']>0),key=lambda r:r['amount'])
        self.assertEqual((result['largest_expense']['date'],result['largest_expense']['amount_minor']),
                         (expense['day'],-expense['amount']))
        self.assertEqual((result['largest_income']['date'],result['largest_income']['amount_minor']),
                         (income['day'],income['amount']))

    def test_highlight_filters_months_category_descendants_account_currency(self):
        self.assertEqual(self.highlights(first='2026-10',last='2026-10')['largest_income'],None)
        self.assertEqual(self.highlights(first='2026-10',last='2026-10')['largest_expense']['amount_minor'],8000)
        scoped=self.highlights(category_id=10)
        self.assertIsNone(scoped['largest_income'])
        self.assertEqual(scoped['largest_expense']['amount_minor'],8000)
        self.assertEqual(self.highlights(category_id=12)['largest_expense']['amount_minor'],2000)
        self.assertEqual(self.highlights(account_id=2)['largest_expense']['amount_minor'],400)
        self.assertIsNone(self.highlights(account_id=2)['largest_income'])
        self.assertEqual(self.highlights(currency_id=2)['largest_expense']['amount_minor'],12345)
        self.assertIsNone(self.highlights(currency_id=2)['largest_income'])

    def test_highlight_exclusions_future_nulls_and_search(self):
        self.assertEqual(self.highlights(first='2026-08',last='2026-08'),{
            'largest_expense':None,'largest_income':None})
        self.assertEqual(self.highlights(category_id=30)['largest_expense'],None)
        self.assertEqual(self.highlights(category_id=40)['largest_expense'],None)
        # The future -7777 entry must not overtake today's -400 entry in November.
        self.assertEqual(self.highlights(first='2026-11',last='2026-11')['largest_expense']['amount_minor'],400)
        self.assertEqual(self.highlights(search='Essen')['largest_expense']['amount_minor'],8000)
        self.assertIsNone(self.highlights(search='Essen')['largest_income'])
        self.assertEqual(self.highlights(search='Arbeitgeber')['largest_income']['amount_minor'],90000)
        self.assertEqual(self.highlights(search='nicht vorhanden'),{
            'largest_expense':None,'largest_income':None})
        with self.db() as db:
            db.execute('PRAGMA query_only=ON')
            largest_bookings(db,first='2026-09',last='2026-11',currency_id=1,
                today='2026-11-26',neutral_ids={30,40},categories=self.cats)
            with self.assertRaises(sqlite3.OperationalError):
                db.execute("INSERT INTO payees VALUES (55,'Write disabled')")

    def test_highlight_tie_is_deterministic(self):
        with self.db() as db:
            db.execute("""INSERT INTO transactions
                (day,account_id,to_account_id,category_id,payee_id,amount,note,is_template)
                VALUES ('2026-10-09',1,0,11,1,-8000,'Gleicher Betrag',0)""")
        self.assertEqual(self.highlights(first='2026-10',last='2026-10')['largest_expense']['date'],
                         '2026-10-03')

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
