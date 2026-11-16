# Financisto Dashboard — Installation and Operations (English)

## New in v1.9.42 — Updated onboarding
- First-login tour updated for the v1.9.41 feature set in both English and German.
- Covers recurring limits, future-dated entries, roles and the language switch.
- Automatic tour remains limited to new users; existing users can replay it using [Help / introduction](docs/ONBOARDING.en.md).

## New in v1.9.41
- Fixed Payee and Category layout in the desktop/tablet transaction form. They are now in one row, Payee on the left and Category on the right. Smartphone layout is unchanged.
- No changes to transaction data, accounting logic or recurring rules.

## New in v1.9.40

The payee field now precedes the category field. Recurring schedules can be limited by an inclusive end date and/or a maximum number of actual occurrences; existing rules remain unlimited. Future-dated transactions are highlighted yellow in lists without delaying their existing impact on account balances.


**Deutsch:** [Ausführliche Dokumentation](README.md) · **English:** You are here

This is an English operations guide for the independently developed FieLanzen web dashboard. For a complete version-by-version history and additional technical details see the original [German manual](README.md) and the [technical documentation](docs/) (primarily German).

## Requirements

A Linux host with Python 3, Docker Engine and Docker Compose; a normal Linux account that owns the project directory and may access the Docker daemon. Do not run install or update scripts with `sudo` or as root.

The application uses Docker containers for the dashboard, a background worker, notifications, and Caddy (HTTPS). Account data, configuration, and secrets are persisted via bind mounts on the host, not in disposable containers.

## New installation

Extract the release ZIP into its own directory. From inside the release's `package` directory:

```bash
cd package
./install.sh
```

The setup wizard configures the project as the current user and checks the required environment and secrets. For interrupted initial setup:

```bash
./install.sh --resume
```

Verify an existing configuration:

```bash
./install.sh --verify
```

Do not install over an existing project directory or copy the release's `package/` tree directly onto production data.

## Update an existing installation

Extract a newer release into **a different directory** from the production installation. Run the updater as the normal user who owns the existing project:

```bash
/path/to/financisto-release-1.9.40/update.sh /path/to/existing/financisto-dashboard
```

A direct upgrade from v1.9.35 to v1.9.38 is supported: no intermediate version is required. The updater checks the directory structure, Docker access, file ownership and Python syntax before making changes. It backs up the prior source and uses SQLite's online backup API to create a consistent database snapshot. Configuration is preserved in the host's `.env` and secrets remain on the host.

The user-facing `.env` values such as `SITE_HOST`, `SITE_ADDRESSES`, `APP_TITLE`, `APP_SUBTITLE` and `APP_FOOTER` are retained when updating. Repository example hostnames (`finance.example.org`) are placeholders only and must be replaced for a **new installation**.

**Never use `docker compose down -v` on an existing installation**: removing volumes may remove information needed to restore the service.

## Caddy and HTTPS

Caddy is bundled with the Docker Compose application and is responsible for internal HTTPS and reverse-proxy access to the dashboard. It uses `tls internal`, so its local CA must be explicitly trusted for direct browser access. When using an upstream Nginx Proxy Manager, terminate public TLS there with a publicly trusted certificate and correctly configure proxy trust. Persistent `caddy/data/` and `caddy/config/` survive updates.

Read the full [Caddy and HTTPS guide](docs/CADDY.en.md) or the [German version](docs/CADDY.de.md).

## Data management

- **Manual import:** Financisto Android `.backup` archives can be imported explicitly using the web interface.
- **Automatic import:** Optional SFTP/FolderSync import can be enabled or disabled in the administrative interface.
- **Source-of-truth modes:** Financisto can remain the authoritative source, or the web application may become authoritative after an explicit switch. Import controls prevent unapproved overwrites of web changes.
- **Export:** Import/return-export compatibility has caveats; some operations involving Android restores remain experimental. Test round trips on nonproduction data.
- **Accounts and transactions:** Use the web interface to manage transactions and transfers where allowed by the active source-of-truth mode and assigned user role.
- **Recurring transactions:** Can be set to paused, manual, or automatic execution by authorized users; the background worker checks eligible schedules periodically.
- **Notifications:** Gotify, Telegram and Web Push support configuration per their respective administrative settings.

## Backups and recovery

The application's SQLite backups are **not** Android Financisto `.backup` archives. The background backup worker creates consistency-checked database snapshots. Store an additional encrypted copy away from the Docker host.

When restoring, preserve the original application secret: TOTP and other encrypted information cannot necessarily be recovered with a newly generated secret. The existing `restore.sh` includes verification and interactive confirmation.

See [Backup & Restore](docs/BACKUP_RESTORE.md) (German). Test a recovery in a separate installation before depending on it for production.

## Access control and security

The dashboard supports administrator, editor and read-only roles, login, and two-factor authentication. The dashboard can be served over HTTPS via Caddy. Only enable optional public access after TLS, user accounts and two-factor enrollment are complete.

Never publish or commit real `.env` files, SQLite databases, user backups, personal bank data, login tokens, keys, or material in the bind-mounted `data/`, `secrets/` or `caddy/` folders.

## Branding and language

The application now supports **German and English**. Use the DE / EN control on the login screen or in the navigation to switch for the current session. The installer asks for a language at setup; its choice becomes the default and can be overridden by every user. The chosen interface language is not saved in financial data or user profiles. See [Language settings](docs/LANGUAGE.en.md).

Existing display names such as `APP_TITLE`, `APP_SUBTITLE`, and `APP_FOOTER` can be customized in `.env`. Their configured values survive normal updates.

## More detailed documentation

- [Original detailed guide (German)](README.md)
- [Backup and restore (German)](docs/BACKUP_RESTORE.md)
- [Branding (German)](docs/BRANDING.md)
- [Notifications (German)](docs/NOTIFICATIONS.md)
- [Recurring transactions (German)](docs/RECURRING.md)
- [Financisto export and limitations (German)](docs/FINANCISTO_EXPORT.md)
- [PWA and Android installation (German)](docs/PWA_ANDROID.md)
- [Telegram transactions (German)](docs/TELEGRAM_BOOKINGS.md)

## License and upstream

The independent dashboard is licensed under [GPL-2.0-only](../LICENSE). Refer to [NOTICE.md](../NOTICE.md) for attribution. The original Financisto Android project is at https://github.com/dsolonenko/financisto.
