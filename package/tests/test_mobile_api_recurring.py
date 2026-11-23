"""Regression tests for the Mobile API recurrence flags (stdlib only).

The production endpoint code is evaluated from app.py with a read-only SQLite
fixture. This tests actual SQL/JSON/pagination without needing Flask in CI.
"""
import ast
import hashlib
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace

SOURCE=Path(__file__).resolve().parents[1]/'src'/'app.py'
FUNCTIONS={'_mobile_book_hash','_mobile_booking','_mobile_book_query','mobile_api_bookings'}

def load_api():
    tree=ast.parse(SOURCE.read_text(encoding='utf-8'))
    nodes=[]
    for node in tree.body:
        if isinstance(node,ast.FunctionDef) and node.name in FUNCTIONS:
            node.decorator_list=[]
            nodes.append(node)
    assert {node.name for node in nodes}==FUNCTIONS
    scope={'hashlib':hashlib,'_mobile_json':json}
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),str(SOURCE),'exec'),scope)
    return scope

class RecurringMobileAPI(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path=Path(tmp.name)/'finance.sqlite3'
        with closing(sqlite3.connect(path)) as db:
            db.executescript("""
            CREATE TABLE transactions(id INTEGER PRIMARY KEY,day TEXT,account_id INT,
              to_account_id INT,category_id INT,payee_id INT,amount INT,note TEXT,
              origin TEXT,is_template INT);
            CREATE TABLE accounts(id INTEGER,title TEXT,currency_id INT);
            CREATE TABLE currencies(id INTEGER,code TEXT,decimals INT);
            CREATE TABLE payees(id INTEGER,title TEXT);
            CREATE TABLE recurring_runs(rule_id INT,due_on TEXT,booking_id INT);
            CREATE TABLE audit_events(event TEXT,detail TEXT);
            INSERT INTO accounts VALUES(1,'Giro',1),(2,'Sparen',1);
            INSERT INTO currencies VALUES(1,'EUR',2);
            INSERT INTO payees VALUES(1,'Empfänger');
            INSERT INTO transactions VALUES
              (1,'2026-11-01',1,0,1,1,-100,'Ausgabe','web',0),
              (2,'2026-11-02',1,0,1,1,200,'Einnahme','web',0),
              (3,'2026-11-03',1,2,0,0,-300,'Umbuchung','web',0),
              (4,'2026-11-04',1,0,1,1,-400,'Automatisch','web',0),
              (5,'2026-11-05',1,0,1,1,-500,'Manuell','web',0),
              (6,'2026-11-06',1,0,1,1,-600,'Zugeordnet','web',0),
              (7,'2026-11-07',1,0,1,1,-700,'Normal','web',0),
              (8,'2026-11-08',1,2,0,0,-800,'Zugeordnet Umbuchung','web',0),
              (9,'2026-11-09',1,0,1,1,-900,'Beides','web',0);
            INSERT INTO recurring_runs VALUES
              (40,'2026-11-04',4),(50,'2026-11-05',5),
              (60,'2026-11-06',6),(80,'2026-11-08',8),
              (90,'2026-11-09',9),(91,'2026-11-09',9);
            INSERT INTO audit_events VALUES
              ('recurring_posted_auto','40:2026-11-04:4'),
              ('recurring_posted_manual','50:2026-11-05:5'),
              ('recurring_posted_auto','91:2026-11-09:9'),
              ('recurring_posted_auto','600:2026-11-06:6');
            """)
        def get_db():
            db=sqlite3.connect('file:'+str(path)+'?mode=ro',uri=True)
            db.row_factory=sqlite3.Row
            return closing(db)
        self.api=load_api()
        self.api.update(get_db=get_db,request=SimpleNamespace(args={}),
                        _mobile_require=lambda: ({'access':'read'},None),
                        _mobile_json_response=lambda value:value,
                        _mobile_denied=lambda status,message:{'status':status,'error':message})

    def page(self,limit=2,before=0):
        self.api['request'].args={'limit':str(limit),'before':str(before)}
        return self.api['mobile_api_bookings']()

    def all_items(self):
        items={}; before=0
        while True:
            response=self.page(before=before)
            for item in response['items']:
                self.assertIs(type(item['is_recurring']),bool)
                self.assertIs(type(item['is_rule_matched']),bool)
                items[item['id']]=item
            before=response['next_before']
            if before is None:
                break
        return items

    def test_requested_cases_and_pagination(self):
        items=self.all_items()
        self.assertEqual(set(items),set(range(1,10)))
        for ident in (1,2,3,7):
            self.assertEqual((items[ident]['is_recurring'],items[ident]['is_rule_matched']),
                             (False,False))
        for ident in (4,5):
            self.assertEqual((items[ident]['is_recurring'],items[ident]['is_rule_matched']),
                             (True,False))
        for ident in (6,8):
            self.assertEqual((items[ident]['is_recurring'],items[ident]['is_rule_matched']),
                             (False,True))
        # Multiple rule links must not mark a posted entry as merely matched.
        self.assertEqual((items[9]['is_recurring'],items[9]['is_rule_matched']),(True,False))
        self.assertEqual(items[3]['kind'],'transfer')
        self.assertEqual(len(items[4]['revision']),32)
        self.assertTrue({'date','account_id','amount_minor','payee','revision',
                         'currency_code','kind'}.issubset(items[2]))
        first=self.page(limit=2)
        self.assertEqual([r['id'] for r in first['items']],[9,8])
        self.assertEqual([r['id'] for r in self.page(limit=2,before=first['next_before'])['items']],[7,6])

    def test_read_authorization_path_unchanged(self):
        self.api['_mobile_require']=lambda: (None,{'error':'Forbidden'})
        self.assertEqual(self.page(),{'error':'Forbidden'})

if __name__=='__main__':
    unittest.main()
