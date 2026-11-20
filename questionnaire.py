"""Questionnaire definition: six competency domains x five Likert items,
background fields and open-ended questions. Single source of truth used by the
API, the front end, validation, import/export and the data dictionary."""

LIKERT = {1: "Strongly disagree", 2: "Disagree", 3: "Neutral", 4: "Agree", 5: "Strongly agree"}

DOMAINS = [
    {"code": "PED", "name": "Pedagogical competence", "color": "#1B7F79",
     "items": [
        "I can plan a lesson with clear learning outcomes, activities and closure.",
        "I can choose teaching strategies that suit the topic and the learners.",
        "I can manage classroom time, routines and learner behaviour effectively.",
        "I can explain difficult ideas in ways learners can follow.",
        "I can connect lesson content to learners' everyday experiences."]},
    {"code": "DAI", "name": "Digital and AI readiness", "color": "#3D5A99",
     "items": [
        "I can select digital tools that support a specific learning goal.",
        "I can design a lesson activity that uses technology meaningfully.",
        "I understand what generative AI tools can and cannot do reliably.",
        "I can check AI-generated content for errors, bias and suitability before using it.",
        "I can guide learners to use digital and AI tools responsibly."]},
    {"code": "ASL", "name": "Assessment literacy", "color": "#C9822B",
     "items": [
        "I can write assessment tasks that match the intended learning outcomes.",
        "I can design a simple rubric with clear performance criteria.",
        "I can use formative assessment to adjust my teaching during a lesson.",
        "I can give feedback that helps learners know what to do next.",
        "I can interpret assessment results to identify learning gaps."]},
    {"code": "INC", "name": "Inclusive teaching", "color": "#8A5A9E",
     "items": [
        "I can adapt materials for learners with different abilities and needs.",
        "I can create a classroom climate where every learner feels respected.",
        "I can recognise learners who may need additional support.",
        "I can use more than one way to present content and let learners show understanding.",
        "I know how to seek help from colleagues or specialists for learner support."]},
    {"code": "SEF", "name": "Teaching self-efficacy", "color": "#B8465A",
     "items": [
        "I am confident that I can motivate learners who show little interest.",
        "I am confident that I can handle disruptive behaviour calmly.",
        "I believe I can help most learners reach the lesson outcomes.",
        "I feel prepared to take full responsibility for a class.",
        "I stay confident in my teaching after a lesson did not go well."]},
    {"code": "PMR", "name": "Practicum, mentoring and reflection", "color": "#5E7D3A",
     "items": [
        "My practicum experiences gave me enough chances to teach real classes.",
        "I receive specific, useful feedback from my mentor teacher or supervisor.",
        "I reflect on my lessons in writing or discussion after teaching.",
        "I change my teaching based on feedback and my own reflection.",
        "My coursework and my school placement support each other."]},
]

BACKGROUND = {
    "category": {"label": "Participant category", "required": True, "options": [
        "B.Ed (two-year)", "Integrated B.Ed (four-year)", "D.El.Ed / diploma",
        "M.Ed or postgraduate", "Other teacher trainee"]},
    "practicum_status": {"label": "Practicum status", "required": True, "options": [
        "Not yet started", "In progress", "Completed one or more placements"]},
    "ai_exposure": {"label": "Use of AI tools for study or teaching", "required": True, "options": [
        "Never", "Occasionally", "Regularly"]},
}

OPEN_QUESTIONS = [
    {"code": "OQ1", "text": "Which part of your training has prepared you best for the classroom, and why?"},
    {"code": "OQ2", "text": "Where do you feel least prepared, and what support would help most?"},
    {"code": "OQ3", "text": "How do you use, or how would you like to use, digital or AI tools in teaching?"},
]

ITEM_CODES = [f"{d['code']}{i}" for d in DOMAINS for i in range(1, len(d["items"]) + 1)]
DOMAIN_BY_CODE = {d["code"]: d for d in DOMAINS}
ITEM_TEXT = {f"{d['code']}{i}": t for d in DOMAINS for i, t in enumerate(d["items"], 1)}
SOURCES = ("collected", "synthetic", "imported")
CONSENT_VERSION = "v1-draft"


def item_domain(code: str) -> str:
    return code[:3]


def public_structure():
    return {
        "likert": LIKERT, "background": BACKGROUND, "open_questions": OPEN_QUESTIONS,
        "consent_version": CONSENT_VERSION,
        "domains": [{"code": d["code"], "name": d["name"], "color": d["color"],
                     "items": [{"code": f"{d['code']}{i}", "text": t}
                               for i, t in enumerate(d["items"], 1)]} for d in DOMAINS],
    }
