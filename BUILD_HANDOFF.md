# BUILD_HANDOFF

## Pull request

- PR: opened from this branch and stacked on scanner PR #1
- Branch: `cursor/product-ui-7260`
- Head SHA: recorded after the tip commit
- Starting SHA: `f1121faaf55cb2d71b0f20156f9489ae43b2aad9`
- Scanner PR: https://github.com/manwai-1/effort-vs-result-radar/pull/1
- Base of that PR: `main` at `41f6ac5a5f540fd6fc35c2266612fefbf9d63ae1`
- Confirmed before coding: `f1121faaf55cb2d71b0f20156f9489ae43b2aad9` was still the tip of `cursor/scanner-data-contract-7fee` and the head of open PR #1

## Documents

- DESIGN.md SHA-256: `4a5444dcb52562d0117e499c6a52452d5079c92e013db4186e7363da2babb38c`
- API_SPEC.md SHA-256: `fa72f4d813019274b80caa6831a16265a2acd431692067352f22a80bc9bc1747`
- DESIGN.md was not edited. API_SPEC.md, the scanner, `watchlist.json`, and the committed empty fixtures were not edited.

## Commands

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m pytest
npm ci
npm test
npm run lint
npm run build
npm run start -- --hostname 127.0.0.1 --port 3000
```

`python` is not on PATH in this environment; `python3 -m pytest` is the same test job CI runs as `python -m pytest`.

## Tested URL

`http://127.0.0.1:3000`

Loopback preview of `next start` on this machine only. It was not deployed, not published, and not opened by anyone else. There is no public preview URL.

## Browser QA

Chrome headless via Playwright, device scale 1.

| Pass | CSS viewport | Result |
| --- | --- | --- |
| Empty fixture | 1440×1000 and 390×844 | `scrollWidth` equals `clientWidth`. No console errors. No images. No `1970`. No 72-hour notice. Plot height 480px and 280px. |
| Populated local fixture | 1440×1200 and 390×844 | `scrollWidth` equals `clientWidth`. No page errors. Last scan `2026-11-26 09:30 香港時間`. Three anomalies. `待補`, `+0.00%`, and U+2212 minus rendered. |
| Stale local fixture | 1440×800 | Header shows the real timestamp and `掃描時間已超過 72 小時，資料可能已過時。` |
| File errors | 1440×900 | Radar abort shows `未能載入 /data/radar.json。` History abort shows `未能載入 /data/history_results.json。` |
| Filters | 1440 and 390 | Market buttons do not overlap tags. HK hides US rows. All tags off shows `請至少選擇一項議價狀態。` |
| Dialog | 1440 and 390 | Methodology copy matches §11.7. Escape closes it. |
| Focus | 1440 | Refresh and chart focus ring is 2px `#E8B849` with 2px `#12161C` offset. |
| Reduced motion | 1440 | `prefers-reduced-motion: reduce` matched. |

Measured contrast on computed colors:

| Pair | Ratio |
| --- | --- |
| Title `#F4F1EA` on card `#12161C` | 16.09:1 |
| Timestamp `#9AA3B2` on card | 7.13:1 |
| Selected tab `#07090C` on `#E8B849` | 10.81:1 |
| Footer `#9AA3B2` on page `#07090C` | 7.84:1 |
| Unselected tag text at the specified 70% opacity, blended onto the page | 8.72:1 |

No specified token pair failed AA. No images are used, so none were broken.

## Screenshots

Local captures from this run:

- `/opt/cursor/artifacts/evr-qa/empty-1440-full.png`
- `/opt/cursor/artifacts/evr-qa/empty-390-full.png`
- `/opt/cursor/artifacts/evr-qa/empty-1440-record.png`
- `/opt/cursor/artifacts/evr-qa/empty-390-record.png`
- `/opt/cursor/artifacts/evr-qa/empty-1440-dialog.png`
- `/opt/cursor/artifacts/evr-qa/empty-390-dialog.png`
- `/opt/cursor/artifacts/evr-qa/chart-card-1440.png`
- `/opt/cursor/artifacts/evr-qa/tip-1440-radar.png`
- `/opt/cursor/artifacts/evr-qa/tip-1440-record.png`
- `/opt/cursor/artifacts/evr-qa/tip-390-radar.png`
- `/opt/cursor/artifacts/evr-qa/final-390-record.png`
- `/opt/cursor/artifacts/evr-qa/leaderboard-zoom.png`
- `/opt/cursor/artifacts/evr-qa/final-stale-header.png`
- `/opt/cursor/artifacts/evr-qa/final-error-radar.png`
- `/opt/cursor/artifacts/evr-qa/final-error-history.png`

## Fixture handling

Committed `public/data/*.json` stays `data_status: empty_fixture` with empty points and records. The UI treats that as the empty state: skeletons, then `尚未有已標記的異常紀錄` and `沒有名稱符合 RVOL ≥ 2.0 且 Displacement ≤ 0.5。` The epoch timestamp is not shown. The last-scan line is `最近掃描：時間未有提供`. The 72-hour notice is not fired.

Populated, stale, and error checks used labeled JSON under `/tmp/qa-fixtures`. Those files were not committed. The committed fixtures were restored afterward.

## Notes

- When a plotted value reaches the default axis ceiling, the domain grows by 5% so the point glyph is not clipped. Reference lines stay at 2.0 and 0.5.
- Pagination controls, used only above 100 anomalies, read `上一頁`, `第 {p} 頁`, and `下一頁`.
- A real history file with `updated_at` shows `Ledger updated {time} 香港時間`. The empty fixture does not.
- `font-mono` falls through to Noto Sans TC so Chinese in formulas is not tofu. IBM Plex Sans, Noto Sans TC, and IBM Plex Mono are self-hosted by `next/font`.
- `tests/test_public_data.py` now keeps UI files out of the scanner package and expects `app/page.tsx`. Scanner behavior tests are unchanged.
- Desktop leaderboard sort icons sit under the column label so the header words stay inside the column.
