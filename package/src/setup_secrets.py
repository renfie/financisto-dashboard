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

# Language is selected before the interactive first-time installer starts.
# The installed DEFAULT_LANGUAGE is only a default: each browser can switch
# language via DE / EN independently during its current session.
import builtins as _builtins
_ORIGINAL_INPUT = _builtins.input
_ORIGINAL_PRINT = _builtins.print
_ORIGINAL_GETPASS = getpass.getpass
INSTALL_LANGUAGE = 'de'

_INSTALL_EN = {
    'Bitte als normaler Benutzer ohne sudo installieren.': 'Install as a normal user without sudo.',
    'Installation muss als Projektbenutzer ausgeführt werden.': 'Please run the installer as the project owner.',
    'Bitte genau eine gültige IPv4- oder IPv6-Adresse eingeben.': 'Enter exactly one valid IPv4 or IPv6 address.',
    'IP oder DNS-Name des Docker-Servers für HTTPS (ohne Port): ': 'Docker server IP or DNS hostname for HTTPS (without port): ',
    'Ungültiger Hostname oder Server-IP.': 'Invalid server hostname or IP address.',
    'HTTPS-Port auf dem Host [8443]: ': 'HTTPS port on host [8443]: ',
    'Ungültiger Port (1–65535).': 'Invalid port number (1–65535).',
    'Sicheres Admin-Passwort automatisch generieren? [J/n]: ': 'Automatically generate a secure admin password? [Y/n]: ',
    'Admin-Passwort (mind. 12 Zeichen): ': 'Admin password (at least 12 characters): ',
    'Passwort wiederholen: ': 'Repeat password: ',
    'Passwort zu kurz oder Eingaben stimmen nicht überein.': 'Password is too short or entries do not match.',
    'Das Passwort darf keine Zeilenumbrüche enthalten.': 'Password must not contain line breaks.',
    'Ersteinrichtung Financisto-Dashboard': 'Financisto Dashboard initial setup',
    'Das erste freigegebene Gerät sollte eine feste IP/DHCP-Reservierung besitzen.': 'The first authorized device should have a static IP or DHCP reservation.',
    'IP-Adresse des ersten freigegebenen PCs: ': 'IP address of the first authorized computer: ',
    'Secrets und Bind-Mounts eingerichtet.': 'Secrets and persistent bind mounts configured.',
    '\nNEUES ADMIN-PASSWORT (nur einmal angezeigt):': '\nNEW ADMIN PASSWORD (displayed only once):',
    'Bitte sofort sicher verwahren und nicht in Tickets/Chats kopieren.\n': 'Store it securely now; never copy it into tickets or chats.\n',
    'Starte zunächst nur die Anwendung.': 'Starting only the application first.',
    'Prüfe das Installationspasswort mit der echten Anmeldefunktion im Container ...': 'Verifying the installation password using the real login function inside the container ...',
    'PASSWORTPRÜFUNG IM CONTAINER ERFOLGREICH': 'PASSWORD VERIFIED SUCCESSFULLY INSIDE THE CONTAINER',
    'Benutzername: admin': 'Username: admin',
    'Caddy verwendet eine lokale CA. Root-Zertifikat auf freigegebenen PCs installieren.': 'Caddy uses a local CA. Install its root certificate on authorized computers.',
    'Aktuelles Admin-Passwort zum Prüfen (keine Änderung): ': 'Current admin password for verification (no changes): ',
    'Bestehendes Admin-Passwort (keine Änderung): ': 'Existing admin password (no changes): ',
    'Installation fortgesetzt. Keine Secrets überschrieben.': 'Setup resumed. No existing secrets were overwritten.',
    'Installation oder Admin-Secret fehlt; nichts verändert.': 'Installation or admin secret is missing; nothing was changed.',
    'Unvollständige Installationsdateien, keine Secrets geändert.': 'Incomplete installation files; no secrets changed.',
    'Verwendung: install.sh [--verify|--resume]': 'Usage: install.sh [--verify|--resume]',
    'Die Passwortprüfung in der laufenden Anwendung war nicht erfolgreich.': 'Password verification inside the running application failed.',
    'Diese Instanz ist bereits eingerichtet. Es wurden keine Daten oder Zugangsdaten verändert. Für Updates: docker compose up -d --build. Zum Login-Test: ./install.sh --verify.': 'This installation already exists. No data or credentials were changed. For updates, use the release update.sh. To verify login: ./install.sh --verify.',
    'INSTALLATION NICHT ABGESCHLOSSEN: Passwort wurde vom laufenden Dashboard nicht bestätigt. Caddy wurde deshalb nicht gestartet. Prüfe die Dashboard-Logs und den Secret-Mount, ohne Secrets zu löschen.': 'INSTALLATION INCOMPLETE: The dashboard did not confirm the password. Caddy was not started. Check dashboard logs and the secret mount without deleting secrets.',
    'PASSWORTPRÜFUNG FEHLGESCHLAGEN: ': 'PASSWORD VERIFICATION FAILED: ',
    'Installation nicht vollständig: Docker-Befehl fehlgeschlagen (Exit ': 'Installation incomplete: Docker command failed (Exit ',
    'Die angelegten Secrets und Daten bleiben erhalten.': 'Created secrets and data remain intact.',
}


def t(message):
    text = str(message)
    if INSTALL_LANGUAGE != 'en':
        return text
    normalized = ' '.join(text.split())
    if normalized in _INSTALL_EN:
        return _INSTALL_EN[normalized]
    for german, english in _INSTALL_EN.items():
        if text.startswith(german) and len(german) > 10:
            return english + text[len(german):]
    if text.startswith('Port ') and 'ist bereits belegt' in text:
        return text.replace('ist bereits belegt. Bitte einen anderen Port wählen.', 'is already in use. Choose another port.')
    if text.startswith('\nInstallation abgeschlossen. URL:'):
        return text.replace('Installation abgeschlossen', 'Installation complete')
    return text


def input(prompt=''):
    return _ORIGINAL_INPUT(t(prompt))


def print(*args, **kwargs):
    return _ORIGINAL_PRINT(*(t(x) if isinstance(x, str) else x for x in args), **kwargs)


def password_prompt(prompt=''):
    return _ORIGINAL_GETPASS(t(prompt))

getpass.getpass = password_prompt


def choose_install_language():
    global INSTALL_LANGUAGE
    while True:
        answer = _ORIGINAL_INPUT('Sprache wählen / Select language [1=Deutsch, 2=English] (1): ').strip().lower()
        if answer in ('', '1', 'de', 'deutsch', 'german'):
            INSTALL_LANGUAGE = 'de'
            return
        if answer in ('2', 'en', 'english', 'englisch'):
            INSTALL_LANGUAGE = 'en'
            return
        _ORIGINAL_PRINT('Bitte 1 oder 2 eingeben / Please enter 1 or 2.')


def use_installed_language():
    global INSTALL_LANGUAGE
    if ENV.exists():
        for line in ENV.read_text(encoding='utf-8').splitlines():
            if line.startswith('DEFAULT_LANGUAGE='):
                selected = line.partition('=')[2].strip().strip('"\'').lower()
                if selected in ('en', 'de'):
                    INSTALL_LANGUAGE = selected
                return


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
    if mode not in ('n', 'nein', 'no'):
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
        f'SITE_HOST={host}\nSITE_ADDRESSES=https://{host}\nTRUSTED_PROXY_IPS=127.0.0.1/32\nHTTPS_PORT={port}\nHTTPS_BIND_IP=0.0.0.0\nAPP_UID={uid}\nAPP_GID={gid}\nAPP_TITLE="Financisto"\nAPP_SUBTITLE="Dashboard"\nAPP_FOOTER="Privates Finanz-Dashboard · Daten bleiben auf deinem Server"\nDEFAULT_LANGUAGE={INSTALL_LANGUAGE}\n',
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
        raise SystemExit(t('PASSWORTPRÜFUNG FEHLGESCHLAGEN: ') + t(error))
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
    if len(sys.argv) == 2 and sys.argv[1] == '--install':
        choose_install_language()
    else:
        use_installed_language()
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
        raise SystemExit(t(str(exc))) from None
    except SystemExit as exc:
        raise SystemExit(t(str(exc))) from None
