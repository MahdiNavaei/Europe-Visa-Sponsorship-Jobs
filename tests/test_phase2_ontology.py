from europe_visa_jobs.intelligence.ontology import SkillOntology


def test_skill_aliases_normalize_to_canonical_names():
    ontology = SkillOntology()
    assert ontology.normalize_skills(["python3", "Torch", "GenAI", "k8s", "ML flow"]) == [
        "Python",
        "PyTorch",
        "LLM",
        "Kubernetes",
        "MLflow",
    ]


def test_skill_extraction_is_deterministic_and_deduplicated():
    ontology = SkillOntology()
    assert ontology.extract("Experience with Torch and GenAI. Also used PyTorch.") == ["PyTorch", "LLM"]


def test_skill_categories_are_available():
    ontology = SkillOntology()
    assert ontology.category("PyTorch") == "machine_learning"
    assert ontology.category("unknown") is None
