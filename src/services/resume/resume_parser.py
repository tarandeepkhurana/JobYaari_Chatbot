import logging
import re

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from src.factories.llm_factory import LLMFactory
from src.services.llm.prompts import (
    RESUME_PARSER_SYSTEM_PROMPT,
)

logger = logging.getLogger("resume.resume_parser")


KNOWN_TECHNOLOGY_TERMS = {
    "aws",
    "azure",
    "c",
    "c#",
    "c++",
    "chromadb",
    "docker",
    "faiss",
    "fastapi",
    "flask",
    "gemini api",
    "git",
    "github actions",
    "google colab",
    "hugging face",
    "java",
    "javascript",
    "jupyter notebook",
    "keras",
    "langchain",
    "langfuse",
    "langgraph",
    "langsmith",
    "matplotlib",
    "mlflow",
    "mongodb",
    "mysql",
    "node.js",
    "numpy",
    "openai api",
    "openai llms",
    "pandas",
    "pinecone",
    "postgresql",
    "postman",
    "python",
    "pytorch",
    "react",
    "scikit-learn",
    "seaborn",
    "sql",
    "supabase",
    "tensorflow",
    "vs code",
}

SEARCH_TERM_REPLACEMENTS = {
    "apis": "api",
    "llms": "llm",
    "rags": "rag",
}

ROLE_SIGNAL_RULES = [
    (
        ("ai", "machine learning", "ml", "deep learning", "nlp", "generative ai"),
        ["ai ml intern", "machine learning intern"],
    ),
    (
        ("rag", "llm", "langchain", "langgraph", "openai", "agentic ai"),
        ["llm intern", "rag developer intern", "ai agent intern"],
    ),
    (
        ("backend", "fastapi", "flask", "node.js", "postgresql", "api development"),
        ["backend developer intern", "software developer intern"],
    ),
    (
        ("data science", "pandas", "numpy", "scikit-learn", "data analysis"),
        ["data science intern", "data analyst intern"],
    ),
    (
        ("quantitative finance", "algorithmic trading", "financial markets"),
        ["quantitative finance intern", "algorithmic trading intern"],
    ),
]

SYSTEM_SIGNAL_PHRASES = [
    "rag",
    "ai chatbot",
    "job search assistant",
    "multi agent system",
    "semantic search",
    "vector search",
    "real time data pipeline",
    "market data aggregation",
    "llm database integration",
    "stock news analysis",
    "market signal generator",
    "financial analytics",
    "trading workflows",
]

DOMAIN_SIGNAL_PHRASES = [
    "quantitative finance",
    "algorithmic trading",
    "financial markets",
    "technical analysis",
    "market data systems",
    "financial analytics",
    "stock market news",
    "semantic search",
    "job search assistance",
]

TECHNOLOGY_PRIORITY = [
    "Python",
    "FastAPI",
    "LangChain",
    "LangGraph",
    "RAG",
    "LLM",
    "OpenAI API",
    "PostgreSQL",
    "SQL",
    "FAISS",
    "ChromaDB",
    "Pinecone",
    "Azure",
    "Docker",
    "Pandas",
    "NumPy",
    "Scikit-Learn",
    "PyTorch",
    "Hugging Face",
    "Flask",
    "Java",
]


def _normalize_key(value: str) -> str:
    return " ".join(str(value).strip().lower().split())


def _dedupe_strings(values: list[str]) -> list[str]:
    deduped = []
    seen = set()

    for value in values or []:
        text = str(value).strip()
        key = _normalize_key(text)

        if not text or key in seen:
            continue

        seen.add(key)
        deduped.append(text)

    return deduped


def _clean_search_term(value: str) -> str:
    text = _normalize_key(value)

    if not text:
        return ""

    text = text.replace("ai/ml", "ai ml")
    text = text.replace("a.i.", "ai")
    text = text.replace("real-time", "real time")
    text = re.sub(r"[^a-z0-9+#. ]+", " ", text)
    text = " ".join(SEARCH_TERM_REPLACEMENTS.get(part, part) for part in text.split())
    return " ".join(text.split())


def _dedupe_search_terms(values: list[str], limit: int | None = None) -> list[str]:
    deduped = []
    seen = set()

    for value in values or []:
        text = _clean_search_term(value)

        if not text or text in seen:
            continue

        seen.add(text)
        deduped.append(text)

        if limit and len(deduped) >= limit:
            break

    return deduped


def _compact_query(values: list[str], limit: int = 18) -> str:
    return " ".join(_dedupe_search_terms(values, limit=limit))


def _resume_corpus(parsed: dict) -> str:
    parts = [
        parsed.get("summary", ""),
        " ".join(parsed.get("skills", [])),
        " ".join(parsed.get("technologies", [])),
        " ".join(parsed.get("domains", [])),
    ]

    for item in parsed.get("experience", []) or []:
        parts.extend([
            item.get("role", ""),
            item.get("company", ""),
            item.get("description", ""),
            " ".join(item.get("technologies", [])),
            " ".join(item.get("domains", [])),
        ])

    for item in parsed.get("projects", []) or []:
        parts.extend([
            item.get("name", ""),
            item.get("description", ""),
            " ".join(item.get("technologies", [])),
            " ".join(item.get("domains", [])),
        ])

    return _clean_search_term(" ".join(str(part) for part in parts if part))


def _contains_any(corpus: str, signals: tuple[str, ...] | list[str]) -> bool:
    return any(_clean_search_term(signal) in corpus for signal in signals)


def _prioritized_technologies(parsed: dict, limit: int = 14) -> list[str]:
    technologies = parsed.get("technologies", []) or []
    corpus = _resume_corpus(parsed)
    selected = []

    for term in TECHNOLOGY_PRIORITY:
        clean_term = _clean_search_term(term)
        matching_resume_term = next(
            (
                value
                for value in technologies
                if _clean_search_term(value) == clean_term
            ),
            None,
        )

        if matching_resume_term or clean_term in corpus:
            selected.append(term)

    selected.extend(technologies)
    return _dedupe_search_terms(selected, limit=limit)


def _experience_role_terms(parsed: dict) -> list[str]:
    terms = []

    for item in parsed.get("experience", []) or []:
        role = item.get("role")

        if role:
            terms.append(role)

    corpus = _resume_corpus(parsed)

    for signals, role_terms in ROLE_SIGNAL_RULES:
        if _contains_any(corpus, signals):
            terms.extend(role_terms)

    return _dedupe_search_terms(terms, limit=12)


def _matched_signal_phrases(corpus: str, phrases: list[str], limit: int) -> list[str]:
    return [
        phrase
        for phrase in _dedupe_search_terms(phrases)
        if _clean_search_term(phrase) in corpus
    ][:limit]


def _project_system_terms(parsed: dict) -> list[str]:
    terms = []

    for item in parsed.get("projects", []) or []:
        terms.append(item.get("name", ""))
        terms.extend(item.get("technologies", []))
        terms.extend(item.get("domains", []))

    corpus = _resume_corpus(parsed)
    terms.extend(_matched_signal_phrases(corpus, SYSTEM_SIGNAL_PHRASES, limit=10))
    return _dedupe_search_terms(terms, limit=16)


def _domain_experience_terms(parsed: dict) -> list[str]:
    terms = list(parsed.get("domains", []) or [])

    for item in parsed.get("experience", []) or []:
        terms.extend(item.get("domains", []))

    for item in parsed.get("projects", []) or []:
        terms.extend(item.get("domains", []))

    corpus = _resume_corpus(parsed)
    terms.extend(_matched_signal_phrases(corpus, DOMAIN_SIGNAL_PHRASES, limit=10))
    return _dedupe_search_terms(terms, limit=14)


def _intent_evidence(parsed: dict, bucket: str) -> list[str]:
    evidence = []

    if bucket in {"role", "hybrid"}:
        for item in parsed.get("experience", []) or []:
            role = item.get("role")
            company = item.get("company")

            if role and company:
                evidence.append(f"{role} at {company}")
            elif role:
                evidence.append(role)

    if bucket in {"technology", "hybrid"}:
        technologies = parsed.get("technologies", [])[:8]

        if technologies:
            evidence.append(f"Technologies: {', '.join(technologies)}")

    if bucket in {"project", "hybrid"}:
        for item in parsed.get("projects", []) or []:
            name = item.get("name")

            if name:
                evidence.append(f"Project: {name}")

    if bucket in {"domain", "hybrid"} and parsed.get("domains"):
        evidence.append(f"Domains: {', '.join(parsed.get('domains', [])[:6])}")

    return _dedupe_strings(evidence)[:6]


def _build_deterministic_target_role_intents(parsed: dict) -> list[dict]:
    role_terms = _experience_role_terms(parsed)
    technology_terms = _prioritized_technologies(parsed)
    project_terms = _project_system_terms(parsed)
    domain_terms = _domain_experience_terms(parsed)

    hybrid_terms = (
        role_terms[:4]
        + technology_terms[:8]
        + project_terms[:5]
        + domain_terms[:5]
    )

    intent_specs = [
        ("Role/title search", _compact_query(role_terms, limit=14), "role"),
        (
            "Skills and technology search",
            _compact_query(technology_terms, limit=16),
            "technology",
        ),
        (
            "Projects and systems search",
            _compact_query(project_terms, limit=16),
            "project",
        ),
        (
            "Domain and experience search",
            _compact_query(domain_terms, limit=14),
            "domain",
        ),
        ("Hybrid best-fit search", _compact_query(hybrid_terms, limit=20), "hybrid"),
    ]

    intents = []
    seen_queries = set()

    for label, query, bucket in intent_specs:
        key = _normalize_key(query)

        if not query or key in seen_queries:
            continue

        seen_queries.add(key)
        intents.append({
            "label": label,
            "query": query,
            "evidence": _intent_evidence(parsed, bucket),
        })

    return intents[:5]


def _clean_nested_items(items: list[dict]) -> list[dict]:
    cleaned = []

    for item in items or []:
        if not isinstance(item, dict):
            continue

        next_item = dict(item)
        next_item["technologies"] = _dedupe_strings(
            next_item.get("technologies", [])
        )
        next_item["domains"] = _dedupe_strings(next_item.get("domains", []))
        cleaned.append(next_item)

    return cleaned


def _normalize_parsed_resume(parsed: dict) -> dict:
    skills = _dedupe_strings(parsed.get("skills", []))
    technologies = _dedupe_strings(parsed.get("technologies", []))
    domains = _dedupe_strings(parsed.get("domains", []))

    technology_keys = {_normalize_key(value) for value in technologies}
    clean_skills = []

    for skill in skills:
        key = _normalize_key(skill)

        if key in technology_keys or key in KNOWN_TECHNOLOGY_TERMS:
            if key not in technology_keys:
                technologies.append(skill)
                technology_keys.add(key)
            continue

        clean_skills.append(skill)

    parsed["skills"] = clean_skills
    parsed["technologies"] = _dedupe_strings(technologies)
    parsed["domains"] = domains
    parsed["experience"] = _clean_nested_items(parsed.get("experience", []))
    parsed["projects"] = _clean_nested_items(parsed.get("projects", []))
    parsed["target_role_intents"] = _build_deterministic_target_role_intents(parsed)

    return parsed


class ExperienceItem(BaseModel):
    role: str = ""
    company: str = ""
    technologies: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)
    description: str = ""

class ProjectItem(BaseModel):
    name: str = ""
    technologies: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)
    description: str = ""

class EducationItem(BaseModel):
    degree: str = ""
    institution: str = ""
    year: str = ""
    description: str = ""

class ParsedResume(BaseModel):
    summary: str = ""

    skills: list[str] = Field(default_factory=list)

    technologies: list[str] = Field(default_factory=list)

    domains: list[str] = Field(default_factory=list)

    experience_years: int | float | None = None

    education: list[EducationItem] = Field(default_factory=list)

    experience: list[ExperienceItem] = Field(default_factory=list)

    projects: list[ProjectItem] = Field(default_factory=list)


async def parse_resume(raw_text: str) -> dict:
    try:
        logger.info("Resume parsing started")
        llm = LLMFactory.get_resume_parser_llm()

        structured_llm = llm.with_structured_output(ParsedResume)

        result = await structured_llm.ainvoke([
            SystemMessage(content=RESUME_PARSER_SYSTEM_PROMPT),
            HumanMessage(content=f"<resume_text>\n{raw_text}\n</resume_text>"),
        ])

        logger.info("Resume parsed successfully")

        return _normalize_parsed_resume(result.model_dump())

    except Exception:
        logger.exception("Resume parsing failed")

        return ParsedResume(
            summary=raw_text[:500]
        ).model_dump()
