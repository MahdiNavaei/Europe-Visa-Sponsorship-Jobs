from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class SkillDefinition:
    canonical_name: str
    category: str
    aliases: tuple[str, ...]


# This is intentionally a small, curated ontology rather than an opaque model. It is easy to
# review, extend, and regression-test. Aliases are ordered longest-first at runtime to prevent
# a short alias from consuming part of a longer phrase.
_SKILLS: tuple[SkillDefinition, ...] = (
    SkillDefinition("Python", "programming", ("python", "python3", "python programming")),
    SkillDefinition("Java", "programming", ("java",)),
    SkillDefinition("JavaScript", "programming", ("javascript", "java script", "js")),
    SkillDefinition("TypeScript", "programming", ("typescript", "type script", "ts")),
    SkillDefinition("Go", "programming", ("golang", "go language")),
    SkillDefinition("Rust", "programming", ("rust programming",)),
    SkillDefinition("C++", "programming", ("c++", "cpp")),
    SkillDefinition("SQL", "data", ("sql", "structured query language")),
    SkillDefinition("PyTorch", "machine_learning", ("pytorch", "torch", "pytorch framework")),
    SkillDefinition("TensorFlow", "machine_learning", ("tensorflow", "tensor flow")),
    SkillDefinition("scikit-learn", "machine_learning", ("scikit-learn", "sklearn", "scikit learn")),
    SkillDefinition("LLM", "machine_learning", ("llm", "large language model", "large language models", "generative ai", "genai", "generative artificial intelligence")),
    SkillDefinition("RAG", "machine_learning", ("rag", "retrieval augmented generation", "retrieval-augmented generation")),
    SkillDefinition("Natural Language Processing", "machine_learning", ("nlp", "natural language processing")),
    SkillDefinition("Computer Vision", "machine_learning", ("computer vision", "cv models")),
    SkillDefinition("MLflow", "machine_learning", ("mlflow", "ml flow")),
    SkillDefinition("Kubernetes", "cloud", ("kubernetes", "k8s")),
    SkillDefinition("Docker", "cloud", ("docker", "docker containers")),
    SkillDefinition("AWS", "cloud", ("aws", "amazon web services")),
    SkillDefinition("Azure", "cloud", ("azure", "microsoft azure")),
    SkillDefinition("Google Cloud", "cloud", ("google cloud", "gcp")),
    SkillDefinition("Terraform", "cloud", ("terraform",)),
    SkillDefinition("CI/CD", "devops", ("ci/cd", "cicd", "continuous integration", "continuous delivery")),
    SkillDefinition("Linux", "infrastructure", ("linux",)),
    SkillDefinition("Git", "tools", ("git", "git version control")),
    SkillDefinition("React", "frontend", ("react", "react.js", "reactjs")),
    SkillDefinition("Vue.js", "frontend", ("vue", "vue.js", "vuejs")),
    SkillDefinition("Angular", "frontend", ("angular",)),
    SkillDefinition("Node.js", "backend", ("node", "node.js", "nodejs")),
    SkillDefinition("Django", "backend", ("django",)),
    SkillDefinition("FastAPI", "backend", ("fastapi", "fast api")),
    SkillDefinition("Spring", "backend", ("spring boot", "spring framework")),
    SkillDefinition("PostgreSQL", "databases", ("postgresql", "postgres", "postgre sql")),
    SkillDefinition("Redis", "databases", ("redis",)),
    SkillDefinition("Kafka", "data", ("kafka", "apache kafka")),
    SkillDefinition("Spark", "data", ("spark", "apache spark", "pyspark")),
    SkillDefinition("Airflow", "data", ("airflow", "apache airflow")),
    SkillDefinition("dbt", "data", ("dbt", "data build tool")),
    SkillDefinition("Prometheus", "observability", ("prometheus",)),
    SkillDefinition("Grafana", "observability", ("grafana",)),
)


def _pattern(alias: str) -> re.Pattern[str]:
    escaped = re.escape(alias.casefold()).replace(r"\ ", r"\s+")
    # Word boundaries do not work well for C++, .NET, or slash-separated names. A conservative
    # alphanumeric boundary avoids matching skills embedded inside unrelated words.
    return re.compile(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])", re.IGNORECASE)


class SkillOntology:
    """Curated canonical skills with deterministic alias normalization and extraction."""

    def __init__(self, definitions: tuple[SkillDefinition, ...] = _SKILLS) -> None:
        self._definitions = definitions
        self._by_canonical = {item.canonical_name.casefold(): item for item in definitions}
        self._aliases: list[tuple[SkillDefinition, re.Pattern[str]]] = []
        for definition in definitions:
            for alias in sorted({definition.canonical_name, *definition.aliases}, key=len, reverse=True):
                self._aliases.append((definition, _pattern(alias)))

    def definitions(self) -> tuple[SkillDefinition, ...]:
        return self._definitions

    def normalize_skill(self, value: str) -> str:
        cleaned = re.sub(r"\s+", " ", value.strip()).casefold()
        definition = self._by_canonical.get(cleaned)
        if definition:
            return definition.canonical_name
        for candidate, pattern in self._aliases:
            if pattern.fullmatch(cleaned):
                return candidate.canonical_name
        return value.strip()

    def normalize_skills(self, values: list[str] | tuple[str, ...]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for value in values:
            if not isinstance(value, str) or not value.strip():
                continue
            canonical = self.normalize_skill(value)
            key = canonical.casefold()
            if key not in seen:
                result.append(canonical)
                seen.add(key)
        return result

    def extract(self, text: str) -> list[str]:
        found: list[str] = []
        seen: set[str] = set()
        for definition, pattern in self._aliases:
            if pattern.search(text) and definition.canonical_name.casefold() not in seen:
                found.append(definition.canonical_name)
                seen.add(definition.canonical_name.casefold())
        return found

    def category(self, canonical_name: str) -> str | None:
        definition = self._by_canonical.get(canonical_name.casefold())
        return definition.category if definition else None
