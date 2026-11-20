"""TeacherEdLab Flask application: pages, JSON API, CSV import/export."""
import hmac
import io
import time
from collections import defaultdict, deque

import pandas as pd
from flask import Flask, Response, abort, jsonify, render_template, request

import analytics
import db
import questionnaire as Q
import training
from config import Config
from validation import clean_text, validate_submission


def create_app(config_object=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_object)
    app.teardown_appcontext(db.close_db)
    db.init_db(app.config["DATABASE"])
    hits = defaultdict(deque)

    # ------------------------------------------------------------------ helpers
    def error(message, status=400, **extra):
        return jsonify({"ok": False, "error": message, **extra}), status

    def require_researcher(fn):
        from functools import wraps

        @wraps(fn)
        def wrapper(*a, **kw):
            supplied = request.headers.get("X-Researcher-Key", "")
            if not hmac.compare_digest(supplied.encode(), app.config["RESEARCHER_KEY"].encode()):
                return error("Researcher key missing or incorrect.", 401)
            return fn(*a, **kw)
        return wrapper

    def csv_safe(value):
        """Neutralise spreadsheet formula injection in exported text."""
        if isinstance(value, str) and value[:1] in ("=", "+", "-", "@", "\t", "\r"):
            return "'" + value
        return value

    @app.after_request
    def security_headers(resp):
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Referrer-Policy"] = "same-origin"
        resp.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
            "script-src 'self'; frame-ancestors 'none'")
        if request.path.startswith("/api/"):
            resp.headers["Cache-Control"] = "no-store"
        return resp

    # -------------------------------------------------------------------- pages
    ctx = dict(domains=Q.DOMAINS, pathway=training.PATHWAY, modules=training.MODULES)

    @app.route("/")
    def home():
        return render_template("index.html", **ctx)

    @app.route("/about")
    def about():
        return render_template("about.html", **ctx)

    @app.route("/questionnaire")
    def questionnaire_page():
        return render_template("questionnaire.html", **ctx)

    @app.route("/dashboard")
    def dashboard_page():
        return render_template("dashboard.html", **ctx)

    @app.route("/training")
    def training_page():
        return render_template("training.html", **ctx)

    @app.route("/modules")
    def modules_page():
        return render_template("modules.html", **ctx)

    @app.route("/export")
    def export_page():
        return render_template("export.html", fields=data_dictionary(), **ctx)

    @app.route("/health")
    def health():
        db.get_db().execute("SELECT 1")
        return jsonify({"status": "ok"})

    # ---------------------------------------------------------------------- API
    @app.get("/api/questionnaire")
    def api_questionnaire():
        return jsonify(Q.public_structure())

    @app.get("/api/modules")
    def api_modules():
        return jsonify({"status": "PROPOSED design, not yet evaluated",
                        "pathway": training.PATHWAY, "modules": training.MODULES})

    @app.post("/api/responses")
    def api_save_response():
        ip = request.remote_addr or "?"
        now = time.time()
        q = hits[ip]
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= app.config["SUBMIT_LIMIT_PER_MINUTE"]:
            return error("Too many submissions from this address. Try again in a minute.", 429)
        q.append(now)

        payload = request.get_json(silent=True)
        if payload is None:
            return error("Send the response as JSON (Content-Type: application/json).", 415)
        clean, errors = validate_submission(payload, app.config["MAX_OPEN_TEXT_CHARS"])
        if errors:
            return error("Validation failed.", 422, fields=errors)
        conn = db.get_db()
        try:
            with conn:
                rid = db.insert_respondent(conn, clean, "collected", Q.CONSENT_VERSION)
        except Exception:                                   # pragma: no cover
            app.logger.exception("Could not save response")
            return error("The response could not be saved. Please try again.", 500)
        return jsonify({"ok": True, "message": "Response saved. Thank you.", "reference": rid}), 201

    @app.get("/api/dashboard/summary")
    def api_dashboard():
        source = request.args.get("source", "all")
        if source not in analytics.VALID_SOURCES:
            return error("source must be one of: " + ", ".join(analytics.VALID_SOURCES))
        category = request.args.get("category") or None
        practicum = request.args.get("practicum") or None
        if category and category not in Q.BACKGROUND["category"]["options"]:
            return error("Unknown category.")
        if practicum and practicum not in Q.BACKGROUND["practicum_status"]["options"]:
            return error("Unknown practicum status.")
        conn = db.get_db()
        counts = {r["source"]: r["c"] for r in conn.execute(
            "SELECT source, COUNT(*) c FROM respondents GROUP BY source")}
        out = analytics.build_dashboard(conn, source, category, practicum)
        out["available_sources"] = counts
        return jsonify(out)

    @app.post("/api/import")
    @require_researcher
    def api_import():
        f = request.files.get("file")
        if not f or not f.filename:
            return error("Attach a CSV file in the 'file' field.")
        if not f.filename.lower().endswith(".csv"):
            return error("Only .csv files are accepted.", 415)
        try:
            df = pd.read_csv(io.BytesIO(f.read()), dtype=str, keep_default_na=False)
        except Exception:
            return error("The file could not be read as CSV.", 422)
        if len(df) == 0:
            return error("The CSV contains no data rows.", 422)
        if len(df) > app.config["MAX_IMPORT_ROWS"]:
            return error(f"Too many rows (limit {app.config['MAX_IMPORT_ROWS']}).", 413)
        missing = [c for c in ["category", "practicum_status", "ai_exposure", *Q.ITEM_CODES] if c not in df.columns]
        if missing:
            return error("Missing required columns.", 422, missing=missing[:40])

        accepted, rejected = [], []
        for idx, row in df.iterrows():
            payload = {"consent": True,  # import requires documented consent upstream
                       "answers": {c: row[c] for c in Q.ITEM_CODES},
                       "open": {q["code"]: row.get(q["code"], "") for q in Q.OPEN_QUESTIONS},
                       **{k: row[k] for k in Q.BACKGROUND}}
            clean, errs = validate_submission(payload, app.config["MAX_OPEN_TEXT_CHARS"])
            if errs:
                rejected.append({"row": int(idx) + 2, "errors": errs})
            else:
                accepted.append(clean)
        conn = db.get_db()
        with conn:
            cur = conn.execute("INSERT INTO import_batches (filename, created_at, rows_read, rows_saved)"
                               " VALUES (?,?,?,?)", (clean_text(f.filename, 120), db.now_iso(), len(df), len(accepted)))
            for c in accepted:
                db.insert_respondent(conn, c, "imported", Q.CONSENT_VERSION, batch_id=cur.lastrowid)
        return jsonify({"ok": True, "rows_read": len(df), "rows_saved": len(accepted),
                        "rows_rejected": len(rejected), "rejected": rejected[:50]}), 200

    def wide_export(conn, source):
        wide = analytics.load_wide(conn, source)
        opens = pd.read_sql_query("SELECT respondent_id, question_code, response_text FROM open_responses", conn)
        if not opens.empty:
            ow = opens.pivot(index="respondent_id", columns="question_code", values="response_text")
            wide = wide.merge(ow, left_on="id", right_index=True, how="left")
        for q in Q.OPEN_QUESTIONS:
            if q["code"] not in wide.columns:
                wide[q["code"]] = ""
        cols = ["id", "created_at", "source", "category", "practicum_status", "ai_exposure",
                *Q.ITEM_CODES, *[q["code"] for q in Q.OPEN_QUESTIONS]]
        wide = wide[cols].rename(columns={"id": "respondent_id"}).fillna("")
        for q in Q.OPEN_QUESTIONS:
            wide[q["code"]] = wide[q["code"]].map(csv_safe)
        return wide

    def csv_response(df, name):
        return Response(df.to_csv(index=False), mimetype="text/csv",
                        headers={"Content-Disposition": f'attachment; filename="{name}"'})

    @app.get("/api/export/responses.csv")
    @require_researcher
    def export_responses():
        source = request.args.get("source", "all")
        if source not in analytics.VALID_SOURCES:
            return error("Invalid source.")
        return csv_response(wide_export(db.get_db(), source), f"teacheredlab_responses_{source}.csv")

    @app.get("/api/export/domain-summary.csv")
    @require_researcher
    def export_summary():
        source = request.args.get("source", "all")
        if source not in analytics.VALID_SOURCES:
            return error("Invalid source.")
        rows = analytics.domain_summary(analytics.load_wide(db.get_db(), source))
        df = pd.DataFrame(rows).drop(columns=["color"])
        df.insert(0, "data_source_filter", source)
        return csv_response(df.rename(columns={"code": "domain_code", "name": "domain", "alpha": "cronbach_alpha"}), f"teacheredlab_domain_summary_{source}.csv")

    @app.get("/api/data-dictionary")
    def api_dictionary():
        return jsonify(data_dictionary())

    def data_dictionary():
        rows = [
            ("respondent_id", "integer", "Internal row number. Not linked to any identity."),
            ("created_at", "ISO 8601 UTC text", "Time the response was saved."),
            ("source", "collected | synthetic | imported", "Where the record came from. Synthetic = demonstration only."),
            ("category", "text", "Participant category (see questionnaire)."),
            ("practicum_status", "text", "Not yet started / In progress / Completed one or more placements."),
            ("ai_exposure", "text", "Never / Occasionally / Regularly."),
        ]
        for d in Q.DOMAINS:
            rows.append((f"{d['code']}1 to {d['code']}5", "integer 1-5",
                         f"Likert items for {d['name']} (1 = strongly disagree, 5 = strongly agree)."))
        for q in Q.OPEN_QUESTIONS:
            rows.append((q["code"], "text (max 1000 chars)", q["text"]))
        return [{"field": a, "type": b, "meaning": c} for a, b, c in rows]

    # ------------------------------------------------------------------- errors
    @app.errorhandler(404)
    def not_found(_e):
        if request.path.startswith("/api/"):
            return error("Not found.", 404)
        return render_template("error.html", code=404, message="That page does not exist.", **ctx), 404

    @app.errorhandler(413)
    def too_large(_e):
        return error("Upload too large (limit 2 MB).", 413)

    @app.errorhandler(405)
    def bad_method(_e):
        return error("Method not allowed.", 405)

    @app.errorhandler(500)
    def server_error(_e):                                   # pragma: no cover
        if request.path.startswith("/api/"):
            return error("Unexpected server error.", 500)
        return render_template("error.html", code=500, message="Something went wrong on our side.", **ctx), 500

    @app.cli.command("init-db")
    def cli_init():
        db.init_db(app.config["DATABASE"]); print("Database initialised:", app.config["DATABASE"])

    return app


if __name__ == "__main__":
    application = create_app()
    print("TeacherEdLab running locally. Press Ctrl+C to stop.")
    application.run(host="127.0.0.1", port=5000, debug=False)
