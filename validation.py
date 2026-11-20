"""Input validation shared by the submission API and the CSV importer."""
import re
from questionnaire import ITEM_CODES, BACKGROUND, OPEN_QUESTIONS

_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def clean_text(value, max_chars):
    if value is None:
        return None
    text = _CTRL.sub("", str(value)).strip()
    if not text:
        return None
    return text[:max_chars]


def validate_submission(payload, max_chars=1000, require_consent=True):
    """Return (clean, errors). `errors` maps field name -> message."""
    errors, clean = {}, {}
    if not isinstance(payload, dict):
        return None, {"_": "Request body must be a JSON object."}

    if require_consent and payload.get("consent") is not True:
        errors["consent"] = "Informed consent is required before submitting."

    for field, spec in BACKGROUND.items():
        val = payload.get(field)
        if val not in spec["options"]:
            errors[field] = f"Choose one of the listed options for '{spec['label']}'."
        else:
            clean[field] = val

    answers = payload.get("answers")
    if not isinstance(answers, dict):
        errors["answers"] = "Answers must be an object keyed by item code."
        answers = {}
    clean_answers = {}
    for code in ITEM_CODES:
        v = answers.get(code)
        if isinstance(v, bool) or not isinstance(v, (int, str)) or str(v).strip() not in {"1", "2", "3", "4", "5"}:
            errors[code] = "Choose a rating from 1 to 5."
        else:
            clean_answers[code] = int(v)
    unknown = set(answers) - set(ITEM_CODES)
    if unknown:
        errors["answers"] = f"Unknown item codes: {', '.join(sorted(unknown))[:80]}"
    clean["answers"] = clean_answers

    open_in = payload.get("open") or {}
    if not isinstance(open_in, dict):
        errors["open"] = "Open-ended answers must be an object."
        open_in = {}
    clean["open"] = {q["code"]: clean_text(open_in.get(q["code"]), max_chars)
                     for q in OPEN_QUESTIONS if clean_text(open_in.get(q["code"]), max_chars)}
    return (None, errors) if errors else (clean, {})
