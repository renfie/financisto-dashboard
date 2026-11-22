from __future__ import annotations
import calendar
import csv
import hashlib
import notifications
import webpush
import telegram_bookings
import hmac
import ipaddress
import os
import re
import secrets
import sqlite3
import time
from decimal import Decimal, InvalidOperation
from io import BytesIO, StringIO
from flask import send_file
from zoneinfo import ZoneInfo
from collections import defaultdict
from datetime import date, datetime, timedelta
from functools import wraps
from pathlib import Path
from urllib.parse import urlencode

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for, jsonify
from cryptography.fernet import InvalidToken
from security import (new_totp_seed, encrypt_seed, decrypt_seed, valid_totp_step,
                      totp_svg_data_uri, new_recovery_codes, recovery_hash)
from financisto_import import BackupError, ImportPaused, parse_backup, save_snapshot, ensure_account_snapshots
from financisto_export import ExportError, make_export, ensure_source_table, store_matching_source
from financisto_recurring_export import merge_recurring_export, preview_summary
from backup_manager import (create_backup as create_verified_backup, status as scheduled_backup_status,
                            current_financisto_backups, export_dir as financisto_export_dir,
                            export_current_financisto)
from job_monitor import ensure_schema as ensure_monitor_schema, dashboard_status
from recurring import (ensure_schema as ensure_recurring_schema, preview_from_backup,
                       save_import_preview, confirm_import, validate_rule,
                       on_or_after, post_one, today as recurring_today)

BASE = Path(__file__).resolve().parent
if BASE.name == 'src':
    BASE = BASE.parent
DATABASE = os.getenv('DATABASE_PATH', str(BASE / 'data' / 'finanzen.sqlite3'))
USER = os.getenv('ADMIN_USERNAME', 'admin')
def read_secret(env, default_path):
    path = Path(os.getenv(env, default_path))
    try:
        return path.read_text().strip()
    except FileNotFoundError as e:
        raise RuntimeError('Bitte zuerst ./install.sh ausführen; fehlender Secret-Pfad: ' + str(path)) from e

HASH = read_secret('ADMIN_PASSWORD_HASH_FILE', str(BASE / 'secrets' / 'admin_password_hash'))
SECRET = read_secret('APP_SECRET_FILE', str(BASE / 'secrets' / 'app_secret'))
INITIAL_IP = read_secret('INITIAL_IP_FILE', str(BASE / 'secrets' / 'initial_ip'))


app = Flask(__name__)
# The installer sets the default language. Individual visitors can switch it
# for the current browser session without changing any financial records.
DEFAULT_LANGUAGE = os.getenv('DEFAULT_LANGUAGE', 'de').strip().lower()
if DEFAULT_LANGUAGE not in ('de', 'en'):
    DEFAULT_LANGUAGE = 'de'


def interface_language():
    requested = session.get('ui_language')
    return requested if requested in ('de', 'en') else DEFAULT_LANGUAGE

app.config.update(SECRET_KEY=SECRET, SESSION_COOKIE_SECURE=True,
                  SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Strict',
                  PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
                  MAX_CONTENT_LENGTH=30*1024*1024)

# Authentication attempts live in SQLite, shared by both Gunicorn workers.
PUBLIC_ACCESS = os.getenv('PUBLIC_ACCESS', '0').strip().lower() in ('1', 'true', 'yes')

# Presentation-only brand settings. Empty/missing settings use the historical defaults.
# No private or account-related data are read from .env beyond these public labels.
def brand_env(key, default, max_length):
    value = os.getenv(key, '').strip()
    return value[:max_length] if value else default

APP_BRANDING = {
    'app_title': brand_env('APP_TITLE', 'Financisto', 90),
    'app_subtitle': brand_env('APP_SUBTITLE', 'Dashboard', 120),
    'app_footer': brand_env('APP_FOOTER', 'Privates Finanz-Dashboard · Daten bleiben auf deinem Server', 240),
    'app_version': (BASE / 'VERSION').read_text(encoding='utf-8').strip(),
}


# English footer can be independently configured without changing an existing
# APP_FOOTER value. Do not machine-translate arbitrary user-defined branding.
def footer_for_language():
    german = APP_BRANDING['app_footer']
    if interface_language() != 'en':
        return german
    english = brand_env('APP_FOOTER_EN', '', 240)
    if english:
        return english
    # Built-in defaults and a formerly used project slogan may be translated
    # without touching custom text in .env. Anything else is shown as supplied.
    known = {
        'Privates Finanz-Dashboard · Daten bleiben auf deinem Server':
            'Private finance dashboard · Your data stays on your server',
        'Alles im Blick. Bis auf den letzten Cent.':
            'Your finances at a glance. Down to the last cent.',
    }
    return known.get(german, german)


def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db


def init_db():
    Path(DATABASE).parent.mkdir(parents=True, exist_ok=True)
    with get_db() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS accounts(id INTEGER PRIMARY KEY,title TEXT,currency_id INTEGER,kind TEXT);
        CREATE TABLE IF NOT EXISTS currencies(id INTEGER PRIMARY KEY,code TEXT,symbol TEXT,decimals INTEGER);
        CREATE TABLE IF NOT EXISTS categories(id INTEGER PRIMARY KEY,title TEXT,lft INTEGER,rgt INTEGER,kind INTEGER);
        CREATE TABLE IF NOT EXISTS payees(id INTEGER PRIMARY KEY,title TEXT);
        CREATE TABLE IF NOT EXISTS transactions(id INTEGER PRIMARY KEY,day TEXT,account_id INTEGER,to_account_id INTEGER,category_id INTEGER,payee_id INTEGER,amount INTEGER,note TEXT,is_template INTEGER);
        CREATE INDEX IF NOT EXISTS tx_day_idx ON transactions(day);
        CREATE INDEX IF NOT EXISTS tx_acc_idx ON transactions(account_id);
        CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT);
        CREATE TABLE IF NOT EXISTS administrator_auth(
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            version INTEGER NOT NULL DEFAULT 1,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        -- Independent household book: Financisto imports never touch these tables.
        CREATE TABLE IF NOT EXISTS household_categories(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL COLLATE NOCASE UNIQUE
        );
        CREATE TABLE IF NOT EXISTS household_entries(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day TEXT NOT NULL,
            kind TEXT NOT NULL CHECK(kind IN ('income','expense')),
            amount_cents INTEGER NOT NULL CHECK(amount_cents>0),
            category_id INTEGER REFERENCES household_categories(id),
            payee TEXT NOT NULL DEFAULT '',
            note TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS hh_day_idx ON household_entries(day);
        CREATE INDEX IF NOT EXISTS hh_category_idx ON household_entries(category_id);
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL COLLATE NOCASE UNIQUE,
            display_name TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin','editor','viewer')),
            password_hash TEXT NOT NULL,
            version INTEGER NOT NULL DEFAULT 1,
            is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0,1)),
            totp_seed_enc TEXT,
            totp_enabled INTEGER NOT NULL DEFAULT 0 CHECK(totp_enabled IN (0,1)),
            last_totp_step INTEGER NOT NULL DEFAULT -1,
            tutorial_completed INTEGER NOT NULL DEFAULT 1 CHECK(tutorial_completed IN (0,1)),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS recovery_codes (
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            code_hash TEXT NOT NULL,
            PRIMARY KEY(user_id,code_hash)
        );
        CREATE TABLE IF NOT EXISTS auth_attempts (
            key TEXT NOT NULL, moment INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS auth_attempts_idx ON auth_attempts(key,moment);
        CREATE TABLE IF NOT EXISTS mobile_api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            user_version INTEGER NOT NULL,
            label TEXT NOT NULL,
            key_hash TEXT NOT NULL UNIQUE,
            access TEXT NOT NULL CHECK(access IN ('read','write')),
            issued_on INTEGER NOT NULL,
            expires_on INTEGER NOT NULL,
            revoked_on INTEGER
        );
        CREATE TABLE IF NOT EXISTS mobile_api_receipts (
            key_id INTEGER NOT NULL REFERENCES mobile_api_keys(id),
            request_id TEXT NOT NULL,
            operation TEXT NOT NULL,
            fingerprint TEXT NOT NULL,
            response_json TEXT NOT NULL,
            created_on INTEGER NOT NULL,
            PRIMARY KEY(key_id,request_id)
        );

        CREATE TABLE IF NOT EXISTS audit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor_id INTEGER, event TEXT NOT NULL, detail TEXT NOT NULL DEFAULT '',
            client_ip TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS allowed_clients(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip TEXT NOT NULL UNIQUE,
            label TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        ''')
        db.execute('BEGIN IMMEDIATE')  # serialize schema check across multiple Gunicorn workers
        ensure_account_snapshots(db)
        ensure_source_table(db)
        ensure_monitor_schema(db)
        notifications.ensure_schema(db)
        webpush.ensure_schema(db, SECRET)
        telegram_bookings.ensure_schema(db)
        # Existing users are NOT interrupted by onboarding during this upgrade.
        # Newly created users receive the tour on their first full login.
        user_columns = {r['name'] for r in db.execute('PRAGMA table_info(users)')}
        if 'tutorial_completed' not in user_columns:
            db.execute('ALTER TABLE users ADD COLUMN tutorial_completed INTEGER NOT NULL DEFAULT 1 CHECK(tutorial_completed IN (0,1))')
        # Non-destructive migration of imported transactions. No old rows are changed.
        cols = {r['name'] for r in db.execute('PRAGMA table_info(transactions)')}
        if 'origin' not in cols:
            db.execute("ALTER TABLE transactions ADD COLUMN origin TEXT NOT NULL DEFAULT 'financisto'")
        # Existing installations remain in Android/Financisto mode with auto-import ON.
        db.execute("INSERT OR IGNORE INTO meta(key,value) VALUES ('finance_mode','import')")
        db.execute("INSERT OR IGNORE INTO meta(key,value) VALUES ('auto_import_enabled','1')")
        db.execute("INSERT OR IGNORE INTO meta(key,value) VALUES ('ledger_web_writes','0')")
        db.execute("INSERT OR IGNORE INTO meta(key,value) VALUES ('default_account_id','')")
        # 1.9.30: One shared default expense category for Web and Telegram.
        # Preserve a previously selected Telegram category when upgrading.
        # If no explicit category existed, reuse an unambiguous existing 'Einkauf'
        # category so the previous Telegram convention is preserved.
        previous = db.execute("SELECT 1 FROM meta WHERE key='default_expense_category_id'").fetchone()
        if not previous:
            telegram = db.execute('SELECT default_category_id FROM telegram_booking_settings WHERE id=1').fetchone()
            migrated = int(telegram['default_category_id'] or 0) if telegram else 0
            if migrated and not db.execute('SELECT 1 FROM categories WHERE id=? AND kind=0',(migrated,)).fetchone():
                migrated = 0
            if not migrated:
                shopping = db.execute("SELECT id FROM categories WHERE kind=0 AND title='Einkauf' COLLATE NOCASE").fetchall()
                if len(shopping) == 1:
                    migrated = shopping[0]['id']
            db.execute("INSERT INTO meta(key,value) VALUES ('default_expense_category_id',?)",
                       (str(migrated) if migrated else '',))
        db.execute("INSERT OR IGNORE INTO meta(key,value) VALUES ('booking_page_size','30')")
        db.execute("INSERT OR IGNORE INTO meta(key,value) VALUES ('daily_backup_enabled','1')")
        db.execute("INSERT OR IGNORE INTO meta(key,value) VALUES ('default_currency_code','EUR')")
        db.execute("INSERT OR IGNORE INTO meta(key,value) VALUES ('public_access_enabled',?)",
                   ('1' if PUBLIC_ACCESS else '0',))
        db.execute("INSERT OR IGNORE INTO meta(key,value) VALUES ('import_overwrite_pending','0')")
        db.execute("INSERT OR IGNORE INTO meta(key,value) VALUES ('import_overwrite_approved','0')")
        # Bootstrap the existing installation hash exactly once. Password updates
        # are written to SQLite, not to the container's read-only secrets mount.
        db.execute('''INSERT OR IGNORE INTO administrator_auth(username,password_hash)
                      VALUES (?,?)''', (USER,HASH))
        # Preserve the original administrator's CURRENT password hash. This runs
        # only once; existing users and TOTP secrets are never reset by an upgrade.
        db.execute('''INSERT OR IGNORE INTO users(username,display_name,role,password_hash)
            SELECT username,'Administrator','admin',password_hash
            FROM administrator_auth
            WHERE username=? AND NOT EXISTS(SELECT 1 FROM users)''', (USER,))
        # Seed the first PC only once. Reboots will never resurrect removed IPs.
        seeded = db.execute("SELECT value FROM meta WHERE key='allowlist_initialized'").fetchone()
        if not seeded:
            first_ip = str(ipaddress.ip_address(INITIAL_IP))
            db.execute('INSERT OR IGNORE INTO allowed_clients(ip,label) VALUES (?,?)',
                       (first_ip, 'Erster PC (Installation)'))
            db.execute("INSERT OR IGNORE INTO meta(key,value) VALUES ('allowlist_initialized','1')")

init_db()
with get_db() as _db:
    ensure_recurring_schema(_db)


def make_password_hash(password):
    salt = secrets.token_bytes(32)
    rounds = 600_000
    digest = hashlib.pbkdf2_hmac('sha256',password.encode('utf-8'),salt,rounds).hex()
    return f'pbkdf2_sha256:{rounds}:{salt.hex()}:{digest}'


def verify_password_hash(password, stored_hash):
    try:
        method, rounds, salt, target = stored_hash.split(':', 3)
        if method != 'pbkdf2_sha256':
            return False
        count = int(rounds)
        if not 1000 <= count <= 2_000_000:
            return False
        digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'),bytes.fromhex(salt),count).hex()
        return hmac.compare_digest(digest,target)
    except (ValueError, TypeError, AttributeError):
        return False


def auth_state():
    """Compatibility with the original install.sh --verify command."""
    with get_db() as db:
        row = db.execute('SELECT password_hash,version FROM users WHERE username=?', (USER,)).fetchone()
    return (row['password_hash'],row['version']) if row else ('', 0)


def check_password(password):
    return verify_password_hash(password, auth_state()[0])


def csrf():
    if 'csrf' not in session:
        session['csrf'] = secrets.token_urlsafe(32)
    return session['csrf']

app.jinja_env.globals['csrf_token'] = csrf


def csrf_ok():
    expected = session.get('csrf', '')
    received = request.form.get('csrf', '')
    return bool(expected) and bool(received) and hmac.compare_digest(expected, received)


def current_user():
    uid = session.get('user_id')
    if not session.get('logged_in') or not isinstance(uid, int) or not session.get('totp_ok'):
        return None
    with get_db() as db:
        row = db.execute('SELECT * FROM users WHERE id=?', (uid,)).fetchone()
    if (not row or not row['is_active'] or not row['totp_enabled'] or
            session.get('auth_version') != row['version']):
        return None
    return row


@app.context_processor
def inject_user():
    return {'viewer': current_user(), 'ui_language': interface_language(), **APP_BRANDING, 'app_footer': footer_for_language()}



@app.post('/language')
def set_interface_language():
    # CSRF must be verified even for presentation-only session changes.
    if not csrf_ok():
        abort(400)
    desired = request.form.get('language', '')
    if desired not in ('de', 'en'):
        abort(400)
    session['ui_language'] = desired
    # Redirect only to an on-site relative URL, never a user-supplied host.
    destination = request.form.get('return_to', '/')
    if not destination.startswith('/') or destination.startswith('//') or '\\' in destination:
        destination = '/'
    return redirect(destination, code=303)


def login_required(f):
    @wraps(f)
    def wrapped(*a, **k):
        if current_user() is None:
            session.clear()
            return redirect(url_for('login'))
        return f(*a, **k)
    return wrapped


def admin_required(f):
    @wraps(f)
    @login_required
    def wrapped(*a, **k):
        if current_user()['role'] != 'admin':
            abort(403)
        return f(*a, **k)
    return wrapped


def audit(db, event, detail='', actor_id=None):
    if actor_id is None:
        actor = current_user()
        actor_id = actor['id'] if actor else None
    db.execute('INSERT INTO audit_events(actor_id,event,detail,client_ip) VALUES(?,?,?,?)',
               (actor_id, event, detail[:250], verified_ip()))


def rate_key(prefix, identity):
    return prefix + ':' + (verified_ip() or 'unknown') + ':' + str(identity).casefold()[:75]


def is_rate_limited(key, limit=8, window=600):
    cutoff = int(time.time()) - window
    with get_db() as db:
        count = db.execute('SELECT COUNT(*) FROM auth_attempts WHERE key=? AND moment>=?',
                           (key, cutoff)).fetchone()[0]
    return count >= limit


def failed_attempt(key):
    with get_db() as db:
        db.execute('DELETE FROM auth_attempts WHERE moment<?', (int(time.time()) - 86400,))
        db.execute('INSERT INTO auth_attempts(key,moment) VALUES(?,?)', (key, int(time.time())))


def clear_attempts(key):
    with get_db() as db:
        db.execute('DELETE FROM auth_attempts WHERE key=?', (key,))


def pending_user():
    uid = session.get('pending_user_id')
    if not isinstance(uid, int):
        return None
    with get_db() as db:
        user = db.execute('SELECT * FROM users WHERE id=?', (uid,)).fetchone()
    if not user or not user['is_active'] or user['version'] != session.get('pending_version'):
        session.clear()
        return None
    return user


def complete_login(user):
    # Keep the user's current language choice across the 2FA login transition.
    chosen_language = session.get('ui_language')
    session.clear()
    if chosen_language in ('de', 'en'):
        session['ui_language'] = chosen_language
    session['logged_in'] = True
    session['user_id'] = user['id']
    session['auth_version'] = user['version']
    session['totp_ok'] = True
    session.permanent = True
    csrf()


@app.after_request
def harden(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; object-src 'none'; frame-ancestors 'none'; form-action 'self'; base-uri 'none'"
    return response


@app.get('/healthz')
def health():
    return 'ok\n', 200, {'Cache-Control': 'no-store'}




def verified_ip():
    # Only Caddy is connected to the app container. Caddy OVERRIDES this header
    # using the physical TCP peer and checks the allowlist on every request.
    raw = request.headers.get('X-Verified-Client-IP', '')
    try:
        address = ipaddress.ip_address(raw)
        if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
            address = address.ipv4_mapped
        return str(address)
    except ValueError:
        return None


@app.get('/_internal/check-ip')
def check_ip_gate():
    ip = verified_ip()
    if not ip:
        abort(403)
    with get_db() as db:
        allowed = db.execute('SELECT 1 FROM allowed_clients WHERE ip=?', (ip,)).fetchone()
        public_row = db.execute("SELECT value FROM meta WHERE key='public_access_enabled'").fetchone()
        public_enabled = bool(public_row and public_row['value'] == '1')
        # Public login is opt-in only and must have a fully enrolled admin.
        # This does NOT authenticate anyone: every private route also requires
        # password + 2FA + an active account.
        admin_enrolled = db.execute("SELECT 1 FROM users WHERE role='admin' AND is_active=1 AND totp_enabled=1 LIMIT 1").fetchone()
    if public_enabled and admin_enrolled:
        return ('', 204)
    return ('', 204) if allowed else ('Dieser PC ist nicht freigegeben. Bitte Administrator kontaktieren.\n', 403)


@app.get('/pcs')
@admin_required
def pcs():
    with get_db() as db:
        clients = db.execute('SELECT id,ip,label,created_at FROM allowed_clients ORDER BY created_at,id').fetchall()
    return render_template('pcs.html', clients=clients, current_ip=verified_ip())


@app.post('/pcs/add')
@admin_required
def add_pc():
    if not csrf_ok(): abort(400)
    try:
        addr = ipaddress.ip_address(request.form.get('ip', '').strip())
        if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped:
            addr = addr.ipv4_mapped
        ip = str(addr)
    except ValueError:
        flash('Bitte eine einzelne gültige IP-Adresse eingeben (z. B. 192.168.1.42).', 'error')
        return redirect(url_for('settings') + '#pc-freigaben')
    label = request.form.get('label', '').strip()[:100] or 'PC'
    try:
        with get_db() as db:
            db.execute('INSERT INTO allowed_clients(ip,label) VALUES (?,?)', (ip,label))
        flash('PC wurde freigegeben: ' + ip, 'success')
    except sqlite3.IntegrityError:
        flash('Diese IP-Adresse ist bereits freigegeben.', 'error')
    return redirect(url_for('settings') + '#pc-freigaben')


@app.post('/pcs/remove/<int:client_id>')
@admin_required
def remove_pc(client_id):
    if not csrf_ok(): abort(400)
    with get_db() as db:
        entry = db.execute('SELECT ip FROM allowed_clients WHERE id=?', (client_id,)).fetchone()
        if not entry:
            abort(404)
        if entry['ip'] == verified_ip():
            flash('Den aktuell verwendeten PC kannst du nicht selbst sperren.', 'error')
        elif db.execute('SELECT COUNT(*) FROM allowed_clients').fetchone()[0] <= 1:
            flash('Mindestens ein PC muss freigegeben bleiben.', 'error')
        else:
            db.execute('DELETE FROM allowed_clients WHERE id=?', (client_id,))
            flash('PC wurde aus der Freigabeliste entfernt.', 'success')
    return redirect(url_for('settings') + '#pc-freigaben')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user():
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        if not csrf_ok():
            abort(400)
        username = request.form.get('username', '').strip()[:80]
        password = request.form.get('password', '')
        key = rate_key('password', username)
        with get_db() as db:
            user = db.execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()
        if is_rate_limited(key):
            flash('Zu viele Anmeldeversuche. Bitte später erneut versuchen.', 'error')
        elif user and user['is_active'] and verify_password_hash(password, user['password_hash']):
            clear_attempts(key)
            chosen_language = session.get('ui_language')
            session.clear()
            if chosen_language in ('de', 'en'):
                session['ui_language'] = chosen_language
            session['pending_user_id'] = user['id']
            session['pending_version'] = user['version']
            session.permanent = False
            csrf()
            return redirect(url_for('totp_verify' if user['totp_enabled'] else 'totp_setup'))
        else:
            failed_attempt(key)
            flash('Anmeldedaten ungültig.', 'error')
    return render_template('login.html')


@app.route('/auth/2fa/setup', methods=['GET', 'POST'])
def totp_setup():
    user = pending_user()
    if not user:
        return redirect(url_for('login'))
    if user['totp_enabled']:
        return redirect(url_for('totp_verify'))
    if not user['totp_seed_enc']:
        seed = new_totp_seed()
        with get_db() as db:
            db.execute('UPDATE users SET totp_seed_enc=? WHERE id=? AND totp_seed_enc IS NULL',
                       (encrypt_seed(seed, SECRET), user['id']))
    with get_db() as db:
        row = db.execute('SELECT totp_seed_enc FROM users WHERE id=?', (user['id'],)).fetchone()
    try:
        seed = decrypt_seed(row['totp_seed_enc'], SECRET)
    except (InvalidToken, TypeError, ValueError):
        abort(500, 'TOTP-Konfiguration kann nicht entschlüsselt werden; app_secret prüfen.')
    if request.method == 'POST':
        if not csrf_ok():
            abort(400)
        key = rate_key('enroll', user['id'])
        code = request.form.get('code', '').strip()
        if is_rate_limited(key, limit=6):
            flash('Zu viele Versuche. Bitte später erneut versuchen.', 'error')
        else:
            with get_db() as db:
                db.execute('BEGIN IMMEDIATE')
                actual = db.execute('SELECT * FROM users WHERE id=?', (user['id'],)).fetchone()
                step = valid_totp_step(seed, code, actual['last_totp_step'])
                if not actual['totp_enabled'] and step is not None:
                    codes = new_recovery_codes()
                    db.execute('''UPDATE users SET totp_enabled=1,last_totp_step=?,
                        version=version+1,updated_at=CURRENT_TIMESTAMP WHERE id=?''',
                        (step, user['id']))
                    db.execute('DELETE FROM recovery_codes WHERE user_id=?', (user['id'],))
                    db.executemany('INSERT INTO recovery_codes(user_id,code_hash) VALUES(?,?)',
                                   [(user['id'], recovery_hash(user['id'], c)) for c in codes])
                    audit(db, '2fa_enrolled', user['username'], actor_id=user['id'])
                    updated = db.execute('SELECT * FROM users WHERE id=?', (user['id'],)).fetchone()
                else:
                    updated = None
            if updated:
                clear_attempts(key)
                complete_login(updated)
                return render_template('recovery_codes.html', codes=codes)
            failed_attempt(key)
            flash('Bestätigungscode ungültig oder bereits verwendet.', 'error')
    return render_template('totp_setup.html', seed=seed, qr=totp_svg_data_uri(seed, user['username']), username=user['username'])


@app.route('/auth/2fa/verify', methods=['GET', 'POST'])
def totp_verify():
    user = pending_user()
    if not user:
        return redirect(url_for('login'))
    if not user['totp_enabled']:
        return redirect(url_for('totp_setup'))
    if request.method == 'POST':
        if not csrf_ok():
            abort(400)
        key = rate_key('totp', user['id'])
        code = request.form.get('code', '').strip()
        if is_rate_limited(key, limit=6):
            flash('Zu viele Versuche. Bitte später erneut versuchen.', 'error')
        else:
            with get_db() as db:
                db.execute('BEGIN IMMEDIATE')
                current = db.execute('SELECT * FROM users WHERE id=?', (user['id'],)).fetchone()
                accepted = False
                if current and current['is_active'] and current['totp_enabled']:
                    if len(code) == 6 and code.isascii() and code.isdigit():
                        try:
                            seed = decrypt_seed(current['totp_seed_enc'], SECRET)
                            step = valid_totp_step(seed, code, current['last_totp_step'])
                        except (InvalidToken, ValueError, TypeError):
                            step = None
                        if step is not None:
                            db.execute('UPDATE users SET last_totp_step=? WHERE id=?', (step, user['id']))
                            accepted = True
                    elif re.fullmatch(r'[0-9a-fA-F]{8}-?[0-9a-fA-F]{8}', code):
                        digest = recovery_hash(user['id'], code)
                        deleted = db.execute('DELETE FROM recovery_codes WHERE user_id=? AND code_hash=?',
                                             (user['id'], digest)).rowcount
                        if deleted:
                            accepted = True
                            audit(db, 'recovery_code_used', user['username'], actor_id=user['id'])
            if accepted:
                clear_attempts(key)
                complete_login(user)
                return redirect(url_for('dashboard'))
            failed_attempt(key)
            flash('2FA-Code ungültig oder bereits verwendet.', 'error')
    return render_template('totp_verify.html', username=user['username'])


@app.post('/account/tutorial/complete')
@login_required
def complete_tutorial():
    if not csrf_ok():
        abort(400)
    outcome = request.form.get('outcome', '')
    if outcome not in ('finished', 'skipped'):
        abort(400)
    user = current_user()
    with get_db() as db:
        db.execute('UPDATE users SET tutorial_completed=1,updated_at=CURRENT_TIMESTAMP WHERE id=?',
                   (user['id'],))
        audit(db, 'tutorial_' + outcome, actor_id=user['id'])
    return {'ok': True}


@app.post('/auth/logout-pending')
def logout_pending():
    if not csrf_ok(): abort(400)
    session.clear()
    return redirect(url_for('login'))


@app.post('/auth/recovery/ack')
@login_required
def recovery_ack():
    if not csrf_ok(): abort(400)
    return redirect(url_for('dashboard'))


@app.route('/account/password', methods=['GET', 'POST'])
@login_required
def change_password():
    user = current_user()
    if request.method == 'POST':
        if not csrf_ok(): abort(400)
        old_password = request.form.get('old_password', '')
        new_password = request.form.get('new_password', '')
        confirm = request.form.get('confirm_password', '')
        if not verify_password_hash(old_password, user['password_hash']):
            flash('Das bisherige Passwort ist nicht korrekt.', 'error')
        elif not 12 <= len(new_password) <= 256:
            flash('Das neue Passwort muss 12 bis 256 Zeichen enthalten.', 'error')
        elif new_password != confirm or new_password == old_password:
            flash('Neue Passwörter stimmen nicht überein oder sind unverändert.', 'error')
        else:
            with get_db() as db:
                changed = db.execute('''UPDATE users SET password_hash=?,version=version+1,
                    updated_at=CURRENT_TIMESTAMP WHERE id=? AND version=?''',
                    (make_password_hash(new_password), user['id'], user['version'])).rowcount
                if changed:
                    audit(db, 'password_changed', actor_id=user['id'])
            if changed:
                session.clear()
                flash('Passwort geändert. Bitte mit Passwort und 2FA neu anmelden.', 'success')
                return redirect(url_for('login'))
            flash('Die Anmeldung wurde zwischenzeitlich geändert. Bitte neu anmelden.', 'error')
    return render_template('change_password.html')




# 1.9.31: per-device Web Push, independent of Telegram/Node-RED/Gotify.
def _push_json():
    token=request.headers.get('X-CSRF-Token','')
    if not token or not hmac.compare_digest(session.get('csrf',''),token): abort(400)
    if not request.is_json: abort(415)
    data=request.get_json(silent=True)
    if not isinstance(data,dict): abort(400)
    return data

@app.get('/api/push/config')
@login_required
def push_config():
    with get_db() as db:
        return jsonify(publicKey=webpush.public_key(db),
                       deviceCount=webpush.count_for_user(db,current_user()['id']),
                       preferences=webpush.preferences(db,current_user()['id']))

@app.post('/api/push/preferences')
@login_required
def push_save_preferences():
    data=_push_json()
    # The client must supply booleans, no permissive truthy-string conversion.
    try:
        if not isinstance(data.get('minAmount'),str):
            raise ValueError('Grenzbetrag fehlt.')
        amount_text=data['minAmount'].strip()
        if not re.fullmatch(r'\d{1,9}(?:[,.]\d{1,2})?',amount_text):
            raise ValueError('Bitte einen positiven EUR-Betrag mit maximal zwei Nachkommastellen eingeben.')
        cents=int(Decimal(amount_text.replace(',','.'))*100)
        with get_db() as db:
            webpush.save_preferences(db,current_user()['id'],
                data.get('expenseEnabled'),data.get('incomeEnabled'),
                cents,data.get('detailLevel'))
            audit(db,'webpush_preferences_saved','Eigene Benachrichtigungseinstellungen')
    except (ValueError,ArithmeticError) as exc:
        return jsonify(error=str(exc)),400
    return jsonify(ok=True)

@app.post('/api/push/device-status')
@login_required
def push_device_status():
    data=_push_json()
    endpoint=data.get('endpoint')
    if not isinstance(endpoint,str) or len(endpoint)>2048: abort(400)
    with get_db() as db:
        ok=bool(db.execute('SELECT 1 FROM webpush_subscriptions WHERE user_id=? AND endpoint=?',
            (current_user()['id'],endpoint)).fetchone())
    return jsonify(enabled=ok)

@app.post('/api/push/subscribe')
@login_required
def push_subscribe():
    data=_push_json()
    try:
        with get_db() as db:
            subscription_id=webpush.subscribe(db,current_user()['id'],data.get('subscription'))
            audit(db,'webpush_enabled','browser device')
    except ValueError as exc:
        return jsonify(error=str(exc)),400
    return jsonify(ok=True)

@app.post('/api/push/unsubscribe')
@login_required
def push_unsubscribe():
    data=_push_json()
    with get_db() as db:
        webpush.unsubscribe(db,current_user()['id'],data.get('endpoint'))
        audit(db,'webpush_disabled','browser device')
    return jsonify(ok=True)

@app.post('/api/push/test')
@login_required
def push_test():
    data=_push_json()
    try:
        with get_db() as db:
            webpush.queue_test(db,current_user()['id'],data.get('endpoint'))
            audit(db,'webpush_test','browser device')
    except ValueError as exc:
        return jsonify(error=str(exc)),400
    return jsonify(ok=True)

@app.get('/settings')
@login_required
def settings():
    # Editors may manage only financial master data. Security/system controls
    # and their records are exclusive to administrators.
    is_admin = current_user()['role'] == 'admin'
    if current_user()['role'] not in ('admin', 'editor'):
        abort(403)
    with get_db() as db:
        # Shared financial masters: the only data rendered to editors here.
        categories = db.execute('SELECT id,title,kind FROM categories ORDER BY title COLLATE NOCASE').fetchall()
        payees = db.execute('SELECT id,title FROM payees ORDER BY title COLLATE NOCASE').fetchall()
        finance_mode = finance_setting(db, 'finance_mode', 'import')
        _, category_names, _ = category_tree(db)
        # Solely financial balance choices; editors never receive admin account management.
        reconcile_accounts = db.execute('''SELECT a.id,a.title,c.code,c.decimals,c.symbol,s.balance_minor
            FROM accounts a JOIN account_snapshots s ON s.account_id=a.id
            JOIN currencies c ON c.id=a.currency_id
            WHERE s.is_active<>0 AND s.balance_minor IS NOT NULL
            ORDER BY a.title COLLATE NOCASE''').fetchall() if finance_mode == 'web' else ()
        if is_admin:
            clients = db.execute('SELECT id,ip,label,created_at FROM allowed_clients ORDER BY created_at,id').fetchall()
            public_enabled = finance_setting(db, 'public_access_enabled', '0') == '1'
            pending_overwrite = finance_setting(db, 'import_overwrite_pending', '0') == '1'
            approved_overwrite = finance_setting(db, 'import_overwrite_approved', '0') == '1'
            mobile_keys = db.execute('''SELECT m.id,m.label,m.access,m.issued_on,m.expires_on,m.revoked_on,u.username,
                                      datetime(m.expires_on,'unixepoch') expires_label
                                      FROM mobile_api_keys m JOIN users u ON u.id=m.user_id
                                      ORDER BY m.id DESC LIMIT 50''').fetchall()
            users = db.execute('''SELECT id,username,display_name,role,is_active,totp_enabled,created_at
                                  FROM users ORDER BY username COLLATE NOCASE''').fetchall()
            accounts = db.execute('''SELECT a.id,a.title,a.kind,s.is_active FROM accounts a
                                     LEFT JOIN account_snapshots s ON s.account_id=a.id
                                     ORDER BY a.title COLLATE NOCASE''').fetchall()
            currencies = db.execute('SELECT * FROM currencies ORDER BY code').fetchall()
            preferred_currency=finance_setting(db,'default_currency_code','EUR')
            currencies=ordered_currencies(currencies,preferred_currency)
            currency_catalog=sorted(SUPPORTED_CURRENCIES)
            auto_enabled = finance_setting(db, 'auto_import_enabled', '1') == '1'
            web_writes = int(finance_setting(db, 'ledger_web_writes', '0'))
            web_transaction_count = db.execute("SELECT COUNT(*) FROM transactions WHERE origin='web'").fetchone()[0]
            default_account_id = finance_setting(db, 'default_account_id', '')
            default_expense_category_id = shared_default_expense_category(db)
            expense_category_choices = sorted(
                ((cid, name) for cid, name in category_names.items()
                 if any(int(c['id']) == cid and int(c['kind']) == 0 for c in categories)),
                key=lambda item: item[1].casefold())
            daily_backup_enabled = finance_setting(db, 'daily_backup_enabled', '1') == '1'
            financisto_current_backups = current_financisto_backups(Path(DATABASE))
            booking_page_size = finance_setting(db, 'booking_page_size', '30')
            booking_suggestions = booking_suggestion_limit(db)
            wanted_source = finance_setting(db, 'last_import_sha256', '')
            export_source_ready = bool(wanted_source and db.execute(
                'SELECT 1 FROM financisto_export_source WHERE sha256=?',(wanted_source,)).fetchone())
            recurring_export_summary = preview_summary(db)
            background_status = dashboard_status(db, DATABASE)
            notify_config, notify_status, notify_last_sent = notifications.summary(db)
            telegram_book_config = telegram_bookings.config(db)
            # Reconciliation form displays as-of-today account balances, not
            # future-inclusive SQLite snapshots.
            upcoming_for_reconcile = future_account_deltas(db, datetime.now(MONTH_TZ).date().isoformat())
            reconcile_accounts = [dict(row) | {'balance_minor': int(row['balance_minor']) - upcoming_for_reconcile.get(row['id'], 0)}
                                  for row in reconcile_accounts]
            default_account_choices = db.execute('''SELECT a.id,a.title,c.code
                  FROM accounts a JOIN account_snapshots s ON s.account_id=a.id
                  JOIN currencies c ON c.id=a.currency_id
                  WHERE s.is_active <> 0 AND s.balance_minor IS NOT NULL
                  ORDER BY a.title COLLATE NOCASE''').fetchall()
        else:
            # No user lists, PC allowlists, admin config or account management
            # data are fetched or passed to an editor's page.
            clients = users = accounts = currencies = default_account_choices = ()
            mobile_keys = ()
            currency_catalog=()
            preferred_currency='EUR'
            public_enabled = pending_overwrite = approved_overwrite = auto_enabled = False
            web_writes = web_transaction_count = 0
            default_account_id = ''
            default_expense_category_id = 0
            expense_category_choices = ()
            daily_backup_enabled = False
            financisto_current_backups = ()
            booking_page_size = '30'
            booking_suggestions = 20
            export_source_ready = False
            recurring_export_summary = dict(total=0,automatic=0,manual=0,paused=0,removed=0,unsupported=0)
            background_status = None
    return render_template('settings.html', users=users, accounts=accounts,
                           categories=categories, payees=payees, currencies=currencies,
                           category_names=category_names, finance_mode=finance_mode,
                           auto_enabled=auto_enabled, web_writes=web_writes,
                           web_transaction_count=web_transaction_count,
                           default_account_id=default_account_id,
                           default_expense_category_id=default_expense_category_id,
                           expense_category_choices=expense_category_choices,
                           default_account_choices=default_account_choices,
                           preferred_currency=preferred_currency,currency_catalog=currency_catalog,
                           reconcile_accounts=reconcile_accounts,
                           mobile_keys=mobile_keys,
                           public_access=public_enabled, clients=clients,
                           current_ip=verified_ip() if is_admin else None,
                           pending_overwrite=pending_overwrite, approved_overwrite=approved_overwrite,
                           daily_backup_enabled=daily_backup_enabled,
                           booking_page_size=booking_page_size,
                           booking_suggestions=booking_suggestions,
                           export_source_ready=export_source_ready, recurring_export_summary=recurring_export_summary,
                           daily_backup_status=scheduled_backup_status(Path(DATABASE)) if is_admin else {},
                           financisto_current_backups=financisto_current_backups,
                           background_status=background_status,
                           notify_config=(notify_config if is_admin else None),
                           notify_status=(notify_status if is_admin else {}),
                           notify_last_sent=(notify_last_sent if is_admin else None),
                           telegram_book_config=(telegram_book_config if is_admin else None),
                           telegram_categories=())


# --- 1.9.26: a dedicated Telegram bot, direct group polling in notifications container ---
@app.post('/settings/telegram-bookings/save')
@admin_required
def settings_telegram_bookings_save():
    if not csrf_ok(): abort(400)
    raw = request.form
    try:
        enabled=int(raw.get('enabled')=='1')
        ids=telegram_bookings.check_ids(raw.get('permitted_user_ids','')) if enabled else (
            raw.get('permitted_user_ids','').strip() or '')
        chat_id=raw.get('allowed_chat_id','').strip()
        if chat_id:
            chat_id=notifications.check_telegram_chat_id(chat_id)
            if not chat_id.startswith('-'):
                raise ValueError('Bitte eine Telegram-Gruppen-Chat-ID eingeben (negative Zahl).')
        aid=int(raw.get('default_account_id','0') or 0)
        auto=int(raw.get('auto_confirm')=='1')
        with get_db() as db:
            db.execute('BEGIN IMMEDIATE')
            cfg=telegram_bookings.config(db)
            if aid and aid not in {a['id'] for a in telegram_bookings.available_accounts(db)}:
                raise ValueError('Standardkonto ist nicht aktiv.')
            bot_enc=cfg['bot_token_enc']
            new_token=False
            if raw.get('remove_bot_token')=='1':
                bot_enc='';new_token=True
            if raw.get('bot_token','').strip():
                plain=notifications.check_telegram_token(raw.get('bot_token'))
                bot_enc=notifications.encrypt(plain,SECRET)
                new_token=True
            if enabled and (not bot_enc or not chat_id or not aid):
                raise ValueError('Zum Aktivieren Bot-Token, Gruppen-Chat-ID und Standardkonto angeben.')
            activation=(int(time.time()) if (enabled and (
                not cfg['enabled'] or cfg['receive_mode']!='direct' or new_token or
                cfg['allowed_chat_id']!=chat_id)) else int(cfg['activation_epoch'] or 0))
            db.execute('''UPDATE telegram_booking_settings SET enabled=?, receive_mode='direct',
                bot_token_enc=?, allowed_chat_id=?, permitted_user_ids=?,default_account_id=?,
                auto_confirm=?,activation_epoch=?,poll_offset=?,
                updated_at=CURRENT_TIMESTAMP WHERE id=1''',
                (enabled,bot_enc,chat_id,ids,aid,auto,activation,
                 0 if new_token else int(cfg['poll_offset'] or 0)))
            audit(db,'telegram_direct_settings_saved',
                  'Direkte Telegram-Buchungen '+('aktiv' if enabled else 'inaktiv'))
        flash('Telegram-Einstellungen gespeichert. Dein FieLanzen-Bot wird direkt vom Benachrichtigungscontainer empfangen.', 'success')
    except (ValueError,sqlite3.Error) as exc:
        flash('Telegram-Einstellungen nicht gespeichert: '+str(exc),'error')
    return redirect(url_for('settings')+'#telegram-buchungen')


@app.post('/api/telegram-bookings/v1')
def telegram_bridge_v1():
    # Machine-to-machine endpoint; Caddy IP filtering remains in force.
    if request.content_length and request.content_length>4096:
        return jsonify(error='Nachricht zu groß.'),413
    if not request.is_json:
        return jsonify(error='JSON erforderlich.'),415
    token=request.headers.get('X-FieLanzen-Bridge-Key','')
    if len(token)<32 or len(token)>160:
        abort(403)
    try:
        with get_db() as db:
            cfg=telegram_bookings.config(db)
            if not cfg or not cfg['enabled'] or cfg['receive_mode']!='bridge' or not cfg['secret_enc']:
                abort(403)
            try:
                known=notifications.decrypt(cfg['secret_enc'],SECRET)
            except (InvalidToken,ValueError):
                abort(403)
            if not hmac.compare_digest(token,known):
                abort(403)
            data=request.get_json(silent=True)
            if not isinstance(data,dict):
                return jsonify(error='JSON-Objekt erwartet.'),400
            user_id=str(data.get('user_id',''))
            chat_id=str(data.get('chat_id',''))
            if not re.fullmatch(r'[1-9]\d{3,19}',user_id) or chat_id!=user_id:
                return jsonify(error='Nur private Chats mit freigegebenen Benutzern sind erlaubt.'),403
            if user_id not in cfg['permitted_user_ids'].split(','):
                return jsonify(error='Telegram-Benutzer ist nicht freigegeben.'),403
            if finance_setting(db,'finance_mode','import')!='web':
                return jsonify(telegram_bookings.response('Telegram-Buchungen benötigen die aktivierte Web-Datenführung.'))
            db.execute('BEGIN IMMEDIATE')
            if 'callback' in data:
                outcome=telegram_bookings.callback(
                    db,str(data['callback']),chat_id,user_id,mark_finance_edit,
                    entry_payee,apply_balance_delta,notifications,'Telegram '+user_id,
                    pass_through_category_ids)
            else:
                message_id=str(data.get('message_id',''))
                if not re.fullmatch(r'[1-9]\d{0,19}',message_id):
                    raise ValueError('Telegram-Nachrichten-ID fehlt.')
                command=str(data.get('command',''))
                if len(command)>400:
                    raise ValueError('Nachricht zu lang.')
                outcome=telegram_bookings.create(
                    db,command,chat_id,user_id,message_id,
                    datetime.now(MONTH_TZ).date().isoformat(),
                    cfg['default_account_id'],shared_default_expense_category(db))
        return jsonify(outcome)
    except (ValueError,sqlite3.IntegrityError) as exc:
        # Rollback occurs before the error is handled, so no partial booking.
        return jsonify(telegram_bookings.response('⚠️ '+str(exc)))


@app.post('/settings/notifications/save')
@admin_required
def settings_notifications_save():
    if not csrf_ok(): abort(400)
    # Each form saves only its own scope. A blank token always means "keep",
    # so configuring Telegram never requires or rewrites Gotify (and vice versa).
    raw = request.form
    scope = raw.get('scope', '')
    try:
        with get_db() as db:
            db.execute('BEGIN IMMEDIATE')
            cfg = notifications.settings(db)
            if scope == 'general':
                enabled = int(raw.get('enabled') == '1')
                amount = minor_amount(raw.get('threshold',''), 2)
                if amount <= 0:
                    raise ValueError('Der Grenzbetrag muss größer als null sein.')
                if enabled and not (cfg['gotify_enabled'] or cfg['telegram_enabled'] or webpush.has_subscribers(db)):
                    raise ValueError('Bitte Gotify, Telegram oder Web Push auf einem Gerät aktivieren.')
                db.execute('''UPDATE notification_settings SET enabled=?,min_amount_cents=?,
                    updated_at=CURRENT_TIMESTAMP WHERE id=1''', (enabled, amount))
                detail = 'Grenzwert und Hauptschalter'
            elif scope == 'gotify':
                channel_enabled = int(raw.get('gotify_enabled') == '1')
                gotify_url = raw.get('gotify_url', '').strip()
                if gotify_url:
                    gotify_url = notifications.check_gotify_url(gotify_url)
                token = cfg['gotify_token_enc']
                if raw.get('remove_gotify_token') == '1':
                    token = ''
                if raw.get('gotify_token', '').strip():
                    token = notifications.encrypt(raw['gotify_token'].strip(), SECRET)
                priority = int(raw.get('gotify_priority', 5))
                if not 0 <= priority <= 10:
                    raise ValueError('Gotify-Priorität nur zwischen 0 und 10.')
                if channel_enabled and (not gotify_url or not token):
                    raise ValueError('Gotify benötigt HTTPS-URL und App-Token.')
                db.execute('''UPDATE notification_settings SET gotify_enabled=?,gotify_url=?,
                    gotify_token_enc=?,gotify_priority=?,updated_at=CURRENT_TIMESTAMP
                    WHERE id=1''', (channel_enabled, gotify_url, token, priority))
                detail = 'Gotify'
            elif scope == 'telegram':
                channel_enabled = int(raw.get('telegram_enabled') == '1')
                token = cfg['telegram_token_enc']
                if raw.get('remove_telegram_token') == '1':
                    token = ''
                if raw.get('telegram_token', '').strip():
                    plain = notifications.check_telegram_token(raw['telegram_token'])
                    token = notifications.encrypt(plain, SECRET)
                chat_id = raw.get('telegram_chat_id', '').strip()
                if chat_id:
                    chat_id = notifications.check_telegram_chat_id(chat_id)
                if channel_enabled and (not token or not chat_id):
                    raise ValueError('Telegram benötigt Bot-Token und numerische Chat-ID.')
                db.execute('''UPDATE notification_settings SET telegram_enabled=?,
                    telegram_token_enc=?,telegram_chat_id=?,updated_at=CURRENT_TIMESTAMP
                    WHERE id=1''', (channel_enabled,token,chat_id))
                detail = 'Telegram'
            else:
                raise ValueError('Ungültiger Einstellungsbereich.')
            # Deactivating the last channel must not leave misleading "enabled" status.
            latest = notifications.settings(db)
            auto_disabled = False
            if latest['enabled'] and not (latest['gotify_enabled'] or latest['telegram_enabled'] or webpush.has_subscribers(db)):
                db.execute('UPDATE notification_settings SET enabled=0 WHERE id=1')
                auto_disabled = True
            audit(db, 'notification_settings_saved', detail)
        flash(detail + ' gespeichert.' +
              (' Warnungen wurden deaktiviert, weil kein Versandkanal mehr aktiv ist.' if auto_disabled else ''),
              'success')
    except (ValueError,sqlite3.Error) as exc:
        flash('Benachrichtigungen nicht geändert: ' + str(exc), 'error')
    return redirect(url_for('settings') + '#benachrichtigungen')


@app.post('/settings/notifications/test')
@admin_required
def settings_notifications_test():
    if not csrf_ok(): abort(400)
    try:
        with get_db() as db:
            db.execute('BEGIN IMMEDIATE')
            count = notifications.queue_test(db)
            audit(db,'notification_test_queued',f'{count} Versandkanal(e)')
        flash('Testbenachrichtigung eingereiht. Der Versanddienst liefert sie im Hintergrund aus.','success')
    except (ValueError,sqlite3.Error) as exc:
        flash('Test nicht eingereiht: '+str(exc),'error')
    return redirect(url_for('settings')+'#benachrichtigungen')


@app.post('/settings/public-access')
@admin_required
def settings_public_access():
    if not csrf_ok(): abort(400)
    enabled = request.form.get('enabled') == '1'
    phrase = 'OEFFENTLICH' if enabled else 'PRIVAT'
    if request.form.get('confirm', '').strip() != phrase or not verify_admin_stepup():
        flash('Bestätigung, Administratorpasswort und frischer 2FA-Code erforderlich.', 'error')
        return redirect(url_for('settings') + '#zugriff')
    with get_db() as db:
        db.execute('BEGIN IMMEDIATE')
        if enabled:
            enrolled = db.execute("SELECT 1 FROM users WHERE role='admin' AND is_active=1 AND totp_enabled=1 LIMIT 1").fetchone()
            if not enrolled:
                flash('Öffentlicher Zugang nicht erlaubt: kein Administrator mit aktiver 2FA.', 'error')
                return redirect(url_for('settings') + '#zugriff')
        else:
            # Avoid cutting off the administrator's present route immediately.
            current = verified_ip()
            if not current or not db.execute('SELECT 1 FROM allowed_clients WHERE ip=?', (current,)).fetchone():
                flash('Vor dem Deaktivieren bitte die derzeitige Client-IP in PC-Freigaben eintragen, um eine Aussperrung zu verhindern.', 'error')
                return redirect(url_for('settings') + '#zugriff')
        db.execute("INSERT OR REPLACE INTO meta(key,value) VALUES ('public_access_enabled',?)",
                   ('1' if enabled else '0',))
        audit(db, 'public_access_changed', 'on' if enabled else 'off')
    flash('Öffentlicher Login ' + ('freigeschaltet. Prüfe Nginx Proxy Manager und externe Erreichbarkeit separat.' if enabled else 'deaktiviert. Nur freigegebene PCs dürfen sich verbinden.'), 'success')
    return redirect(url_for('settings') + '#zugriff')


@app.post('/settings/users/add')
@admin_required
def settings_add_user():
    if not csrf_ok(): abort(400)
    username = request.form.get('username', '').strip()
    name = request.form.get('display_name', '').strip()[:100]
    role = request.form.get('role', 'viewer')
    password = request.form.get('password', '')
    if not re.fullmatch(r'[A-Za-z0-9._-]{3,40}', username) or not name or role not in ('admin','editor','viewer'):
        flash('Bitte Benutzername, Anzeigename und Rolle prüfen.', 'error')
    elif not 12 <= len(password) <= 256:
        flash('Das neue Passwort muss mindestens 12 und höchstens 256 Zeichen enthalten.', 'error')
    else:
        try:
            with get_db() as db:
                db.execute('INSERT INTO users(username,display_name,role,password_hash,tutorial_completed) VALUES(?,?,?,?,0)',
                           (username, name, role, make_password_hash(password)))
                audit(db, 'user_created', username)
            flash('Benutzer angelegt. Beim ersten Login ist 2FA verpflichtend.', 'success')
        except sqlite3.IntegrityError:
            flash('Der Benutzername ist bereits vergeben.', 'error')
    return redirect(url_for('settings') + '#benutzer')


@app.post('/settings/users/<int:user_id>/toggle')
@admin_required
def settings_toggle_user(user_id):
    if not csrf_ok(): abort(400)
    user = current_user()
    if user['id'] == user_id:
        flash('Das eigene Benutzerkonto kann nicht deaktiviert werden.', 'error')
    else:
        with get_db() as db:
            target = db.execute('SELECT * FROM users WHERE id=?', (user_id,)).fetchone()
            if not target: abort(404)
            if target['role'] == 'admin' and target['is_active'] and db.execute("SELECT COUNT(*) FROM users WHERE role='admin' AND is_active=1").fetchone()[0] <= 1:
                flash('Der letzte aktive Administrator darf nicht deaktiviert werden.', 'error')
            else:
                db.execute('UPDATE users SET is_active=1-is_active,version=version+1 WHERE id=?', (user_id,))
                audit(db, 'user_toggled', target['username'])
                flash('Benutzerstatus geändert.', 'success')
    return redirect(url_for('settings') + '#benutzer')


def verify_admin_stepup():
    """Require both admin password and a fresh TOTP for credential resets."""
    me = current_user()
    password = request.form.get('admin_password', '')
    code = request.form.get('admin_totp', '').strip()
    if not me or me['role'] != 'admin' or not verify_password_hash(password, me['password_hash']):
        return False
    with get_db() as db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT totp_seed_enc,last_totp_step FROM users WHERE id=?', (me['id'],)).fetchone()
        try:
            seed = decrypt_seed(row['totp_seed_enc'], SECRET)
            step = valid_totp_step(seed, code, row['last_totp_step'])
        except (InvalidToken, TypeError, ValueError):
            step = None
        if step is None:
            return False
        db.execute('UPDATE users SET last_totp_step=? WHERE id=?', (step, me['id']))
    return True


@app.post('/settings/users/<int:user_id>/delete')
@admin_required
def settings_delete_user(user_id):
    """Permanently remove a non-self user without touching financial transactions.

    Historic audit entries are kept. An existing browser session is invalidated
    because current_user() checks the user record on every request.
    """
    if not csrf_ok(): abort(400)
    if current_user()['id'] == user_id:
        flash('Das eigene Benutzerkonto kann nicht gelöscht werden.', 'error')
        return redirect(url_for('settings') + '#benutzer')
    expected = request.form.get('confirm_username', '').strip()
    if not expected:
        flash('Zur Löschung bitte den Benutzernamen bestätigen.', 'error')
        return redirect(url_for('settings') + '#benutzer')
    with get_db() as db:
        target = db.execute('SELECT username FROM users WHERE id=?', (user_id,)).fetchone()
    if not target: abort(404)
    if expected != target['username']:
        flash('Bestätigung stimmt nicht mit dem Benutzernamen überein.', 'error')
        return redirect(url_for('settings') + '#benutzer')
    if not verify_admin_stepup():
        flash('Administratorpasswort und frischen 2FA-Code zur Löschung eingeben.', 'error')
        return redirect(url_for('settings') + '#benutzer')
    with get_db() as db:
        db.execute('BEGIN IMMEDIATE')
        target = db.execute('SELECT id,username,role,is_active FROM users WHERE id=?', (user_id,)).fetchone()
        if not target: abort(404)
        if target['username'] != expected:
            flash('Benutzerdaten wurden zwischenzeitlich geändert. Vorgang abgebrochen.', 'error')
            return redirect(url_for('settings') + '#benutzer')
        if target['id'] == current_user()['id']:
            flash('Das eigene Konto darf nicht gelöscht werden.', 'error')
            return redirect(url_for('settings') + '#benutzer')
        if (target['role'] == 'admin' and target['is_active'] and
            db.execute("SELECT COUNT(*) FROM users WHERE role='admin' AND is_active=1").fetchone()[0] <= 1):
            flash('Der letzte aktive Administrator darf nicht gelöscht werden.', 'error')
            return redirect(url_for('settings') + '#benutzer')
        # No financial transaction is deleted. Auth material is purged with the
        # account; historical audit_events remain for traceability.
        db.execute('DELETE FROM recovery_codes WHERE user_id=?', (user_id,))
        db.execute('DELETE FROM recurring_import_previews WHERE user_id=?', (user_id,))
        for sub in db.execute('SELECT id FROM webpush_subscriptions WHERE user_id=?',(user_id,)).fetchall():
            webpush.delete_subscription(db,sub['id'])
        db.execute('DELETE FROM webpush_preferences WHERE user_id=?',(user_id,))
        db.execute('DELETE FROM users WHERE id=?', (user_id,))
        audit(db, 'user_deleted', expected)
    flash('Benutzer dauerhaft gelöscht. Seine bestehenden Sitzungen sind ungültig; Finanzbuchungen bleiben erhalten.', 'success')
    return redirect(url_for('settings') + '#benutzer')


@app.post('/settings/users/<int:user_id>/reset-2fa')
@admin_required
def settings_reset_totp(user_id):
    if not csrf_ok(): abort(400)
    me = current_user()
    if me['id'] == user_id:
        flash('Eigene 2FA nicht über diese Funktion zurücksetzen. Notfallverfahren auf dem Docker-Host verwenden.', 'error')
    elif not verify_admin_stepup():
        flash('Admin-Passwort und einen frischen Authenticator-Code zur Bestätigung eingeben.', 'error')
    else:
        with get_db() as db:
            target = db.execute('SELECT username FROM users WHERE id=?', (user_id,)).fetchone()
            if not target: abort(404)
            db.execute('''UPDATE users SET totp_seed_enc=NULL,totp_enabled=0,
                last_totp_step=-1,version=version+1 WHERE id=?''', (user_id,))
            db.execute('DELETE FROM recovery_codes WHERE user_id=?', (user_id,))
            audit(db, '2fa_reset', target['username'])
        flash('2FA zurückgesetzt: erneute Einrichtung nach Passwortanmeldung erforderlich.', 'success')
    return redirect(url_for('settings') + '#benutzer')


@app.post('/settings/users/<int:user_id>/set-password')
@admin_required
def settings_set_password(user_id):
    if not csrf_ok(): abort(400)
    if current_user()['id'] == user_id:
        flash('Eigene Kennwortänderungen unter „Passwort ändern“ durchführen.', 'error')
    else:
        password = request.form.get('password','')
        if not 12 <= len(password) <= 256:
            flash('Das Passwort muss 12 bis 256 Zeichen enthalten.', 'error')
        elif not verify_admin_stepup():
            flash('Admin-Passwort und einen frischen Authenticator-Code zur Bestätigung eingeben.', 'error')
        else:
            with get_db() as db:
                target = db.execute('SELECT username FROM users WHERE id=?', (user_id,)).fetchone()
                if not target: abort(404)
                db.execute('UPDATE users SET password_hash=?,version=version+1 WHERE id=?',
                           (make_password_hash(password), user_id))
                audit(db, 'password_reset_by_admin', target['username'])
            flash('Passwort geändert. Alle bestehenden Sitzungen dieses Benutzers wurden beendet.', 'success')
    return redirect(url_for('settings') + '#benutzer')


@app.post('/logout')
@login_required
def logout():
    if not csrf_ok(): abort(400)
    session.clear()
    return redirect(url_for('login'))


@app.route('/import', methods=['GET', 'POST'])
@admin_required
def upload():
    if request.method == 'POST':
        if not csrf_ok(): abort(400)
        upload_file = request.files.get('file')
        if not upload_file or not upload_file.filename.lower().endswith('.backup'):
            flash('Bitte eine Financisto-.backup-Datei auswählen.', 'error')
            return redirect(url_for('upload'))
        try:
            content = upload_file.read(30*1024*1024 + 1)
            if len(content) > 30*1024*1024:
                raise BackupError('Datei zu groß (maximal 30 MiB).')
            with get_db() as db:
                mode = finance_setting(db, 'finance_mode', 'import')
                pending = finance_setting(db, 'import_overwrite_pending', '0') == '1'
                writes = int(finance_setting(db, 'ledger_web_writes', '0'))
                approved = finance_setting(db, 'import_overwrite_approved', '0') == '1'
            if mode == 'web':
                records = parse_backup(content)
                flash('Sicherung geprüft: {:,} Buchungen, {} Konten. Keine Daten verändert.'
                      .format(len(records['transactions']), len(records['account'])).replace(',', '.'), 'success')
                return redirect(url_for('upload'))
            destructive = bool(pending or writes)
            if destructive:
                records = parse_backup(content)
                digest = hashlib.sha256(content).hexdigest()
                preview_matches = session.get('manual_import_preview_sha256') == digest
                approved_here = (preview_matches and request.form.get('confirm') == 'UEBERSCHREIBEN'
                                 and request.form.get('risk_ack') == '1')
                if not approved_here:
                    session['manual_import_preview_sha256'] = digest
                    flash('Vorschau erstellt: Bitte dieselbe Sicherung nochmals auswählen und ausdrücklich bestätigen. Noch keine Finanzdaten verändert.', 'success')
                    return render_template('import.html', finance_mode=mode, auto_enabled=False,
                        destructive_pending=True, manual_preview=(len(records['transactions']), len(records['account'])))
                if not verify_admin_stepup():
                    flash('Admin-Passwort und einen neuen 2FA-Code zur Importbestätigung eingeben.', 'error')
                    return render_template('import.html', finance_mode=mode, auto_enabled=False,
                        destructive_pending=True, manual_preview=(len(records['transactions']), len(records['account'])))
                create_data_backup('vor-manuellem-ueberschreiben')
            with get_db() as db:
                db.execute('BEGIN IMMEDIATE')
                result = save_snapshot(db, content, source='manual', allow_destructive=destructive)
            if destructive:
                session.pop('manual_import_preview_sha256', None)
            flash(f'Sicherung erfolgreich importiert: {result["count"]:,} Buchungen.'.replace(',', '.'), 'success')
            return redirect(url_for('dashboard'))
        except (BackupError, ImportPaused, sqlite3.Error, ValueError, OSError) as e:
            flash(f'Import fehlgeschlagen: {e}', 'error')
    with get_db() as db:
        mode = db.execute("SELECT value FROM meta WHERE key='finance_mode'").fetchone()['value']
        enabled = db.execute("SELECT value FROM meta WHERE key='auto_import_enabled'").fetchone()['value'] == '1'
    with get_db() as db:
        pending_import = finance_setting(db,'import_overwrite_pending','0')=='1' or int(finance_setting(db,'ledger_web_writes','0'))>0
    return render_template('import.html', finance_mode=mode, auto_enabled=enabled, destructive_pending=pending_import)


def ym(month, fallback):
    if not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', month):
        return fallback
    return month


def money(n, decimals=2):
    return f'{n:.{decimals}f}'.replace('.', ',') if decimals != 2 else f'{n:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')

app.jinja_env.filters['money'] = money

# Only Financisto data is used for visualizations. Legacy manual data remains archived.
MONTH_TZ = ZoneInfo('Europe/Berlin')


def prev_month(month):
    year, number = map(int, month.split('-'))
    return f'{year - 1:04d}-12' if number == 1 else f'{year:04d}-{number - 1:02d}'


MONTH_NAMES_DE = ('Januar', 'Februar', 'März', 'April', 'Mai', 'Juni',
                  'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember')
MONTH_SHORT_DE = ('Jan', 'Feb', 'Mär', 'Apr', 'Mai', 'Jun',
                  'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez')


def month_label_de(month, short=False):
    """Readable localized names for two-month comparisons, independent of OS locale."""
    year, number = map(int, month.split('-'))
    return f'{(MONTH_SHORT_DE if short else MONTH_NAMES_DE)[number-1]} {year}'


# Legacy household tables are kept in SQLite for non-destructive upgrades.
# There are deliberately no routes to enter or modify a second set of bookings.

# --- 1.9.0: controlled transition from imported snapshots to an editable ledger ---
def finance_setting(db, key, default=''):
    row = db.execute('SELECT value FROM meta WHERE key=?', (key,)).fetchone()
    return row['value'] if row else default


def booking_suggestion_limit(db):
    """Admin-controlled maximum items for both booking autocomplete menus."""
    try:
        count = int(finance_setting(db, 'booking_suggestion_limit', '20'))
    except (ValueError, TypeError):
        return 20
    return max(1, min(100, count))


def shared_default_expense_category(db):
    """Unified expense default. Ignore stale IDs and non-expense categories."""
    raw = finance_setting(db, 'default_expense_category_id', '')
    if not raw.isdigit():
        return 0
    row = db.execute('SELECT id FROM categories WHERE id=? AND kind=0', (int(raw),)).fetchone()
    return int(row['id']) if row else 0


def finance_editor_required(f):
    @wraps(f)
    @login_required
    def wrapped(*args, **kwargs):
        user = current_user()
        if user['role'] not in ('admin', 'editor'):
            abort(403)
        with get_db() as db:
            if finance_setting(db, 'finance_mode', 'import') != 'web':
                abort(403, description='Zuerst die Web-Finanzverwaltung unter Einstellungen aktivieren.')
        return f(*args, **kwargs)
    return wrapped


def mark_finance_edit(db, event, detail=''):
    db.execute('''UPDATE meta SET value=CAST(value AS INTEGER)+1
                  WHERE key='ledger_web_writes' ''')
    audit(db, event, detail)


def minor_amount(text, decimals=2):
    """No floating point and no silent rounding of customer-entered amounts."""
    value = (text or '').strip().replace(' ', '').replace(',', '.')
    if not re.fullmatch(r'\d{1,12}(?:\.\d{1,6})?', value):
        raise ValueError('Bitte einen gültigen positiven Betrag eingeben.')
    amount = Decimal(value) * (10 ** decimals)
    if amount != amount.to_integral_value() or amount <= 0:
        raise ValueError('Betrag hat zu viele Nachkommastellen oder ist 0.')
    if amount > 10 ** 15:
        raise ValueError('Betrag überschreitet das zulässige Limit.')
    return int(amount)


# Supported ISO 4217 codes are a guided selection; each currency is stored
# independently, without silently converting balances across currencies.
SUPPORTED_CURRENCIES = {
    'EUR': ('€',2), 'USD': ('$',2), 'GBP': ('£',2), 'CHF': ('CHF',2),
    'DKK': ('kr',2), 'NOK': ('kr',2), 'SEK': ('kr',2), 'PLN': ('zł',2),
    'CZK': ('Kč',2), 'HUF': ('Ft',2), 'RON': ('lei',2), 'BGN': ('лв',2),
    'ISK': ('kr',0), 'TRY': ('₺',2), 'UAH': ('₴',2), 'RSD': ('din',2),
    'ALL': ('L',2), 'BAM': ('KM',2), 'MKD': ('ден',2),
    'CAD': ('C$',2), 'AUD': ('A$',2), 'NZD': ('NZ$',2), 'JPY': ('¥',0),
    'CNY': ('¥',2), 'HKD': ('HK$',2), 'SGD': ('S$',2), 'KRW': ('₩',0),
    'INR': ('₹',2), 'IDR': ('Rp',2), 'THB': ('฿',2), 'MYR': ('RM',2),
    'PHP': ('₱',2), 'VND': ('₫',0), 'TWD': ('NT$',2),
    'BRL': ('R$',2), 'MXN': ('Mex$',2), 'ARS': ('AR$',2), 'CLP': ('CL$',0),
    'COP': ('Col$',2), 'PEN': ('S/',2), 'ZAR': ('R',2), 'EGP': ('E£',2),
    'MAD': ('د.م.',2), 'NGN': ('₦',2), 'KES': ('KSh',2),
    'AED': ('د.إ',2), 'SAR': ('﷼',2), 'ILS': ('₪',2), 'QAR': ('ر.ق',2),
}


def ordered_currencies(rows, preferred='EUR'):
    return sorted(rows, key=lambda r: (0 if r['code']==preferred else 1, (r['code'] or '').casefold()))


def opening_amount(text, decimals=2):
    raw = (text or '0').strip()
    if raw in ('0','0,00','0.00','+0','-0'):
        return 0
    return (-1 if raw.startswith('-') else 1) * minor_amount(raw.lstrip('+-'), decimals)


def existing_account(db, account_id):
    row = db.execute('''SELECT a.*,s.balance_minor,s.is_active,s.include_in_totals,
                              c.decimals,c.code
                       FROM accounts a JOIN account_snapshots s ON s.account_id=a.id
                       JOIN currencies c ON c.id=a.currency_id
                       WHERE a.id=?''', (account_id,)).fetchone()
    if row is None or row['is_active'] == 0 or row['balance_minor'] is None:
        raise ValueError('Konto ist nicht aktiv oder hat noch keinen bekannten Kontostand.')
    return row


def entry_payee(db, payee_title):
    title = (payee_title or '').strip()
    if not title:
        return 0
    if len(title) > 120:
        raise ValueError('Empfängername zu lang (maximal 120 Zeichen).')
    row = db.execute('SELECT id FROM payees WHERE title=? COLLATE NOCASE', (title,)).fetchone()
    if row:
        return row['id']
    cur = db.execute('INSERT INTO payees(title) VALUES (?)', (title,))
    return cur.lastrowid


@app.post('/settings/booking-page-size')
@admin_required
def settings_booking_page_size():
    if not csrf_ok():
        abort(400)
    size = request.form.get('booking_page_size', '')
    if size not in ('20','30','50','100'):
        abort(400)
    with get_db() as db:
        db.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('booking_page_size',?)", (size,))
        audit(db, 'booking_page_size_changed', size)
    flash('Buchungen pro Seite: ' + size, 'success')
    return redirect(url_for('settings') + '#buchungseinstellungen')


@app.post('/settings/booking-suggestions')
@admin_required
def settings_booking_suggestions():
    if not csrf_ok():
        abort(400)
    raw = request.form.get('booking_suggestion_limit', '').strip()
    if not raw.isascii() or not raw.isdecimal():
        abort(400)
    count = int(raw)
    if not 1 <= count <= 100:
        abort(400)
    with get_db() as db:
        db.execute("INSERT OR REPLACE INTO meta(key,value) VALUES ('booking_suggestion_limit',?)", (str(count),))
        audit(db, 'booking_suggestions_changed', str(count))
    flash(f'Vorschläge für Empfänger und Kategorien: maximal {count}', 'success')
    return redirect(url_for('settings') + '#buchungseinstellungen')


@app.post('/settings/default-account')
@admin_required
def settings_default_account():
    if not csrf_ok(): abort(400)
    value = request.form.get('account_id', '').strip()
    selected_category = request.form.get('default_category_id', '').strip()
    try:
        with get_db() as db:
            db.execute('BEGIN IMMEDIATE')
            if selected_category:
                if not selected_category.isdigit():
                    raise ValueError('Ungültige Standardkategorie.')
                if not db.execute('SELECT 1 FROM categories WHERE id=? AND kind=0',
                                  (int(selected_category),)).fetchone():
                    raise ValueError('Die Standardkategorie muss eine Ausgabenkategorie sein.')
            if value:
                if not value.isdigit():
                    raise ValueError('Ungültige Kontonummer.')
                account = db.execute('''SELECT a.id, s.is_active, s.balance_minor
                                        FROM accounts a
                                        JOIN account_snapshots s ON s.account_id=a.id
                                        WHERE a.id=?''', (int(value),)).fetchone()
                if not account or account['is_active'] == 0 or account['balance_minor'] is None:
                    raise ValueError('Standardkonto muss aktiv sein und einen bekannten Kontostand besitzen.')
            db.execute("INSERT OR REPLACE INTO meta(key,value) VALUES ('default_account_id',?)", (value,))
            db.execute("INSERT OR REPLACE INTO meta(key,value) VALUES ('default_expense_category_id',?)",
                       (selected_category,))
            audit(db, 'booking_defaults_changed',
                  'account='+ (value or 'none') + ';category='+ (selected_category or 'none'))
        flash('Standardkonto und Standardkategorie gespeichert.', 'success')
    except (ValueError,sqlite3.Error) as exc:
        flash('Buchungsvorgaben nicht geändert: ' + str(exc), 'error')
    return redirect(url_for('settings') + '#standardkonto')


@app.post('/settings/auto-import')
@admin_required
def settings_auto_import():
    if not csrf_ok(): abort(400)
    enabled = request.form.get('enabled') == '1'
    with get_db() as db:
        mode = finance_setting(db, 'finance_mode', 'import')
        writes = int(finance_setting(db, 'ledger_web_writes', '0'))
        pending = finance_setting(db,'import_overwrite_pending','0') == '1'
        if enabled and mode != 'import':
            flash('Automatischer Import bleibt im Web-Modus deaktiviert.', 'error')
            return redirect(url_for('settings') + '#datenfuehrung')
    backup = None
    if enabled and (writes or pending):
        if (request.form.get('confirm') != 'UEBERSCHREIBEN' or
                request.form.get('risk_ack') != '1' or not verify_admin_stepup()):
            flash('Vor möglichem Überschreiben: Datenverlust bestätigen, UEBERSCHREIBEN eingeben, Passwort und frischen 2FA-Code angeben.', 'error')
            return redirect(url_for('settings') + '#datenfuehrung')
        try:
            backup = create_data_backup('vor-auto-import-ueberschreiben')
        except (OSError,sqlite3.Error) as exc:
            flash('Import bleibt aus: Sicherung fehlgeschlagen: '+str(exc),'error')
            return redirect(url_for('settings') + '#datenfuehrung')
    with get_db() as db:
        db.execute('BEGIN IMMEDIATE')
        if finance_setting(db,'finance_mode','import') != 'import' and enabled:
            flash('Datenführung inzwischen geändert, Import nicht aktiviert.', 'error')
        else:
            db.execute("INSERT OR REPLACE INTO meta(key,value) VALUES ('auto_import_enabled',?)",
                       ('1' if enabled else '0',))
            if backup:
                db.execute("INSERT OR REPLACE INTO meta(key,value) VALUES ('import_overwrite_approved','1')")
            audit(db,'automatic_import_changed', ('on' if enabled else 'off') + (' destructive approval' if backup else ''))
            flash('Automatischer Import '+('aktiviert.' if enabled else 'deaktiviert.')+
                  (' Sicherung: '+backup.name if backup else ''), 'success')
    return redirect(url_for('settings') + '#datenfuehrung')


def create_data_backup(label):
    # Verified, crash-consistent SQLite snapshot shared with scheduled backup service.
    return create_verified_backup(Path(DATABASE), label)


@app.post('/settings/backup/schedule')
@admin_required
def settings_backup_schedule():
    if not csrf_ok(): abort(400)
    enabled = request.form.get('enabled') == '1'
    # Disabling every automated database backup warrants step-up authentication.
    if not enabled and not verify_admin_stepup():
        flash('Zum Ausschalten der täglichen Sicherung Admin-Passwort und frischen 2FA-Code bestätigen.', 'error')
        return redirect(url_for('settings') + '#datensicherung')
    with get_db() as db:
        db.execute("INSERT OR REPLACE INTO meta(key,value) VALUES ('daily_backup_enabled',?)",
                   ('1' if enabled else '0',))
        audit(db, 'daily_backup_changed', 'on' if enabled else 'off')
    flash('Tägliche SQLite-Sicherungen ' + ('aktiviert.' if enabled else 'deaktiviert.'), 'success')
    return redirect(url_for('settings') + '#datensicherung')


@app.post('/settings/backup/create')
@admin_required
def settings_create_backup():
    if not csrf_ok(): abort(400)
    # Both backups are independent. A failed export must never be reported as
    # successful, and must not suppress the completed SQLite snapshot.
    try:
        path = create_verified_backup(Path(DATABASE), 'manuell')
        with get_db() as db:
            audit(db, 'sqlite_backup_created', path.name)
        flash('SQLite-Sicherung erstellt: ' + path.name, 'success')
    except (OSError, sqlite3.Error, RuntimeError) as exc:
        flash('SQLite-Sicherung fehlgeschlagen: ' + str(exc), 'error')
    try:
        export_current_financisto(Path(DATABASE), force=True)
        backups = current_financisto_backups(Path(DATABASE))
        if not backups:
            raise RuntimeError('Keine aktuelle Financisto-Backup-Datei gefunden.')
        filename = backups[0]['name']
        with get_db() as db:
            audit(db, 'financisto_snapshot_created', filename)
        flash('Financisto-Sicherung erstellt: ' + filename, 'success')
    except (ExportError, BackupError, OSError, sqlite3.Error, ValueError, RuntimeError) as exc:
        flash('Financisto-Sicherung fehlgeschlagen: ' + str(exc), 'error')
    return redirect(url_for('settings') + '#datensicherung')

@app.post('/settings/switch-to-web')
@admin_required
def settings_switch_to_web():
    if not csrf_ok(): abort(400)
    if request.form.get('confirm') != 'WEB' or not verify_admin_stepup():
        flash('Bitte WEB eingeben sowie Admin-Passwort und einen frischen TOTP-Code bestätigen.', 'error')
        return redirect(url_for('settings') + '#datenfuehrung')
    with get_db() as db:
        if finance_setting(db, 'finance_mode', 'import') != 'import':
            flash('Die Web-Finanzverwaltung ist bereits führend.', 'success')
            return redirect(url_for('settings') + '#datenfuehrung')
    try:
        backup = create_data_backup('vor-web-umstellung')
    except (OSError, sqlite3.Error) as exc:
        flash(f'Umstellung abgebrochen: Datenbanksicherung fehlgeschlagen ({exc}).', 'error')
        return redirect(url_for('settings') + '#datenfuehrung')
    with get_db() as db:
        db.execute('BEGIN IMMEDIATE')
        if finance_setting(db, 'finance_mode', 'import') != 'import':
            flash('Zwischenzeitlich umgestellt. Keine weiteren Änderungen.', 'error')
        else:
            db.execute("UPDATE meta SET value='web' WHERE key='finance_mode'")
            db.execute("UPDATE meta SET value='0' WHERE key='auto_import_enabled'")
            db.execute("INSERT OR REPLACE INTO meta(key,value) VALUES ('import_overwrite_pending','0')")
            db.execute("INSERT OR REPLACE INTO meta(key,value) VALUES ('import_overwrite_approved','0')")
            audit(db, 'web_ledger_activated', backup.name)
            flash('Web-Finanzverwaltung aktiviert, Auto-Import gestoppt. Sicherung: ' + backup.name, 'success')
    return redirect(url_for('settings') + '#datenfuehrung')


@app.post('/settings/switch-to-import')
@admin_required
def settings_switch_to_import():
    if not csrf_ok(): abort(400)
    if request.form.get('confirm') != 'FINANCISTO':
        flash('Zur Rückschaltung FINANCISTO als Bestätigung eingeben.', 'error')
        return redirect(url_for('settings') + '#datenfuehrung')
    with get_db() as db:
        if finance_setting(db,'finance_mode','import')!='web':
            flash('Financisto ist bereits führend.', 'success')
            return redirect(url_for('settings') + '#datenfuehrung')
        writes = int(finance_setting(db, 'ledger_web_writes', '0'))
        origin_count = db.execute("SELECT COUNT(*) FROM transactions WHERE origin='web'").fetchone()[0]
    risk = bool(writes or origin_count)
    if risk and (request.form.get('risk_ack') != '1' or
                 request.form.get('loss_confirm', '').strip() != 'DATENVERLUST'):
        flash('Es liegen Web-Änderungen vor. Bitte Datenverlust ausdrücklich bestätigen und DATENVERLUST eingeben.', 'error')
        return redirect(url_for('settings') + '#datenfuehrung')
    if not verify_admin_stepup():
        flash('Admin-Passwort und frischen 2FA-Code prüfen.', 'error')
        return redirect(url_for('settings') + '#datenfuehrung')
    try:
        backup = create_data_backup('vor-rueckschaltung-financisto')
    except (OSError,sqlite3.Error) as exc:
        flash('Rückschaltung abgebrochen: SQLite-Sicherung fehlgeschlagen: ' + str(exc), 'error')
        return redirect(url_for('settings') + '#datenfuehrung')
    with get_db() as db:
        db.execute('BEGIN IMMEDIATE')
        if finance_setting(db,'finance_mode','import')!='web':
            flash('Datenführung wurde zwischenzeitlich geändert. Keine Rückschaltung.', 'error')
        else:
            # Web transactions stay untouched here. Only a later explicitly approved
            # full import can replace them; until then the importer remains OFF.
            writes = int(finance_setting(db,'ledger_web_writes','0'))
            count = db.execute("SELECT COUNT(*) FROM transactions WHERE origin='web'").fetchone()[0]
            if (writes or count) and not risk:
                flash('Zwischenzeitlich sind neue Änderungen hinzugekommen. Bitte erneut bestätigen.', 'error')
            else:
                db.execute("UPDATE meta SET value='import' WHERE key='finance_mode'")
                # Never surprise-post old rules after a later switch back to Web.
                db.execute("UPDATE recurring_rules SET active=0,auto_post=0 WHERE active=1")
                db.execute("UPDATE meta SET value='0' WHERE key='auto_import_enabled'")
                db.execute("INSERT OR REPLACE INTO meta(key,value) VALUES ('import_overwrite_pending',?)",
                           ('1' if writes or count else '0',))
                db.execute("INSERT OR REPLACE INTO meta(key,value) VALUES ('import_overwrite_approved','0')")
                audit(db,'financisto_authority_restored', backup.name + (' (web changes)' if writes or count else ''))
                flash('Financisto wieder führend. Keine Web-Buchung wurde bei der Rückschaltung gelöscht. Auto-Import bleibt aus. Sicherung: '+backup.name, 'success')
    return redirect(url_for('settings') + '#datenfuehrung')


@app.get('/settings/backup/financisto/<name>')
@admin_required
def settings_download_financisto_snapshot(name):
    # The allowlist comes from the two newest app-generated snapshots only.
    permitted = {entry['name'] for entry in current_financisto_backups(Path(DATABASE))}
    if name not in permitted:
        abort(404)
    directory = financisto_export_dir(Path(DATABASE), create=False)
    if directory is None:
        abort(404)
    path = directory / name
    if path.is_symlink() or not path.is_file():
        abort(404)
    response = send_file(path, as_attachment=True, download_name=name,
                         mimetype='application/octet-stream', max_age=0,
                         conditional=False)
    response.headers['Cache-Control'] = 'private, no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


@app.get('/settings/backup/download')
@admin_required
def settings_download_backup():
    # SQLite backup through its API, never a raw copy of a live database/WAL.
    with sqlite3.connect(DATABASE) as source:
        with sqlite3.connect(':memory:') as destination:
            source.backup(destination)
            content = destination.serialize()
    return send_file(BytesIO(content), as_attachment=True,
                     download_name='financisto-dashboard-' + date.today().isoformat() + '.sqlite3',
                     mimetype='application/vnd.sqlite3', max_age=0)


@app.post('/settings/export-financisto')
@admin_required
def settings_export_financisto():
    # An experimental OFFLINE return file; never alters the ledger or Android.
    if not csrf_ok(): abort(400)
    if not verify_admin_stepup():
        flash('Für den Export bitte Administratorpasswort und einen frischen 2FA-Code verwenden.', 'error')
        return redirect(url_for('settings')+'#financisto-export')
    try:
        with get_db() as db:
            db.execute('BEGIN')
            raw, stats=make_export(db)
            # Recurring schedules are optional and explicitly selected. The
            # legacy export path is unchanged when the checkbox is empty.
            if request.form.get('include_recurring') == '1':
                raw, stats = merge_recurring_export(db,raw,stats)
            # Close the read transaction before returning the attachment.
        with get_db() as audit_db:
            audit(audit_db, 'financisto_test_export_downloaded', f"{stats['transactions']} bookings; recurring={stats.get('recurring_exported', 'not selected')}")
        filename='financisto-testexport-'+date.today().strftime('%Y%m%d')+'.backup'
        return send_file(BytesIO(raw), as_attachment=True, download_name=filename,
                         mimetype='application/octet-stream',max_age=0)
    except (ExportError,BackupError,sqlite3.Error,ValueError) as exc:
        flash('Financisto-Testexport nicht möglich: '+str(exc),'error')
        return redirect(url_for('settings')+'#financisto-export')


@app.post('/settings/export-source')
@admin_required
def settings_upload_export_source():
    # Store a missing exact-match original in SQLite; no financial data import.
    if not csrf_ok(): abort(400)
    if not verify_admin_stepup():
        flash('Administratorpasswort und frischen 2FA-Code bestätigen.', 'error')
        return redirect(url_for('settings')+'#financisto-export')
    upload=request.files.get('export_source')
    if not upload or not upload.filename.lower().endswith('.backup'):
        flash('Bitte die zuletzt importierte Original-.backup-Datei auswählen.', 'error')
        return redirect(url_for('settings')+'#financisto-export')
    raw=upload.read(30*1024*1024+1)
    if len(raw)>30*1024*1024:
        flash('Die Sicherung überschreitet die maximal zulässige Größe.', 'error')
        return redirect(url_for('settings')+'#financisto-export')
    try:
        with get_db() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute("SELECT value FROM meta WHERE key='last_import_sha256'").fetchone()
            if not row or not row[0]:
                raise ExportError('Es gibt noch keinen importierten Originalstand.')
            store_matching_source(db,raw,sha256=row[0])
            audit(db,'financisto_export_source_stored','SHA256-matched original')
        flash('Die exakt passende Original-Sicherung ist nun für den Rückexport gesichert. Finanzbuchungen unverändert.', 'success')
    except (ExportError,BackupError,sqlite3.Error,ValueError) as exc:
        flash('Originaldatei wurde nicht übernommen: '+str(exc),'error')
    return redirect(url_for('settings')+'#financisto-export')


@app.post('/settings/payees/save')
@finance_editor_required
def settings_save_payee():
    if not csrf_ok(): abort(400)
    title = request.form.get('title', '').strip()
    payee_id = request.form.get('id', '').strip()
    if not title or len(title) > 120:
        flash('Empfängername muss 1 bis 120 Zeichen enthalten.', 'error')
    else:
        try:
            with get_db() as db:
                db.execute('BEGIN IMMEDIATE')
                if db.execute('SELECT id FROM payees WHERE title=? COLLATE NOCASE AND id<>?',
                              (title, int(payee_id) if payee_id.isdigit() else -1)).fetchone():
                    raise ValueError('Dieser Empfänger existiert bereits.')
                if payee_id.isdigit():
                    if not db.execute('UPDATE payees SET title=? WHERE id=?', (title, int(payee_id))).rowcount:
                        abort(404)
                else:
                    db.execute('INSERT INTO payees(title) VALUES (?)', (title,))
                mark_finance_edit(db, 'payee_saved', title)
            flash('Empfänger gespeichert.', 'success')
        except ValueError as exc:
            flash(str(exc), 'error')
    return redirect(url_for('settings') + '#stammdaten')


@app.post('/settings/categories/save')
@finance_editor_required
def settings_save_category():
    if not csrf_ok(): abort(400)
    title = request.form.get('title','').strip()
    category_id = request.form.get('id','').strip()
    parent_id = request.form.get('parent_id','').strip()
    if not title or len(title)>100:
        flash('Kategorie muss 1 bis 100 Zeichen enthalten.', 'error')
        return redirect(url_for('settings') + '#stammdaten')
    try:
        with get_db() as db:
            db.execute('BEGIN IMMEDIATE')
            if category_id.isdigit():
                if not db.execute('UPDATE categories SET title=? WHERE id=?', (title,int(category_id))).rowcount:
                    abort(404)
            else:
                if parent_id:
                    parent = db.execute('SELECT * FROM categories WHERE id=?', (int(parent_id),)).fetchone()
                    if not parent: raise ValueError('Übergeordnete Kategorie nicht gefunden.')
                    right = parent['rgt']
                    db.execute('UPDATE categories SET rgt=rgt+2 WHERE rgt>=?', (right,))
                    db.execute('UPDATE categories SET lft=lft+2 WHERE lft>=?', (right,))
                    kind = parent['kind']
                    left, right = right, right+1
                else:
                    last = db.execute('SELECT MAX(rgt) FROM categories').fetchone()[0] or 0
                    left, right, kind = last+1, last+2, 0
                db.execute('INSERT INTO categories(title,lft,rgt,kind) VALUES (?,?,?,?)',
                           (title,left,right,kind))
            mark_finance_edit(db,'category_saved',title)
        flash('Kategorie gespeichert.', 'success')
    except (ValueError,sqlite3.Error) as exc:
        flash('Kategorie nicht geändert: ' + str(exc), 'error')
    return redirect(url_for('settings') + '#stammdaten')


@app.post('/settings/accounts/save')
@admin_required
def settings_save_account():
    if not csrf_ok(): abort(400)
    with get_db() as db:
        if finance_setting(db,'finance_mode','import')!='web':
            abort(403)
    title = request.form.get('title','').strip()
    account_id = request.form.get('id','').strip()
    if not title or len(title)>100:
        flash('Kontoname muss 1 bis 100 Zeichen enthalten.', 'error')
        return redirect(url_for('settings') + '#stammdaten')
    try:
        with get_db() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT id FROM accounts WHERE title=? COLLATE NOCASE AND id<>?',
                          (title,int(account_id) if account_id.isdigit() else -1)).fetchone():
                raise ValueError('Kontoname existiert bereits.')
            if account_id.isdigit():
                if not db.execute('UPDATE accounts SET title=? WHERE id=?', (title,int(account_id))).rowcount:
                    abort(404)
            else:
                currency_id = int(request.form.get('currency_id',''))
                currency = db.execute('SELECT decimals FROM currencies WHERE id=?',(currency_id,)).fetchone()
                if not currency: raise ValueError('Währung nicht gefunden.')
                opening = opening_amount(request.form.get('opening_balance','0'), int(currency['decimals']))
                cur = db.execute('INSERT INTO accounts(title,currency_id,kind) VALUES (?,?,?)',
                                 (title,currency_id,'CASH'))
                db.execute('''INSERT INTO account_snapshots(account_id,balance_minor,include_in_totals,is_active)
                              VALUES (?,?,1,1)''', (cur.lastrowid,opening))
            mark_finance_edit(db,'account_saved',title)
        flash('Konto gespeichert.', 'success')
    except (ValueError,sqlite3.Error) as exc:
        flash('Konto nicht geändert: '+str(exc),'error')
    return redirect(url_for('settings') + '#stammdaten')


@app.post('/settings/currency/new')
@admin_required
def settings_create_currency():
    if not csrf_ok(): abort(400)
    code=request.form.get('code','').strip().upper()
    if code not in SUPPORTED_CURRENCIES:
        flash('Währung nicht unterstützt. Bitte einen der aufgeführten ISO-Codes wählen.','error')
        return redirect(url_for('settings')+'#stammdaten')
    try:
        with get_db() as db:
            db.execute('BEGIN IMMEDIATE')
            if finance_setting(db,'finance_mode','import')!='web': abort(403)
            if db.execute('SELECT 1 FROM currencies WHERE code=? COLLATE NOCASE',(code,)).fetchone():
                raise ValueError('Diese Währung ist bereits vorhanden.')
            symbol,decimals=SUPPORTED_CURRENCIES[code]
            db.execute('INSERT INTO currencies(code,symbol,decimals) VALUES (?,?,?)',(code,symbol,decimals))
            mark_finance_edit(db,'currency_created',code)
        flash('Währung '+code+' hinzugefügt. Konten können jetzt in dieser Währung angelegt werden.','success')
    except (ValueError,sqlite3.Error) as exc:
        flash('Währung nicht angelegt: '+str(exc),'error')
    return redirect(url_for('settings')+'#stammdaten')


@app.post('/settings/default-currency')
@admin_required
def settings_default_currency():
    if not csrf_ok(): abort(400)
    code=request.form.get('currency_code','').strip().upper()
    try:
        with get_db() as db:
            db.execute('BEGIN IMMEDIATE')
            if not db.execute('SELECT 1 FROM currencies WHERE code=?',(code,)).fetchone():
                raise ValueError('Standardwährung muss zuvor angelegt sein.')
            db.execute("INSERT OR REPLACE INTO meta(key,value) VALUES ('default_currency_code',?)",(code,))
            audit(db,'default_currency_changed',code)
        flash('Standardwährung auf '+code+' gesetzt.','success')
    except (ValueError,sqlite3.Error) as exc:
        flash('Standardwährung nicht geändert: '+str(exc),'error')
    return redirect(url_for('settings')+'#stammdaten')


@app.post('/settings/accounts/reconcile')
@finance_editor_required
def settings_reconcile_account():
    if not csrf_ok(): abort(400)
    # A fixed destination prevents open redirects from form fields.
    source = request.form.get('return_to', 'settings')
    if source not in ('settings', 'dashboard'): abort(400)
    destination = (url_for('dashboard') + '#kontostaende' if source == 'dashboard'
                   else url_for('settings') + '#kontostand-abgleichen')
    account_id = request.form.get('account_id', '').strip()
    if not account_id.isdigit(): abort(400)
    try:
        with get_db() as db:
            db.execute('BEGIN IMMEDIATE')
            if finance_setting(db, 'finance_mode', 'import') != 'web': abort(403)
            account = existing_account(db, int(account_id))
            if not request.form.get('actual_balance', '').strip():
                raise ValueError('Bitte den tatsächlichen Kontostand eingeben.')
            actual = opening_amount(request.form.get('actual_balance', ''), int(account['decimals']))
            # A current bank statement excludes future-dated ledger entries;
            # compensate the projected SQLite snapshot when reconciling today.
            ahead = future_account_deltas(db, datetime.now(MONTH_TZ).date().isoformat()).get(int(account_id), 0)
            effective = int(account['balance_minor']) - ahead
            change = actual - effective
            if not change:
                flash('Kontostand bereits korrekt – keine Buchung angelegt.', 'success')
                return redirect(destination)
            # Single correction type for every account, including cash and depots.
            # Existing historical depot categories remain recognized as adjustments.
            action = 'income' if change > 0 else 'expense'
            title, kind = ADJUSTMENT_CATEGORIES[('reconciliation', action)]
            found = db.execute('SELECT id FROM categories WHERE title=? COLLATE NOCASE AND kind=?',
                               (title, kind)).fetchone()
            category_id = int(found['id']) if found else insert_category(db, title, kind)
            note = request.form.get('note', '').strip()[:500] or 'Kontostand abgeglichen'
            today = datetime.now(MONTH_TZ).date().isoformat()
            row = dict(day=today, account_id=int(account_id), to_account_id=0, category_id=category_id,
                       payee_id=0, amount=change, note=note, is_template=0)
            db.execute("""INSERT INTO transactions
                      (day,account_id,to_account_id,category_id,payee_id,amount,note,is_template,origin)
                      VALUES (:day,:account_id,:to_account_id,:category_id,:payee_id,:amount,:note,:is_template,'web')""", row)
            apply_balance_delta(db, row, +1)
            final = db.execute('SELECT balance_minor FROM account_snapshots WHERE account_id=?',
                               (int(account_id),)).fetchone()[0]
            if final != actual + ahead: raise ValueError('Saldoabgleich konnte nicht verifiziert werden.')
            mark_finance_edit(db, 'account_reconciled', f'{account_id}: {change:+d} {account["code"]}')
        flash('Saldoabgleich als eigene Buchung erfasst. Der Kontostand wurde auf den eingegebenen Wert gesetzt.', 'success')
    except (ValueError, sqlite3.Error) as exc:
        flash('Kontostand nicht geändert: ' + str(exc), 'error')
    return redirect(destination)


@app.post('/settings/accounts/<int:account_id>/toggle')
@admin_required
def settings_toggle_account(account_id):
    if not csrf_ok(): abort(400)
    with get_db() as db:
        db.execute('BEGIN IMMEDIATE')
        if finance_setting(db,'finance_mode','import') != 'web': abort(403)
        row=db.execute('SELECT is_active FROM account_snapshots WHERE account_id=?',(account_id,)).fetchone()
        if not row: abort(404)
        current=1 if row['is_active'] is None else int(row['is_active'])
        db.execute('UPDATE account_snapshots SET is_active=? WHERE account_id=?',
                   (0 if current else 1,account_id))
        mark_finance_edit(db,'account_toggled',str(account_id))
    flash('Kontostatus angepasst. Inaktive Konten bleiben in der Historie sichtbar.','success')
    return redirect(url_for('settings') + '#stammdaten')


@app.post('/settings/master/delete')
@login_required
def settings_delete_master():
    # Editors can delete UNUSED payees/categories only. Account deletion is
    # explicitly administrator-only, enforced by the server, not just the UI.
    user_role = current_user()['role']
    if user_role not in ('admin', 'editor'): abort(403)
    if not csrf_ok(): abort(400)
    group = request.form.get('group','')
    value = request.form.get('id','')
    if group not in ('payees','categories','accounts') or not value.isdigit():
        abort(400)
    if group == 'accounts' and user_role != 'admin': abort(403)
    with get_db() as db:
        if finance_setting(db,'finance_mode','import')!='web': abort(403)
    n=int(value)
    try:
        with get_db() as db:
            db.execute('BEGIN IMMEDIATE')
            if group=='payees':
                if db.execute('SELECT 1 FROM transactions WHERE payee_id=? LIMIT 1',(n,)).fetchone():
                    raise ValueError('Empfänger hat Buchungen; bitte zuerst zusammenführen.')
            elif group=='categories':
                cat=db.execute('SELECT lft,rgt FROM categories WHERE id=?',(n,)).fetchone()
                if not cat: abort(404)
                if cat['rgt'] != cat['lft']+1:
                    raise ValueError('Kategorie hat Unterkategorien.')
                if db.execute('SELECT 1 FROM transactions WHERE category_id=? LIMIT 1',(n,)).fetchone():
                    raise ValueError('Kategorie wird noch in Buchungen verwendet.')
            elif group=='accounts':
                if db.execute('''SELECT 1 FROM transactions WHERE account_id=? OR to_account_id=? LIMIT 1''',(n,n)).fetchone():
                    raise ValueError('Konto hat Buchungen und darf nicht gelöscht werden.')
                snap=db.execute('SELECT balance_minor FROM account_snapshots WHERE account_id=?',(n,)).fetchone()
                if snap and snap['balance_minor'] != 0:
                    raise ValueError('Konto mit Restguthaben darf nicht gelöscht werden.')
                db.execute('DELETE FROM account_snapshots WHERE account_id=?',(n,))
            if not db.execute('DELETE FROM '+group+' WHERE id=?',(n,)).rowcount:
                abort(404)
            if group=='categories':
                db.execute('UPDATE categories SET lft=lft-2 WHERE lft>?',(cat['rgt'],))
                db.execute('UPDATE categories SET rgt=rgt-2 WHERE rgt>?',(cat['rgt'],))
            mark_finance_edit(db,'master_deleted',group+':'+str(n))
        flash('Unbenutzter Eintrag gelöscht.', 'success')
    except (ValueError,sqlite3.Error) as exc:
        flash('Löschen nicht möglich: '+str(exc),'error')
    return redirect(url_for('settings')+'#stammdaten')


# Eine gewöhnliche Financisto-Kategorie bleibt auch nach Export und erneutem
# Import erhalten. Ihre Buchungen ändern den Kontostand, zählen hier jedoch
# weder als Haushalts-Einnahme noch als Haushalts-Ausgabe.
# Financisto trennt Kategorien nach type: 0=Ausgabe, 1=Einnahme.
# Daher zwei eigene Kategorien. Ihr Name bleibt beim Backup-Rundlauf erhalten.
PASS_THROUGH_CATEGORIES = {
    'expense': ('Durchlaufender Posten (Ausgabe)', 0),
    'income': ('Durchlaufender Posten (Eingang)', 1),
}
ADJUSTMENT_CATEGORIES = {
    ('reconciliation','income'): ('Kontostandskorrektur (Zugang)', 1),
    ('reconciliation','expense'): ('Kontostandskorrektur (Abgang)', 0),
    ('valuation','income'): ('Depot-Wertanpassung (Zugang)', 1),
    ('valuation','expense'): ('Depot-Wertanpassung (Abgang)', 0),
}


def adjustment_category_ids(db):
    rows=db.execute('SELECT id,title,lft,rgt FROM categories').fetchall()
    names={v[0].casefold() for v in ADJUSTMENT_CATEGORIES.values()}
    roots=[r for r in rows if r['title'].strip().casefold() in names]
    return {r['id'] for r in rows if any(r['lft']>=root['lft'] and r['rgt']<=root['rgt'] for root in roots)}



def pass_through_category_ids(db):
    """Both ordinary Financisto categories and all their descendants."""
    rows = db.execute('SELECT id,title,lft,rgt FROM categories').fetchall()
    names = {v[0].casefold() for v in PASS_THROUGH_CATEGORIES.values()} | {v[0].casefold() for v in ADJUSTMENT_CATEGORIES.values()}
    roots = [r for r in rows if r['title'].strip().casefold() in names]
    result = {r['id'] for r in roots}
    for r in rows:
        if any(root['lft'] is not None and root['rgt'] is not None and
               r['lft'] is not None and r['rgt'] is not None and
               r['lft'] >= root['lft'] and r['rgt'] <= root['rgt'] for root in roots):
            result.add(r['id'])
    return result


def ensure_pass_through_category(db, action):
    """Create an Android-compatible income or expense category when needed."""
    title, kind = PASS_THROUGH_CATEGORIES[action]
    found = db.execute('SELECT id FROM categories WHERE title=? COLLATE NOCASE AND kind=? LIMIT 1',
                       (title, kind)).fetchone()
    if found:
        return int(found['id'])
    # Defensive: don't invent a duplicate category with the same name and
    # another type; that would be ambiguous on Android.
    if db.execute('SELECT 1 FROM categories WHERE title=? COLLATE NOCASE', (title,)).fetchone():
        raise ValueError('Kategorie für durchlaufende Posten existiert mit falscher Art.')
    last = db.execute('SELECT MAX(rgt) FROM categories').fetchone()[0] or 0
    cur = db.execute('INSERT INTO categories(title,lft,rgt,kind) VALUES (?,?,?,?)',
                     (title, last + 1, last + 2, kind))
    return cur.lastrowid


def insert_category(db, title, kind, parent_id=None):
    if parent_id is not None:
        parent=db.execute('SELECT * FROM categories WHERE id=?',(parent_id,)).fetchone()
        if not parent: raise ValueError('Übergeordnete Kategorie existiert nicht.')
        if int(parent['kind']) != kind: raise ValueError('Unterkategorie muss zur Einnahmen- bzw. Ausgabenart passen.')
        right=int(parent['rgt'])
        db.execute('UPDATE categories SET rgt=rgt+2 WHERE rgt>=?',(right,))
        db.execute('UPDATE categories SET lft=lft+2 WHERE lft>=?',(right,))
        left,right=right,right+1
    else:
        last=db.execute('SELECT MAX(rgt) FROM categories').fetchone()[0] or 0
        left,right=last+1,last+2
    return db.execute('INSERT INTO categories(title,lft,rgt,kind) VALUES (?,?,?,?)',
                      (title,left,right,kind)).lastrowid


@app.post('/buchungen/kategorien/neu')
@finance_editor_required
def booking_new_category():
    if not csrf_ok(): abort(400)
    title=request.form.get('title','').strip()
    action=request.form.get('kind','expense')
    parent=request.form.get('parent_id','').strip()
    if not title or len(title)>100 or action not in ('income','expense'):
        return jsonify(error='Kategorie oder Buchungsart ungültig.'),400
    if parent and not parent.isdigit():
        return jsonify(error='Übergeordnete Kategorie ungültig.'),400
    kind=1 if action=='income' else 0
    try:
        with get_db() as db:
            db.execute('BEGIN IMMEDIATE')
            p=int(parent) if parent else None
            if p is not None:
                existing_parent=db.execute('SELECT lft,rgt FROM categories WHERE id=?',(p,)).fetchone()
                if not existing_parent: raise ValueError('Übergeordnete Kategorie nicht gefunden.')
                # Duplicate category names within one parent cause ambiguous selection.
                sibling=db.execute("""SELECT 1 FROM categories WHERE title=? COLLATE NOCASE AND kind=?
                    AND lft>? AND rgt<? AND NOT EXISTS (
                      SELECT 1 FROM categories parent_cat WHERE parent_cat.lft>?
                      AND parent_cat.rgt<? AND parent_cat.lft<categories.lft
                      AND parent_cat.rgt>categories.rgt) LIMIT 1""",
                      (title,kind,existing_parent['lft'],existing_parent['rgt'],
                       existing_parent['lft'],existing_parent['rgt'])).fetchone()
                if sibling: raise ValueError('Diese Unterkategorie existiert bereits.')
            elif db.execute('SELECT 1 FROM categories WHERE title=? COLLATE NOCASE AND kind=? LIMIT 1',
                            (title,kind)).fetchone():
                raise ValueError('Eine Kategorie mit diesem Namen existiert bereits.')
            ident=insert_category(db,title,kind,p)
            _,names,_=category_tree(db)
            mark_finance_edit(db,'category_saved',title)
        return jsonify(id=ident,title=names[ident],kind=kind)
    except (ValueError,sqlite3.Error) as exc:
        return jsonify(error=str(exc)),400


@app.get('/buchungen/erfassen')
@login_required
def booking_list():
    if current_user()['role']=='viewer': abort(403)
    with get_db() as db:
        mode=finance_setting(db,'finance_mode','import')
        accounts=db.execute('''SELECT a.id,a.title,a.currency_id,c.code,c.symbol,c.decimals,s.balance_minor
                               FROM accounts a LEFT JOIN account_snapshots s ON a.id=s.account_id
                               JOIN currencies c ON c.id=a.currency_id
                               WHERE s.is_active IS NULL OR s.is_active<>0
                               ORDER BY a.title COLLATE NOCASE''').fetchall()
        category_records,category_names,_=category_tree(db)
        payees=db.execute('SELECT title FROM payees ORDER BY title COLLATE NOCASE').fetchall()
        rows=db.execute('''SELECT t.*,a.title account_title,c.code currency_code,
                          EXISTS(SELECT 1 FROM recurring_runs rr
                              JOIN audit_events ev ON ev.event IN ('recurring_posted_auto','recurring_posted_manual')
                                AND ev.detail = CAST(rr.rule_id AS TEXT) || ':' || rr.due_on || ':' || CAST(rr.booking_id AS TEXT)
                              WHERE rr.booking_id=t.id) AS is_recurring,
                          EXISTS(SELECT 1 FROM recurring_runs rr
                              WHERE rr.booking_id=t.id
                              AND NOT EXISTS (
                                  SELECT 1 FROM audit_events ev
                                  WHERE ev.event IN ('recurring_posted_auto','recurring_posted_manual')
                                    AND ev.detail = CAST(rr.rule_id AS TEXT) || ':' || rr.due_on || ':' || CAST(rr.booking_id AS TEXT)
                              )) AS is_rule_matched,
                          c.symbol,c.decimals,p.title payee_title
                          FROM transactions t JOIN accounts a ON a.id=t.account_id
                          JOIN currencies c ON c.id=a.currency_id
                          LEFT JOIN payees p ON p.id=t.payee_id
                          WHERE t.origin IN ('web','financisto_edited') ORDER BY t.day DESC,t.id DESC LIMIT 100''').fetchall()
        # Always select the last 100 web transactions first; column sorting
        # affects this fixed set rather than silently changing which rows exist.
        sort_key = request.args.get('sort', 'date')
        sort_direction = request.args.get('dir', 'desc')
        if sort_key not in ('date', 'type', 'account', 'payee', 'note', 'amount'):
            sort_key = 'date'
        if sort_direction not in ('asc', 'desc'):
            sort_direction = 'desc'
        sort_adjustment_ids = adjustment_category_ids(db) if sort_key == 'type' else set()
        sort_neutral_ids = pass_through_category_ids(db) if sort_key == 'type' else set()
        def booking_sort_value(row):
            if sort_key == 'date':
                return row['day']
            if sort_key == 'type':
                return ('Umbuchung' if row['to_account_id'] else
                        'Saldoabgleich' if row['category_id'] in sort_adjustment_ids else
                        'Durchlaufend' if row['category_id'] in sort_neutral_ids else
                        'Ausgabe' if row['amount'] < 0 else
                        'Einnahme' if row['amount'] > 0 else 'Ohne Betrag').casefold()
            if sort_key == 'account':
                return (row['account_title'] or '').casefold()
            if sort_key == 'payee':
                return (row['payee_title'] or '').casefold()
            if sort_key == 'note':
                return (row['note'] or '').casefold()
            return int(row['amount'])
        rows = sorted(rows, key=booking_sort_value, reverse=(sort_direction == 'desc'))
        configured_default_account = finance_setting(db, 'default_account_id', '')
        default_expense_category_id = shared_default_expense_category(db)
        suggestion_limit = booking_suggestion_limit(db)
        valid_account_ids = {str(a['id']) for a in accounts if a['balance_minor'] is not None}
        default_account_id = (configured_default_account if configured_default_account in valid_account_ids else '')
        edit_value = request.args.get('edit','')
        edit_row = db.execute("SELECT t.*,p.title payee_title FROM transactions t LEFT JOIN payees p ON p.id=t.payee_id WHERE t.id=? AND t.is_template=0",
                              (int(edit_value),)).fetchone() if edit_value.isdigit() else None
        clone_value = request.args.get('clone','') if not edit_row else ''
        clone_row = db.execute("""SELECT t.*,p.title payee_title FROM transactions t
            LEFT JOIN payees p ON p.id=t.payee_id WHERE t.id=? AND t.is_template=0""",
            (int(clone_value),)).fetchone() if clone_value.isdigit() else None
        neutral_ids = pass_through_category_ids(db)
        adjustment_ids = adjustment_category_ids(db)
        form_row = edit_row or clone_row
        # Cloning is preparation only. It must NEVER turn into an edit/update.
        valid_account_ids_all = {a['id'] for a in accounts}
        if clone_row and (clone_row['account_id'] not in valid_account_ids_all or
                          (clone_row['to_account_id'] and clone_row['to_account_id'] not in valid_account_ids_all)):
            flash('Das ursprüngliche Konto ist inaktiv. Bitte ein gültiges Konto auswählen.', 'error')
    edit_amount = ''
    if edit_row:
        currency_row = next((a for a in accounts if a['id'] == edit_row['account_id']), None)
        if currency_row:
            precision = int(currency_row['decimals'])
            # Form parser accepts comma decimals, not grouped thousands (e.g. 1.715,13).
            edit_amount = f"{Decimal(abs(edit_row['amount'])) / (10 ** precision):.{precision}f}".replace('.', ',')
    return render_template('bookings.html',finance_mode=mode,accounts=accounts,
                           categories=sorted(category_names.items(),key=lambda p:p[1].casefold()),
                           category_records=category_records,category_names=category_names,
                           payees=payees,rows=rows,edit_row=edit_row,clone_row=clone_row,
                           form_row=form_row,neutral_ids=neutral_ids,
                           adjustment_ids=adjustment_ids,
                           default_account_id=default_account_id,
                           default_expense_category_id=default_expense_category_id,
                           booking_suggestion_limit=suggestion_limit,
                           today=datetime.now(MONTH_TZ).date().isoformat(),
                           edit_amount=edit_amount,
                           booking_sort=sort_key,booking_direction=sort_direction)


def booking_payload(db):
    action=request.form.get('kind','expense')
    if action not in ('expense','income','transfer'):
        raise ValueError('Ungültiger Buchungstyp.')
    day=request.form.get('day','').strip()
    if not re.fullmatch(r'20\d\d-(0[1-9]|1[0-2])-([0-2]\d|3[01])',day):
        raise ValueError('Ungültiges Buchungsdatum.')
    try:
        if date.fromisoformat(day).isoformat()!=day: raise ValueError()
    except ValueError:
        raise ValueError('Ungültiges Kalenderdatum.') from None
    account_id=int(request.form.get('account_id',''))
    account=existing_account(db,account_id)
    decimals=int(account['decimals'])
    amount=minor_amount(request.form.get('amount',''),decimals)
    dest_id=0
    if action=='transfer':
        dest_id=int(request.form.get('to_account_id',''))
        dest=existing_account(db,dest_id)
        if dest_id==account_id or dest['currency_id']!=account['currency_id']:
            raise ValueError('Umbuchung nur zwischen verschiedenen Konten mit gleicher Währung.')
    # The category itself is the portable classification; an SQLite-only flag
    # would disappear in a backup imported back from Android.
    neutral = request.form.get('pass_through') == '1' and action != 'transfer'
    raw_cat=request.form.get('category_id','').strip()
    category_id=ensure_pass_through_category(db,action) if neutral else (int(raw_cat) if raw_cat else 0)
    if category_id and not db.execute('SELECT 1 FROM categories WHERE id=?',(category_id,)).fetchone():
        raise ValueError('Kategorie nicht gefunden.')
    payee_id=entry_payee(db,request.form.get('payee_title',''))
    signed=amount if action=='income' else -amount
    note=request.form.get('note','').strip()[:1000]
    return dict(day=day,account_id=account_id,to_account_id=dest_id,
                category_id=category_id if action!='transfer' else 0,
                payee_id=payee_id,amount=signed,note=note,is_template=0)


def apply_balance_delta(db, entry, direction):
    # A transfer debits its source and credits the destination.
    change = direction*entry['amount']
    for account_id, delta in [(entry['account_id'],change)]+(
            [(entry['to_account_id'],-change)] if entry['to_account_id'] else []):
        if not db.execute('''UPDATE account_snapshots SET balance_minor=balance_minor+?
                             WHERE account_id=? AND balance_minor IS NOT NULL''',
                          (delta,account_id)).rowcount:
            raise ValueError('Kontostand ist unbekannt. Buchung nicht gespeichert.')


@app.post('/buchungen/erfassen')
@finance_editor_required
def booking_add():
    if not csrf_ok(): abort(400)
    try:
        with get_db() as db:
            db.execute('BEGIN IMMEDIATE')
            row=booking_payload(db)
            edit_id=request.form.get('edit_id','').strip()
            if edit_id:
                if not edit_id.isdigit(): raise ValueError('Ungültige Buchungsnummer.')
                old = db.execute("SELECT * FROM transactions WHERE id=? AND is_template=0",
                                 (int(edit_id),)).fetchone()
                if not old: raise ValueError('Buchung nicht gefunden.')
                apply_balance_delta(db,old,-1)
                db.execute('''UPDATE transactions SET day=:day,account_id=:account_id,
                    to_account_id=:to_account_id,category_id=:category_id,payee_id=:payee_id,
                    amount=:amount,note=:note,is_template=0,origin=:origin WHERE id=:id AND is_template=0 ''',
                    {**row,'id':int(edit_id),
                     'origin': 'financisto_edited' if old['origin'] != 'web' else 'web'})
                event='booking_updated'
            else:
                inserted = db.execute('''INSERT INTO transactions
                    (day,account_id,to_account_id,category_id,payee_id,amount,note,is_template,origin)
                    VALUES (:day,:account_id,:to_account_id,:category_id,:payee_id,:amount,:note,:is_template,'web')''',row)
                event='booking_created'
            apply_balance_delta(db,row,+1)
            mark_finance_edit(db,event,row['day'])
            # Send new-booking push independently of the Gotify/Telegram warning threshold.
            # Edits, imports, transfers and balance corrections do not create push.
            notify_message = ''
            if not edit_id and not row['to_account_id']:
                actor=current_user()
                count=notifications.queue_booking(db,{**row,'notification_tx_id':inserted.lastrowid},
                                                  actor['display_name'] if actor else '')
                if count:
                    notify_message = f' {count} Benachrichtigung(en) zum Versand vorgemerkt.'
                elif row['amount']<0:
                    reason,_=notifications.expense_decision(db,row)
                    if reason:
                        notify_message = ' Gotify/Telegram: '+reason
        flash('Buchung gespeichert und Kontostand aktualisiert.'+notify_message,'success')
    except (ValueError,sqlite3.Error) as exc:
        flash('Buchung nicht gespeichert: '+str(exc),'error')
    return redirect(url_for('booking_list'))


@app.post('/buchungen/<int:booking_id>/delete')
@finance_editor_required
def booking_delete(booking_id):
    if not csrf_ok(): abort(400)
    if request.form.get('confirm','')!='LOESCHEN':
        flash('Zum Löschen LOESCHEN eingeben.','error')
        return redirect(url_for('booking_list'))
    try:
        with get_db() as db:
            db.execute('BEGIN IMMEDIATE')
            tx=db.execute("SELECT * FROM transactions WHERE id=? AND is_template=0",(booking_id,)).fetchone()
            if not tx: abort(404)
            apply_balance_delta(db,tx,-1)
            db.execute("DELETE FROM transactions WHERE id=? AND is_template=0",(booking_id,))
            mark_finance_edit(db,'booking_deleted',str(booking_id))
        flash('Buchung gelöscht. Kontostand zurückgerechnet.','success')
    except (ValueError,sqlite3.Error) as exc:
        flash('Buchung nicht gelöscht: '+str(exc),'error')
    return redirect(url_for('booking_list'))


# --- 1.9.9: recurring transaction rules, independent of imported ledgers ---
@app.get('/wiederkehrend')
@login_required
def recurring_list():
    with get_db() as db:
        rules=db.execute('''SELECT r.*,
            (SELECT COUNT(*) FROM recurring_runs runs WHERE runs.rule_id=r.id) completed_count,
            a.title account_title, c.code currency_code,
            c.decimals, p.title payee_title
            FROM recurring_rules r
            LEFT JOIN accounts a ON a.id=r.account_id
            LEFT JOIN currencies c ON c.id=a.currency_id
            LEFT JOIN payees p ON p.id=r.payee_id
            WHERE r.deleted_on IS NULL
            ORDER BY r.active DESC, r.title COLLATE NOCASE, r.id''').fetchall()
        accounts=db.execute('''SELECT a.id,a.title,c.code,c.decimals,s.is_active,s.balance_minor
            FROM accounts a JOIN currencies c ON c.id=a.currency_id
            LEFT JOIN account_snapshots s ON s.account_id=a.id
            ORDER BY a.title COLLATE NOCASE''').fetchall()
        categories=db.execute('SELECT id,title FROM categories ORDER BY title COLLATE NOCASE').fetchall()
        payees=db.execute('SELECT id,title FROM payees ORDER BY title COLLATE NOCASE').fetchall()
        recurring_suggestion_limit=booking_suggestion_limit(db)
        mode=finance_setting(db,'finance_mode','import')
        editing=request.args.get('edit','')
        edit=db.execute('''SELECT r.*, p.title AS payee_title FROM recurring_rules r
            LEFT JOIN payees p ON p.id=r.payee_id
            WHERE r.id=? AND r.deleted_on IS NULL''',(int(editing),)).fetchone() if editing.isdigit() else None
    recurring_edit_amount = ''
    if edit:
        acc = next((a for a in accounts if a['id'] == edit['account_id']), None)
        decimals = int(acc['decimals']) if acc else 2
        recurring_edit_amount = money(abs(edit['amount_minor']) / (10 ** decimals),decimals)
    return render_template('recurring.html',rules=rules,accounts=accounts,categories=categories,
        payees=payees,booking_suggestion_limit=recurring_suggestion_limit,finance_mode=mode,edit_rule=edit,
        rules_data=[dict(r) for r in rules] if mode == 'web' and current_user()['role'] in ('admin','editor') else [],
        edit_amount=recurring_edit_amount,now=recurring_today().isoformat())


@app.post('/wiederkehrend/vorschau')
@admin_required
def recurring_preview():
    if not csrf_ok(): abort(400)
    uploaded=request.files.get('backup')
    if not uploaded or not uploaded.filename.lower().endswith('.backup'):
        flash('Bitte eine Financisto-.backup-Datei auswählen.', 'error')
        return redirect(url_for('recurring_list'))
    try:
        raw=uploaded.read(30*1024*1024+1)
        if len(raw)>30*1024*1024: raise ValueError('Sicherung über 30 MiB')
        with get_db() as db:
            entries, count=preview_from_backup(raw,db)
            token=save_import_preview(db,current_user()['id'],entries)
        return render_template('recurring_preview.html',entries=entries,count=count,token=token)
    except (ValueError,BackupError,sqlite3.Error,OSError) as exc:
        flash('Vorlagen nicht gelesen: '+str(exc),'error')
        return redirect(url_for('recurring_list'))


@app.post('/wiederkehrend/uebernehmen')
@admin_required
def recurring_import_confirm():
    if not csrf_ok(): abort(400)
    token=request.form.get('token','')
    try:
        with get_db() as db:
            db.execute('BEGIN IMMEDIATE')
            count=confirm_import(db,token,current_user()['id'])
            audit(db,'recurring_templates_imported',str(count))
        flash(f'{count} wiederkehrende Vorlagen übernommen; alle sind deaktiviert. Bestehende Regeln bleiben unverändert.','success')
    except (ValueError,sqlite3.Error) as exc:
        flash('Übernahme fehlgeschlagen: '+str(exc),'error')
    return redirect(url_for('recurring_list'))


def recurring_form_payload(db, old=None):
    action=request.form.get('kind','expense')
    if action not in ('income','expense','transfer'): raise ValueError('Ungültige Buchungsart')
    frequency=request.form.get('frequency','monthly')
    if frequency not in ('daily','weekly','monthly','quarterly','yearly'):
        raise ValueError('Bitte ein unterstütztes Intervall auswählen')
    period=int(request.form.get('interval_count','1'))
    if not 1<=period<=120: raise ValueError('Wiederholung 1–120 erlaubt')
    day_of_month=int(request.form.get('day_of_month','1'))
    if not 1<=day_of_month<=31: raise ValueError('Tag muss zwischen 1 und 31 liegen')
    start=request.form.get('start_on','').strip()
    run_at=request.form.get('run_at','00:00').strip() or '00:00'
    if not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', run_at):
        raise ValueError('Uhrzeit muss HH:MM sein (00:00 bis 23:59)')
    start_date=date.fromisoformat(start)
    if not 2000<=start_date.year<=2100: raise ValueError('Startdatum außerhalb des Bereichs')
    end_on = request.form.get('end_on','').strip() or None
    if end_on is not None:
        end_date = date.fromisoformat(end_on)
        if end_date < start_date or end_date.year > 2100:
            raise ValueError('Enddatum muss am oder nach dem Startdatum liegen.')
    max_raw = request.form.get('max_occurrences','').strip()
    max_occurrences = None
    if max_raw:
        if not max_raw.isdigit() or not 1 <= int(max_raw) <= 10000:
            raise ValueError('Anzahl der Ausführungen muss zwischen 1 und 10000 liegen.')
        max_occurrences = int(max_raw)
    source=int(request.form.get('account_id','0'))
    dest=int(request.form.get('to_account_id','0')) if action=='transfer' else 0
    account=existing_account(db,source)
    amount=minor_amount(request.form.get('amount',''),int(account['decimals']))
    category=int(request.form.get('category_id','0')) if action!='transfer' else 0
    # Match one-off bookings: reuse a payee by name or create it on save.
    # The entire recurring rule and any new payee are committed atomically.
    payee_title=request.form.get('payee_title')
    payee=entry_payee(db,payee_title) if payee_title is not None else int(request.form.get('payee_id','0'))
    title=request.form.get('title','').strip()[:160]
    if not title: raise ValueError('Bezeichnung fehlt')
    note=request.form.get('note','').strip()[:1000]
    signed=amount if action=='income' else -amount
    payload={'title':title,'kind':action,'account_id':source,'to_account_id':dest,
             'category_id':category,'payee_id':payee,'amount_minor':signed,'note':note,
             'frequency':frequency,'interval_count':period,'day_of_month':day_of_month,
             'start_on':start,'run_at':run_at,'end_on':end_on,
             'max_occurrences':max_occurrences}
    validate_rule(db,payload)
    return payload


@app.post('/wiederkehrend/speichern')
@finance_editor_required
def recurring_save():
    if not csrf_ok(): abort(400)
    try:
        with get_db() as db:
            db.execute('BEGIN IMMEDIATE')
            edit=request.form.get('edit_id','').strip()
            old=db.execute('SELECT * FROM recurring_rules WHERE id=? AND deleted_on IS NULL',(int(edit),)).fetchone() if edit.isdigit() else None
            if edit and not old: raise ValueError('Regel nicht gefunden')
            row=recurring_form_payload(db,old)
            if old:
                db.execute('''UPDATE recurring_rules SET title=:title,kind=:kind,
                    account_id=:account_id,to_account_id=:to_account_id,
                    category_id=:category_id,payee_id=:payee_id,amount_minor=:amount_minor,
                    note=:note,frequency=:frequency,interval_count=:interval_count,
                    day_of_month=:day_of_month,start_on=:start_on,run_at=:run_at,
                    end_on=:end_on,max_occurrences=:max_occurrences,active=0,auto_post=0,
                    next_on=NULL,completed_on=NULL,needs_review='',updated_on=CURRENT_TIMESTAMP
                    WHERE id=:id''',{**row,'id':int(edit)})
            else:
                db.execute('''INSERT INTO recurring_rules(title,kind,account_id,to_account_id,
                    category_id,payee_id,amount_minor,note,frequency,interval_count,
                    day_of_month,start_on,run_at,end_on,max_occurrences,active,auto_post)
                    VALUES(:title,:kind,:account_id,:to_account_id,:category_id,:payee_id,
                           :amount_minor,:note,:frequency,:interval_count,:day_of_month,
                           :start_on,:run_at,:end_on,:max_occurrences,0,0)''',row)
            audit(db,'recurring_rule_saved',edit or 'new')
        flash('Regel gespeichert, zunächst deaktiviert. Danach bewusst aktivieren.','success')
    except (ValueError,sqlite3.Error) as exc:
        flash('Regel nicht gespeichert: '+str(exc),'error')
    return redirect(url_for('recurring_list'))


@app.post('/wiederkehrend/<int:rule_id>/status')
@finance_editor_required
def recurring_status(rule_id):
    if not csrf_ok(): abort(400)
    # 1.9.10: one explicit state, to avoid confusing manual and automatic activation.
    mode=request.form.get('mode')
    if mode is not None:
        if mode not in ('paused', 'manual', 'auto'):
            abort(400)
        enabled=mode != 'paused'
        auto=mode == 'auto'
    else:
        # Compatibility for existing forms/clients.
        enabled=request.form.get('enabled')=='1'
        auto=request.form.get('auto_post')=='1'
    # Automatic ledger changes require administrator privileges.
    if auto and current_user()['role']!='admin': abort(403)
    try:
        with get_db() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT * FROM recurring_rules WHERE id=? AND deleted_on IS NULL',(rule_id,)).fetchone()
            if not row: abort(404)
            if enabled:
                validate_rule(db,row)
                next_on=on_or_after(date.fromisoformat(row['start_on']),row['frequency'],
                    int(row['interval_count']),int(row['day_of_month']),recurring_today()).isoformat()
                already_done=db.execute('SELECT COUNT(*) FROM recurring_runs WHERE rule_id=?',
                    (rule_id,)).fetchone()[0]
                if row['max_occurrences'] is not None and already_done>=int(row['max_occurrences']):
                    raise ValueError('Die maximale Anzahl der Ausführungen ist bereits erreicht.')
                if row['end_on'] is not None and next_on>row['end_on']:
                    raise ValueError('Das Enddatum der Regel ist bereits erreicht.')
                db.execute('''UPDATE recurring_rules SET active=1,auto_post=?,next_on=?,
                    needs_review='',completed_on=NULL,updated_on=CURRENT_TIMESTAMP WHERE id=?''',(int(auto),next_on,rule_id))
            else:
                db.execute('''UPDATE recurring_rules SET active=0,auto_post=0,
                    updated_on=CURRENT_TIMESTAMP WHERE id=?''',(rule_id,))
            audit(db,'recurring_rule_status',f'{rule_id}:active={int(enabled)}:auto={int(auto)}')
        flash(('Wiederkehrende Regel automatisch aktiviert.' if auto else 'Wiederkehrende Regel für manuelle Ausführung aktiviert.') if enabled else 'Wiederkehrende Regel pausiert.', 'success')
    except (ValueError,sqlite3.Error) as exc:
        flash('Status unverändert: '+str(exc),'error')
    return redirect(url_for('recurring_list'))


@app.post('/wiederkehrend/<int:rule_id>/loeschen')
@finance_editor_required
def recurring_delete(rule_id):
    if not csrf_ok(): abort(400)
    try:
        with get_db() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT id,title FROM recurring_rules WHERE id=? AND deleted_on IS NULL',(rule_id,)).fetchone()
            if not row: abort(404)
            if request.form.get('confirm_title','') != row['title']:
                raise ValueError('Zur Bestätigung den vollständigen Vorlagennamen eingeben.')
            # Soft-delete: existing ledger entries, recurring_runs and import identity
            # remain intact. This prevents re-import of a deleted Financisto rule.
            db.execute('''UPDATE recurring_rules
                SET deleted_on=CURRENT_TIMESTAMP,active=0,auto_post=0,next_on=NULL,
                    updated_on=CURRENT_TIMESTAMP WHERE id=? AND deleted_on IS NULL''',(rule_id,))
            audit(db,'recurring_rule_deleted',f'{rule_id}:{row["title"]}')
        flash('Wiederkehrende Regel entfernt. Bereits gebuchte Umsätze bleiben erhalten.','success')
    except (ValueError,sqlite3.Error) as exc:
        flash('Regel nicht gelöscht: '+str(exc),'error')
    return redirect(url_for('recurring_list'))


@app.post('/wiederkehrend/<int:rule_id>/buchen')
@finance_editor_required
def recurring_post(rule_id):
    if not csrf_ok(): abort(400)
    if request.form.get('confirm')!='BUCHEN':
        flash('Zur Bestätigung BUCHEN eingeben.','error')
        return redirect(url_for('recurring_list'))
    try:
        with get_db() as db:
            db.execute('BEGIN IMMEDIATE')
            result=post_one(db,rule_id,automatic=False)
        flash(f'Fällige Buchung #{result} erzeugt und Kontostand aktualisiert.','success')
    except (ValueError,sqlite3.Error) as exc:
        flash('Nicht gebucht: '+str(exc),'error')
    return redirect(url_for('recurring_list'))


# 1.9.45: Booking-list presets are independent from shared two-month reports.
# No persisted settings or financial data are touched when switching periods.
BOOKING_PERIODS = ('custom', '1w', '1m', '3m', '6m')


def booking_period_dates(today, selected, first_month, last_month):
    if selected == '1w':
        return today - timedelta(days=6), today
    if selected == '1m':
        return today.replace(day=1), today
    if selected in ('3m', '6m'):
        months = int(selected[0])
        index = today.year * 12 + (today.month - 1) - (months - 1)
        return date(index // 12, index % 12 + 1, 1), today
    return date.fromisoformat(first_month + '-01'), date.fromisoformat(last_month + '-01').replace(
        day=calendar.monthrange(*map(int, last_month.split('-')))[1])


def cashflow_period_buckets(start, end, selected):
    """Calendar-aligned buckets for chart; date intervals are inclusive."""
    if selected == '1w':
        return [(start + timedelta(days=offset), start + timedelta(days=offset),
                 (start + timedelta(days=offset)).strftime('%d.%m.'))
                for offset in range((end-start).days+1)]
    if selected == '1m':
        result = []
        cursor = start
        while cursor <= end:
            last = min(end, cursor + timedelta(days=6))
            result.append((cursor,last,f'{cursor.day:02d}.–{last.day:02d}.'))
            cursor = last + timedelta(days=1)
        return result
    month_start = date(start.year, start.month, 1)
    result = []
    while month_start <= end and len(result) < 36:
        next_month = date(month_start.year + (month_start.month == 12), month_start.month % 12 + 1, 1)
        begin, last = max(month_start,start), min(next_month-timedelta(days=1),end)
        result.append((begin,last,month_start.strftime('%m/%Y')))
        month_start = next_month
    return result


def build_cashflow(entries, start, end, selected, divisor):
    """Net cash flow, excluding transfers, pass-through money and balance adjustments."""
    buckets = cashflow_period_buckets(start,end,selected)
    result = []
    for begin,last,label in buckets:
        members = (t for t in entries if begin.isoformat() <= t['day'] <= last.isoformat()
                   and not t.get('to_account_id') and not t.get('pass_through')
                   and not t.get('adjustment'))
        income,expenses=0,0
        for t in members:
            amount = int(t['amount'])
            if amount > 0: income += amount
            elif amount < 0: expenses -= amount
        result.append(dict(label=label,income=income,expenses=expenses,net=income-expenses))
    peak=max((max(r['income'],r['expenses']) for r in result),default=0) or 1
    for row in result:
        row['income_height'] = round(row['income']/peak*100,1)
        row['expenses_height'] = round(row['expenses']/peak*100,1)
    return result


SORTS = {'date','account','category','payee','amount','note','type'}

SHARED_FILTER_KEYS = ('a', 'b', 'currency', 'account', 'category', 'q')


def shared_analysis_filters():
    """Keep filters synchronized between the dashboard and historical analysis."""
    if request.args.get('reset') == '1':
        session.pop('finance_analysis_filters', None)
        return {}
    previous = session.get('finance_analysis_filters', {})
    if not isinstance(previous, dict):
        previous = {}
    values = {key: str(previous.get(key, ''))[:100] for key in SHARED_FILTER_KEYS}
    if any(key in request.args for key in SHARED_FILTER_KEYS):
        for key in SHARED_FILTER_KEYS:
            if key in request.args:
                values[key] = request.args.get(key, '')[:100]
        session['finance_analysis_filters'] = values
        session.modified = True
    return values


def calendar_months(start, end):
    """All months between two YYYY-MM dates, including both endpoints."""
    year, number = map(int, start.split('-'))
    end_year, end_number = map(int, end.split('-'))
    result = []
    while (year, number) <= (end_year, end_number):
        result.append(f'{year:04d}-{number:02d}')
        number += 1
        if number == 13:
            year, number = year + 1, 1
    return result

def future_account_deltas(db, today):
    """Already-stored ledger impact from transactions strictly after today.

    The existing accounting snapshot includes these transactions. Subtract the
    amounts for an as-of-today display, retaining that snapshot as the future
    projection. Do not update SQLite or duplicate any booking.
    """
    rows = db.execute("""SELECT account_id,to_account_id,amount FROM transactions
        WHERE is_template=0 AND day>?""", (today,)).fetchall()
    deltas = defaultdict(int)
    for entry in rows:
        deltas[entry['account_id']] += int(entry['amount'])
        if entry['to_account_id']:
            deltas[entry['to_account_id']] -= int(entry['amount'])
    return deltas


def running_account_balances(db, currency_id):
    """Balance AFTER each transaction, from the last known account balance backwards.

    Transfers are included in the reverse calculation even though income/expense
    reports exclude them. Cross-currency transfers cannot be reconstructed from
    the normalized one-amount table; their destination history is marked unknown.
    """
    rows = db.execute('''SELECT a.id,a.currency_id,s.balance_minor
        FROM accounts a LEFT JOIN account_snapshots s ON s.account_id=a.id
        WHERE a.currency_id=?''', (currency_id,)).fetchall()
    balances = {row['id']: row['balance_minor'] for row in rows}
    result = {}
    entries = db.execute('''SELECT t.id,t.account_id,t.to_account_id,t.amount,
          origin.currency_id origin_currency, destination.currency_id destination_currency
        FROM transactions t JOIN accounts origin ON origin.id=t.account_id
        LEFT JOIN accounts destination ON destination.id=t.to_account_id
        WHERE t.is_template=0 AND
              (origin.currency_id=? OR destination.currency_id=?)
        ORDER BY t.day DESC,t.id DESC''', (currency_id, currency_id)).fetchall()
    for entry in entries:
        aid = entry['account_id']; destination = entry['to_account_id']
        # Current balance is the state after this transaction before reversing it.
        if aid in balances:
            result[entry['id']] = balances[aid]
            if balances[aid] is not None:
                balances[aid] -= entry['amount']
        if destination in balances:
            if entry['origin_currency'] != entry['destination_currency']:
                balances[destination] = None
            elif balances[destination] is not None:
                balances[destination] += entry['amount']
    return result


@app.get('/')
@login_required
def dashboard():
    with get_db() as db:
        imported = db.execute('SELECT COUNT(*) FROM transactions').fetchone()[0]
        if not imported:
            return render_template('empty.html')

        current = datetime.now(MONTH_TZ).strftime('%Y-%m')
        filters = shared_analysis_filters()
        month_a = ym(filters.get('a',''), current)
        month_b = ym(filters.get('b',''), prev_month(current))
        range_start, range_end = sorted((month_a, month_b))
        selected_period = request.args.get('period','custom')
        if selected_period not in BOOKING_PERIODS:
            selected_period = 'custom'
        today_period = datetime.now(MONTH_TZ).date()
        booking_start,booking_end = booking_period_dates(today_period,selected_period,range_start,range_end)
        currs=db.execute('SELECT * FROM currencies ORDER BY code').fetchall()
        if not currs:
            currs=[dict(id=0,code='EUR',symbol='€',decimals=2)]
        curr_ids={str(c['id']) for c in currs}
        preferred=finance_setting(db,'default_currency_code','EUR')
        default_curr=next((str(c['id']) for c in currs if c['code']==preferred),next((str(c['id']) for c in currs if c['code']=='EUR'),str(currs[0]['id'])))
        currency=filters.get('currency') or default_curr
        if currency not in curr_ids: currency=default_curr
        selected_currency=next(c for c in currs if str(c['id'])==currency)
        decimals=max(0,min(int(selected_currency['decimals'] if selected_currency['decimals'] is not None else 2),6))
        divisor=10**decimals
        symbol=selected_currency['symbol'] or selected_currency['code']
        accounts=db.execute('SELECT * FROM accounts WHERE currency_id=? ORDER BY title',(currency,)).fetchall()
        account_ids={str(a['id']) for a in accounts}
        account=filters.get('account','')
        if account not in account_ids: account=''
        # Kontostände stammen aus total_amount im aktuellen Financisto-Backup.
        # Anders als die Monats-Salden sind diese Werte unabhängig von Datum,
        # Kategorie, Konto-Filter und Suchtext. Niemals Währungen addieren.
        balance_rows = db.execute('''SELECT a.id, a.title, s.balance_minor,
                      s.include_in_totals, s.is_active
                      FROM accounts a LEFT JOIN account_snapshots s
                        ON s.account_id=a.id
                      WHERE a.currency_id=? ORDER BY a.title COLLATE NOCASE''', (currency,)).fetchall()
        balance_accounts = [dict(r) for r in balance_rows]
        # Financial snapshot is a forecast including posted future entries.
        # Effective balances show only transactions dated up to today.
        upcoming_deltas = future_account_deltas(db, today_period.isoformat())
        for entry in balance_accounts:
            entry['projected_balance_minor'] = entry['balance_minor']
            entry['upcoming_delta_minor'] = upcoming_deltas.get(entry['id'], 0)
            if entry['balance_minor'] is not None:
                entry['balance_minor'] -= entry['upcoming_delta_minor']
        # Die Liste wird spaltenweise (oben nach unten) gelesen:
        # 1) aktive Konten mit bekanntem Saldo != 0, 2) inaktive mit
        #    Saldo != 0, 3) Konten mit unbekanntem Saldo, 4) alle Nullkonten.
        # Innerhalb jeder Gruppe alphabetisch; keine Beträge werden verändert.
        def balance_order(a):
            value = a['balance_minor']
            if value == 0:
                group = 3
            elif value is None:
                group = 2
            elif a['is_active'] == 0:
                group = 1
            else:
                group = 0
            return (group, (a['title'] or '').casefold(), a['id'])
        balance_accounts.sort(key=balance_order)
        can_reconcile = (finance_setting(db, 'finance_mode', 'import') == 'web'
                         and current_user()['role'] in ('admin', 'editor'))
        # Only accounts in the displayed currency. Never show inactive/unknown balances as editable.
        reconcile_accounts = [dict(id=a['id'], title=a['title'], balance_minor=a['balance_minor'],
                                   decimals=decimals, code=selected_currency['code'])
                              for a in balance_accounts
                              if a['is_active'] != 0 and a['balance_minor'] is not None]
        included_accounts = [a for a in balance_accounts if a['include_in_totals'] != 0]
        # Missing include flag or amount means that the full total is unknown.
        balance_total_ready = all(
            a['include_in_totals'] == 1 and a['balance_minor'] is not None
            for a in included_accounts
        ) and all(a['include_in_totals'] is not None for a in balance_accounts)
        balance_total_minor = (sum(a['balance_minor'] for a in included_accounts)
                               if balance_total_ready else None)
        balance_snapshot_known = all(
            a['balance_minor'] is not None and a['include_in_totals'] is not None
            for a in balance_accounts
        ) and bool(balance_accounts)
        categories,cat_names,cat_root=category_tree(db)
        neutral_ids = pass_through_category_ids(db)
        adjustment_ids = adjustment_category_ids(db)
        category=filters.get('category','')
        if category not in {str(c['id']) for c in categories}: category=''
        search=filters.get('q','').strip()[:100]
        where=['substr(t.day,1,7) BETWEEN ? AND ?','a.currency_id=?','t.is_template=0','t.to_account_id=0']
        params=[range_start,range_end,currency]
        if account:
            where.append('t.account_id=?');params.append(account)
        if category:
            selected=next(c for c in categories if str(c['id'])==category)
            descendants=[c['id'] for c in categories if c['lft']>=selected['lft'] and c['rgt']<=selected['rgt']]
            where.append('t.category_id IN ('+','.join('?' for _ in descendants)+')')
            params.extend(descendants)
        if search:
            match=like_match(search)
            where.append("(p.title LIKE ? ESCAPE '\\' OR t.note LIKE ? ESCAPE '\\' OR c.title LIKE ? ESCAPE '\\')")
            params.extend([match,match,match])
        sql='''SELECT t.id,t.day,t.origin,t.category_id,t.amount,t.note,a.title account_title,
                         c.title category_title,p.title payee_title
                 FROM transactions t JOIN accounts a ON a.id=t.account_id
                 LEFT JOIN categories c ON c.id=t.category_id
                 LEFT JOIN payees p ON p.id=t.payee_id
                 WHERE '''+' AND '.join(where)
        transactions=[dict(r)|{'source':'Financisto','group_key':r['category_id'],
                               'pass_through': r['category_id'] in neutral_ids,
                               'adjustment': r['category_id'] in adjustment_ids}
                      for r in db.execute(sql,params)]
        months={month_a,month_b}
        totals={m:{'expenses':0,'income':0,'balance':0} for m in months}
        projected_totals={m:{'expenses':0,'income':0,'balance':0} for m in months}
        grouped=defaultdict(lambda:{m:0 for m in months})
        for t in transactions:
            month=t['day'][:7]
            if t['category_id'] in neutral_ids or month not in totals:
                continue  # Transfers/pass-through excluded in both calculations.
            forecast = projected_totals[month]
            actual = totals[month] if t['day'] <= today_period.isoformat() else None
            if t['amount'] < 0:
                amount = -t['amount']
                forecast['expenses'] += amount
                if actual is not None:
                    actual['expenses'] += amount
                    grouped[t['group_key']][month] += amount
            else:
                forecast['income'] += t['amount']
                if actual is not None:
                    actual['income'] += t['amount']
        for m in months:
            totals[m]['balance'] = totals[m]['income'] - totals[m]['expenses']
            projected_totals[m]['balance'] = (projected_totals[m]['income'] - projected_totals[m]['expenses'])
        rows=[]
        for key,values in grouped.items():
            name=cat_names.get(key,'Ohne Kategorie')
            first=values[month_a]/divisor
            second=values[month_b]/divisor
            rows.append(dict(category=name,first=first,second=second,total=first+second))
        rows.sort(key=lambda x:x['total'],reverse=True)
        peak=max((max(x['first'],x['second']) for x in rows),default=1) or 1
        for row in rows:
            row['first_width']=round(row['first']/peak*100,2)
            row['second_width']=round(row['second']/peak*100,2)

        # The full booking ledger includes transfers. This is deliberately a
        # second query: the income/expense charts above must remain unaffected.
        # A transfer is a single transaction with a source and a destination,
        # not an expense followed by a separate income.
        ledger_where=['t.day BETWEEN ? AND ?', 'a.currency_id=?', 't.is_template=0']
        ledger_params=[booking_start.isoformat(),booking_end.isoformat(),currency]
        if account:
            # A transfer must also be visible while viewing its destination account.
            ledger_where.append('(t.account_id=? OR t.to_account_id=?)')
            ledger_params.extend([account,account])
        if category:
            ledger_where.append('t.category_id IN ('+','.join('?' for _ in descendants)+')')
            ledger_params.extend(descendants)
        if search:
            ledger_where.append("(p.title LIKE ? ESCAPE '\\' OR t.note LIKE ? ESCAPE '\\' OR c.title LIKE ? ESCAPE '\\' OR a.title LIKE ? ESCAPE '\\' OR target.title LIKE ? ESCAPE '\\')")
            ledger_params.extend([match]*5)
        ledger_sql='''SELECT t.id,t.day,t.origin,t.to_account_id,t.category_id,t.amount,t.note,
                         EXISTS(SELECT 1 FROM recurring_runs rr
                              JOIN audit_events ev ON ev.event IN ('recurring_posted_auto','recurring_posted_manual')
                                AND ev.detail = CAST(rr.rule_id AS TEXT) || ':' || rr.due_on || ':' || CAST(rr.booking_id AS TEXT)
                              WHERE rr.booking_id=t.id) AS is_recurring,
                          EXISTS(SELECT 1 FROM recurring_runs rr
                              WHERE rr.booking_id=t.id
                              AND NOT EXISTS (
                                  SELECT 1 FROM audit_events ev
                                  WHERE ev.event IN ('recurring_posted_auto','recurring_posted_manual')
                                    AND ev.detail = CAST(rr.rule_id AS TEXT) || ':' || rr.due_on || ':' || CAST(rr.booking_id AS TEXT)
                              )) AS is_rule_matched,
                         a.title account_title,target.title target_account_title,
                         c.title category_title,p.title payee_title
                 FROM transactions t JOIN accounts a ON a.id=t.account_id
                 LEFT JOIN accounts target ON target.id=t.to_account_id
                 LEFT JOIN categories c ON c.id=t.category_id
                 LEFT JOIN payees p ON p.id=t.payee_id
                 WHERE '''+' AND '.join(ledger_where)
        ledger_transactions=[dict(r)|{'pass_through':r['category_id'] in neutral_ids,
                                      'adjustment':r['category_id'] in adjustment_ids}
                             for r in db.execute(ledger_sql,ledger_params)]

        # Independent cashflow chart uses exactly this ledger period and filters,
        # but never counts internal transfers or own-account balance adjustments.
        # Only already-dated transactions enter the chart: future notices remain
        # visibly marked in the ledger without being shown as realised cashflow.
        cashflow_rows = build_cashflow(ledger_transactions,booking_start,min(booking_end,today_period),
                                       selected_period,divisor)
        cashflow_income = sum(r['income'] for r in cashflow_rows)
        cashflow_expenses = sum(r['expenses'] for r in cashflow_rows)
        cashflow_net = cashflow_income - cashflow_expenses

        cashflow_net_abs = max((abs(r['net']) for r in cashflow_rows),default=0) or 1

        # This quick filter affects the bookings table only, not cards or diagrams.
        quick=request.args.get('quick','').strip()[:100]
        count_unfiltered=len(ledger_transactions)
        if quick:
            terms=quick.casefold().split()
            def matches_quick(t):
                day=t['day']
                text=' '.join(str(x) for x in (day,f'{day[8:10]}.{day[5:7]}.{day[:4]}',
                    t.get('account_title') or '',t.get('target_account_title') or '',
                    cat_names.get(t['category_id'],'Ohne Kategorie'),
                    t.get('payee_title') or '',t.get('note') or '',
                    'Wiederkehrend' if t.get('is_recurring') else 'Regel zugeordnet' if t.get('is_rule_matched') else '',
                    'Umbuchung' if t['to_account_id'] else
                    (('Saldoabgleich' if t['category_id'] in adjustment_ids else 'Durchlaufend') if t['category_id'] in neutral_ids else ('Ausgabe' if t['amount'] < 0 else ('Einnahme' if t['amount'] > 0 else 'Ohne Betrag'))),
                    money(t['amount']/divisor,decimals),f'{t["amount"]/divisor:.{decimals}f}')).casefold()
                return all(term in text for term in terms)
            ledger_transactions=[t for t in ledger_transactions if matches_quick(t)]
        sort=request.args.get('sort','date')
        if sort not in SORTS: sort='date'
        direction=request.args.get('dir','desc')
        if direction not in ('asc','desc'):direction='desc'
        def sort_key(t):
            if sort=='type':
                # Group expenses/income with stable order by date and id.
                return (0 if t['to_account_id'] else (-1 if t['amount'] < 0 else (1 if t['amount'] > 0 else 0)), t['day'], t['id'])
            key={'date':'day','account':'account_title','category':'category_title',
                 'payee':'payee_title','note':'note','amount':'amount'}[sort]
            value=t.get(key)
            if sort=='amount': return (value or 0,t['id'])
            return (str(value or '').casefold(),t['id'])
        ledger_transactions.sort(key=sort_key,reverse=direction=='desc')
        # CSV export uses the exact same filtered and sorted ledger as the page,
        # before pagination. It never modifies any financial record.
        if request.args.get('export') == 'csv':
            csv_text = StringIO(newline='')
            writer = csv.writer(csv_text, delimiter=';', lineterminator='\r\n')
            writer.writerow(['Datum', 'Art', 'Konto', 'Zielkonto', 'Kategorie',
                             'Empfänger', 'Notiz', 'Betrag', 'Währung', 'Wiederkehrend', 'Regel zugeordnet',
                             'Kontostand danach'])
            running_export = running_account_balances(db, currency)
            def safe_cell(value):
                # Spreadsheet formulas must not be executable through payee/note text.
                result = str(value or '')
                return "'" + result if result.lstrip().startswith(('=', '+', '-', '@')) or result.startswith(('\t', '\r', '\n')) else result
            def amount_csv(minor):
                return f'{Decimal(minor) / Decimal(divisor):.{decimals}f}'.replace('.', ',')
            for entry in ledger_transactions:
                transfer = bool(entry['to_account_id'])
                kind = ('Umbuchung' if transfer else 'Saldoabgleich' if entry['adjustment']
                        else 'Durchlaufend' if entry['pass_through'] else 'Ausgabe' if entry['amount'] < 0
                        else 'Einnahme' if entry['amount'] > 0 else 'Ohne Betrag')
                balance = running_export.get(entry['id'])
                writer.writerow([
                    entry['day'][8:10]+'.'+entry['day'][5:7]+'.'+entry['day'][:4], kind,
                    safe_cell(entry['account_title']), safe_cell(entry.get('target_account_title')) if transfer else '',
                    '' if transfer else safe_cell(entry.get('category_title') or 'Ohne Kategorie'),
                    safe_cell(entry.get('payee_title')), safe_cell(entry.get('note')),
                    amount_csv(entry['amount']), selected_currency['code'],
                    'Ja' if entry['is_recurring'] else 'Nein',
                    'Ja' if entry['is_rule_matched'] else 'Nein',
                    amount_csv(balance) if balance is not None else ''])
            payload = ('\ufeff' + csv_text.getvalue()).encode('utf-8')
            response = send_file(BytesIO(payload), mimetype='text/csv; charset=utf-8',
                                 as_attachment=True,
                                 download_name=f'fielanzen-buchungen-{booking_start:%Y%m%d}-{booking_end:%Y%m%d}.csv',
                                 max_age=0)
            response.headers['Cache-Control'] = 'private, no-store'
            response.headers['X-Content-Type-Options'] = 'nosniff'
            return response
        page_str=request.args.get('page','1')
        page=max(1,min(100000,int(page_str) if page_str.isdigit() else 1))
        count=len(ledger_transactions)
        configured_size = finance_setting(db, 'booking_page_size', '30')
        page_size = int(configured_size) if configured_size in ('20','30','50','100') else 30
        page_count=max(1,(count+page_size-1)//page_size)
        page=min(page,page_count)
        tx=ledger_transactions[(page-1)*page_size:page*page_size]
        running = running_account_balances(db, currency)
        for entry in tx:
            entry['balance_after'] = running.get(entry['id'])
        fields={'a':month_a,'b':month_b,'currency':currency,'account':account,
                'category':category,'q':search,'quick':quick,'sort':sort,'dir':direction,'period':selected_period}
        def link(**changes):
            return url_for('dashboard')+'?'+urlencode({**fields,**changes})+'#buchungen'
        last_import=db.execute("SELECT value FROM meta WHERE key='last_import'").fetchone()
        import_source=db.execute("SELECT value FROM meta WHERE key='last_import_source'").fetchone()
        newest=db.execute('SELECT MAX(day) FROM transactions').fetchone()[0]
        return render_template('dashboard.html',a=month_a,b=month_b,
            month_a_label=month_label_de(month_a),month_b_label=month_label_de(month_b),
            month_a_short=month_label_de(month_a, short=True),month_b_short=month_label_de(month_b, short=True),
            current_month=current,previous_month=prev_month(current),latest_date=newest,
            currencies=currs,currency=currency,selected_currency=selected_currency,accounts=accounts,account=account,
            balance_accounts=balance_accounts,balance_total_minor=balance_total_minor,
            projected_balance_total_minor=(sum(a['projected_balance_minor'] for a in included_accounts)
                                           if balance_total_ready else None),
            balance_snapshot_known=balance_snapshot_known,
            can_reconcile=can_reconcile,reconcile_accounts=reconcile_accounts,
            categories=categories,category=category,cat_names=cat_names,q=search,
            quick=quick,count_unfiltered=count_unfiltered,rows=rows,totals=totals,projected_totals=projected_totals,divisor=divisor,
            period=selected_period,booking_start=booking_start.isoformat(),booking_end=booking_end.isoformat(),
            cashflow_rows=cashflow_rows,cashflow_income=cashflow_income,
            cashflow_expenses=cashflow_expenses,cashflow_net=cashflow_net,
            cashflow_net_abs=cashflow_net_abs,
            decimals=decimals,symbol=symbol,tx=tx,count=count,page=page,
            page_count=page_count,page_size=page_size,range_start=range_start,range_end=range_end,sort=sort,direction=direction,link=link,
            last_import=last_import['value'] if last_import else 'Noch kein Import',
            last_import_source=import_source['value'] if import_source else 'Manuell',
            can_clone=(finance_setting(db,'finance_mode','import')=='web' and current_user()['role'] in ('admin','editor')),
            can_modify=(finance_setting(db,'finance_mode','import')=='web' and current_user()['role'] in ('admin','editor')),
            today=datetime.now(MONTH_TZ).date().isoformat(),
            finance_mode=finance_setting(db,'finance_mode','import'))



# --- 1.9.8: historical analyses of the inclusive, shared date interval ---
HISTORY_PIE_PALETTE = ('#087b83','#b56822','#6985b4','#789d52','#b66c91',
                       '#7274ab','#d1a348','#517c86','#8b9fa3')


def pie_overview(values, limit=7):
    ordered = sorted(((str(name), int(value)) for name,value in values.items()
                      if value > 0), key=lambda pair: pair[1], reverse=True)
    if len(ordered) > limit:
        ordered = ordered[:limit] + [('Weitere Kategorien', sum(x[1] for x in ordered[limit:]))]
    total = sum(v for _,v in ordered)
    portions = []
    previous = 0.0
    for index, (name, value) in enumerate(ordered):
        end = (sum(v for _,v in ordered[:index+1]) / total * 100) if total else 0
        portions.append(dict(name=name, value=value, percent=round(value / total * 100, 1),
                             color=HISTORY_PIE_PALETTE[index], start=previous, end=end))
        previous = end
    gradient = ', '.join(f'{item["color"]} {item["start"]:.4f}% {item["end"]:.4f}%'
                         for item in portions)
    return dict(rows=portions, total=total,
                gradient=('conic-gradient('+gradient+')' if portions else 'none'))


@app.get('/historische-auswertung')
@login_required
def historical_analysis():
    with get_db() as db:
        if not db.execute('SELECT 1 FROM transactions LIMIT 1').fetchone():
            return render_template('empty.html')
        filters = shared_analysis_filters()
        today_month = datetime.now(MONTH_TZ).strftime('%Y-%m')
        a = ym(filters.get('a',''), today_month)
        b = ym(filters.get('b',''), prev_month(today_month))
        start,end = sorted((a,b))
        months = calendar_months(start,end)
        currencies = db.execute('SELECT * FROM currencies ORDER BY code').fetchall()
        if not currencies:
            currencies = [dict(id=0,code='EUR',symbol='€',decimals=2)]
        codes = {str(r['id']) for r in currencies}
        preferred=finance_setting(db,'default_currency_code','EUR')
        default_currency = next((str(c['id']) for c in currencies if c['code']==preferred),
                                next((str(c['id']) for c in currencies if c['code']=='EUR'),str(currencies[0]['id'])))
        currency = filters.get('currency') or default_currency
        if currency not in codes:
            currency = default_currency
        chosen = next(c for c in currencies if str(c['id'])==currency)
        decimals = max(0,min(int(chosen['decimals'] if chosen['decimals'] is not None else 2),6))
        divisor = 10 ** decimals
        symbol = chosen['symbol'] or chosen['code']
        accounts = db.execute('SELECT * FROM accounts WHERE currency_id=? ORDER BY title COLLATE NOCASE',
                              (currency,)).fetchall()
        account = filters.get('account','')
        if account not in {str(r['id']) for r in accounts}:
            account = ''
        categories, names, _ = category_tree(db)
        neutral_ids = pass_through_category_ids(db)
        category = filters.get('category','')
        if category not in {str(r['id']) for r in categories}:
            category = ''
        search = filters.get('q','').strip()[:100]
        where = ["substr(t.day,1,7) BETWEEN ? AND ?",'a.currency_id=?',
                 't.is_template=0','t.to_account_id=0']
        params = [start,end,currency]
        if account:
            where.append('t.account_id=?'); params.append(account)
        if category:
            cat = next(c for c in categories if str(c['id'])==category)
            descendants=[c['id'] for c in categories if c['lft']>=cat['lft'] and c['rgt']<=cat['rgt']]
            where.append('t.category_id IN ('+','.join('?' for _ in descendants)+')')
            params.extend(descendants)
        if search:
            pattern = like_match(search)
            where.append("(p.title LIKE ? ESCAPE '\\' OR t.note LIKE ? ESCAPE '\\' OR c.title LIKE ? ESCAPE '\\')")
            params.extend([pattern]*3)
        sql = """SELECT t.id,t.day,t.amount,t.category_id,a.title account_title,
                       p.title payee_title,c.title category_title
                 FROM transactions t JOIN accounts a ON a.id=t.account_id
                 LEFT JOIN categories c ON c.id=t.category_id
                 LEFT JOIN payees p ON p.id=t.payee_id
                 WHERE """ + ' AND '.join(where)
        tx = db.execute(sql,params).fetchall()
        monthly = {m:dict(month=m,label=month_label_de(m,short=True),income=0,expenses=0,count=0)
                   for m in months}
        expense_groups = defaultdict(int)
        income_groups = defaultdict(int)
        expense_counts = defaultdict(int)
        income_counts = defaultdict(int)
        biggest_expense = None
        biggest_income = None
        expense_count = income_count = total_expenses = total_income = 0
        for t in tx:
            m=t['day'][:7]
            month_row=monthly[m]
            if t['category_id'] in neutral_ids:
                continue  # Exclude third-party funds from averages and diagrams.
            month_row['count']+=1
            category_title=names.get(t['category_id'],'Ohne Kategorie')
            if t['amount'] < 0:
                amt = -t['amount']
                month_row['expenses'] += amt
                expense_groups[category_title] += amt
                expense_counts[category_title] += 1
                total_expenses += amt
                expense_count += 1
                if biggest_expense is None or amt > -biggest_expense['amount']:
                    biggest_expense = dict(t)
            elif t['amount'] > 0:
                amt = t['amount']
                month_row['income'] += amt
                income_groups[category_title] += amt
                income_counts[category_title] += 1
                total_income += amt
                income_count += 1
                if biggest_income is None or amt > biggest_income['amount']:
                    biggest_income = dict(t)
        timeline = list(monthly.values())
        for month_row in timeline:
            month_row['balance'] = month_row['income'] - month_row['expenses']
        max_monthly = max([max(row['income'],row['expenses']) for row in timeline] + [1])
        for month_row in timeline:
            month_row['income_pct'] = round(month_row['income']/max_monthly*100,2)
            month_row['expense_pct'] = round(month_row['expenses']/max_monthly*100,2)
        avg_expense_cat = max(expense_groups,
                              key=lambda k:expense_groups[k]/expense_counts[k]) if expense_groups else None
        avg_income_cat = max(income_groups,
                             key=lambda k:income_groups[k]/income_counts[k]) if income_groups else None
        total_months = len(timeline)
        return render_template('historical.html',a=a,b=b,start=start,end=end,
          start_label=month_label_de(start),end_label=month_label_de(end),months=total_months,
          currencies=currencies,currency=currency,accounts=accounts,account=account,
          categories=categories,category=category,cat_names=names,q=search,
          decimals=decimals,divisor=divisor,symbol=symbol,
          total_income=total_income,total_expenses=total_expenses,
          period_balance=total_income-total_expenses,
          income_count=income_count,expense_count=expense_count,
          avg_income=(total_income/income_count if income_count else 0),
          avg_expense=(total_expenses/expense_count if expense_count else 0),
          avg_income_month=total_income/total_months,
          avg_expense_month=total_expenses/total_months,
          biggest_income=biggest_income,biggest_expense=biggest_expense,
          top_expense_average=(avg_expense_cat,expense_groups[avg_expense_cat]/expense_counts[avg_expense_cat]) if avg_expense_cat else None,
          top_income_average=(avg_income_cat,income_groups[avg_income_cat]/income_counts[avg_income_cat]) if avg_income_cat else None,
          expense_pie=pie_overview(expense_groups),income_pie=pie_overview(income_groups),
          timeline=timeline,filtered_count=len(tx))


def like_match(value):
    return '%' + value.replace('\\','\\\\').replace('%','\\%').replace('_','\\_') + '%'


def category_tree(db):
    categories=db.execute('SELECT * FROM categories ORDER BY lft,title').fetchall()
    names,roots={},{}
    stack=[]
    for c in categories:
        while stack and stack[-1]['rgt'] < c['lft']:
            stack.pop()
        names[c['id']]=' / '.join([v['title'] for v in stack]+[c['title']])
        roots[c['id']]=stack[0]['title'] if stack else c['title']
        stack.append(c)
    return categories,names,roots


def monthly_report_context():
    """Print-friendly monthly report, exclusively Financisto, with category visibility."""
    with get_db() as db:
        current = datetime.now(MONTH_TZ).strftime('%Y-%m')
        currencies = db.execute('SELECT * FROM currencies ORDER BY code').fetchall()
        if not currencies:
            return dict(no_data=True, month=ym(request.args.get('month', ''), current))
        preferred=finance_setting(db,'default_currency_code','EUR')
        default_curr = next((str(c['id']) for c in currencies if c['code']==preferred),
                            next((str(c['id']) for c in currencies if c['code']=='EUR'),str(currencies[0]['id'])))
        currency = request.args.get('currency', default_curr)
        if currency not in {str(c['id']) for c in currencies}:
            currency = default_curr
        selected = next(c for c in currencies if str(c['id']) == currency)
        decimals = max(0, min(int(selected['decimals'] if selected['decimals'] is not None else 2), 6))
        divisor = 10 ** decimals
        symbol = selected['symbol'] or selected['code']
        accounts = db.execute('SELECT * FROM accounts WHERE currency_id=? ORDER BY title', (currency,)).fetchall()
        account = request.args.get('account', '')
        if account not in {str(a['id']) for a in accounts}:
            account = ''
        # Honor any explicitly selected month (even a month without bookings).
        # Only the first visit should default to the newest month with real
        # transactions for the chosen currency/account. Never mutate Financisto.
        newest_query = '''SELECT MAX(substr(t.day, 1, 7))
                          FROM transactions t
                          JOIN accounts a ON a.id=t.account_id
                          WHERE a.currency_id=? AND t.is_template=0
                            AND t.to_account_id=0 AND t.amount<>0'''
        newest_args = [currency]
        if account:
            newest_query += ' AND t.account_id=?'
            newest_args.append(account)
        latest_month = db.execute(newest_query, newest_args).fetchone()[0]
        month = ym(request.args.get('month', ''), latest_month or current)
        _, cat_names, cat_roots = category_tree(db)
        neutral_ids = pass_through_category_ids(db)
        group_by = request.args.get('group', 'category')
        if group_by not in ('category', 'payee'):
            group_by = 'category'

        where = ['substr(t.day,1,7)=?', 'a.currency_id=?', 't.is_template=0', 't.to_account_id=0']
        args = [month, currency]
        if account:
            where.append('t.account_id=?')
            args.append(account)
        sql = '''SELECT t.id,t.day,t.origin,t.category_id,t.amount,t.note,a.title account_title,
                        p.title payee_title
                 FROM transactions t JOIN accounts a ON a.id=t.account_id
                 LEFT JOIN payees p ON p.id=t.payee_id
                 WHERE ''' + ' AND '.join(where) + ' ORDER BY t.day,t.id'
        transactions = db.execute(sql, args).fetchall()

        # A user can hide any income or expense category independently. Never persist
        # report filters into Financisto's data or household legacy tables.
        choices = {'income': {}, 'expense': {}}
        for t in transactions:
            if t['amount'] == 0 or t['category_id'] in neutral_ids:
                continue
            kind = 'expense' if t['amount'] < 0 else 'income'
            key = f"{kind[0]}:{int(t['category_id'] or 0)}"
            path = cat_names.get(t['category_id'], 'Ohne Kategorie')
            choices[kind][key] = {'key': key, 'label': path}
        income_choices = sorted(choices['income'].values(), key=lambda x: x['label'].casefold())
        expense_choices = sorted(choices['expense'].values(), key=lambda x: x['label'].casefold())
        known_keys = set(choices['income']) | set(choices['expense'])
        hidden = set(request.args.getlist('hide')) & known_keys

        groups = {}
        incomes = []
        expense_total = income_total = 0
        expense_total_all = income_total_all = 0
        expense_skipped = income_skipped = 0
        visible_count = 0
        for t in transactions:
            minor = int(t['amount'])
            if not minor or t['category_id'] in neutral_ids:
                continue
            kind = 'expense' if minor < 0 else 'income'
            minor_abs = abs(minor)
            if kind == 'expense':
                expense_total_all += minor_abs
            else:
                income_total_all += minor_abs
            key = f"{kind[0]}:{int(t['category_id'] or 0)}"
            if key in hidden:
                if kind == 'expense':
                    expense_skipped += 1
                else:
                    income_skipped += 1
                continue
            visible_count += 1
            category_path = cat_names.get(t['category_id'], 'Ohne Kategorie')
            item = {'day': t['day'], 'payee': t['payee_title'] or '–',
                    'note': t['note'] or '', 'category_path': category_path,
                    'amount': minor_abs/divisor, 'account': t['account_title']}
            if kind == 'expense':
                expense_total += minor_abs
                # The second level is important: 'Einkauf / Lebensmittel' and
                # 'Einkauf / Haushaltsartikel' must NOT collapse into 'Einkauf'.
                name = (category_path if group_by == 'category' else
                        (t['payee_title'] or cat_roots.get(t['category_id'], 'Ohne Empfänger')))
                group = groups.setdefault(name, {'name': name, 'amount_minor': 0, 'items': []})
                group['amount_minor'] += minor_abs
                group['items'].append(item)
            else:
                income_total += minor_abs
                incomes.append(item)

        ordered_groups = sorted(groups.values(), key=lambda x: (x['name'].casefold()))
        for group in ordered_groups:
            group['amount'] = group['amount_minor']/divisor
        incomes.sort(key=lambda x: (x['day'], x['payee'].casefold()))
        return dict(no_data=False, month=month,
            currencies=currencies, currency=currency, accounts=accounts, account=account,
            symbol=symbol, decimals=decimals, expense_total=expense_total/divisor,
            income_total=income_total/divisor, balance=(income_total-expense_total)/divisor,
            expense_total_all=expense_total_all/divisor,
            income_total_all=income_total_all/divisor,
            expense_skipped=expense_skipped, income_skipped=income_skipped,
            hidden=hidden, income_choices=income_choices, expense_choices=expense_choices,
            groups=ordered_groups, incomes=incomes, transaction_count=visible_count,
            group_by=group_by, generated_at=datetime.now(MONTH_TZ).strftime('%d.%m.%Y %H:%M'))


@app.get('/haushaltsauswertung')
@login_required
def monthly_report():
    return render_template('report.html', **monthly_report_context())


@app.get('/haushaltsauswertung/kompakt')
@login_required
def monthly_report_compact():
    """A5 paper-style print, using the exact same source data and visible filters."""
    return render_template('compact_report.html', **monthly_report_context())


# Version 1.9.27: PWA endpoints. No account or session data is cached offline.
@app.get('/manifest.webmanifest')
def pwa_manifest():
    return app.send_static_file('manifest.webmanifest'), 200, {'Content-Type': 'application/manifest+json', 'Cache-Control': 'no-cache'}

@app.get('/sw.js')
def pwa_service_worker():
    return app.send_static_file('sw.js'), 200, {'Content-Type': 'application/javascript', 'Service-Worker-Allowed': '/', 'Cache-Control': 'no-cache'}


# --- Versioned Android API. All private requests use explicit bearer credentials;
# session cookies are not API credentials and never skip CSRF for browser forms.
import json as _mobile_json
from uuid import UUID as _MobileUUID


def _mobile_json_response(body, status=200):
    response = jsonify(body)
    response.status_code = status
    response.headers['Cache-Control'] = 'private, no-store'
    return response


def _mobile_denied(status=401, message='API-Key fehlt oder ist ungültig.'):
    result = _mobile_json_response({'error': message}, status)
    if status == 401:
        result.headers['WWW-Authenticate'] = 'Bearer realm="FieLanzen Mobile"'
    return result


def _mobile_authorize(*, write=False):
    header = request.headers.get('Authorization','')
    if not header.startswith('Bearer '):
        return None
    token = header[7:].strip()
    if len(token) < 32 or len(token) > 160 or not re.fullmatch(r'fm1_[A-Za-z0-9_-]+',token):
        return None
    digest = hashlib.sha256(('FieLanzen-Mobile-Key-v1:'+token).encode()).hexdigest()
    with get_db() as db:
        record = db.execute('''SELECT k.id key_id,k.access,k.expires_on,u.id user_id,
               u.username,u.role,u.version,u.is_active,u.totp_enabled,k.user_version
               FROM mobile_api_keys k JOIN users u ON k.user_id=u.id
               WHERE k.key_hash=? AND k.revoked_on IS NULL''',(digest,)).fetchone()
    if (not record or record['expires_on'] <= int(time.time()) or
            not record['is_active'] or not record['totp_enabled'] or
            record['version'] != record['user_version']):
        return None
    if write and (record['access'] != 'write' or record['role'] not in ('admin','editor')):
        return None
    return dict(record)


def _mobile_require(write=False):
    user=_mobile_authorize(write=write)
    if user is None:
        return None,_mobile_denied()
    if write:
        with get_db() as db:
            if finance_setting(db,'finance_mode','import')!='web':
                return None,_mobile_denied(409,'Web-Verwaltung ist nicht führend. Kein Schreibzugriff.')
    return user,None


def _mobile_book_hash(row):
    attrs=(row['id'],row['day'],row['account_id'],row['to_account_id'],row['category_id'],
           row['payee_id'],row['amount'],row['note'],row['origin'])
    return hashlib.sha256(_mobile_json.dumps(attrs,ensure_ascii=False).encode()).hexdigest()[:32]


def _mobile_booking(row):
    return {'id':int(row['id']), 'date':row['day'],'account_id':int(row['account_id']),
            'to_account_id':int(row['to_account_id'] or 0),
            'category_id':int(row['category_id'] or 0),'payee_id':int(row['payee_id'] or 0),
            'amount_minor':int(row['amount']), 'note':row['note'] or '',
            'currency_code':row['currency_code'], 'decimals':int(row['decimals']),
            'kind':'transfer' if row['to_account_id'] else 'income' if row['amount']>0 else 'expense',
            'payee':row['payee_title'] or '', 'account':row['account_title'],
            'revision':_mobile_book_hash(row)}


def _mobile_book_query():
    return '''SELECT t.*,a.title account_title,c.code currency_code,c.decimals,
              p.title payee_title FROM transactions t
              JOIN accounts a ON a.id=t.account_id
              JOIN currencies c ON c.id=a.currency_id
              LEFT JOIN payees p ON p.id=t.payee_id'''


@app.get('/api/mobile/v1/capabilities')
@app.get('/api/mobile/v1/status')
@app.get('/api/mobile/v1')
@app.get('/api/v1/mobile')
@app.get('/api/v1/mobile/status')
def mobile_api_capabilities():
    return _mobile_json_response({'product':'fielanzen-dashboard','mobile_api':1,
       'status':'available','authentication':'api_key_bearer',
       'features':{'accounts':True,'categories':True,'payees':True,'bookings':True,
                   'create_booking':True,'update_booking':True,'delete_booking':True,
                   'server_authoritative':True,'offline_conflict_merge':False},
       'server_base_path':'/api/mobile/v1',
       'message':'Online-Servermodus verfügbar. Kein automatischer Import lokaler Android-Daten.'})


@app.post('/settings/mobile-keys/create')
@admin_required
def mobile_key_create():
    if not csrf_ok(): abort(400)
    if not verify_admin_stepup():
        flash('Für die Erstellung bitte Admin-Passwort und einen frischen 2FA-Code eingeben.','error')
        return redirect(url_for('settings')+'#mobile-keys')
    label=request.form.get('label','').strip()[:80]
    access=request.form.get('access','read')
    if not label or access not in ('read','write'):
        flash('Gerätenamen und Berechtigung prüfen.','error')
        return redirect(url_for('settings')+'#mobile-keys')
    user=current_user()
    token='fm1_'+secrets.token_urlsafe(32)
    digest=hashlib.sha256(('FieLanzen-Mobile-Key-v1:'+token).encode()).hexdigest()
    now=int(time.time())
    with get_db() as db:
        db.execute('''INSERT INTO mobile_api_keys(user_id,user_version,label,key_hash,access,issued_on,expires_on)
                      VALUES(?,?,?,?,?,?,?)''',
                   (user['id'],user['version'],label,digest,access,now,now+90*86400))
        audit(db,'mobile_key_created',label,actor_id=user['id'])
    return render_template('mobile_key_created.html',secret=token,label=label,access=access)


@app.post('/settings/mobile-keys/<int:key_id>/revoke')
@admin_required
def mobile_key_revoke(key_id):
    if not csrf_ok(): abort(400)
    if not verify_admin_stepup():
        flash('Sperren bitte mit Admin-Passwort und frischem 2FA-Code bestätigen.','error')
        return redirect(url_for('settings')+'#mobile-keys')
    with get_db() as db:
        key=db.execute('SELECT label FROM mobile_api_keys WHERE id=?',(key_id,)).fetchone()
        if key is None: abort(404)
        db.execute('UPDATE mobile_api_keys SET revoked_on=? WHERE id=? AND revoked_on IS NULL',
                   (int(time.time()),key_id))
        audit(db,'mobile_key_revoked',key['label'])
    flash('Geräteschlüssel gesperrt.','success')
    return redirect(url_for('settings')+'#mobile-keys')


@app.get('/api/mobile/v1/session')
def mobile_api_session():
    user,error=_mobile_require()
    if error:return error
    with get_db() as db:
        mode=finance_setting(db,'finance_mode','import')
    return _mobile_json_response({'username':user['username'],'role':user['role'],
        'access':user['access'],'finance_mode':mode,'can_write':mode=='web' and user['access']=='write'
        and user['role'] in ('admin','editor')})


@app.get('/api/mobile/v1/accounts')
def mobile_api_accounts():
    user,error=_mobile_require()
    if error:return error
    with get_db() as db:
        rows=db.execute('''SELECT a.id,a.title,c.code currency_code,c.symbol,c.decimals,
                     s.balance_minor,s.is_active,s.include_in_totals
                     FROM accounts a JOIN currencies c ON c.id=a.currency_id
                     LEFT JOIN account_snapshots s ON s.account_id=a.id
                     ORDER BY a.title COLLATE NOCASE''').fetchall()
        future=future_account_deltas(db,datetime.now(MONTH_TZ).date().isoformat())
    return _mobile_json_response({'items':[{'id':r['id'],'name':r['title'],
         'currency':r['currency_code'],'symbol':r['symbol'],'decimals':r['decimals'],
         'balance_minor':r['balance_minor']-future.get(r['id'],0) if r['balance_minor'] is not None else None,
         'projected_balance_minor':r['balance_minor'],'active':bool(r['is_active']),
         'included_in_total':bool(r['include_in_totals'])} for r in rows]})


@app.get('/api/mobile/v1/categories')
def mobile_api_categories():
    user,error=_mobile_require()
    if error:return error
    with get_db() as db:
        rows=db.execute('SELECT id,title,kind FROM categories ORDER BY title COLLATE NOCASE').fetchall()
    return _mobile_json_response({'items':[{'id':r['id'],'name':r['title'],
        'kind':'expense' if r['kind']==0 else 'income'} for r in rows]})


@app.get('/api/mobile/v1/payees')
def mobile_api_payees():
    user,error=_mobile_require()
    if error:return error
    with get_db() as db:
        rows=db.execute('SELECT id,title FROM payees ORDER BY title COLLATE NOCASE').fetchall()
    return _mobile_json_response({'items':[{'id':r['id'],'name':r['title']} for r in rows]})


@app.get('/api/mobile/v1/bookings')
def mobile_api_bookings():
    user,error=_mobile_require()
    if error:return error
    try:
        limit=max(1,min(200,int(request.args.get('limit','100'))))
        cursor=int(request.args.get('before','0'))
        if cursor < 0: raise ValueError()
    except (TypeError,ValueError):
        return _mobile_denied(400,'Ungültige Paginierung.')
    with get_db() as db:
        sql=_mobile_book_query()+' WHERE t.is_template=0'
        params=[]
        if cursor:
            sql+=' AND t.id<?';params.append(cursor)
        sql+=' ORDER BY t.id DESC LIMIT ?';params.append(limit+1)
        rows=db.execute(sql,params).fetchall()
    page=rows[:limit]
    return _mobile_json_response({'items':[_mobile_booking(r) for r in page],
         'next_before':page[-1]['id'] if len(rows)>limit else None})


def _mobile_payload(db, data):
    if not isinstance(data,dict):raise ValueError('JSON-Objekt erforderlich.')
    kind=data.get('kind','')
    if kind not in ('income','expense','transfer'):
        raise ValueError('Ungültige Buchungsart.')
    day=data.get('date','')
    if not isinstance(day,str) or not re.fullmatch(r'20\d\d-(0[1-9]|1[0-2])-([0-2]\d|3[01])',day):
        raise ValueError('Ungültiges Datum.')
    try: date.fromisoformat(day)
    except ValueError:raise ValueError('Ungültiges Kalenderdatum.') from None
    account_id=int(data.get('account_id',0))
    account=existing_account(db,account_id)
    amount=data.get('amount_minor')
    if isinstance(amount,bool) or not isinstance(amount,int) or amount<=0 or amount>10**15:
        raise ValueError('Ungültiger positiver Betrag (Minor Units).')
    target=int(data.get('to_account_id') or 0)
    if kind=='transfer':
        destination=existing_account(db,target)
        if target==account_id or destination['currency_id']!=account['currency_id']:
            raise ValueError('Umbuchung benötigt ein anderes Konto derselben Währung.')
    elif target:
        raise ValueError('Nur Umbuchungen haben ein Zielkonto.')
    category=int(data.get('category_id') or 0)
    if kind=='transfer':
        category=0
    elif category:
        row=db.execute('SELECT kind FROM categories WHERE id=?',(category,)).fetchone()
        if not row or int(row['kind'])!=(1 if kind=='income' else 0):
            raise ValueError('Kategorie passt nicht zur Buchungsart.')
    payee_id=int(data.get('payee_id') or 0)
    if payee_id:
        if not db.execute('SELECT 1 FROM payees WHERE id=?',(payee_id,)).fetchone():
            raise ValueError('Empfänger existiert nicht.')
    else:
        title=data.get('payee_title','')
        if not isinstance(title,str) or len(title)>120:
            raise ValueError('Ungültiger Empfänger.')
        payee_id=entry_payee(db,title)

    note=data.get('note','')
    if not isinstance(note,str) or len(note)>1000:
        raise ValueError('Notiz zu lang.')
    return {'day':day,'account_id':account_id,'to_account_id':target,
      'category_id':category,'payee_id':payee_id,
      'amount':amount if kind=='income' else -amount,'note':note,'is_template':0}


def _mobile_body_and_request_id():
    data=request.get_json(silent=True)
    if not isinstance(data,dict):raise ValueError('JSON-Objekt erforderlich.')
    rid=request.headers.get('Idempotency-Key','')
    try:
        if str(_MobileUUID(rid))!=rid.lower():raise ValueError()
    except (TypeError,ValueError,AttributeError):
        raise ValueError('Idempotency-Key muss eine UUID sein.') from None
    return data,rid


def _mobile_receipt(db,user,request_id,operation,payload):
    fingerprint=hashlib.sha256(_mobile_json.dumps(payload,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    old=db.execute('SELECT operation,fingerprint,response_json FROM mobile_api_receipts WHERE key_id=? AND request_id=?',
                   (user['key_id'],request_id)).fetchone()
    if old:
        if old['operation']!=operation or old['fingerprint']!=fingerprint:
            raise ValueError('Idempotency-Key wurde mit anderen Daten wiederverwendet.')
        return _mobile_json.loads(old['response_json']),fingerprint
    return None,fingerprint


def _mobile_save_receipt(db,user,rid,operation,fingerprint,result):
    db.execute('''INSERT INTO mobile_api_receipts(key_id,request_id,operation,fingerprint,response_json,created_on)
                  VALUES(?,?,?,?,?,?)''',(user['key_id'],rid,operation,fingerprint,
                  _mobile_json.dumps(result,ensure_ascii=False),int(time.time())))


@app.post('/api/mobile/v1/bookings')
def mobile_api_create_booking():
    user,error=_mobile_require(write=True)
    if error:return error
    try:data,rid=_mobile_body_and_request_id()
    except ValueError as exc:return _mobile_denied(400,str(exc))
    try:
        with get_db() as db:
            db.execute('BEGIN IMMEDIATE')
            old,fingerprint=_mobile_receipt(db,user,rid,'create',data)
            if old is not None:return _mobile_json_response(old)
            values=_mobile_payload(db,data)
            row=db.execute('''INSERT INTO transactions(day,account_id,to_account_id,category_id,
                payee_id,amount,note,is_template,origin)
                VALUES(:day,:account_id,:to_account_id,:category_id,:payee_id,:amount,:note,0,'web')''',values)
            apply_balance_delta(db,values,+1)
            db.execute("UPDATE meta SET value=CAST(value AS INTEGER)+1 WHERE key='ledger_web_writes'")
            audit(db,'mobile_booking_created',str(row.lastrowid),actor_id=user['user_id'])
            response={'id':row.lastrowid,'saved':True}
            _mobile_save_receipt(db,user,rid,'create',fingerprint,response)
        return _mobile_json_response(response,201)
    except (ValueError,sqlite3.Error) as exc:
        return _mobile_denied(409,str(exc))


def _mobile_edit_booking(booking_id,delete=False):
    user,error=_mobile_require(write=True)
    if error:return error
    try:data,rid=_mobile_body_and_request_id()
    except ValueError as exc:return _mobile_denied(400,str(exc))
    expected=request.headers.get('If-Match','')
    if not re.fullmatch(r'[0-9a-f]{32}',expected):
        return _mobile_denied(428,'If-Match mit aktueller Buchungsrevision erforderlich.')
    op='delete' if delete else 'update'
    try:
        with get_db() as db:
            db.execute('BEGIN IMMEDIATE')
            payload={'id':booking_id,'revision':expected,'data':data}
            previous,fingerprint=_mobile_receipt(db,user,rid,op,payload)
            if previous is not None:return _mobile_json_response(previous)
            old=db.execute(_mobile_book_query()+' WHERE t.id=? AND t.is_template=0',(booking_id,)).fetchone()
            if old is None:return _mobile_denied(404,'Buchung nicht vorhanden.')
            if _mobile_book_hash(old)!=expected:
                return _mobile_denied(409,'Buchung wurde inzwischen verändert. Bitte neu laden.')
            if db.execute('SELECT 1 FROM recurring_runs WHERE booking_id=? LIMIT 1',(booking_id,)).fetchone():
                return _mobile_denied(409,'Wiederkehrende Buchung bitte in der Weboberfläche bearbeiten.')
            if delete:
                apply_balance_delta(db,old,-1)
                db.execute('DELETE FROM transactions WHERE id=?',(booking_id,))
            else:
                row=_mobile_payload(db,data)
                apply_balance_delta(db,old,-1)
                db.execute('''UPDATE transactions SET day=:day,account_id=:account_id,
                  to_account_id=:to_account_id,category_id=:category_id,payee_id=:payee_id,
                  amount=:amount,note=:note,is_template=0,origin='web' WHERE id=:id''',
                  {**row,'id':booking_id})
                apply_balance_delta(db,row,+1)
            db.execute("UPDATE meta SET value=CAST(value AS INTEGER)+1 WHERE key='ledger_web_writes'")
            audit(db,'mobile_booking_deleted' if delete else 'mobile_booking_updated',str(booking_id),actor_id=user['user_id'])
            result={'id':booking_id,'deleted':delete,'saved':not delete}
            _mobile_save_receipt(db,user,rid,op,fingerprint,result)
        return _mobile_json_response(result)
    except (ValueError,sqlite3.Error) as exc:
        return _mobile_denied(409,str(exc))


@app.put('/api/mobile/v1/bookings/<int:booking_id>')
def mobile_api_update_booking(booking_id):
    return _mobile_edit_booking(booking_id)


@app.delete('/api/mobile/v1/bookings/<int:booking_id>')
def mobile_api_delete_booking(booking_id):
    return _mobile_edit_booking(booking_id,delete=True)
