# Financisto Dashboard (FieLanzen)

**Language / Sprache:** **English** | [Deutsch](README.de.md)

<p align="center">
  <img src="package/static/sea-wolves-logo.webp" alt="Sea Wolves dashboard logo" width="260">
</p>


**An independent, self-hosted personal-finance dashboard for Docker**, featuring transaction management, financial reporting, recurring transactions, an installable PWA, and import/export compatibility with [Financisto](https://github.com/dsolonenko/financisto) backups.

**Latest release:** [Download ZIP and checksum](https://github.com/renfie/financisto-dashboard/releases/latest) · [Release history](https://github.com/renfie/financisto-dashboard/releases).


## Features

- Manage accounts, transactions, transfers, payees, and categories with user roles and two-factor authentication
- Monthly reports, household spending summaries, account balances, historical comparisons, and printable reports
- **Manual `.backup` import remains available**; optional SFTP/FolderSync auto-import can be enabled and disabled in the web interface
- Choose **Financisto or the web dashboard as the source of truth**, with safeguards against accidentally overwriting web-created transactions
- Recurring transactions and transfers with optional end date or maximum number of runs; Web Push, Gotify and Telegram notifications
- Future-dated transactions remain visible in yellow; today's displayed balances exclude their impact while future-inclusive projections remain available (stored ledger entries are not deferred)
- Responsive layouts for desktop, tablet and smartphone, plus an installable Progressive Web App (PWA)
- Combined daily and manual SQLite and Financisto-backup snapshots, with explicit export status and recurring-rule compatibility checks
- Versioned bearer-token Mobile API for accounts and bookings; device keys are non-expiring, revocable and deletable by administrators
- Docker Compose deployment, local HTTPS, backup/update scripts, and persistent bind-mounted data

## Guided introduction

New users receive a **role-aware, bilingual introduction** after setting up their account. The tour explains reports, filters, balances, future-dated transactions, bookings, recurring limits, imports and the language selector. Existing users are not forced to repeat it; anyone can restart it from **Help / introduction**. See [English](package/docs/ONBOARDING.en.md) or [Deutsch](package/docs/ONBOARDING.de.md).

## Relationship to Financisto

This project is a **standalone web application**. It is **not an official release, fork, or continuation** of the Financisto Android app. It supports the backup data format used by Financisto and an Android fork but does not claim affiliation with their authors.

- **Original Financisto project:** [dsolonenko/financisto](https://github.com/dsolonenko/financisto), by Denis Solonenko and contributors
- **Compatible Android fork:** [Financisto Holo (tiberiusteng/financisto1-holo)](https://github.com/tiberiusteng/financisto1-holo)

All rights in third-party projects and names remain with their respective owners.

## Screenshots

These screenshots show **real dashboard layouts with example data substituted for private account names and amounts**. Desktop and mobile images were captured from an earlier development version (v1.9.17); some UI elements may differ in v1.9.59.

### Desktop dashboard

![Desktop overview with example financial data](docs/screenshots/dashboard-desktop-demo.png)

### Mobile dashboard

<img src="docs/screenshots/dashboard-mobil-demo.png" alt="Mobile finance dashboard with sample data" width="340">

### Enter a transaction

![Transaction-entry screen with example account](docs/screenshots/buchung-erfassen-demo.png)

## Languages: English and German

The web interface supports **German (DE) and English (EN)**. Use the **DE / EN switch** on the sign-in screen, mobile header or desktop sidebar. Switching applies immediately after reloading the current page and **does not require a new login**. The selection is stored in the browser's protected application session, not in financial database tables or in permanent user profile records; it resets to the installation default after logout or session expiry.

The **first-time installer is bilingual**: its first prompt asks for **Deutsch / English**, and subsequent setup prompts are displayed in the chosen language. This choice sets `DEFAULT_LANGUAGE=de` or `DEFAULT_LANGUAGE=en` in the newly created `.env`. On an existing installation, `DEFAULT_LANGUAGE` is optional and defaults to German; every user can still switch in the web UI.

Translations are bundled locally; no third-party translation service receives financial data. A few specialized or legacy diagnostic messages may still be shown in German. See [language configuration (English)](package/docs/LANGUAGE.en.md) or [Deutsch](package/docs/LANGUAGE.de.md).

## Built-in Caddy HTTPS reverse proxy

Caddy is **included as a separate Docker Compose service**, handling internal HTTPS and proxying authorized requests to the dashboard. It uses an **internal Caddy CA** (`tls internal`) for LAN and upstream TLS; publicly trusted certificates must be configured separately at an optional Nginx Proxy Manager. Caddy's CA keys, certificates and configuration are persistent bind-mounted data, retained when updating.

**Full guide:** [Caddy / HTTPS / Nginx Proxy Manager (English)](package/docs/CADDY.en.md) · [Deutsch](package/docs/CADDY.de.md).

## Repository layout

| Location | Purpose |
| --- | --- |
| `package/` | Application sources, Docker Compose files, `install.sh`, templates, assets and product documentation |
| `update.sh` | Update an existing installation, including backup and validation |
| `setup_financisto_sftp.sh` | Optional setup of a dedicated SFTP import account |
| `README.txt` | Brief release notes in German |
| `package/CHANGELOG.md` | Detailed German version history |
| `package/CHANGELOG.en.md` | English release notes for recent versions |
| `package/README.md` | Detailed setup and operation guide (German) |
| `package/README.en.md` | English setup and operation guide |
| `package/docs/` | Additional technical guides (currently primarily in German) |

## Installation

Clone the repository or download its source ZIP. From the checkout root, run the installation script as the regular Linux project user, **not as root**:

```bash
cd package
./install.sh
```

The script guides you through initial configuration. See the [English installation and operations guide](package/README.en.md) or the [German original](package/README.md). Do **not** run the installer over an existing deployment.

## Updating an existing installation

Check out the new version **in a separate directory**. Run the update script as the Linux account that owns the existing installation:

```bash
./update.sh /path/to/existing/financisto-dashboard
```

Updates can be applied **directly to v1.9.59**, including from earlier development versions; intermediate installation steps are not necessary. The update script validates the layout and access rights and backs up the existing database and program files. It preserves configured domains in `.env`, existing secrets, and bind-mounted financial data. Do not copy release files indiscriminately over the production data directories.

For additional details see the [English operations guide](package/README.en.md) and [backup/restore documentation](package/docs/BACKUP_RESTORE.md) (German).

## Privacy and security

**Never commit or publish** production SQLite databases, `.backup` files containing financial information, filled-in `.env` configurations, passwords, keys, tokens or other runtime secrets. The repository [`.gitignore`](.gitignore) excludes typical sensitive files, but every public release still requires an explicit privacy check. Example domains and IP addresses use documentation-only placeholders rather than private deployment details.

## Changelog / development history

All German and English release histories are available in [German](CHANGELOG.md) and [English](CHANGELOG.en.md), and inside the app under **Changelog**. The **License & legal** menu item explains rights and duties with the original GPLv2 text. Both views follow the DE/EN setting.

## License

Own dashboard components are distributed under the **GNU General Public License version 2 (GPL-2.0-only)**; see [LICENSE](LICENSE) and [NOTICE.md](NOTICE.md). Recipients may modify and redistribute their own copies subject to the GPL, but this **does not grant write permission** to this repository. The original Financisto Android app is also licensed under GPL v2; compatibility does not imply endorsement or transfer of third-party branding rights.

## Downloads and versioned releases

[**Download the latest release**](https://github.com/renfie/financisto-dashboard/releases/latest) or browse the [release history](https://github.com/renfie/financisto-dashboard/releases). Each release includes a complete Docker installation/update ZIP archive and its SHA256 checksum.

A GitHub Actions [release workflow](.github/workflows/release.yml) creates a new versioned release when `package/VERSION` changes on `main`. Publishing is **not automatic when we discuss or edit code in ChatGPT**; source changes first need to be committed to GitHub and the version needs to be updated. Release notes are available in both English and German.

The repository and downloadable releases are public. Only authorized collaborators can modify the official repository.


## Copyright and redistribution

Copyright © 2026 René Fieler (RenFie). First-party source files are licensed under **GNU GPL v2 only (GPL-2.0-only)**. Keep existing copyright, license and warranty notices when distributing copies. Clearly mark modified files and change dates, include the complete GPLv2 license, and provide corresponding source code or another GPLv2 §3-compliant option with distributed executables. See [LICENSE](LICENSE) and [NOTICE.md](NOTICE.md). Third-party rights remain with their owners.
