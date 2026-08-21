from europe_visa_jobs.schemas import JobFamily
from europe_visa_jobs.utils import classify_role, infer_country, normalize_company_name


def test_country_inference_uses_country_city_and_default():
    assert infer_country("Amsterdam, Netherlands") == "Netherlands"
    assert infer_country("Berlin") == "Germany"
    assert infer_country("Remote", "Ireland") == "Ireland"
    assert infer_country("Remote") is None
    assert infer_country("Kyiv, Ukraine") is None


def test_role_classifier_covers_target_families():
    assert classify_role("Senior Machine Learning Engineer") == JobFamily.AI_ML
    assert classify_role("Staff MLOps Engineer") == JobFamily.MLOPS
    assert classify_role("Backend Software Engineer") == JobFamily.BACKEND
    assert classify_role("Data Engineer") == JobFamily.DATA_ENGINEERING
    assert classify_role("Account Executive") == JobFamily.OTHER


def test_company_normalization_removes_legal_suffixes():
    assert normalize_company_name("Example Technologies GmbH") == "example technologies"
    assert normalize_company_name("Foo & Bar B.V.") == "foo and bar"
