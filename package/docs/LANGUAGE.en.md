# German and English language support

**Language / Sprache:** **English** | [Deutsch](LANGUAGE.de.md)

## Web interface

Choose **DE** or **EN** on the sign-in screen, the mobile header or the desktop sidebar. Switching language submits a CSRF-protected form and reloads the current page without signing out. The language preference is stored **only in the browser's signed application session**. It is not written to any user profile, database table, transaction, or backup. Logging out or an expired session resets to the installation default.

The interface uses an offline dictionary in `static/i18n.js`. No translation network service is used. Names of accounts, categories, payees, notes, amounts, values, IDs and other financial record data are not translated. A small number of seldom-used legacy diagnostics or composite messages may remain in German.

## First-time installer

Run `package/install.sh` as the normal project user, **never as root**. The installer begins with a bilingual prompt:

```text
Sprache wählen / Select language [1=Deutsch, 2=English] (1):
```

Then it displays setup prompts in the selected language and writes one of these lines to the new project `.env`:

```dotenv
DEFAULT_LANGUAGE=de
# or
DEFAULT_LANGUAGE=en
```

The language is only the **default**. Each user may switch DE / EN at any time. Existing installations without the variable automatically default to German. Existing `.env` values are preserved by the release updater.

## Changing the installation default later

Edit the `DEFAULT_LANGUAGE` value in your *existing* `.env` on the Docker host (do not upload it to GitHub), then recreate the dashboard service:

```bash
cd /path/to/financisto-dashboard
docker compose up -d --no-deps --force-recreate dashboard
```

This affects future/new browser sessions, but not sessions that explicitly chose a language. It does not affect authentication, data, accounting, or Caddy certificates.

## Translation maintenance

The German application text is the original. English strings are an explicit static dictionary loaded locally; when adding new user-visible UI labels, add a corresponding entry to `static/i18n.js` and test both languages. Keep strings containing user-defined financial data unmodified. Prefer server-side localization for newly introduced dynamic error messages.
