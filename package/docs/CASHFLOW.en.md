# Transaction quick periods and cash flow (v1.9.45)

**Language / Sprache:** English | [Deutsch](CASHFLOW.de.md)

## Period presets

The transaction list has 1W (last seven days including today), 1M (current calendar month), 3M (current and two previous calendar months), and 6M (current and five previous calendar months). **Month selection** restores the original date range between the two comparison months. Summary cards and category comparisons retain their own selected months.

The separate **Filter** control opens the full-text search. A link to **Advanced month, account and category filters** retains the original filtering interface. Quick text search changes only the transaction list, not reports or charts. URL parameters are shareable; the presets do not create persistent settings.

## Cash-flow chart

The chart shows income, expenses and net cash flow by day (1W), week segment (1M), or month (3M, 6M and month selection). The bars represent income and expenses; the dark dashed line represents net cash flow on a separate scale centered at zero. The aggregation runs locally, without tracking or external chart libraries.

**Scope:** Internal transfers, pass-through transactions, account/investment valuation adjustments, and future-dated entries are not realized cash flow. The chart never changes financial records or balances. Future-dated entries remain yellow in the transaction list.

Only the chosen currency is included and there is no cross-currency conversion. Account, category, and advanced search filters also affect chart data; the transaction-list quick search does not.

## Transaction actions

Clone, Edit, and Delete are compact and side by side on wide desktop screens. Tablets and phones retain their larger touch-friendly cards.

## Dashboard layout and pagination (v1.9.46)

The collapsible **Transactions** section is directly below account balances; category comparison and cash flow come after it. It starts collapsed, but transaction links, page-number links and sorting/filter links reopen it automatically. Direct numbered navigation with ellipses complements Previous/Next.

Cash-flow colors match the month/category palette: teal bars for income and orange bars for expenses. The dashed dark line represents each period's net value (income minus expenses), with the horizontal midpoint indicating zero on a separate net-value scale. This is not the current account balance. The line and bars share the same column grid, including in three-month mode.

## Display behavior from 1.9.47
Cash flow starts collapsed on dashboard visits but can be expanded manually or via `#cashflow`. The transaction ledger starts expanded.
