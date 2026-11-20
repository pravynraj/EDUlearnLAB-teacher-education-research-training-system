"""Generate SYNTHETIC demonstration responses (clearly labelled source='synthetic').

These records exist only to demonstrate the dashboard. They are not participant
data and must never be reported as research findings. Open-ended answers are
deliberately left empty so that no invented 'quotations' exist.
"""
import argparse
import numpy as np
from config import Config
from db import init_db, insert_respondent, _connect
from questionnaire import BACKGROUND, DOMAINS, CONSENT_VERSION

# Arbitrary demonstration means (NOT empirical estimates).
DEMO_BASE = {"PED": 3.8, "DAI": 3.2, "ASL": 3.0, "INC": 3.4, "SEF": 3.5, "PMR": 3.6}


def generate(n=120, seed=2026):
    rng = np.random.default_rng(seed)
    records = []
    for _ in range(n):
        g = rng.normal(0, 0.55)                       # general readiness factor
        cat = rng.choice(BACKGROUND["category"]["options"], p=[.35, .30, .15, .12, .08])
        prac = rng.choice(BACKGROUND["practicum_status"]["options"], p=[.25, .35, .40])
        ai = rng.choice(BACKGROUND["ai_exposure"]["options"], p=[.15, .50, .35])
        answers = {}
        for d in DOMAINS:
            dom = rng.normal(0, 0.45)
            bonus = 0.25 if (d["code"] == "PMR" and prac != "Not yet started") else 0
            bonus += 0.30 if (d["code"] == "DAI" and ai == "Regularly") else 0
            for i in range(1, 6):
                val = DEMO_BASE[d["code"]] + g + dom + bonus + rng.normal(0, 0.6)
                answers[f"{d['code']}{i}"] = int(np.clip(round(val), 1, 5))
        records.append({"category": str(cat), "practicum_status": str(prac),
                        "ai_exposure": str(ai), "answers": answers, "open": {}})
    return records


def seed(path, n=120, seed_value=2026, replace=True):
    init_db(path)
    conn = _connect(path)
    if replace:
        conn.execute("DELETE FROM respondents WHERE source='synthetic'")
    for rec in generate(n, seed_value):
        insert_respondent(conn, rec, "synthetic", CONSENT_VERSION)
    conn.commit(); conn.close()
    return n


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=120)
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--db", default=Config.DATABASE)
    a = ap.parse_args()
    print(f"Seeded {seed(a.db, a.n, a.seed)} SYNTHETIC respondents into {a.db}")
