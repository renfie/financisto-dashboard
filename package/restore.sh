#!/usr/bin/env bash
# Offline-Wiederherstellung einer SQLite-Sicherung. Benötigt den Projektbenutzer, kein sudo.
set -Eeuo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
[[ $EUID -ne 0 ]] || { echo 'Bitte als normaler Projektbenutzer ausführen.' >&2; exit 1; }
[[ $# -eq 1 ]] || { echo 'Aufruf: ./restore.sh /pfad/zur/sicherung.sqlite3' >&2; exit 2; }
SOURCE="$(realpath -e -- "$1")"
[[ "$SOURCE" != "$(realpath -e data/finanzen.sqlite3)" ]] || { echo 'Quelldatei ist die aktive Datenbank!' >&2; exit 1; }
[[ -f "$SOURCE" && ! -L "$1" && -r "$SOURCE" ]] || { echo 'Sicherung nicht lesbar.' >&2; exit 1; }
export RESTORE_SOURCE="$SOURCE"
python3 - <<'PYVALID'
import os,sqlite3
p=os.environ['RESTORE_SOURCE']
with sqlite3.connect(f'file:{p}?mode=ro',uri=True) as db:
    if db.execute('PRAGMA quick_check').fetchone()[0]!='ok':
        raise SystemExit('Sicherung ist beschädigt.')
    for table in ('users','transactions','accounts','meta'):
        if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone():
            raise SystemExit('Pflichttabelle fehlt: '+table)
    print('Sicherung geprüft: '+str(db.execute('SELECT count(*) FROM transactions').fetchone()[0])+' Buchungen')
PYVALID
[[ -r secrets/app_secret ]] || { echo 'Wichtiges Secret fehlt: secrets/app_secret' >&2; exit 1; }
echo 'ACHTUNG: Diese Aktion ersetzt alle Finanzdaten, Benutzer und 2FA-Einstellungen durch den Sicherungsstand.'
echo 'Bestehende Secrets (insbesondere app_secret) müssen zur Sicherung passen, sonst funktionieren TOTP-Seeds nicht.'
read -r -p 'Zum Fortfahren WIEDERHERSTELLEN eingeben: ' ANSWER
[[ "$ANSWER" == WIEDERHERSTELLEN ]] || { echo 'Abgebrochen.'; exit 1; }
# Stop all DB writers. Caddy stays running but shows a short-lived 502 until startup.
docker compose stop dashboard background
start_again() { docker compose up -d dashboard background; }
trap start_again EXIT
mkdir -p backups
export RESTORE_DB="$(pwd)/data/finanzen.sqlite3"
export RESTORE_SAFE="$(pwd)/backups/vor-restore-$(date +%Y%m%d-%H%M%S)-$$.sqlite3"
python3 - <<'PYREST'
import os,sqlite3,tempfile,pathlib,stat
src=pathlib.Path(os.environ['RESTORE_SOURCE'])
db_path=pathlib.Path(os.environ['RESTORE_DB'])
safe=pathlib.Path(os.environ['RESTORE_SAFE'])
with sqlite3.connect(db_path) as live, sqlite3.connect(safe) as dst:
    live.backup(dst)
safe.chmod(0o600)
fd,temp=tempfile.mkstemp(prefix='.financisto-restore-',suffix='.sqlite3',dir=db_path.parent)
os.fchmod(fd,0o600);os.close(fd)
temp=pathlib.Path(temp)
try:
    with sqlite3.connect(f'file:{src}?mode=ro',uri=True) as incoming, sqlite3.connect(temp) as target:
        incoming.backup(target)
        assert target.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    # Live containers are stopped; any WAL must be checkpointed before replacement.
    with sqlite3.connect(db_path) as old:
        old.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        if old.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
            raise RuntimeError('Aktuelle Datenbank beschädigt, Abbruch')
    with temp.open('rb') as handle: os.fsync(handle.fileno())
    os.replace(temp,db_path)
    for ext in ('-wal','-shm'):
        side=pathlib.Path(str(db_path)+ext)
        if side.exists() and not side.is_symlink(): side.unlink()
    print('Datenbank wiederhergestellt. Sicherheitskopie des vorherigen Standes:',safe)
finally:
    temp.unlink(missing_ok=True)
PYREST
# EXIT trap restarts the web app and its sole combined background writer.
echo 'Wiederherstellung abgeschlossen; Docker-Dienste werden gestartet.'
