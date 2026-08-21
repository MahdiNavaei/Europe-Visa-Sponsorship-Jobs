from europe_visa_jobs.intelligence.profile_parser import CandidateProfileParser


def test_profile_parser_extracts_roles_skills_experience_and_countries():
    profile = CandidateProfileParser().parse(
        "Role: Senior AI Engineer\n7 years of experience with Python, Torch and GenAI.\nOpen to Germany or Sweden.",
        name="Candidate",
    )
    assert profile.target_roles == ["Senior AI Engineer"]
    assert profile.skills == ["Python", "PyTorch", "LLM"]
    assert profile.years_of_experience == 7
    assert profile.preferred_countries == ["Germany", "Sweden"]


def test_profile_parser_uses_safe_defaults_when_text_is_sparse():
    profile = CandidateProfileParser().parse("Curious builder", name="Candidate")
    assert profile.target_roles == ["Software Engineer"]
    assert profile.skills == []
    assert profile.visa_required is True
