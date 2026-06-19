from __future__ import annotations

from collections import Counter


MAX_RESUME_SEARCH_INTENTS = 5


# Legacy fallback used only for resumes uploaded before resume_intents existed.
# New uploads should use LLM-extracted/stored intents from the resume_intents table.
PROFILE_BUCKETS = {
    "ai_ml_rag": {
        "query_terms": [
            "AI",
            "ML",
            "RAG",
            "LangChain",
            "LangGraph",
            "Python",
            "LLM",
        ],
        "keywords": {
            "agentic ai",
            "ai",
            "deep learning",
            "generative ai",
            "hugging face",
            "keras",
            "langchain",
            "langgraph",
            "llm",
            "machine learning",
            "nlp",
            "pytorch",
            "rag",
            "retrieval-augmented generation",
            "scikit-learn",
            "tensorflow",
            "vector",
        },
    },
    "backend": {
        "query_terms": [
            "Python",
            "FastAPI",
            "Backend",
            "PostgreSQL",
            "API",
        ],
        "keywords": {
            "api",
            "backend",
            "docker",
            "fastapi",
            "flask",
            "mysql",
            "postgresql",
            "python",
            "sql",
            "supabase",
        },
    },
    "data": {
        "query_terms": [
            "Data Science",
            "Python",
            "Pandas",
            "SQL",
            "Machine Learning",
        ],
        "keywords": {
            "data analysis",
            "data science",
            "eda",
            "matplotlib",
            "numpy",
            "pandas",
            "python",
            "seaborn",
            "sql",
        },
    },
    "finance": {
        "query_terms": [
            "Quant Finance",
            "Algorithmic Trading",
            "Python",
            "Financial Markets",
        ],
        "keywords": {
            "algorithmic trading",
            "finance",
            "financial",
            "market",
            "quant",
            "quantitative finance",
            "stock",
            "technical analysis",
            "trading",
        },
    },
}


def _clean_text(value) -> str:
    return " ".join(str(value or "").strip().split())


def _dedupe(values: list[str], limit: int | None = None) -> list[str]:
    deduped = []
    seen = set()

    for value in values or []:
        text = _clean_text(value)
        key = text.lower()

        if not text or key in seen:
            continue

        seen.add(key)
        deduped.append(text)

        if limit and len(deduped) >= limit:
            break

    return deduped


def _collect_profile_terms(parsed: dict) -> list[str]:
    terms = []
    terms.extend(parsed.get("domains", []) or [])
    terms.extend(parsed.get("skills", []) or [])
    terms.extend(parsed.get("technologies", []) or [])

    for item in parsed.get("experience", []) or []:
        terms.append(item.get("role", ""))
        terms.extend(item.get("domains", []) or [])
        terms.extend(item.get("technologies", []) or [])
        terms.append(item.get("description", ""))

    for item in parsed.get("projects", []) or []:
        terms.append(item.get("name", ""))
        terms.extend(item.get("domains", []) or [])
        terms.extend(item.get("technologies", []) or [])
        terms.append(item.get("description", ""))

    return [_clean_text(term) for term in terms if _clean_text(term)]


def get_resume_embedding(resume: dict | None) -> list[float] | None:
    embedding = (resume or {}).get("embedding")

    return _normalize_embedding(embedding)



def get_resume_intent_embedding(intent: dict) -> list[float] | None:
    embedding = (intent or {}).get("embedding")

    return _normalize_embedding(embedding)


def _normalize_embedding(embedding):
    if embedding is None:
        return None

    try:
        if len(embedding) == 0:
            return None
    except TypeError:
        return None

    return embedding


def build_resume_search_profile(resume: dict | None) -> str:
    parsed = (resume or {}).get("parsed_data") or {}

    if not parsed:
        return ""

    lines = [
        f"Summary: {_clean_text(parsed.get('summary'))}",
        "Domains: " + ", ".join(_dedupe(parsed.get("domains", []), limit=8)),
        "Skills: " + ", ".join(_dedupe(parsed.get("skills", []), limit=10)),
        "Technologies: "
        + ", ".join(_dedupe(parsed.get("technologies", []), limit=14)),
    ]

    experiences = []
    for item in parsed.get("experience", []) or []:
        role = _clean_text(item.get("role"))
        company = _clean_text(item.get("company"))
        domains = ", ".join(_dedupe(item.get("domains", []), limit=4))
        technologies = ", ".join(_dedupe(item.get("technologies", []), limit=5))
        description = _clean_text(item.get("description"))
        experiences.append(
            f"{role} at {company}; domains: {domains}; technologies: {technologies}; {description}"
        )

    if experiences:
        lines.append("Experience: " + " | ".join(experiences[:3]))

    projects = []
    for item in parsed.get("projects", []) or []:
        name = _clean_text(item.get("name"))
        domains = ", ".join(_dedupe(item.get("domains", []), limit=4))
        technologies = ", ".join(_dedupe(item.get("technologies", []), limit=5))
        description = _clean_text(item.get("description"))
        projects.append(
            f"{name}; domains: {domains}; technologies: {technologies}; {description}"
        )

    if projects:
        lines.append("Projects: " + " | ".join(projects[:3]))

    intents = []
    stored_intents = (resume or {}).get("intents") or []

    for intent in stored_intents[:5]:
        label = _clean_text(intent.get("label"))
        query = _clean_text(intent.get("query"))

        if label or query:
            intents.append(f"{label}: {query}")

    if intents:
        lines.append("Target role intents: " + " | ".join(intents))

    return "\n".join(line for line in lines if line.split(":", 1)[-1].strip())


def _build_legacy_resume_search_intents(resume: dict | None) -> list[str]:
    parsed = (resume or {}).get("parsed_data") or {}

    if not parsed:
        return []

    terms = " ".join(_collect_profile_terms(parsed)).lower()
    scores = Counter()

    for bucket_name, bucket in PROFILE_BUCKETS.items():
        for keyword in bucket["keywords"]:
            if keyword in terms:
                scores[bucket_name] += 1

    ranked_buckets = [
        bucket_name
        for bucket_name, _score in scores.most_common(MAX_RESUME_SEARCH_INTENTS)
    ]
    intents = []

    for bucket_name in ranked_buckets:
        query_terms = PROFILE_BUCKETS[bucket_name]["query_terms"]
        intents.append(" ".join(query_terms + ["internship", "job"]))

    if len(intents) < MAX_RESUME_SEARCH_INTENTS:
        fallback_terms = []
        fallback_terms.extend(_dedupe(parsed.get("domains", []), limit=4))
        fallback_terms.extend(_dedupe(parsed.get("technologies", []), limit=8))

        if fallback_terms:
            intents.append(" ".join(fallback_terms[:10] + ["internship", "job"]))

    return _dedupe(intents, limit=MAX_RESUME_SEARCH_INTENTS)


def get_resume_search_intents(resume: dict | None) -> list[dict]:
    stored_intents = (resume or {}).get("intents") or []

    if stored_intents:
        return [
            {
                "label": intent.get("label") or intent.get("query") or "Role intent",
                "query": intent.get("query") or "",
                "evidence": intent.get("evidence") or [],
                "embedding": _normalize_embedding(intent.get("embedding")),
            }
            for intent in stored_intents[:MAX_RESUME_SEARCH_INTENTS]
            if intent.get("query")
        ]

    return [
        {
            "label": query,
            "query": query,
            "evidence": [],
            "embedding": None,
        }
        for query in _build_legacy_resume_search_intents(resume)
    ]
