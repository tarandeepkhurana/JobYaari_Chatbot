import logging
from src.utils.embeddings import generate_embedding

logger = logging.getLogger("resume.resume_embedding")


def build_resume_embedding_text(
    parsed_resume: dict,
) -> str:

    sections = []

    # -------------------------
    # Summary
    # -------------------------
    if parsed_resume.get("summary"):
        sections.append(parsed_resume["summary"])

    # -------------------------
    # Skills
    # -------------------------
    skills = parsed_resume.get("skills", [])
    if skills:
        sections.append("Skills: " + " ".join(skills))

    # -------------------------
    # Technologies
    # -------------------------
    technologies = parsed_resume.get("technologies", [])
    if technologies:
        sections.append(
            "Technologies: " + " ".join(technologies)
        )

    # -------------------------
    # Domains
    # -------------------------
    domains = parsed_resume.get("domains", [])
    if domains:
        sections.append(
            "Domains: " + " ".join(domains)
        )

    # -------------------------
    # Experience
    # -------------------------
    experience_items = parsed_resume.get(
        "experience",
        [],
    )

    for exp in experience_items:

        exp_text = " ".join([
            exp.get("role", ""),
            exp.get("company", ""),
            " ".join(exp.get("technologies", [])),
            " ".join(exp.get("domains", [])),
            exp.get("description", ""),
        ])

        sections.append(exp_text)

    # -------------------------
    # Projects
    # -------------------------
    project_items = parsed_resume.get(
        "projects",
        [],
    )

    for proj in project_items:

        proj_text = " ".join([
            proj.get("name", ""),
            " ".join(proj.get("technologies", [])),
            " ".join(proj.get("domains", [])),
            proj.get("description", ""),
        ])

        sections.append(proj_text)

    target_role_intents = parsed_resume.get(
        "target_role_intents",
        [],
    )

    for intent in target_role_intents:
        intent_text = " ".join([
            intent.get("label", ""),
            intent.get("query", ""),
            " ".join(intent.get("evidence", [])),
        ])

        sections.append(intent_text)

    return "\n".join(sections).strip()


async def generate_resume_embedding(
    parsed_resume: dict,
) -> list[float]:

    try:
        logger.info(
            "Resume embedding generation started"
        )
        embedding_text = build_resume_embedding_text(
            parsed_resume
        )

        response = await generate_embedding(embedding_text)

        logger.info(
            "Resume embedding generated successfully"
        )

        return response

    except Exception:
        logger.exception(
            "Resume embedding generation failed"
        )
        return []


async def generate_resume_intent_embeddings(
    intents: list[dict],
) -> list[dict]:
    """Attach one embedding per target role intent query."""

    enriched_intents = []

    for intent in intents[:5]:
        query = (intent.get("query") or "").strip()

        if not query:
            continue

        try:
            logger.info("Generating embedding for resume intent: %s", query)
            embedding = await generate_embedding(query)
        except Exception:
            logger.exception(
                "Resume intent embedding generation failed for query: %s",
                query,
            )
            embedding = []

        enriched_intents.append({
            "label": intent.get("label") or query,
            "query": query,
            "evidence": intent.get("evidence") or [],
            "embedding": embedding,
        })

    return enriched_intents
