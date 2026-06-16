from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYAFIPWS_COMMIT = "d595b072110accec9dae1ddb58165ab847b8520a"


def read_text(relative_path):
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_requirements_do_not_install_pyafipws_from_old_pypi_release():
    requirements = read_text("requirements.txt")

    assert "PyAfipWs==2.7.1874" not in requirements


def test_readme_documents_pyafipws_github_strategy():
    readme = read_text("README.md")

    assert "github.com/reingart/pyafipws" in readme
    assert "PyPI" in readme
    assert "2016" in readme
    assert "desactualizada" in readme or "no es fuente principal" in readme
    assert "requirements-pyafipws.txt" in readme


def test_gitignore_keeps_legacy_local_pyafipws_copy_ignored():
    gitignore = read_text(".gitignore")

    assert "pyafipws/" in gitignore


def test_requirements_pyafipws_points_to_official_github_source():
    requirements_pyafipws = read_text("requirements-pyafipws.txt")

    assert "github.com/reingart/pyafipws" in requirements_pyafipws
    assert "<COMMIT_SHA_PROBADO>" not in requirements_pyafipws
    assert PYAFIPWS_COMMIT in requirements_pyafipws


def test_readme_documents_pinned_pyafipws_commit():
    readme = read_text("README.md")

    assert PYAFIPWS_COMMIT in readme
