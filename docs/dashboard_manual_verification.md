# Dashboard Manual Verification (M19-C)

## Launch

```bash
DATABASE_URL=sqlite:///./dev.db streamlit run src/fx_ai_trading/dashboard/app.py
```

Open `http://localhost:8501` in a browser.

## Panel Checklist (10 panels)

### Row 1 — 3 columns

| Panel | Expected (no DB) | Expected (with DB) |
|---|---|---|
| Market State | phase_mode/environment shown as "—" | shows phase6 / demo |
| Strategy Summary | "No orders" info | order count per status |
| Meta Decision | static placeholder text | static placeholder text (Iteration 2) |

### Row 2 — 2 columns

| Panel | Expected (no DB) | Expected (with DB) |
|---|---|---|
| Positions | "No open positions" info | table with open positions |
| Daily Metrics | zeros for all counts | today's filled/canceled/failed counts |

### Row 3 — 2 columns

| Panel | Expected (no DB) | Expected (with DB) |
|---|---|---|
| Supervisor Status | "No supervisor events" info | recent event list |
| Recent Signals | "No recent orders" info | last 20 orders |

### Row 4 — 3 columns (M19)

| Panel | Expected (no DB) | Expected (with DB, pre-M20) | Expected (with DB, post-M20) |
|---|---|---|---|
| Top Candidates | "No candidates available. (TSS mart populated after M20.)" | same (table absent) | ranked candidates table |
| Execution Quality | "No execution metrics recorded yet." | fill/slippage/latency table | fill/slippage/latency table |
| Risk State Detail | "No risk events recorded yet." | risk decisions table | risk decisions table |

## Verification Steps

1. Start without `DATABASE_URL` → all panels show graceful fallback messages (no exceptions, no red error boxes).
2. Start with `DATABASE_URL` pointing to a seeded dev DB → Row 1–3 panels show table data, Row 4 panels show data if tables exist.
3. Confirm no "Error" or Python traceback appears in the browser.
4. Confirm page title is "FX-AI Trading Dashboard" and caption shows "Iteration 2 · M19".
5. Confirm layout: 3 columns / divider / 2 columns / divider / 2 columns / divider / 3 columns.

## Notes

- `top_candidates` panel shows fallback until M20 migration creates `dashboard_top_candidates` mart.
- All panels use `@st.cache_data(ttl=5)` — data refreshes automatically every 5 seconds.
