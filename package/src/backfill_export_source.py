"""Retain SHA256-matched original backup in SQLite for future round-trip export.

Never imports or changes bookings. A missing source just disables experimental export.
"""
from __future__ import annotations
import hashlib,os,sqlite3
from pathlib import Path
from financisto_export import ensure_source_table,store_matching_source

BASE=Path(os.environ.get('FINANCISTO_PROJECT_DIR',Path(__file__).resolve().parent))
DB=BASE/'data/finanzen.sqlite3'

def run():
    with sqlite3.connect(DB) as db:
        ensure_source_table(db)
        row=db.execute("SELECT value FROM meta WHERE key='last_import_sha256'").fetchone()
        if not row or not row[0]:
            print('Exportgrundlage: noch kein ursprünglicher Import; nichts verändert.')
            return False
        digest=row[0]
        ready=db.execute('SELECT 1 FROM financisto_export_source WHERE sha256=?',(digest,)).fetchone()
        if ready:
            print('Exportgrundlage: bereits in SQLite enthalten.')
            return True
        for directory in (BASE/'data/import-archive',BASE/'data/inbox'):
            if not directory.is_dir(): continue
            for path in directory.glob('*.backup'):
                if path.is_symlink() or not path.is_file(): continue
                if path.stat().st_size>30*1024*1024: continue
                raw=path.read_bytes()
                if hashlib.sha256(raw).hexdigest()!=digest: continue
                store_matching_source(db,raw,sha256=digest)
                print('Exportgrundlage: zuletzt importierte Original-Sicherung in SQLite übernommen.')
                return True
        print('Hinweis: Passende Original-Sicherung fehlt; Export noch gesperrt. Manueller Nachtrag möglich.')
        return False

if __name__=='__main__': run()
