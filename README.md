# Effort vs Result Radar

Deterministic US and Hong Kong scanner for high-volume, low-displacement sessions. Python and yfinance write static JSON. Routine scans do not call an AI model.

The data contract, formulas, session clock, and publish gate are in [API_SPEC.md](API_SPEC.md). There is no web UI in this repository.

```bash
python -m pip install -r requirements-dev.txt
python -m pytest
python -m scanner \
  --watchlist tests/fixtures/mini_watchlist.json \
  --bars tests/fixtures/mini_bars.json \
  --now 2026-11-27T15:00:00-05:00 \
  --radar /tmp/evr-radar.json \
  --history /tmp/evr-history.json
```

`watchlist.json` is a dated Nasdaq-100 and Hang Seng Index membership snapshot. `public/data/radar.json` and `public/data/history_results.json` are empty fixtures, not live results. `--push` publishes only from GitHub Actions.
