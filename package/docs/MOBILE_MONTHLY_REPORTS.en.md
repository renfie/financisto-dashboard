# Mobile API: complete monthly financial reports

**Draft for `develop`, not yet published to GitHub.** 2026-11-26.

## Endpoint, access and capability

`GET /api/mobile/v1/reports/monthly` calculates all selected months from the **complete server-side transaction database**, independently of the paged bookings API. It is read-only and accepts the existing `Authorization: Bearer <API-Key>` credential, including read-only keys. Replies carry `Cache-Control: private, no-store`.

Once reviewed, tested and approved, `/api/mobile/v1/capabilities` should advertise `features.monthly_reports: true`. The draft does **not** enable it until approval.

Example: `/api/mobile/v1/reports/monthly?from=2025-12&to=2026-11&currency=EUR`.

| Parameter | Meaning |
|---|---|
| `from`, `to` | Inclusive months in `YYYY-MM`; both required if either is present |
| `currency` | Uppercase three-letter ISO currency code; default is dashboard currency |
| `account_id` | Optional existing account within selected currency |
| `category_id` | Optional category ID including descendants according to nested set hierarchy |

With neither month set, the default is 12 months including the current one. Inclusive range limit is 1–36 months; invalid or reversed ranges, invalid filters and unknown arguments return 400.

## Response

```json
{
  "currency":"EUR","decimals":2,"from":"2026-10","to":"2026-11","complete":true,
  "months":[{
    "month":"2026-10","income_minor":0,"expense_minor":0,"balance_minor":0,
    "booking_count":0,"transfer_count":0,"transfer_minor":0,
    "categories":{"income":[],"expense":[]}
  }]
}
```

These amounts are **schema placeholders**, not production results. Every requested month appears, including empty months, in ascending order. `complete: true` means the server evaluated its full ledger and filters; it does **not** mean the current calendar month has finished.

Income, expenses, transfer absolute amounts and category amounts are non-negative integer minor units (such as cents), while the balance may be negative. Category entries contain `{ "category_id": 11, "category": "Shopping / Food", "amount_minor": 5000, "booking_count": 1 }` using full category paths. `booking_count` includes regular nonzero income/expense bookings; internal transfers use separate count/absolute source amount. Pass-through and balance-adjustment categories and their descendants are excluded from ordinary income and expenses, as on the web dashboard.

**Actual vs future:** only entries dated on or before server-local today contribute to returned amounts; future-dated entries are excluded. Internally the common helper also computes projections for the web dashboard, but this Mobile API version intentionally omits forecast fields. The client must never mix future entries into complete actuals.

The web dashboard month comparison, historical timeline and this API all use `summarize_months` (`package/src/monthly_reports.py`) for matching filters. Extra web-only search or hidden-category filters are not equivalent to unfiltered API queries.

## Errors, compatibility and safety

- `400`: malformed date, range over 36 months, invalid filters, foreign-currency account or unknown query key.
- `401`: missing or invalid key.
- `500`: SQL read error; internal diagnostics are not exposed.

Error JSON is `{ "error": "..." }`. Older servers without `features.monthly_reports` and failed API requests must never cause Android to present a partially downloaded booking set as a complete report. No database mutations, ledger or balance writes, schema upgrades, changes to recurring rules, backup formats or existing paginated booking endpoints are introduced.
