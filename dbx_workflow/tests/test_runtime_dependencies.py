import re
import tomllib
from pathlib import Path


PROJECT_DIR = Path(__file__).parents[1]
REPOSITORY_ROOT = PROJECT_DIR.parent
MANIFESTS = (REPOSITORY_ROOT / "pyproject.toml", PROJECT_DIR / "pyproject.toml")
ROOT_REQUIREMENTS = REPOSITORY_ROOT / "requirements.txt"
FORBIDDEN_TERMS = (
    "databricks",
    "pyspark",
    "dbt-databricks",
    "py4j",
    "python-dotenv",
    "dotenv",
)


def _canonical_name(requirement):
    match = re.match(r"[A-Za-z0-9][A-Za-z0-9._-]*", requirement)
    assert match is not None
    return re.sub(r"[-_.]+", "-", match.group(0)).lower()


def _project_dependencies(manifest):
    document = tomllib.loads(manifest.read_text(encoding="utf-8"))
    return {
        _canonical_name(requirement)
        for requirement in document["project"].get("dependencies", [])
    }


def _dev_dependencies(manifest):
    document = tomllib.loads(manifest.read_text(encoding="utf-8"))
    requirements = document["project"].get("optional-dependencies", {}).get("dev", [])
    return {_canonical_name(requirement) for requirement in requirements}


def test_manifests_exclude_forbidden_runtimes():
    violations = []

    for path in MANIFESTS:
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            normalized = line.lower().replace("_", "-")
            for term in FORBIDDEN_TERMS:
                if term in normalized:
                    violations.append(
                        f"{path.relative_to(REPOSITORY_ROOT)}:{line_number} contains {term}"
                    )

    assert violations == []


def test_workspace_has_one_lock_and_no_requirements_exports():
    assert (REPOSITORY_ROOT / "uv.lock").is_file()
    assert not (PROJECT_DIR / "uv.lock").exists()
    assert not (PROJECT_DIR / "requirements.txt").exists()
    assert (
        not ROOT_REQUIREMENTS.exists()
    ), "requirements.txt at the repository root is forbidden; use uv.lock"


def test_raw_ingest_source_excludes_forbidden_runtimes():
    violations = []

    for path in (PROJECT_DIR / "src" / "raw_ingest").rglob("*.py"):
        source = path.read_text(encoding="utf-8").lower().replace("_", "-")
        for term in FORBIDDEN_TERMS:
            if term in source:
                violations.append(f"{path.relative_to(PROJECT_DIR)} contains {term}")

    assert violations == []


def test_pydantic_remains_a_runtime_dependency():
    assert "pydantic" in _project_dependencies(PROJECT_DIR / "pyproject.toml")


def test_pytest_is_dev_only():
    for manifest in MANIFESTS:
        assert "pytest" not in _project_dependencies(manifest)
        assert "pytest" in _dev_dependencies(manifest)
