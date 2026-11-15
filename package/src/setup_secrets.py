#!/usr/bin/env python3
"""Safe first-time installation and non-destructive password verification.

No password is put into process arguments, command history, the .env file, or
persistent plaintext files. The running application's own check_password()
is exercised before the Caddy frontend is started.
"""

import getpass
import hashlib
import ipaddress
import os
import pwd
import re
import secrets
import socket
import subprocess
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SECRETS = BASE / 'secrets'
ENV = BASE / '.env'

# IMPORTANT: Same secret names and format as the released app.py. Changing
# this format without changing the application would break existing logins.
def project_owner():
    """Install as the current non-root owner, independent of local account name."""
    if os.geteuid() == 0:
        raise SystemExit('Bitte als normaler Benutzer ohne sudo installieren.')
    return os.getuid(), os.getgid()


def owner_path(path, uid, gid):
    if (uid, gid) != (os.getuid(), os.getgid()):
        raise RuntimeError("Installation muss als Projektbenutzer ausgeführt werden.")



def ask_ip(prompt):
    while True:
        value = input(prompt).strip()
        try:
            return str(ipaddress.ip_address(value))
        except ValueError:
            print('Bitte genau eine gültige IPv4- oder IPv6-Adresse eingeben.')


def ask_site_host():
    while True:
        host = input('IP oder DNS-Name des Docker-Servers für HTTPS (ohne Port): ').strip()
        if host and len(host) < 250 and re.fullmatch(r'[A-Za-z0-9.\-]+', host) and not host.startswith('-'):
            return host
        print('Ungültiger Hostname oder Server-IP.')


def port_is_free(port):
    # Compose binds on 0.0.0.0 by default, so test that exact address.
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(('0.0.0.0', port))
        return True
    except OSError:
        return False


def ask_https_port():
    while True:
        value = input('HTTPS-Port auf dem Host [8443]: ').strip() or '8443'
        if not value.isdecimal() or not 1 <= int(value) <= 65535:
            print('Ungültiger Port (1–65535).')
            continue
        port = int(value)
        if not port_is_free(port):
            print(f'Port {port} ist bereits belegt. Bitte einen anderen Port wählen.')
            continue
        return port


def ask_password():
    mode = input('Sicheres Admin-Passwort automatisch generieren? [J/n]: ').strip().lower()
    if mode not in ('n', 'nein'):
        return secrets.token_urlsafe(24), True
    while True:
        password = getpass.getpass('Admin-Passwort (mind. 12 Zeichen): ')
        confirm = getpass.getpass('Passwort wiederholen: ')
        if len(password) < 12 or password != confirm:
            print('Passwort zu kurz oder Eingaben stimmen nicht überein.')
            continue
        if '\n' in password or '\r' in password:
            print('Das Passwort darf keine Zeilenumbrüche enthalten.')
            continue
        return password, False


def make_password_hash(password):
    salt = secrets.token_bytes(32)
    rounds = 600_000
    digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, rounds).hex()
    return f'pbkdf2_sha256:{rounds}:{salt.hex()}:{digest}'


def verify_password_in_container(password):
    """Call the actual application verifier; secret travels through stdin only."""
    script = (
        'import app, sys; '
        'password = sys.stdin.readline().rstrip("\\n"); '
        'sys.exit(0 if app.check_password(password) else 17)'
    )
    try:
        result = subprocess.run(
            ['docker', 'compose', 'exec', '-T', 'dashboard', 'python', '-c', script],
            cwd=BASE, input=password + '\n', text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f'Containerprüfung konnte nicht durchgeführt werden: {exc}'
    if result.returncode != 0:
        # NEVER print stderr: an unexpected dependency might log sensitive data.
        return False, 'Die Passwortprüfung in der laufenden Anwendung war nicht erfolgreich.'
    return True, ''


def test_until_ready(password):
    for _ in range(30):
        ok, err = verify_password_in_container(password)
        if ok:
            return
        time.sleep(1)
    raise RuntimeError(
        'INSTALLATION NICHT ABGESCHLOSSEN: Passwort wurde vom laufenden '
        'Dashboard nicht bestätigt. Caddy wurde deshalb nicht gestartet. '
        'Prüfe die Dashboard-Logs und den Secret-Mount, ohne Secrets zu löschen.'
    )


def install():
    if ENV.exists() or SECRETS.exists():
        raise SystemExit(
            'Diese Instanz ist bereits eingerichtet. Es wurden keine Daten '
            'oder Zugangsdaten verändert. Für Updates: docker compose up -d --build. '
            'Zum Login-Test: ./install.sh --verify.'
        )
    print('Ersteinrichtung Financisto-Dashboard')
    print('Das erste freigegebene Gerät sollte eine feste IP/DHCP-Reservierung besitzen.')
    ip = ask_ip('IP-Adresse des ersten freigegebenen PCs: ')
    host = ask_site_host()
    port = ask_https_port()
    password, generated = ask_password()

    uid,gid=project_owner()
    os.umask(0o077)
    SECRETS.mkdir(mode=0o700)
    salt_hash = make_password_hash(password)
    entries = {
        'app_secret': secrets.token_urlsafe(48),
        'admin_password_hash': salt_hash,
        'initial_ip': ip,
    }
    for name, value in entries.items():
        path = SECRETS / name
        path.write_text(value + '\n', encoding='utf-8')
        path.chmod(0o600)
        owner_path(path,uid,gid)
    owner_path(SECRETS,uid,gid)
    ENV.write_text(
        f'SITE_HOST={host}\nSITE_ADDRESSES=https://{host}\nTRUSTED_PROXY_IPS=127.0.0.1/32\nHTTPS_PORT={port}\nHTTPS_BIND_IP=0.0.0.0\nAPP_UID={uid}\nAPP_GID={gid}\nAPP_TITLE="Financisto"\nAPP_SUBTITLE="Dashboard"\nAPP_FOOTER="Privates Finanz-Dashboard · Daten bleiben auf deinem Server"\n',
        encoding='utf-8',
    )
    ENV.chmod(0o600)
    owner_path(ENV,uid,gid)
    (BASE / 'data').mkdir(exist_ok=True)
    owner_path(BASE / 'data',uid,gid)
    (BASE / 'data').chmod(0o700)
    (BASE / 'data' / 'inbox').mkdir(exist_ok=True)
    owner_path(BASE / 'data' / 'inbox',uid,gid)
    (BASE / 'caddy' / 'data').mkdir(parents=True, exist_ok=True)
    (BASE / 'caddy' / 'config').mkdir(parents=True, exist_ok=True)
    owner_path(BASE / 'caddy',uid,gid)
    owner_path(BASE / 'caddy' / 'data',uid,gid)
    owner_path(BASE / 'caddy' / 'config',uid,gid)
    # The project itself and shipped code belong to the selected user, not root.
    # Dateien werden bereits vom aufrufenden Projektbenutzer erstellt.
    # Kein chown notwendig oder zulässig.

    print('Secrets und Bind-Mounts eingerichtet.')
    # Display the generated password BEFORE invoking Docker. Even if a build
    # fails, the administrator has the password corresponding to the hash.
    if generated:
        print('\nNEUES ADMIN-PASSWORT (nur einmal angezeigt):', password)
        print('Bitte sofort sicher verwahren und nicht in Tickets/Chats kopieren.\n')

    print('Starte zunächst nur die Anwendung.')
    # A failed password verification must prevent exposing the service via Caddy.
    subprocess.run(['docker', 'compose', 'config', '--quiet'], cwd=BASE, check=True)
    subprocess.run(['docker', 'compose', 'up', '-d', '--build', 'dashboard'], cwd=BASE, check=True)

    print('Prüfe das Installationspasswort mit der echten Anmeldefunktion im Container ...')
    test_until_ready(password)
    print('PASSWORTPRÜFUNG IM CONTAINER ERFOLGREICH')

    subprocess.run(['docker', 'compose', 'up', '-d', 'caddy', 'background', 'notifications'], cwd=BASE, check=True)
    print(f'\nInstallation abgeschlossen. URL: https://{host}:{port}')
    print('Benutzername: admin')
    print('Caddy verwendet eine lokale CA. Root-Zertifikat auf freigegebenen PCs installieren.')


def verify():
    if not ENV.exists() or not (SECRETS / 'admin_password_hash').is_file():
        raise SystemExit('Installation oder Admin-Secret fehlt; nichts verändert.')
    password = getpass.getpass('Aktuelles Admin-Passwort zum Prüfen (keine Änderung): ')
    ok, error = verify_password_in_container(password)
    if not ok:
        raise SystemExit('PASSWORTPRÜFUNG FEHLGESCHLAGEN: ' + error)
    print('PASSWORTPRÜFUNG IM CONTAINER ERFOLGREICH')


def resume():
    """Continue a partial installation without modifying saved credentials."""
    if not ENV.exists() or not all((SECRETS / n).is_file() for n in ('app_secret', 'admin_password_hash', 'initial_ip')):
        raise SystemExit('Unvollständige Installationsdateien, keine Secrets geändert.')
    password = getpass.getpass('Bestehendes Admin-Passwort (keine Änderung): ')
    subprocess.run(['docker', 'compose', 'config', '--quiet'], cwd=BASE, check=True)
    subprocess.run(['docker', 'compose', 'up', '-d', '--build', 'dashboard'], cwd=BASE, check=True)
    test_until_ready(password)
    print('PASSWORTPRÜFUNG IM CONTAINER ERFOLGREICH')
    subprocess.run(['docker', 'compose', 'up', '-d', 'caddy', 'background', 'notifications'], cwd=BASE, check=True)
    print('Installation fortgesetzt. Keine Secrets überschrieben.')


def main():
    os.umask(0o077)
    if len(sys.argv) == 2 and sys.argv[1] == '--verify':
        verify()
    elif len(sys.argv) == 2 and sys.argv[1] == '--resume':
        resume()
    elif len(sys.argv) == 2 and sys.argv[1] == '--install':
        install()
    else:
        raise SystemExit('Verwendung: install.sh [--verify|--resume]')


if __name__ == '__main__':
    try:
        main()
    except subprocess.CalledProcessError as exc:
        raise SystemExit(
            f'Installation nicht vollständig: Docker-Befehl fehlgeschlagen (Exit {exc.returncode}). '
            'Die angelegten Secrets und Daten bleiben erhalten.'
        ) from None
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from None
