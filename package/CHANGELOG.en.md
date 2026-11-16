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
