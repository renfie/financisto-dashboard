# Mobile API: Account reconciliation

**Version:** 1.9.62-dev.4 (`develop`), 2026-11-26.

The server is the sole source of truth in DASHBOARD-SERVER mode. The web form (`POST /settings/accounts/reconcile`) and Mobile API use the same transaction-safe reconciliation helper.

## Availability and access

`GET /api/mobile/v1/capabilities` advertises `features.account_reconciliation: true`, preserving `monthly_reports`, `history_highlights` and `recurring_rules`. Authenticate with the existing `Authorization: Bearer <API-Key>`. Requires a **write key**, enabled admin/editor user and authoritative `finance_mode=web`. Responses are private and noncacheable.

## Request

`POST /api/mobile/v1/accounts/{account_id}/reconcile`

```http
Authorization: Bearer <API-Key>
Content-Type: application/json
Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000
```

```json
{"actual_balance_minor":127500,"expected_balance_minor":125000,"note":"Balance checked"}
```

All three fields must be present. The note can be empty, maximum 500 characters. Both balances are signed integer **minor units**. Currency code and decimal count come from `GET /api/mobile/v1/accounts`; never send a client-computed difference.

## Successful reply

```json
{
 "success":true,"account_id":12,"currency":"EUR","decimals":2,
 "previous_balance_minor":125000,"actual_balance_minor":127500,
 "change_minor":2500,"booking_id":15432,"unchanged":false,
 "balance_minor":127500,"projected_balance_minor":127500
}
```

The numbers are illustrative. `balance_minor` is the verified as-of-today effective balance; `projected_balance_minor` includes future-dated entries. Zero change returns `unchanged:true`, `change_minor:0`, `booking_id:null`, and creates no booking.

## Shared Web/Mobile posting logic

Inside SQLite `BEGIN IMMEDIATE`, effective balance equals the stored snapshot minus `future_account_deltas(today)`. A mismatch with `expected_balance_minor` returns **409 Conflict** without booking. The server alone calculates the adjustment; positive and negative differences use existing **Kontostandskorrektur (Zugang/Abgang)** categories excluded from regular income/expense reports. The existing `apply_balance_delta` adjusts the snapshot; final verification checks snapshot equals the actual amount plus future transactions. Posting day uses server time (Europe/Berlin), and the audit log records the mobile user.

## Errors and safe retries

| HTTP | Meaning |
|---|---|
| 200 | Success or no change |
| 400 | Invalid JSON, amount, note or UUID |
| 401 | Invalid credentials, no write access |
| 404 | Unknown account |
| 409 | Stale expected balance, inactive account, import mode or reused UUID with different payload |
| 500 | Database failure, result must not be assumed successful |

Error format: `{"error":"..."}`. Each mutation requires a UUID `Idempotency-Key`. Same UUID, account ID and body return the committed receipt without a duplicate. On timeout **do not silently generate a new UUID**: retry the exact original payload with the same UUID or first verify server state. On a stale-balance 409 refresh accounts and obtain a new explicit user confirmation.

After success refresh server accounts and paged bookings, and dependent reports if relevant. Never create an Android-local correction in server mode.

No schema, backup-format, existing API or Android repository changes.
