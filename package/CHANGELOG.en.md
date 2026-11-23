## 1.9.58-dev.19 – Finite recurring schedules in Financisto exports (2026-11-23)
- Monthly, quarterly and yearly Web rules with an end date or maximum occurrence count now use native Financisto `STOPS_ON_DATE:date@yyyyMMddT000000#` and `EXACTLY_TIMES:count@N#` termination formats.
- When both constraints are set, the earlier effective constraint is encoded. Format verified against Financisto `RecurrencePeriod` / `RecurrenceViewFactory` sources; sample backups parse correctly and preserve existing native templates.
- Monthly day 29–31 is rejected rather than silently altering short-month behavior. Other unsupported recurrence patterns still produce explicit errors.
- Bump export validation revision so scheduled backup retries after installation even when a same-day export already exists. Financial data and SQLite backups remain unchanged. Native Android restore still requires an independent test.

## 1.9.58-dev.18 – Unified SQLite and Financisto backup status (2026-11-23)
- Remove duplicate test-export section; existing administrator session suffices for the combined backup action.
- Scheduled backup service independently attempts both SQLite and a current Financisto .backup every day; recurrence templates are always validated.
- Persist the last Financisto attempt, success, and failure in a protected status file and display errors in Settings. Stale downloaded files are not presented as fresh exports.
- Force an upgraded-format Financisto export on first scheduled pass after updating, even if an old file exists for today. Keep the latest two successful exports.
- Preserve existing executed bookings and native recurrence templates; explicitly verify recurrence counts. Unsupported rule types fail with an explanation rather than being silently omitted.
- Allow supplying the exact matching original backup, when missing, from inside Backup Settings under the existing admin session and SHA256 check.
- No Android release or changes to financial ledger data; SQLite remains the complete restore format.

## 1.9.58-dev.17 – Session-based API key management and safe recurring export (2026-11-22)
- Existing admin session plus CSRF verification is sufficient to create or revoke device API keys. Permanent deletion requires a confirmation and removes related idempotency receipts; audit records remain. No repeated password or TOTP is needed.
- Manual and scheduled Financisto backups and the test export now run the recurrence merge automatically. Unmodified original Financisto templates are preserved, and compatible active automatic Web rules are included.
- Paused original templates retain their native original definition; Web pause status cannot be transported. Unsupported or manual/paused Web-only recurrence semantics cause a clear export error rather than silent data loss. Full SQLite backups always preserve all Web rules.
- No financial ledger mutation, no schema changes and no official release.

## 1.9.58-dev.16 – Non-expiring, revocable Mobile API keys (2026-11-22)
- New device API keys no longer have a scheduled expiry (`expires_on=0`); authentication no longer checks an expiry timestamp.
- Previously unexpired keys are migrated to unlimited validity. Already expired keys stay disabled and are never silently reactivated.
- Administrator revocation, inactive users, disabled 2FA and account security-version changes continue to invalidate keys.
- The Settings UI now shows “Unbegrenzt” instead of a date. Creation and revocation still require administrator password and fresh 2FA.
- Dashboard only. No Android release, transaction changes or bind-mount changes; only API-key metadata is migrated.

## 1.9.58-dev.15 – Online Mobile API and device-scoped credentials (2026-11-22)
- Admin 2FA-protected, revocable 90-day device API keys, stored as hashes; keys are shown only once.
- Versioned Mobile API for session, accounts, categories, payees, paginated transactions and safe create/edit/delete with idempotency UUID and revision checks.
- Remote online mode is server-authoritative, keeps offline Android data separate and never merges or uploads it automatically.
- Additive database migration only; existing bind mounts and transactions preserved.

## 1.9.58-dev.14 – Mobile API discovery and simplified recurring screen (2026-11-22)
- Add safe, public, read-only JSON API discovery at `/api/mobile/v1/status` (also `/api/mobile/v1`, `/api/v1/mobile/status` and `/api/v1/mobile`) for Android Alpha 18's connection check.
- No private data or credentials are exposed. The response states `server_mode_available=false`; authentication, account endpoints and synchronization are not enabled.
- Remove duplicate .backup upload form from Recurring Bookings; the Settings import remains unchanged.
- Development build only, no schema or bind mount changes.

## 1.9.58-dev.13 – Edit larger income amounts and select recurring payees (2026-11-18)
- Editing an existing transaction now pre-fills the amount without thousands separators so amounts from 1,000.00 upward parse correctly in the booking form.
- New and edited recurring rules select a prefilled payee on focus/tap for direct replacement while keeping payee suggestions available.
- No database schema, transaction, recurring-rule or bind mount changes.

## 1.9.58-dev.12 – Notes and sorting in the web booking list (2026-11-18)
- Add a Note column under Booking entry → Web transactions.
- Clicking the Date, Type, Account, Payee, Note or Amount header toggles ascending and descending sort.
- Sorting operates on the existing latest 100 web-booking entries without changing the underlying selection. Edit, clone and delete actions remain available.
- No changes to transactions, balances, database or bind mounts.

## 1.9.58-dev.11 – Booking type badges match the dashboard (2026-11-18)
- The web-bookings entry table now displays the same rounded booking type badges as the dashboard: red downward expense, green upward income, and neutral transfer, adjustment and pass-through types.
- Full-row highlights and future/recurring status badges remain unchanged. No financial data or balances are modified.

## 1.9.58-dev.10 – Booking-entry row highlighting matches dashboard (2026-11-18)
- The web-bookings table now uses matching full-row colors: transfers light blue, recurring transactions mint green, recurring transfers lavender, and future-dated transactions yellow with priority.
- Recurring and rule-matched labels appear beneath the date. A matched rule alone does not add a row color.
- No changes to transaction posting, account balances or financial data.

## 1.9.58-dev.9 – Separate actual and projected future transactions (2026-11-18)
- Monthly dashboard income, expenses, and net reflect transactions dated through today, with future-inclusive projections shown in parentheses when applicable.
- Individual and total displayed balances back out the future-dated entries already included in SQLite snapshots and show the stored future-inclusive balance as a forecast.
- Transfers adjust source and destination accounts in opposite directions; account reconciliation uses today's effective balance. Category comparisons exclude future-dated amounts.
- Bookings remain visible and unchanged. Underlying stored snapshots and Financisto exports are unchanged: this is an as-of-date dashboard and reconciliation presentation, not a deferred ledger posting mechanism.

## 1.9.58-dev.8 – Distinguish posted recurring entries from matched existing transactions (2026-11-18)
- “Recurring” identifies a transaction posted by a recurring rule, whereas “Rule matched” identifies an existing transaction assigned to a due occurrence without reposting it.
- Labels appear beneath the date even for transfers. Truly recurring transfers stay purple; rule-matched transfers keep blue highlighting.
- The dashboard, booking entry and CSV export distinguish both statuses. No ledger or account balance changes.

## 1.9.58-dev.7 – Mark only actually posted recurring transactions (2026-11-18)
- Recurring labels now require an actual recurring-post event matching the run, rather than any recurring-run reference.
- Pre-existing manual transactions merely matched to a recurring due date are no longer incorrectly labeled.
- Consistent on dashboard, CSV export and transaction entry; no ledger, balance, rule or bind-mount changes.

## 1.9.58-dev.6 – Recurring label under transaction date (2026-11-18)
- The recurring label appears below the date, like the future-date label, instead of beside the transaction type.
- Future recurring entries display both labels below the date.
- Full-row highlights remain unchanged; no ledger or bind mount changes.

## 1.9.58-dev.5 – Prefilled payee input in new bookings (2026-11-18)
- Focusing or tapping an existing payee selects its entire value so the next input replaces it, matching category selection.
- User-entered search queries remain editable and suggestions still work.
- No ledger, database, or bind mount changes.

## 1.9.58-dev.4 – Booking highlights, manual dual backup and executable updater (2026-11-18)
- The manual backup action independently creates and reports SQLite and current-ledger Financisto export snapshots.
- Blue full-row highlights for transfers and green highlights for recurring transactions; recurring transfers have a distinct lavender background.
- Future-dated rows retain the overriding yellow highlight. The compact mobile list also receives the new highlights.
- The ZIP marks `update.sh` executable for the existing one-command installation procedure.
- No financial-data, account-balance, database or bind-mount changes.

## 1.9.58-dev.3 – Two current Financisto export snapshots (2026-11-18)
- Alongside daily SQLite snapshots, create a validated `.backup` export from the current web ledger.
- Keep the two newest successful exports in `data/financisto-backups/`, downloadable by administrators from Settings.
- Reuse the tested default exporter without optional Web recurring-rule conversion; missing source templates fail safely without affecting SQLite backups.
- Existing Android import archives, bind mounts, secrets and transactions remain unchanged.

## 1.9.58-dev.2 – Inline CSV export and English labels (2026-11-18)
- CSV export button is positioned beside ledger pagination instead of on an extra row.
- Add English translations for page count, CSV export and running balance labels.
- Development build only; no official release or financial-data changes.

## 1.9.58-dev.1 – Dashboard ledger CSV export (development, 2026-11-18)
- Export the entire filtered and sorted dashboard ledger, across all pages, as CSV.
- Includes dates, transaction type, source/destination account, category, payee, note, amount, currency, recurring status and running balance.
- Excel-friendly UTF-8 BOM, semicolons and comma decimals. User text is protected against spreadsheet formula injection.
- Read-only export; no database, data mount or secret changes.
- Development branch only: not an official release.

## 1.9.57 – Recurring schedules and streamlined documentation (2026-11-18)
- New recurring rules initialize their day-of-month from the start date and track subsequent start-date changes until the day is manually customized.
- Hide the irrelevant month-day field for daily and weekly schedules, while monthly, quarterly and yearly rules keep an independent editable month day.
- Previously stored rules, booking dates and transactions are unchanged.
- Remove stale release blocks and the 1.9.48 local test note from the GitHub READMEs; release notes and changelogs retain version details.
- Docker image tags and package version agree on 1.9.57; financial data and bind mounts remain preserved.

## 1.9.56 – Category field and Docker image version (2026-11-17)
- Selecting the prefilled category label on focus/tap lets typing replace the text rather than append to it.
- All three application services now use a matching Docker image tag (1.9.56).
- The updater and GitHub release build reject inconsistent image tags and package versions.
- Bind mounts, finance data, secrets, and configuration remain unchanged; the updater backs up SQLite before deployment.

## 1.9.54 – Ledger, recurring transactions and filters (2026-11-17)
- Future-dated transaction highlighting now fills the full table row, including the action cell.
- Transactions linked to recorded recurrence runs carry an additional "Recurring" label in the dashboard and bookings list. Existing records are not modified.
- Quick search is always directly visible next to or below period shortcuts; "Advanced" still opens month/account/category controls.
- Auto-search delay reduced from five to four seconds; Search/Enter submit immediately.
- Recurring-rule editor accepts both existing and new payee names through the same compact mobile-safe autocomplete. New payees are created atomically when the rule is saved.
- No changes to user finance data, import logic or certificates. The updater backs up SQLite before installation.

## 1.9.53 — Show payee suggestions immediately on focus (2026-11-16)
- Tapping or focusing the payee field now immediately shows known payees in alphabetical order even with an empty query, matching the category picker.
- Typing continues to narrow suggestions, while tapping the field again reopens the full list.
- The shared administrator-configured payee/category suggestion limit (1–100, default 20), compact mobile layout and scrollability are preserved.
- Free-text payees and existing financial records, imports, database schema and access controls remain unchanged.

## 1.9.52 — Admin-managed autocomplete suggestion limit (2026-11-16)
- Payee and category suggestions default to 20 matches instead of 8.
- Administrators can set the shared per-list maximum to 1–100 under **Settings → Transaction list**, without redeploying or restarting containers. The setting applies to all users.
- The selected limit persists in the existing SQLite metadata table across restarts and upgrades. Transactions, account data and category IDs are unchanged.
- Mobile lists remain compact (maximum 236 px tall) and scrollable. Touch and keyboard selection are preserved.

## 1.9.51 — Searchable category picker and five-second search pause (2026-11-16)
- This public release includes the previously local-only v1.9.50 payee autocomplete improvements.
- Replaced Android's large native category picker in the transaction form with a compact, searchable suggestion list matching the payee UI; up to eight category matches are displayed at once.
- Preserved original category IDs, the form field name, existing transactions and the category creation/edit workflow, including graceful fallback when JavaScript is disabled.
- Dashboard quick search now submits automatically five seconds after the last keystroke (previously 650 ms); the explicit Search action remains immediate.
- No database, finance, import/export or security changes.

## 1.9.50 — Reliable mobile payee suggestions (2026-11-16)
- Replaced the native HTML datalist with a compact app-controlled autocomplete to avoid oversized translucent popups on some Android browsers.
- Results remain anchored to the field, with up to eight matches and automatic placement above the on-screen keyboard when needed.
- Arbitrary new payees are still accepted; booking behavior and stored data are unchanged.
- Accessible keyboard controls (arrows, Enter, Escape); no network service is used.

## 1.9.49 — Consolidated release since public v1.9.43 (2026-11-16)
- **English interface (v1.9.44–1.9.49):** More complete offline translation for dashboard summaries, history, accounts, imports, A5/A4 reports, settings, notifications, Web Push, system status, Telegram, Gotify and the experimental Financisto export. Dynamic labels with counts, dates, months and mixed formatted text have improved support. User-created account/category/payee names and notes remain unchanged.
- **Final language fix (v1.9.49):** The recurring-rules warning in the switch-back-to-Financisto form is now fully English in EN mode. The confirmation label reads “Enter FINANCISTO to confirm”; the required technical confirmation token is still exactly `FINANCISTO`.
- **Cash flow (since v1.9.45):** Added income/expense bars and a dashed net line with a clear explanation; chart colors match category comparisons, net-line alignment is corrected and mobile scrolling is supported. Transfers, pass-through transactions, reconciliations and future-dated bookings are excluded from realized cash flow.
- **Date presets and filtering (v1.9.45):** 1-week, 1-/3-/6-month shortcuts for the transaction list and a separate expandable advanced search; existing two-month comparisons and month selection are preserved.
- **Dashboard structure (v1.9.46–1.9.47):** Account balances → transactions → expenses by category → cash flow. The transaction list starts expanded and cash flow collapsed. Sections remain user-toggleable; deep links open the relevant section.
- **Pagination and row actions (v1.9.45–1.9.46):** Clickable page numbers plus Previous/Next, and more compact inline Clone/Edit/Delete actions on desktop.
- **Reports and footers (v1.9.48):** Translated additional A5-report captions, account notices and import guidance. Existing `.env` variables support different footers: `APP_FOOTER` (German) and optional `APP_FOOTER_EN` (English). Existing settings are preserved on upgrade.
- **Safety and compatibility:** No changes to accounting, import, balance or recurring-rule logic, existing finance records, SQLite schema, users, 2FA, Caddy certificates or permissions. Manual Financisto `.backup` import remains available.
- **Upgrade:** Complete ZIP distribution including `update.sh`, with direct upgrade support from v1.9.43 through v1.9.48. The updater backs up SQLite, program files and `.env` before installation.

## 1.9.48 — Local test build: English text and configurable footers (2026-11-16)
- Completed account-header, balance sorting and Financisto import text translation.
- Server-rendered English/German fixed labels in the A5 household report, preserving user category names and transaction text.
- Added optional APP_FOOTER_EN alongside existing APP_FOOTER in .env; preserves existing customization on upgrade.
- No financial records, booking logic, users or Caddy configuration changed.

## 1.9.47 — Default panels and expanded offline English translations (local test build, 2026-11-16)
- The dashboard ledger is expanded by default; cash flow is collapsed by default. Deep links to either panel expand the relevant section.
- Additional English translations for transaction captions, recurring rules, push notifications, background job status, public access, Telegram, Gotify, Financisto export and financial master data.
- Specific dynamic labels, counts, dates and protected confirmation terms are translated without modifying account names, payees, notes or financial records.
- No changes to booking calculations, persistent data, database schema or Docker services. Not pushed to GitHub; local testing only.

## 1.9.46 — Collapsible ledger, numbered pagination and cash-flow alignment (2026-11-16)
- Moved the transaction list directly below account balances and made it collapsible. Pagination and transaction deep links expand it automatically.
- Added numbered page links with ellipses alongside Previous/Next; existing period and search filters remain.
- Kept category comparison and cash flow below the ledger. Cash-flow colors now match the month/category palette; the dark dashed net line has an explicit caption and centered zero reference.
- Fixed net-line alignment in the three-month chart by sharing equal-width tracks with the bars; smaller screens scroll the plot when necessary.
- Presentation changes only; no financial data, database, booking or import modifications. Local test build, not pushed to GitHub.

## 1.9.45 — Cash flow, quick periods, compact actions and translation fixes (2026-11-16)
- Independent 1W, 1M, 3M and 6M transaction-list presets. Existing two-month comparison and advanced filters remain available.
- Full-text search moved into a separate compact Filter control.
- Offline cash-flow chart with income, expenses and net amounts for the ledger period. Internal transfers, pass-through entries, balance adjustments and future-dated entries are excluded from realized cash flow.
- Desktop Clone, Edit and Delete actions now fit inline without unnecessarily widening transaction rows; touch controls on mobile stay unchanged.
- Improved English for historical analysis, printed reports, imports, dynamic captions and a locally translated file picker.
- No database-schema, stored transaction, recurring-rule or data-import changes.

## 1.9.44 — More complete English interface translation (2026-11-16)
- Fixed untranslated dashboard captions: import date, monthly comparison, transaction counts, sort summary, quick filter and its search placeholder.
- Added safe local translation patterns for known interface captions containing dates, month names, counts and status values; individual account/payee/note data remain unchanged.
- Expanded fixed English text in import, reports, recurring rules, administrative settings and explanatory messages.
- No changes to financial records, posting/import logic, database schemas, accounts, 2FA, Caddy or Docker networking.
- This ZIP is a local test build; not yet published on GitHub.

## 1.9.43 — Complete English authentication text and compact dashboard actions (2026-11-16)
- Fixed the mixed-language 2FA verification paragraph while keeping the actual username intact.
- Completed English text for authenticator setup, QR-code guidance, recovery codes and password changes.
- On desktop and tablet, the three dashboard quick actions are arranged side-by-side, with the import timestamp underneath; the smartphone layout is unchanged.
- No changes to financial records, authentication data, databases, import jobs or Caddy certificates.

## 1.9.42 — Updated bilingual onboarding (2026-11-16)
- Refreshed the first-login tour for functionality through v1.9.41, with complete offline German and English copy.
- Covers current account balances, yellow future-dated transactions (already included in stored balances), payee/category entry, recurring end dates and execution caps, import/data-source modes and DE/EN language switching.
- Role-aware explanations for administrators, editors and read-only users; the tour does not claim unauthorized controls are available.
- Automatic first-login onboarding remains limited to new users who have not completed it; existing users are not prompted again.
- Replay through Help / introduction at any time, with Back, Next, Skip and Finish controls.
- No changes to financial data, database schema, accounting/import logic, secrets or Caddy certificates.

## 1.9.41 — Fix booking-form grid on desktop and tablets (2026-11-15)
- Payee and Category now appear side by side in one row on desktops and tablets, with Payee on the left and Category on the right, matching the existing keyboard/mobile field order.
- For transfers, the destination account and Payee share a row at desktop widths; smartphone layout remains stacked.
- CSS-only change; no impact on stored bookings, recurrence, import, authentication or Caddy configuration.

## 1.9.40 — Recurrence limits and future-dated transaction highlighting (2026-11-15)
- Transaction entry: Payee appears before Category on desktop and mobile, including keyboard navigation order.
- Recurring entries: Optional inclusive end date and/or maximum number of actual occurrences. The rule ends when the first configured limit is reached; legacy rules remain unlimited, previous executions count, existing transactions are kept.
- Future-dated transactions are shaded yellow and labeled on dashboard tables, mobile cards and the recent web-entry list until their date is reached (after page refresh). This is display-only, without changing the existing balance calculation.
- Updated translations; no changes to authentication, imports, secrets or the Caddy certificate authority.

## 1.9.39 — English and German web interface and installer (2026-11-15)
- Bundled offline English translations for the web dashboard's navigation, forms, reports, settings and common notifications; the German original remains available.
- DE / EN language control on sign-in, mobile header and desktop sidebar. Language can be changed at any time and is retained for the current session only.
- Bilingual installer prompts for German or English at the beginning; the choice sets DEFAULT_LANGUAGE in the local .env file and controls subsequent install prompts.
- No remote translation API, user-profile migration or changes to financial records, passwords, import logic or Caddy certificates.
- English and German language documentation and bilingual release notes. A small number of rarely used legacy diagnostic messages may remain in German.
- Supports updating directly from v1.9.35 to v1.9.39.

## 1.9.38 — Direct upgrade support and Caddy documentation (2026-11-15)
- Fixed a release preflight bug: the updater now reads the actual version from `package/VERSION` instead of asserting version 1.9.36.
- Supports updating directly from v1.9.35 to v1.9.38 without installing the intervening releases.
- Added comprehensive English and German guides covering bundled Caddy HTTPS, internal CA certificates, optional Nginx Proxy Manager integration and persistent configuration.
- No changes to financial data, accounting, import logic, users or existing Caddy certificates.

# Changelog (English)

## 1.9.37 — Public release cleanup and bilingual documentation (2026-11-15)

- Prepared an English-first GitHub project page, with a complete German version and links between languages.
- Added an English installation and operations guide, while retaining the detailed German documentation.
- Included anonymized screenshots of the desktop dashboard, mobile view and transaction-entry form.
- Replaced private deployment domains and internal IP addresses in distributed examples with documentation-only placeholders; the user's existing `.env` configuration is not replaced during updates.
- Added English and German release notes, release ZIP validation and SHA256 checksums.
- No changes to accounting logic, personal financial records, import modes, user accounts or stored authentication secrets.

## 1.9.36 — Compact dashboard transaction list (2026-11-14)

- Smartphone and tablet views show concise transaction rows containing amount, date, description and account; more information is shown on tap.
- Expandable details contain category, payee, note, balance after the transaction, and source/destination accounts for transfers.
- Authorized users can clone, edit or delete transactions from expanded details.
- In tablet landscape orientation, the compact sortable view replaces the horizontally scrolling table.
- No changes to stored transactions, notifications, source-of-truth modes or Financisto imports.

## 1.9.35 — Transfers and scheduled execution times (2026-11-13)

- The dashboard transaction list also includes transfers, including recurring transfers.
- Account filters include both transfer endpoints, while income/expense totals exclude transfers.
- Source-account balance is clearly labeled for transfers.
- Recurring transactions support an optional earliest execution time in Europe/Berlin; existing schedules retain the 00:00 default.

For complete historical release details, see [the German changelog](CHANGELOG.md).
