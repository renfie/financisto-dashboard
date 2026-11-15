#!/usr/bin/env bash
# One-time, host-level SFTP setup for Financisto Dashboard, revision 2.
# The dashboard project is NOT updated by this script.
set -Eeuo pipefail

PROJECT="${FINANCISTO_PROJECT:-/home/pi/docker-files/financisto-dashboard}"
INBOX="$PROJECT/data/inbox"
UPLOAD_USER='financisto-sync'
UPLOAD_GROUP='financisto-sftp'
JAIL='/srv/financisto-sftp'
SSHD_CONFIG='/etc/ssh/sshd_config'

fail() { printf 'FEHLER: %s\n' "$*" >&2; exit 1; }
[[ $EUID -eq 0 ]] || fail 'Nur die einmalige SSH-Systemeinrichtung benötigt sudo: sudo bash ./setup_financisto_sftp.sh'
for cmd in getent useradd groupadd chgrp chmod chown install mount mountpoint findmnt stat sshd setfacl python3 chpasswd systemctl; do
  command -v "$cmd" >/dev/null 2>&1 || { [[ "$cmd" == sshd && -x /usr/sbin/sshd ]] || fail "Programm fehlt: $cmd (für setfacl: sudo apt install acl)"; }
done
[[ -d "$INBOX" && -f "$PROJECT/compose.yaml" ]] || fail "Projekt / Inbox nicht gefunden: $PROJECT"
[[ ! -L "$INBOX" ]] || fail 'Inbox darf kein symbolischer Link sein'
[[ -f "$SSHD_CONFIG" ]] || fail 'Keine OpenSSH-Systemkonfiguration gefunden'
APP_UID="$(stat -c %u "$PROJECT")"
APP_USER="$(getent passwd "$APP_UID" | cut -d: -f1)"
[[ -n "$APP_USER" && "$APP_UID" != 0 ]] || fail 'Projekt muss einem regulären Linux-Benutzer gehören'
# A previously prepared SFTP inbox may be owned by root while its ACLs
# grant the application user access. Both are valid; do not chown the jail.
INBOX_UID="$(stat -c %u "$INBOX")"
[[ "$INBOX_UID" == "$APP_UID" || "$INBOX_UID" == 0 ]] || fail "Inbox hat unerwarteten Besitzer UID $INBOX_UID"
[[ -d /srv && "$(stat -c %u /srv)" == 0 ]] || fail '/srv muss Root gehören'
[[ ! -e "$JAIL" || ( -d "$JAIL" && ! -L "$JAIL" ) ]] || fail 'Unerwarteter Chroot-Pfad'
if getent passwd "$UPLOAD_USER" >/dev/null; then
  [[ "$(getent passwd "$UPLOAD_USER" | cut -d: -f6)" == /upload ]] || fail "Benutzer $UPLOAD_USER existiert bereits mit anderem Home – Sicherheitsabbruch"
fi

printf 'Financisto-Projekt: %s\nProjektbesitzer: %s (UID %s)\nSSH-Zugang: %s (SFTP-only)\n' "$PROJECT" "$APP_USER" "$APP_UID" "$UPLOAD_USER"

# Keep the host pi / admin SSH account entirely unchanged.
getent group "$UPLOAD_GROUP" >/dev/null || groupadd --system "$UPLOAD_GROUP"
if ! getent passwd "$UPLOAD_USER" >/dev/null; then
  useradd --system --gid "$UPLOAD_GROUP" --home-dir /upload --shell /usr/sbin/nologin --no-create-home "$UPLOAD_USER"
fi

install -d -o root -g root -m 0755 "$JAIL"
install -d -o root -g root -m 0755 "$JAIL/upload"
if mountpoint -q "$JAIL/upload"; then
  [[ "$(stat -c %d:%i "$JAIL/upload")" == "$(stat -c %d:%i "$INBOX")" ]] || fail "Upload ist bereits von einem anderen Verzeichnis eingehängt"
else
  mount --bind "$INBOX" "$JAIL/upload"
fi

chgrp "$UPLOAD_GROUP" "$INBOX"
chmod 2770 "$INBOX"
# The dashboard runs in Docker with the owner's numeric UID (not host supplementary groups).
# A default ACL lets that UID read files uploaded by the separate SFTP user.
setfacl -m "u:${APP_UID}:rwx" "$INBOX"
setfacl -d -m "u:${APP_UID}:rwx" "$INBOX"

# Retain the bind mount after reboot; never mount the whole project into the jail.
cp -p /etc/fstab "/etc/fstab.financisto-before-$(date +%Y%m%d-%H%M%S)"
if ! grep -Fq "$INBOX $JAIL/upload none bind,nofail 0 0" /etc/fstab; then
  printf '%s %s none bind,nofail 0 0\n' "$INBOX" "$JAIL/upload" >>/etc/fstab
fi

# Append the Match clause *after* existing global directives. Putting Match in an
# include file included at the top may invalidate subsequent global sshd options.
SSHD_BACKUP="${SSHD_CONFIG}.financisto-before-$(date +%Y%m%d-%H%M%S)"
cp -p "$SSHD_CONFIG" "$SSHD_BACKUP"
restore_ssh_config() { cp -p "$SSHD_BACKUP" "$SSHD_CONFIG"; }
if ! grep -Fq '# BEGIN FINANCISTO SFTP' "$SSHD_CONFIG"; then
  cat >> "$SSHD_CONFIG" <<'EOF'

# BEGIN FINANCISTO SFTP
Match User financisto-sync
    ChrootDirectory /srv/financisto-sftp
    ForceCommand internal-sftp -d /upload -u 0007
    PasswordAuthentication yes
    DisableForwarding yes
    PermitTTY no
    X11Forwarding no
# END FINANCISTO SFTP
EOF
fi

SSHD_BIN="$(command -v sshd || echo /usr/sbin/sshd)"
if ! "$SSHD_BIN" -t; then
  restore_ssh_config
  fail 'sshd -t ist fehlgeschlagen. SSH-Konfiguration wurde zurückgesetzt; SSH NICHT neu geladen.'
fi
# Capture the COMPLETE effective configuration first. Under `set -o pipefail`,
# `sshd -T | grep -q` can fail even when the rule matches because grep closes
# the pipe early and sshd receives SIGPIPE.
if ! SSH_EFFECTIVE="$("$SSHD_BIN" -T -C "user=${UPLOAD_USER},host=homesrv,addr=192.168.2.100")"; then
  restore_ssh_config
  fail 'sshd -T konnte die wirksame SSH-Konfiguration nicht ermitteln. Änderung rückgängig gemacht.'
fi
EXPECTED_CHROOT='chrootdirectory /srv/financisto-sftp'
ACTUAL_CHROOT="$(printf '%s\n' "$SSH_EFFECTIVE" | grep -i '^chrootdirectory ' || true)"
ACTUAL_FORCE="$(printf '%s\n' "$SSH_EFFECTIVE" | grep -i '^forcecommand ' || true)"
if [[ "$ACTUAL_CHROOT" != "$EXPECTED_CHROOT" ]]; then
  restore_ssh_config
  printf 'Wirksame SSH-Einstellung: %s\n' "${ACTUAL_CHROOT:-keine Chroot-Regel}" >&2
  fail 'SFTP-Chroot nicht wirksam. Eventuell überschreibt eine frühere Match-Regel die Konfiguration. SSH-Änderung rückgängig gemacht.'
fi
if [[ "$ACTUAL_FORCE" != 'forcecommand internal-sftp -d /upload -u 0007' ]]; then
  restore_ssh_config
  printf 'Wirksame SSH-Einstellung: %s\n' "${ACTUAL_FORCE:-kein ForceCommand}" >&2
  fail 'SFTP-ForceCommand nicht wirksam. SSH-Änderung rückgängig gemacht.'
fi

if ! systemctl reload ssh && ! systemctl reload sshd; then
  restore_ssh_config
  fail 'SSH-Neuladen fehlgeschlagen; SSH-Konfiguration wurde zurückgesetzt. Bestehende Sitzung offen lassen und Logs prüfen.'
fi
PASSWORD="$(python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(24))
PY
)"
printf '%s:%s\n' "$UPLOAD_USER" "$PASSWORD" | chpasswd

printf '\nEINRICHTUNG ERFOLGREICH\n'
SFTP_HOST="$(sed -n 's/^SITE_HOST=//p' "$PROJECT/.env" | head -n 1)"
printf 'Host: %s\nPort: 22 (vorherigen SSH-Port verwenden, falls abweichend)\n' "${SFTP_HOST:-IP-Adresse-von-homesrv}"
printf 'SFTP-Benutzer: %s\n' "$UPLOAD_USER"
printf 'SFTP-Passwort: %s\n' "$PASSWORD"
printf 'SFTP-Zielordner in FolderSync: /upload\n'
printf '\nACHTUNG: Passwort nur hier ablesen und nicht in den Chat senden. Kein Router-Portforwarding einrichten.\n'
