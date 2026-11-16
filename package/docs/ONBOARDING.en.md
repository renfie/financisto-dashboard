# Guided introduction (version 1.9.42)

**Language / Sprache:** **English** | [Deutsch](ONBOARDING.de.md)

## Starting and replaying the tour

After a new user configures their account and two-factor authentication, an interactive tour appears on their first dashboard visit. **Existing users are not automatically prompted again by this update.** Completion or skipping is recorded per user in the existing `users.tutorial_completed` field.

Select **Help / introduction** in the navigation to replay the tour at any time. Use **Back**, **Next**, **Skip**, and **Finish** to navigate. Replaying manually does not reset completion status.

## Language

The tour follows the currently selected **DE / EN** interface language. All translated strings ship with `static/tour.js`; no external translation or analytics services are called. Switching languages only affects the current browser session, not the accounting data.

## Covered features

- Comparison of monthly income/expenses, filters, balances, and the transaction list
- Yellow indicators for future-dated transactions and their immediate effect on stored account balances
- Historical analysis and printable monthly reports (A5/A4)
- Booking form with payee before category, editing, cloning, and future dates
- Recurring rules including manual/automatic posting, optional end dates, and execution-count limits
- Manual Financisto backup import and optional automatic SFTP import
- User permissions, settings, language switching, and replaying Help / introduction

Steps depend on the current user role: administrator, editor, or read-only. Creating transactions also requires the web dashboard to be the authoritative finance source. The tour explains the interface; it does not execute bookings or change settings.

## Technical files

- `static/tour.js` – steps, bilingual content, highlighting and keyboard handling
- `static/style.css` – existing tour styling
- `src/app.py` – existing `/account/tutorial/complete` endpoint for status updates

Existing privacy and security safeguards are unchanged.
