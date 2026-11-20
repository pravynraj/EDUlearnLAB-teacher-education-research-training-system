# TeacherEdLab

Working prototype for **"Integrated Pre-Service Teacher Education: Proposed Methodology, Data Collection & Training Architecture"**.
Flask + SQLite + pandas/NumPy back end; HTML/CSS/JavaScript + Bootstrap 5.3.2 front end.

## Run it (local only)
```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python seed_demo.py          # OPTIONAL: adds 120 SYNTHETIC demonstration respondents
python app.py                # http://127.0.0.1:5000
```
The database (`instance/teacheredlab.sqlite3`) is created automatically on first start.
Set `TEDLAB_RESEARCHER_KEY` (see `config.example.env`); the default `demo-researcher-key` is for local demonstration only.

## Tests
```bash
python tests/run_tests.py                      # 32 API / validation / database / CSV / analytics tests
python app.py &                                # then, with a running server:
python tests/browser_check.py http://127.0.0.1:5000   # 10 real-browser checks (needs: playwright install chromium)
```
Results are written to `docs/test_results.json` and `docs/browser_results.json`.
Run the browser checks against a scratch database (`TEDLAB_DB=/tmp/x.sqlite3`): they submit one real form entry.

## Data honesty
* `source = synthetic` rows come from `seed_demo.py`. They are **demonstration data, not participants or findings**, and the dashboard says so.
* The dashboard shows a "MIXED DATA" warning whenever more than one source is in view.
* No empirical results, reliability coefficients or interview findings are included.

## What is and is not implemented
Implemented: consent-gated questionnaire (30 Likert items, 3 open questions), validation, SQLite storage, dashboard with filters,
CSV import/export (researcher key), data dictionary, training pathway and learning modules pages, rate limiting, security headers.
Not implemented: an Administrator role, user accounts (the researcher key is a single shared secret), CSRF tokens, interview
capture, thematic analysis tooling, production deployment (WSGI/HTTPS). Charts use a small in-house SVG module because Chart.js
could not be downloaded in the offline build environment; swap in Chart.js in `static/js/charts.js` if required.

## Layout
`app.py` routes · `db.py` schema · `analytics.py` pandas/NumPy · `validation.py` · `questionnaire.py` content · `training.py` content ·
`seed_demo.py` · `templates/` · `static/` · `tests/` · `docs/`
