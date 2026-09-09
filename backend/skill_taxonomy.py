import re


# This compact taxonomy improves retrieval; it is not used to assert that a
# candidate owns a skill. The grounded classifier must still cite resume text.
SKILL_ALIASES: dict[str, set[str]] = {
    "python": {"python"},
    "c++": {"c++", "cpp", "c plus plus"},
    "c": {"c programming", "c language"},
    "java": {"java"},
    "javascript": {"javascript", "js"},
    "typescript": {"typescript", "ts"},
    "pytorch": {"pytorch", "torch"},
    "tensorflow": {"tensorflow", "keras"},
    "jax": {"jax"},
    "scikit-learn": {"scikit-learn", "sklearn"},
    "opencv": {"opencv"},
    "computer vision": {"computer vision", "image processing"},
    "nlp": {"natural language processing", "nlp"},
    "large language models": {"large language model", "llm", "llms"},
    "transformers": {"transformer", "transformers", "hugging face"},
    "generative ai": {"generative ai", "genai"},
    "gan": {"generative adversarial network", "gan", "gans"},
    "diffusion models": {"diffusion model", "diffusion models"},
    "reinforcement learning": {
        "reinforcement learning",
        "deep reinforcement learning",
        "drl",
    },
    "mlops": {"mlops", "machine learning operations"},
    "docker": {"docker", "containerisation", "containerization"},
    "kubernetes": {"kubernetes", "k8s"},
    "aws": {"aws", "amazon web services"},
    "gcp": {"gcp", "google cloud platform"},
    "azure": {"azure", "microsoft azure"},
    "sql": {"sql"},
    "postgresql": {"postgresql", "postgres", "pgvector"},
    "fastapi": {"fastapi"},
    "react": {"react", "react.js", "reactjs"},
    "next.js": {"next.js", "nextjs"},
    "git": {"git", "github", "gitlab"},
}


SKILL_RELATIONSHIPS: dict[str, set[str]] = {
    "pytorch": {"deep learning", "machine learning"},
    "tensorflow": {"deep learning", "machine learning"},
    "jax": {"deep learning", "machine learning"},
    "opencv": {"computer vision", "image processing"},
    "gan": {"generative ai", "deep learning"},
    "diffusion models": {"generative ai", "deep learning"},
    "large language models": {"nlp", "transformers", "generative ai"},
    "kubernetes": {"containers", "mlops"},
    "docker": {"containers", "mlops"},
    "postgresql": {"sql", "databases"},
    "fastapi": {"python", "web APIs"},
    "next.js": {"react", "javascript", "typescript"},
}


def _contains_alias(text: str, alias: str) -> bool:
    escaped = re.escape(alias).replace(r"\ ", r"\s+")
    return bool(
        re.search(
            rf"(?<![a-z0-9]){escaped}(?![a-z0-9])",
            text,
            re.IGNORECASE,
        )
    )


def extract_canonical_skills(text: str) -> list[str]:
    return sorted(
        canonical
        for canonical, aliases in SKILL_ALIASES.items()
        if any(_contains_alias(text, alias) for alias in aliases)
    )


def related_skill_terms(skills: list[str]) -> list[str]:
    related = set()
    for skill in skills:
        related.update(SKILL_RELATIONSHIPS.get(skill, set()))
    return sorted(related.difference(skills))
