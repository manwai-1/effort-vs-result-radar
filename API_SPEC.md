# API_SPEC.md — Effort vs Result Radar data contract

This is a file and pipeline contract. There is no HTTP API, no application server, and no AI call in a routine scan. The scanner reads `watchlist.json`, optionally a fixture bar file, and writes two JSON files. A later UI may read those files as static assets. This document matches the scanner in this repository.

DESIGN.md §7 field names are unchanged. Fields that DESIGN.md left open (the price change, the volume window, the ATR method, the trend rule, and the `summary_by_tag` object) are defined here and locked by tests.

## 1. Inputs

### 1.1 `watchlist.json`

Scanner configuration. The UI does not edit it. Every symbol carries `market`. The scanner does not infer US vs HK from the ticker spelling.

| Field | Required | Meaning |
| --- | --- | --- |
| `symbols` | yes | Non-empty array |
| `symbols[].ticker` | yes | Yahoo-style symbol the scanner writes and, on a live run, passes to yfinance. Pattern `^[A-Z0-9][A-Z0-9.\-]{0,20}$` |
| `symbols[].market` | yes | `"US"` or `"HK"` |
| `symbols[].name` | no | Display name for humans. Not copied into the output JSON |
| `symbols[].index` | no | Source index label |
| `symbols[].source_code` | no | Listing code before Yahoo padding, for audit |
| `retrieved_on`, `sources`, `snapshot_note`, `yahoo_symbol_rule` | no | Snapshot provenance |

Rules:

- Duplicate tickers are rejected.
- `market: "HK"` requires a `.HK` suffix. `market: "US"` rejects a `.HK` suffix. That is a consistency check, not market inference.
- Hong Kong codes in the committed snapshot are zero-padded to 4 digits (`700` → `0700.HK`) because that is the yfinance symbol. Output tickers are those strings, verbatim.

The committed file is a membership snapshot, not a live index feed and not a weight file.

- Nasdaq-100: 101 securities, as of 2026-11-02, from Nasdaq's UCITS weights page `https://www.nasdaq.com/docs/global-indexes/NDX`. Both Alphabet classes (`GOOGL`, `GOOG`) are included. Cross-check: Nasdaq XNDX reported 101 components as of 2026-11-25. An Xtrackers Nasdaq 100 UCITS ETF holdings table as of 2026-11-25 matches this set except that the ETF shows one Alphabet line.
- Hang Seng Index: 95 securities, as of 2026-11-20, from Hang Seng Indexes Company's review `https://www.hsi.com.hk/content/dam/wpb/hsil/en_hk/press_releases/content/20261120T174500.pdf`. Appendix 1. Adds: nil. Removes: nil. Weight changes effective 2026-12-07 do not change membership.
- `retrieved_on` is 2026-11-26.

### 1.2 Clock and run mode

| Invocation | Behavior |
| --- | --- |
| `python -m scanner` | Full scan at the current clock. Live yfinance bars. Writes both JSON files when at least one point can be measured. |
| `python -m scanner --scheduled` | Used by the cron workflow. A market in its regular session refreshes the live radar from that session's partial daily bar. A market in its post-close window is a full scan of the session that just completed: `radar.json` is rewritten with the official close and full-day volume, and only that market's same-day ledger rows are finalized (§2, §5.2). When neither a regular session nor a post-close window is open, do not rewrite `radar.json`. Backfill completed T+N returns only, and only rewrite `history_results.json` when a null return becomes a number. |
| `workflow_dispatch` | The workflow runs `python -m scanner --push` without `--scheduled`. Full scan of the latest real bars even when both markets are closed. It does not synthesize a session. A measurement session that is already complete is finalized the same way as a post-close run (§5.2). A session that is still open keeps the intraday first-flag rule. |
| `--bars FILE --now TIMESTAMP` | Fixture mode. No yfinance import and no network. `--now` is ISO-8601 and must include an offset (`Z` is accepted as `+00:00`). |
| `--push` | After a successful write, commit and `git push` the two JSON files. See §6. |

### 1.3 Fixture bars

`--bars` reads JSON:

```json
{
  "note": "Synthetic fixture bars. Not market prices and not performance.",
  "series": {
    "FIXU": [
      {"date": "2026-11-27", "open": 100, "high": 101, "low": 99, "close": 100, "volume": 1000}
    ]
  }
}
```

`series` keys are tickers. Each bar needs `date` (`YYYY-MM-DD`), `open`, `high`, `low`, `close`, `volume`. A bar with high < low, a non-positive close, or a negative volume is rejected at load time for fixtures. Unknown top-level keys such as `note` are ignored.

### 1.4 Environment

No project environment variables are required. The publish gate reads `GITHUB_ACTIONS` and `GITHUB_REPOSITORY`, which GitHub Actions sets. There is no `.env` file and no `.env.example`. Do not add tokens. Routine scans do not call an AI model.

## 2. Session clock

Zones are `America/New_York` and `Asia/Hong_Kong` from the system time-zone database. US daylight-saving time is not a fixed UTC offset. The weekday is the market's local weekday, so Monday 09:30 in Hong Kong (still Sunday evening in New York) opens only HK.

A market is in its regular session when the local weekday is Monday–Friday and the local time is **at or after 09:30 and strictly before 16:00**.

Hong Kong lunch (12:00–13:00) is inside that window. Lunch prints are the vendor's last traded prices, not invented prices. One clock covers 09:30–16:00. The cron fires through lunch on purpose.

A session dated today is **completed** when the local clock is at or after 16:00. A session dated before the market's local date is completed. The 16:00 minute is therefore complete for T+N backfill. It is not, by itself, the post-close scan.

**Post-close window.** A market is in its post-close window on a Monday–Friday when the local time is **at or after 16:20**, until that local date changes. The 16:20 scheduled run is a full scan of the session that just completed. It rewrites `radar.json` with that session's official close and full-day volume. It is not a closed-market no-op, and it does not leave the 15:30 partial bar in place. A later scheduled run that is still on that local date and at or after 16:20 finalizes the same session, so a delayed 16:20 job still writes the completed bar. After the local date changes, the session is no longer just-completed.

Each market is judged on its own clock. Finalizing one market does not depend on the other market being open or closed.

- A US 16:20 America/New_York run finalizes US names. At that moment Hong Kong is already on the next local date (early morning, not in session). HK names are not finalized and no HK price is invented for a session that has not started.
- An HK 16:20 Asia/Hong_Kong run finalizes HK names. At that moment the US session has not opened (03:20 EST or 04:20 EDT). US names are not finalized. A US bar dated today is not the measurement bar, because the ceiling is still the previous date (§3).
- The two sessions do not overlap at 16:20, but a later same-date run can see one market still inside its post-close window while the other market is open. Hong Kong's next morning is still the previous evening in New York, and a Hong Kong evening after 21:30 during US daylight-saving time is still that Hong Kong date while New York is in its regular session. Only the market inside the post-close window is finalized. The open market may refresh the live radar from its partial daily bar. Its same-day ledger row, if one was already appended, is not replaced.

The workflow cron is UTC, weekdays only, and is a superset so that both EST and EDT are covered, including both 16:20 slots. `workflow_dispatch` stays available.

| Cron (UTC, weekdays) | Why it is there |
| --- | --- |
| `30 1 * * 1-5` | 09:30 Asia/Hong_Kong |
| `*/30 2-7 * * 1-5` | 10:00–15:30 Asia/Hong_Kong, including 12:00 and 12:30 lunch |
| `20 8 * * 1-5` | 16:20 Asia/Hong_Kong. HKT has no DST, so 16:20 HKT is 08:20 UTC |
| `30 13 * * 1-5` | 09:30 America/New_York during EDT; 08:30 during EST (the job no-ops that market in winter) |
| `*/30 14-20 * * 1-5` | Through 15:30 local in both EST and EDT. 20:30 UTC is 16:30 EDT, which is inside the US post-close window, and 15:30 EST, which is still the regular session |
| `20 20 * * 1-5` | 16:20 America/New_York during EDT (20:20 UTC). During EST this is 15:20, still the regular session. The Python clock does not treat it as post-close |
| `20 21 * * 1-5` | 16:20 America/New_York during EST (21:20 UTC). During EDT this is 17:20, still the same local date after 16:20, so that completed US session is finalized |

The Python clock is authoritative. A cron slot that is not an open session and not a post-close window does not invent prices and does not rewrite `radar.json`. GitHub may delay a scheduled run. A delay that is still inside the post-close window still finalizes that market. Scheduled workflows run only from the default branch after this workflow is on that branch.

Exchange holidays are not hard-coded. If the clock says a market is open but the vendor has no bar for that local date, the scanner uses the latest real bar on or before that date. It does not create a bar.

## 3. Metrics

All of these are deterministic.

**Measurement session.** The latest daily bar whose session date is on or before the session-date ceiling. From the local 09:30 open onward, including the post-close window, the ceiling is the market's local date. Before the local open on a weekday, the ceiling is the previous calendar date, so a bar dated today is not measured and is not used as a price for a session that has not started. While that session is still before 16:00 local, the bar may be partial (today's yfinance daily bar). It is still the measurement session for an intraday refresh. From 16:20 local the scheduled run treats that same session date as the completed session: the bar's close is the official close and its volume is the full-day volume. Baseline bars are strictly earlier. The measurement bar is excluded from average volume, ATR, and the trend. The scanner does not create a bar when the vendor has none.

**Minimum history.** 21 baseline bars plus the measurement bar (22 sessions). Fewer than that, a non-positive average volume, a non-positive ATR, or a non-positive close: skip the ticker. Do not emit a point and do not invent a metric.

**Session date.** The calendar date of the bar timestamp in that timestamp's own timezone. Yahoo localizes daily bars to the listing exchange, so a Hong Kong midnight bar stays on that Hong Kong date. A naive timestamp uses its calendar date. Duplicate dates: the last row wins.

**RVOL.** `measurement volume / arithmetic mean of the last 20 baseline volumes`. The current bar is not in the mean.

**price_change.** `measurement close − previous baseline close`, in price units, not a percent, and not close minus open.

**ATR.** 14-day Wilder ATR on baseline bars only. True range is `max(high−low, abs(high−previous close), abs(low−previous close))`. The seed is the simple average of the first 14 true ranges. After that, `ATR_t = (ATR_(t−1) × 13 + TR_t) / 14`.

**Rounding.** Half away from zero. RVOL, displacement, and anomaly score use 6 decimal places. Prices and returns use 4. Hit rates use 4. The anomaly rule and the score use the rounded RVOL and rounded displacement, so the JSON is internally consistent.

**Displacement.** `abs(price_change) / ATR`.

**Anomaly score.** `rounded RVOL / max(rounded displacement, 0.1)`, then rounded to 6 decimal places.

**is_anomaly.** Rounded RVOL ≥ 2.0 and rounded displacement ≤ 0.5. The boundaries are included.

**trend_20d.** On baseline closes, oldest first: `return = close[-1] / close[-21] − 1` (20 sessions). `"up"` when return > 0.03, `"down"` when return < −0.03, otherwise `"sideways"`. A move of exactly 3% is sideways. Closes older than those 21 bars are ignored.

## 4. Tags

Assigned only when `is_anomaly` is true. Otherwise `bargaining_power`, `bargaining_power_label_en`, and `bargaining_power_label_zh` are JSON `null`.

| trend_20d | bargaining_power | English | Traditional Chinese |
| --- | --- | --- | --- |
| `down` | `buyer_absorption` | Buyer Absorption | 買方暗中承接 |
| `up` | `seller_distribution` | Seller Distribution | 賣方暗中出貨 |
| `sideways` | `stalemate_compression` | Stalemate / Compression | 多空角力壓縮 |

The scanner does not retag a row from an earlier session. A same-day partial row is retagged when that market's post-close finalization replaces it with the completed session (§5.2). After that replacement, the tag stays.

## 5. Outputs

Writes are atomic (`*.tmp` then replace). A document that fails validation is not written. Numbers are JSON numbers. Chinese labels are raw UTF-8, not `\u` escapes.

Live scanner output does **not** include `data_status`. The files committed under `public/data/` are empty fixtures (`data_status: "empty_fixture"`) so a checkout is not mistaken for a live scan or for performance. The loader treats an empty fixture with zero records as an empty ledger. It refuses a fixture file that already contains records.

### 5.1 `public/data/radar.json`

Replaced on every full scan. A full scan is a manual run, `workflow_dispatch`, a scheduled run with at least one market in its regular session, or a scheduled run with at least one market in its post-close window. The 16:20 post-close run rewrites this file with the just-completed session's official close and full-day volume. It does not leave the previous intraday file, including a 15:30 partial bar, in place. Points for the other market come from that market's latest real bar on or before its own ceiling. A scheduled run that finds neither an open session nor a post-close window does not rewrite this file.

| Field | Type |
| --- | --- |
| `generated_at` | ISO-8601 string with an offset, second precision, the run clock |
| `universe.us_count` | Number of US points written |
| `universe.hk_count` | Number of HK points written |
| `points` | Array, sorted US then HK, then ticker |

`universe` counts are points in this file, not the watchlist size. A skipped ticker is absent, not filled with a stale or invented point.

Each point:

| Field | Type |
| --- | --- |
| `ticker` | string, verbatim |
| `market` | `"US"` or `"HK"` |
| `rvol` | number |
| `displacement` | number |
| `anomaly_score` | number |
| `is_anomaly` | boolean |
| `trend_20d` | `"down"`, `"up"`, or `"sideways"` |
| `bargaining_power` | one of the three keys, or `null` |
| `bargaining_power_label_en` | contract English label, or `null` |
| `bargaining_power_label_zh` | contract Traditional Chinese label, or `null` |
| `last_price` | number. This scanner always supplies it. Rounded measurement close, 4 decimal places |
| `currency` | `"USD"` for US, `"HKD"` for HK. Always supplied. No FX conversion |

`generated_at` moves when a full scan writes a new file, including the 16:20 post-close scan. A scheduled run outside an open session and outside every post-close window does not refresh it.

### 5.2 `public/data/history_results.json`

Append-only ledger of daily anomalies, plus a full recompute of `summary_by_tag` whenever the file is written.

| Field | Type |
| --- | --- |
| `updated_at` | ISO-8601 string with an offset. Written only when the file is written |
| `records` | Array. Existing order is kept. Rows added in one run are sorted by date, market, ticker |
| `summary_by_tag` | Array of exactly three objects, in the order buyer absorption, seller distribution, stalemate |

Dedup key: `date` + `ticker`. One row per pair.

**Intraday, while that market's session is still open.** The first row for the pair is kept. A later intraday scan does not overwrite `signal_price`, RVOL, displacement, score, tag, or labels. A later intraday scan that no longer sees an anomaly does not delete the row. A new anomaly may be appended. That row is the partial bar. It is not the finalized record. The live radar may still refresh from the partial daily bar.

**Post-close finalization.** This runs for a market inside its post-close window on a scheduled run, and for a manual or `workflow_dispatch` run whose measurement session is already complete (the market is not in its regular session). It applies only to that market and only to the completed session date. The other market is left alone, whether it is still open, already closed, or not yet open.

- If the completed session is an anomaly and a same-day row already exists, replace `signal_price`, RVOL, displacement, anomaly score, bargaining-power tag, and both labels with the completed-session values. `signal_price` is the official close. RVOL uses the full-day volume over the prior 20 sessions, excluding that bar. Displacement, score, and tag use the same formulas as an intraday point. An earlier partial bar must not remain as those stored fields. A filled T+N return on that row is not cleared and is not revised.
- If the completed session is an anomaly and no same-day row exists, append the row. A name that was not an anomaly on the partial bar can still be flagged once the full day is known.
- If the completed session is not an anomaly and a same-day row exists, remove that row. A partial bar must not lock a flag, a price, an RVOL, a displacement, a score, or a tag that the completed session does not confirm. Rows for other dates are not removed.
- A ticker with no real bar on the completed session date is not finalized and is not deleted. The scanner does not invent that price.

A later session does not overwrite a finalized row, except that a still-null T+N return can be filled. `summary_by_tag` is recomputed whenever the file is written, so a replacement or a removal updates the cards.

Each record:

| Field | Type |
| --- | --- |
| `date` | `YYYY-MM-DD`, the measurement session's date in that market |
| `ticker` | string |
| `market` | `"US"` or `"HK"` |
| `signal_price` | number, the measurement close recorded for that session. An intraday row may still hold the partial close. The post-close run replaces it with the official close |
| `currency` | `"USD"` or `"HKD"` |
| `rvol`, `displacement`, `anomaly_score` | numbers from the intraday row until the post-close run replaces them with the completed session. RVOL then uses the full-day volume |
| `bargaining_power` | one of the three keys. Never null on a ledger row |
| `bargaining_power_label_en` | contract English label |
| `bargaining_power_label_zh` | contract Traditional Chinese label |
| `t_plus_3_return_pct` | number or `null` |
| `t_plus_5_return_pct` | number or `null` |
| `t_plus_10_return_pct` | number or `null` |

Returns are percentage points: `1.25` means +1.25%. `0` means a flat return, not "missing". Missing stays `null` (the UI's 待補). A filled return is not revised if a later download differs.

**T+N.** N is N session dates in that ticker's downloaded daily bars after the signal date, not N calendar days. The scanner does not insert weekends or missing sessions. The close is used only when that target session is completed (§2). 

`return = (round(close, 4) / round(signal_price, 4) − 1) × 100`, then rounded to 4 decimal places.

Downloads use yfinance `auto_adjust=False` and the unadjusted `Close` column. `Adj Close` is ignored. `repair` is off. A split between the signal and T+N can distort the percentage. This MVP does not invent a split adjustment.

**Scheduled run, no open session and no post-close window.** No new ledger rows and no same-day replacement (that would be a fresh flag, and the radar is not being refreshed). Existing null returns are filled from completed bars. If no return changes, the file is left untouched, including `updated_at`. A 16:00 local slot is this case. A 16:20 local slot is not.

**Full scan (manual, workflow_dispatch, at least one market open, or at least one market in its post-close window).** `radar.json` is rewritten from the latest real bars. Ledger rows follow the intraday rule for an open market and the post-close rule for a market being finalized. Null returns may be filled. Both files are written. A post-close run still writes `radar.json` when the ledger row count does not change, because the official close replaces the partial bar.

### 5.3 `summary_by_tag`

This is the unfiltered Track Record card payload (§11.6). The UI recomputes when the user filters; the file is the full-ledger figure. The scanner always writes all three tags, including zeros.

```json
{
  "bargaining_power": "buyer_absorption",
  "bargaining_power_label_en": "Buyer Absorption",
  "bargaining_power_label_zh": "買方暗中承接",
  "sample_count": 2,
  "t_plus_3": {
    "sample_count": 1,
    "average_return_pct": 1.0,
    "hit_rate_pct": 100.0,
    "hit_rate_applicable": true,
    "hit_rate_label": null
  },
  "t_plus_5": {
    "sample_count": 0,
    "average_return_pct": null,
    "hit_rate_pct": null,
    "hit_rate_applicable": true,
    "hit_rate_label": null
  },
  "t_plus_10": {
    "sample_count": 0,
    "average_return_pct": null,
    "hit_rate_pct": null,
    "hit_rate_applicable": true,
    "hit_rate_label": null
  }
}
```

| Field | Meaning |
| --- | --- |
| `sample_count` on the tag | Ledger rows with that tag, including rows whose returns are still null. This is 樣本 |
| `t_plus_N.sample_count` | Rows with a non-null return for that horizon. This is the footnote count |
| `t_plus_N.average_return_pct` | Arithmetic mean of those returns, 4 decimal places, or `null` when the horizon sample is 0 (尚無). Not a numeric 0 unless the mean is actually 0 |
| `t_plus_N.hit_rate_pct` | Hits / horizon sample × 100, 4 decimal places. `100.0` means 100%. `0.0` means the sample exists and none were hits |
| `t_plus_N.hit_rate_applicable` | `false` only for stalemate |
| `t_plus_N.hit_rate_label` | `"不適用"` for stalemate, otherwise `null` |

Hit rules:

- Buyer Absorption: a hit is a return **strictly greater than 0**.
- Seller Distribution: a hit is a return **strictly less than 0**.
- A return of exactly 0 is inside the horizon sample and is not a hit.
- Null returns are excluded from that horizon's average and hit rate.
- Stalemate / Compression has no directional test. `hit_rate_pct` is `null` and `hit_rate_label` is `不適用` even when the horizon sample is non-zero. That is not a numeric 0.

The stalemate object is the same shape, with `hit_rate_applicable: false` and `hit_rate_label: "不適用"` on every horizon.

## 6. Validation, errors, and security

The scanner validates both documents before replacing them. Validation checks required fields, the US/HK and tag enums, label strings, finite numbers, dedup keys, the anomaly rule against the rounded metrics, and that `summary_by_tag` equals a fresh compute from `records`.

| Exit | When | Files |
| --- | --- | --- |
| 0 | Scan written, or an honest no-op (scheduled run with no open session and no post-close window, and nothing to backfill, or backfill found no completed session) | Unchanged on a no-op |
| 2 | Watchlist, fixture, clock, or existing history failed validation | Unchanged |
| 3 | Live download produced no usable bars, or every ticker was skipped | Unchanged. A partial outage that still yields some points writes those points and skips the rest |
| 4 | `--push` refused, or git commit/push failed | A refused `--push` does not write. A git failure after a successful write leaves the local JSON in place and does not force-push |

Security:

- Tickers are a closed character set and are passed as arguments to the yfinance library, never through a shell.
- `--push` runs only when `GITHUB_ACTIONS=true` and `GITHUB_REPOSITORY` is set. A local or unattended `--push` is refused before any file write and before `git commit` or `git push`.
- `--push` together with `--bars` is refused even inside GitHub Actions. Fixture output cannot be published as a scan.
- The publish command is `git push` with no `--force` and no lease bypass.
- No secrets are read or written. Do not commit an API token. There is nothing to put in `.env`.
- The scanner does not call an AI model and does not send the watchlist to one.

Downloads are chunked at 40 symbols. A chunk that throws is skipped. If every chunk fails, the run exits 3 and keeps the previous JSON.

## 7. Local commands

Install and test (no network, no live prices):

```bash
python -m pip install -r requirements-dev.txt
python -m pytest
```

Fixture scan (writes only the paths you pass; does not touch a publish step):

```bash
python -m scanner \
  --watchlist tests/fixtures/mini_watchlist.json \
  --bars tests/fixtures/mini_bars.json \
  --now 2026-11-27T15:00:00-05:00 \
  --radar /tmp/evr-radar.json \
  --history /tmp/evr-history.json
```

Scheduled post-close scan of the same fixture (16:20 America/New_York). This rewrites the radar with the completed session instead of taking the closed-market backfill path. The fixture bars are synthetic. They are not live prices.

```bash
python -m scanner \
  --watchlist tests/fixtures/mini_watchlist.json \
  --bars tests/fixtures/mini_bars.json \
  --now 2026-11-27T16:20:00-05:00 \
  --scheduled \
  --radar /tmp/evr-radar-postclose.json \
  --history /tmp/evr-history-postclose.json
```

`python` is `python3` on images that do not install the `python` alias. GitHub Actions uses `python` from `actions/setup-python` 3.12.

A `--bars` run that targets `public/data/radar.json` or `public/data/history_results.json` is refused (exit 2) before those files are opened for writing. Fixture numbers stay out of the committed ledger.

CI (`.github/workflows/ci.yml`) runs `python -m pytest` on pull requests and on pushes to `main`. It does not download market data. The fixture path is tested with yfinance patched to fail if called.

The scan workflow (`.github/workflows/scan.yml`) is `schedule` plus `workflow_dispatch` only. It installs `requirements.txt` (no pytest) and runs the scanner with `--push`.

## 8. What this repository does not do

- No HTML, CSS, Tailwind, React, Next.js, or other UI.
- No Vercel project, no deploy, no repository-setting changes.
- No live performance numbers in git. `public/data/*.json` is an empty labeled fixture until a real Actions run replaces it.
- No currency conversion, no in-app threshold editor, and no browser recalculation of RVOL or tags.
