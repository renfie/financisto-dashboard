#!/usr/bin/env bash
# Financisto Dashboard update script: supports direct upgrades to the packaged VERSION.
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
# Works from the extracted release (no arguments) or, for later releases,
# from the installed project: ./update.sh /path/to/new/extracted-release
if [[ -d "$SCRIPT_DIR/package" ]]; then
  RELEASE_DIR="$SCRIPT_DIR"
  TARGET="${1:-$(dirname "$SCRIPT_DIR")/financisto-dashboard}"
else
  [[ $# -eq 1 && -d "$1/package" ]] || {
    echo 'Aufruf: bash /pfad/zum-entpackten-release/update.sh' >&2
    echo '  oder: bash /pfad/zum/financisto-dashboard/update.sh /pfad/zum-entpackten-release' >&2
    exit 2
  }
  RELEASE_DIR="$(cd -- "$1" && pwd -P)"
  TARGET="$SCRIPT_DIR"
fi
SOURCE="$RELEASE_DIR/package"
RELEASE_VERSION="$(tr -d '[:space:]' < "$SOURCE/VERSION")"
[[ "$RELEASE_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo 'Ungültige Releaseversion.' >&2; exit 1; }

error() { printf '\nFEHLER: %s\n' "$*" >&2; exit 1; }
[[ $EUID -ne 0 ]] || error 'Update bitte als Projektbenutzer ohne sudo ausführen; als Root ist ein versehentlicher Besitzwechsel möglich.'
for cmd in python3 docker id cp chmod tar stat; do command -v "$cmd" >/dev/null || error "Programm fehlt: $cmd"; done
[[ -d "$SOURCE" && -f "$SOURCE/src/app.py" && -f "$SOURCE/compose.yaml" && -f "$SOURCE/Caddyfile" ]] || error 'Vollständiges Release-Paket fehlt.'
[[ -d "$TARGET" && -f "$TARGET/compose.yaml" && -f "$TARGET/.env" ]] || error "Keine bestehende Installation unter: $TARGET"
[[ ! -L "$TARGET" ]] || error 'Projektverzeichnis darf kein symbolischer Link sein.'
for d in data data/inbox secrets caddy caddy/data caddy/config backups; do
  [[ ! -L "$TARGET/$d" ]] || error "Sicherheitsabbruch: $TARGET/$d ist ein symbolischer Link."
done
[[ -d "$TARGET/secrets" ]] || error 'Secrets-Verzeichnis fehlt; Update abgebrochen.'
[[ -f "$TARGET/secrets/admin_password_hash" ]] || error 'Installations-Secret fehlt; Update abgebrochen.'
# No sudo required: the current non-root Linux user must own the existing project.
# We never recursively chown data, secrets, or Caddy keys during an update.
OWNER_USER="$(id -un)"
OWNER_UID="$(id -u)"
OWNER_GID="$(id -g)"
[[ "$(stat -c '%u' "$TARGET")" == "$OWNER_UID" ]] || error "Das Projekt gehört nicht $OWNER_USER. Bitte einmalig die Besitzrechte korrigieren; Update nicht als root ausführen."
for folder in "$TARGET" "$TARGET/data" "$TARGET/data/inbox" "$TARGET/secrets" "$TARGET/caddy/data" "$TARGET/caddy/config" "$TARGET/backups" "$TARGET/templates" "$TARGET/static"; do
    [[ -d "$folder" && -w "$folder" ]] || error "Ordner fehlt oder ist nicht beschreibbar für $OWNER_USER: $folder"
done
[[ -w "$TARGET/.env" ]] || error '.env ist für den Projektbenutzer nicht beschreibbar.'
[[ -r "$TARGET/data/finanzen.sqlite3" || ! -e "$TARGET/data/finanzen.sqlite3" ]] || error 'SQLite-Datenbank kann nicht gelesen werden.'
for command in docker; do $command info >/dev/null 2>&1 || error "Docker ist für Benutzer $OWNER_USER nicht erreichbar. Bitte Docker-Berechtigungen prüfen."; done
printf 'Projektbenutzer: %s (UID %s, GID %s) – kein sudo erforderlich\n' "$OWNER_USER" "$OWNER_UID" "$OWNER_GID"

# Parse before copying; no bytecode or state files are written to the project.
SOURCE_DIR="$SOURCE" EXPECTED_RELEASE_VERSION="$RELEASE_VERSION" python3 - <<'PY'
import ast, os
from pathlib import Path
base = Path(os.environ['SOURCE_DIR'])
for p in (base/'src').glob('*.py'):
    ast.parse(p.read_text(encoding='utf-8'), filename=str(p))
app = (base/'src/app.py').read_text(encoding='utf-8')
assert app.count("def monthly_report():") == 1, 'Monatsauswertung fehlt oder doppelt definiert'
assert 'def household():' not in app, 'Manuelle Haushaltsbuch-Erfassung ist noch aktiv'
assert "@app.route('/account/password'" in app, 'Passwortänderung fehlt'
assert "def totp_verify():" in app and "def totp_setup():" in app, 'Verpflichtende 2FA fehlt'
assert "def settings_add_user():" in app and "def settings_delete_user(user_id):" in app, 'Benutzerverwaltung oder Benutzerlöschung fehlt'
# Runtime dependencies imported by app.py must be present in the Docker image.
# This check runs before copying anything into the installed project.
import ast
runtime_modules = {'app', 'security', 'financisto_import', 'financisto_export', 'financisto_recurring_export',
                   'backup_manager', 'sync_import', 'background_worker', 'job_monitor', 'manage', 'notifications', 'telegram_bookings', 'telegram_receiver', 'webpush'}
dockerfile = (base / 'Dockerfile').read_text(encoding='utf-8')
copied_py = {p.stem for p in (base/'src').glob('*.py')}
assert 'COPY src/ ./' in dockerfile, 'Dockerfile kopiert die neuen src-Dateien nicht.'
assert 'COPY VERSION ./VERSION' in dockerfile, 'Version muss im Docker-Image vorhanden sein.'
assert (base/'VERSION').read_text(encoding='utf-8').strip() == os.environ['EXPECTED_RELEASE_VERSION'], 'Falsche Releaseversion.'
imports = set()
for stmt in ast.walk(ast.parse(app)):
    if isinstance(stmt, ast.ImportFrom) and stmt.module:
        imports.add(stmt.module.split('.')[0])
    elif isinstance(stmt, ast.Import):
        imports.update(alias.name.split('.')[0] for alias in stmt.names)
missing = (imports & runtime_modules) - copied_py
assert not missing, f'Dockerfile enthält nicht alle benötigten App-Module: {sorted(missing)}'
assert 'financisto_export' in copied_py and 'financisto_recurring_export' in copied_py, 'Financisto-Exporter fehlt im Dockerfile'
print('Quellcode geprüft: Syntax, Monatsauswertung, 2FA und Benutzerverwaltung mit Löschfunktion OK.')
PY

BACKUP_DIR="$TARGET/backups/upgrade-$(date +%Y%m%d-%H%M%S)"
mkdir -m 700 -p "$BACKUP_DIR"
# A read-only SQLite snapshot remains consistent even if an older container is still alive.
if [[ -f "$TARGET/data/finanzen.sqlite3" ]]; then
  SOURCE_DB="$TARGET/data/finanzen.sqlite3" TARGET_DB="$BACKUP_DIR/finanzen.sqlite3" python3 - <<'PY'
import os, sqlite3
src=os.environ['SOURCE_DB']; dst=os.environ['TARGET_DB']
with sqlite3.connect('file:'+src+'?mode=ro', uri=True) as read:
    with sqlite3.connect(dst) as write:
        read.backup(write)
print('SQLite-Sicherung erfolgreich.')
PY
  chmod 600 "$BACKUP_DIR/finanzen.sqlite3"
fi
# Back up only code/configuration. Secrets, financial data and Caddy keys are NOT copied into the release.
tar -C "$TARGET" -czf "$BACKUP_DIR/previous-code.tar.gz" \
  --ignore-failed-read \
  app.py security.py financisto_import.py financisto_export.py financisto_recurring_export.py recurring.py backfill_export_source.py backfill_balances.py sync_import.py manage.py backup_manager.py background_worker.py job_monitor.py notifications.py telegram_bookings.py telegram_receiver.py webpush.py restore.sh compose.yaml Caddyfile Dockerfile \
  install.sh setup_secrets.py requirements.txt static templates README.md src docs 2>/dev/null \
  || error 'Sicherung des bisherigen Programmcodes fehlgeschlagen.'
cp -p "$TARGET/.env" "$BACKUP_DIR/env-before-update"
chmod 600 "$BACKUP_DIR/env-before-update"

# Keep the user's original site aliases before installing the new Caddyfile.
cp -p "$TARGET/Caddyfile" "$BACKUP_DIR/old-Caddyfile"
# Preserve local configuration. 1.6.1 overwrote Caddyfile each update;
# migrate the user's extra domains from the old site-address line to .env.
# Also keep the effective remote IP for a *trusted* NPM rather than blindly
# allowing all traffic from NPM's IP.
ENV_FILE="$TARGET/.env" OLD_CADDY_BACKUP="$BACKUP_DIR/old-Caddyfile" NEW_UID="$OWNER_UID" NEW_GID="$OWNER_GID" python3 - <<'PYENV'
import os, pathlib, re, ipaddress
p = pathlib.Path(os.environ['ENV_FILE'])
lines = p.read_text(encoding='utf-8').splitlines()
values = {line.split('=', 1)[0].strip(): line.split('=',1)[1].strip()
          for line in lines if '=' in line and not line.lstrip().startswith('#')}
host = values.get('SITE_HOST', '').strip()
if not host or not re.fullmatch(r'[A-Za-z0-9.\-]+', host):
    raise SystemExit('SITE_HOST fehlt oder ist ungueltig; keine Änderung')
addresses = values.get('SITE_ADDRESSES', '').strip()
if not addresses:
    hosts = [host]
    # Take existing manually added aliases into the new persistent .env.
    caddy = pathlib.Path(os.environ['OLD_CADDY_BACKUP']).read_text(encoding='utf-8')
    for line in caddy.splitlines():
        if 'https://{$SITE_HOST}' not in line or '{' not in line:
            continue
        for candidate in re.findall(r'https://([A-Za-z0-9][A-Za-z0-9.\-]*)', line):
            if candidate not in hosts:
                hosts.append(candidate)
    addresses = ', '.join('https://' + h for h in hosts)
# Safe site-address character set; deliberately no Caddyfile directives.
for item in addresses.split(','):
    item=item.strip()
    if not re.fullmatch(r'https://[A-Za-z0-9][A-Za-z0-9.\-]*', item):
        raise SystemExit('Ungültige SITE_ADDRESSES in .env: ' + item)
proxies = values.get('TRUSTED_PROXY_IPS', '127.0.0.1/32').strip()
if not proxies:
    proxies='127.0.0.1/32'
for ip in proxies.split():
    net=ipaddress.ip_network(ip, strict=False)
    # Block accidentally trusting every client.
    if net.prefixlen == 0:
        raise SystemExit('Unsicheres TRUSTED_PROXY_IPS: ' + ip)
settings = {
    'APP_UID': os.environ['NEW_UID'], 'APP_GID': os.environ['NEW_GID'],
    'SITE_ADDRESSES': addresses, 'TRUSTED_PROXY_IPS': proxies,
}
seen=set(); out=[]
for line in lines:
    key=line.split('=',1)[0].strip() if '=' in line else None
    if key in settings:
        if key not in seen:
            out.append(f'{key}={settings[key]}')
            seen.add(key)
    else:
        out.append(line)
for key,val in settings.items():
    if key not in seen:
        out.append(f'{key}={val}')
# Brand labels are user configuration; never replace existing nonempty values.
# Append only absent keys so subsequent releases preserve individual wording.
branding_defaults = {
    'APP_TITLE': '"Financisto"',
    'APP_SUBTITLE': '"Dashboard"',
    'APP_FOOTER': '"Privates Finanz-Dashboard · Daten bleiben auf deinem Server"',
}
for key, default in branding_defaults.items():
    if key not in values:
        out.append(f'{key}={default}')
p.write_text('\n'.join(out)+'\n', encoding='utf-8')
print('Caddy-Hostnamen dauerhaft in .env:', addresses)
print('Trusted-Proxies:', proxies)
PYENV

# This does NOT touch .env, financial databases, secrets, the Caddy CA or imported backups.
# New code and documentation are copied alongside the old flat files first.
# The old files are removed only after all services pass their health checks.
mkdir -p "$TARGET/src" "$TARGET/docs"
[[ ! -L "$TARGET/src" && ! -L "$TARGET/docs" ]] || error 'src/docs sind symbolische Links; Abbruch.'
cp -R "$SOURCE/src/." "$TARGET/src/"
cp -R "$SOURCE/docs/." "$TARGET/docs/"
for name in restore.sh compose.yaml Caddyfile Dockerfile install.sh requirements.txt README.md README.en.md CHANGELOG.md CHANGELOG.en.md VERSION .dockerignore .gitignore; do
  cp -f "$SOURCE/$name" "$TARGET/$name"
done
cp -R "$SOURCE/templates/." "$TARGET/templates/"
# Alte Formulare bleiben lediglich in der Code-Sicherung; keine aktiven Routen mehr.
rm -f "$TARGET/templates/household.html" "$TARGET/templates/household_edit.html"
cp -R "$SOURCE/static/." "$TARGET/static/"
cp -f "$RELEASE_DIR/update.sh" "$TARGET/update.sh"
chmod 755 "$TARGET/install.sh" "$TARGET/src/setup_secrets.py" "$TARGET/update.sh" "$TARGET/restore.sh"

# The auto-import service reads only this bind-mounted inbox.
mkdir -p "$TARGET/data/inbox"
# Kein chown: alle Bind-Mount-Daten und privaten Schlüssel behalten unveränderte Eigentümer.
# An bestehenden Secrets und deren Dateimodi wird nichts geändert.

cd "$TARGET"
docker compose config --quiet || error 'Compose-Konfiguration ungültig. Vorherigen Code unter backups/upgrade-* gesichert.'
# Before auto-import resumes, check the latest incoming Android backup read-only.
# This prevents thousands of queued files being cleaned up with an unrecognized schema.
cd "$TARGET"
PYTHONPATH="$TARGET/src" python3 - <<'PYPREFLIGHT'
from pathlib import Path
from financisto_import import parse_backup, normalized_backup, BackupError
from sync_import import BACKUP_NAME
inbox = Path('data/inbox')
files = [p for p in inbox.glob('*.backup') if p.is_file() and not p.is_symlink()]
if files:
    # Android uses YYYYMMDD_HHMMSS_mmm.backup. The newest filename, not
    # the newest FolderSync upload timestamp, identifies the recent snapshot.
    candidates = [p for p in files if BACKUP_NAME.fullmatch(p.name)]
    p = max(candidates or files, key=lambda item: item.name)
    print('Vorprüfung der neuesten Android-Sicherung:', p.name)
    try:
        if p.stat().st_size > 30 * 1024 * 1024:
            raise BackupError('Sicherung überschreitet 30 MiB')
        parsed = parse_backup(p.read_bytes())
        accounts, currencies, categories, payees, tx = normalized_backup(parsed)
        if not accounts or not tx or len(tx) != len(parsed['transactions']):
            raise BackupError('Beim Einlesen fehlen Konten oder Buchungen')
        if len({row[0] for row in tx}) != len(tx):
            raise BackupError('Doppelte Buchungs-IDs')
        print(f'Vorprüfung OK: {len(accounts)} Konten, {len(categories)} Kategorien, {len(tx)} Buchungen')
    except (BackupError, OSError, ValueError) as exc:
        raise SystemExit('ABBRUCH: Importformat vor automatischer Verarbeitung prüfen: ' + str(exc))
else:
    print('Vorprüfung: Inbox leer; kein Android-Backup vorhanden.')
PYPREFLIGHT
echo 'Baue ein gemeinsames Python-Image für Dashboard und Hintergrunddienste ...'
docker compose build dashboard || error 'Docker-Build fehlgeschlagen (Dashboard/Auto-Import). Backup liegt unter backups/upgrade-*.'
# Prevent another boot loop from a missing Python module (e.g. financisto_export).
# The ephemeral container uses the just-built image without touching the running service.
echo 'Prüfe Python-Module im neuen Dashboard-Image ...'
COMPOSE_IGNORE_ORPHANS=true docker compose run --rm --no-deps --entrypoint python dashboard -c \
  'from financisto_export import ExportError, make_export, ensure_source_table, store_matching_source; import security, financisto_import, backup_manager, recurring, background_worker, job_monitor, financisto_recurring_export, notifications, telegram_bookings; print("Python-Module vollständig")' \
  || error 'Dashboard-Image unvollständig: erforderliche Python-Module fehlen. Laufende Anwendung nicht neu gestartet.'

# Explicitly retire ONLY this application's old workers, not other Compose projects.
# Stop old jobs before the new process begins to avoid two schedulers posting
# the same recurring payment. Leave them stopped until the new worker is healthy.
echo 'Beende bisherige Hintergrundcontainer kontrolliert ...'
for old in financisto-dashboard-auto-import financisto-dashboard-recurring financisto-dashboard-backup; do
  if docker inspect "$old" >/dev/null 2>&1; then
    old_running="$(docker inspect -f '{{.State.Running}}' "$old")"
    if [[ "$old_running" == true ]]; then
      docker stop -t 30 "$old" >/dev/null || error "Alter Hintergrunddienst konnte nicht beendet werden: $old"
    fi
    docker rm "$old" >/dev/null || error "Altcontainer konnte nicht entfernt werden: $old"
    echo "Entfernt: $old"
  fi
done

echo "Starte Dashboard, Caddy und gemeinsamen Hintergrunddienst mit Benutzer $OWNER_USER ..."
docker compose up -d dashboard caddy background notifications || error 'Docker-Start fehlgeschlagen. Vorherige SQLite-/Code-Sicherung ist erhalten.'

for _ in $(seq 1 45); do
  state="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' financisto-dashboard-app 2>/dev/null || true)"
  [[ "$state" == healthy ]] && break
  [[ "$state" == unhealthy ]] && break
  sleep 2
done
if [[ "$state" != healthy ]]; then
  docker compose logs --tail 40 dashboard >&2 || true
  error "Dashboard nicht healthy (Status: $state). Vorheriger Code und SQLite-Sicherung: $BACKUP_DIR"
fi

# Preserve the exact original backup in SQLite before import-archive retention can rotate it.
FINANCISTO_PROJECT_DIR="$TARGET" PYTHONPATH="$TARGET/src" python3 "$TARGET/src/backfill_export_source.py" || error 'Exportgrundlage konnte nicht geprüft werden; SQLite-Sicherung liegt im Update-Backup.'

# Restore account balances only if an archived backup matches the active SQLite snapshot.
# Never overwrite bookings, user settings, credentials, or mismatched balances.
FINANCISTO_PROJECT_DIR="$TARGET" PYTHONPATH="$TARGET/src" python3 "$TARGET/src/backfill_balances.py" || error 'Kontostand-Abgleich fehlgeschlagen. Datenbank-Sicherung liegt im Update-Backup.'

# Confirm Caddy is also still running; HTTPS setup is separate from the app healthcheck.
sleep 2
caddy_state="$(docker inspect -f '{{.State.Running}}' financisto-dashboard-caddy 2>/dev/null || true)"
if [[ "$caddy_state" != true ]]; then
  docker compose logs --tail 40 caddy >&2 || true
  error "Caddy läuft nicht. Vorheriger Code und SQLite-Sicherung: $BACKUP_DIR"
fi

notification_state="$(docker inspect -f '{{.State.Running}}' financisto-dashboard-notifications 2>/dev/null || true)"
if [[ "$notification_state" != true ]]; then
  docker compose logs --tail 40 notifications >&2 || true
  error "Benachrichtigungsdienst läuft nicht. Vorheriger Code und SQLite-Sicherung: $BACKUP_DIR"
fi

background_state="$(docker inspect -f '{{.State.Running}}' financisto-dashboard-background 2>/dev/null || true)"
if [[ "$background_state" != true ]]; then
  docker compose logs --tail 40 background >&2 || true
  error "Gemeinsamer Hintergrunddienst läuft nicht. Vorherige Daten/Code-Sicherung: $BACKUP_DIR"
fi
# Check the actual Python worker in the built image; a stale image can look
# healthy but process old code. Do not run the tasks during this check.
local_worker_hash="$(python3 - "$TARGET/src/background_worker.py" <<'PYHASH'
import hashlib,sys
print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())
PYHASH
)"
container_worker_hash="$(docker compose exec -T background python -c 'import hashlib;print(hashlib.sha256(open("/app/background_worker.py","rb").read()).hexdigest())' 2>/dev/null || true)"
[[ -n "$container_worker_hash" && "$container_worker_hash" == "$local_worker_hash" ]] || error "Background-Image enthält nicht den aktuellen Code. Backup: $BACKUP_DIR"

# Verify ownership of private project paths after the update. The SFTP inbox
# is intentionally different: the SFTP jail may own it as root:financisto-sftp,
# while the project user has write access through POSIX ACLs. Ownership of the
# inbox MUST NOT be forcibly changed here, and access is checked instead.
for folder in "$TARGET/data" "$TARGET/secrets" "$TARGET/caddy/data" "$TARGET/caddy/config"; do
  [[ "$(stat -c '%u' "$folder")" == "$OWNER_UID" ]] || error "Verzeichnis gehört nicht dem Projektbenutzer: $folder"
done
[[ -d "$TARGET/data/inbox" && -w "$TARGET/data/inbox" ]] || error "SFTP-Inbox für $OWNER_USER nicht beschreibbar: $TARGET/data/inbox"

# Only now retire the obsolete root-level code and documentation.
# Files are backed up in previous-code.tar.gz, with a consistent database snapshot.
echo 'Räume alte Python-Dateien und Dokumentation im Projekt-Hauptverzeichnis auf ...'
for name in app.py security.py financisto_import.py financisto_export.py financisto_recurring_export.py recurring.py \
    backfill_export_source.py backfill_balances.py sync_import.py manage.py backup_manager.py \
    background_worker.py job_monitor.py notifications.py telegram_bookings.py telegram_receiver.py \
    webpush.py setup_secrets.py; do
  [[ -f "$TARGET/src/$name" ]] || error "Neue Python-Datei fehlt: src/$name"
  rm -f -- "$TARGET/$name"
done
for name in BACKUP_RESTORE.md BRANDING.md DESIGN_SEA_WOLVES.md FINANCISTO_EXPORT.md \
    MOBILE_1920.md NOTIFICATIONS.md PWA_ANDROID.md RECURRING.md SECURITY_UPGRADE.md \
    TELEGRAM_BOOKINGS.md WEB_PUSH.md; do
  [[ -f "$TARGET/docs/$name" ]] || error "Neue Dokumentation fehlt: docs/$name"
  rm -f -- "$TARGET/$name"
done
# Local Python caches can be deleted; never touch data, backups, secrets or caddy.
if [[ -d "$TARGET/__pycache__" && ! -L "$TARGET/__pycache__" ]]; then
  find "$TARGET/__pycache__" -maxdepth 1 -type f -name '*.pyc' -delete
  rmdir "$TARGET/__pycache__" 2>/dev/null || true
fi

printf '\nUPDATE %s ERFOLGREICH.\nBackup: %s\nAusgeführt als %s (UID %s, GID %s); bestehende Eigentümer unverändert.\n' "$RELEASE_VERSION" "$BACKUP_DIR" "$OWNER_USER" "$OWNER_UID" "$OWNER_GID"
echo 'Verwende die bestehende Dashboard-Adresse und dein bisheriges Administratorpasswort.'
