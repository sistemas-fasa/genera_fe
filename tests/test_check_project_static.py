from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECK_PROJECT = ROOT / "check_project.py"


def read_text(relative_path):
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_check_project_script_exists_and_has_safe_entrypoint():
    source = CHECK_PROJECT.read_text(encoding="utf-8")

    assert 'if __name__ == "__main__"' in source
    assert "configparser" in source
    assert "importlib" in source


def test_check_project_avoids_imports_or_calls_with_side_effects():
    source = CHECK_PROJECT.read_text(encoding="utf-8")

    forbidden_fragments = [
        "modelos.ModeloBase",
        "controladores.FE",
        "Conectar(",
        "envia_correo",
        "encolar_email",
    ]

    for fragment in forbidden_fragments:
        assert fragment not in source


def test_check_project_does_not_print_sensitive_config_values_directly():
    source = CHECK_PROJECT.read_text(encoding="utf-8")

    sensitive_terms = ["password", "privatekey", "token", "sign"]
    output_calls = [
        line.strip()
        for line in source.splitlines()
        if line.strip().startswith(("print(", "report.ok(", "report.warn(", "report.error("))
    ]

    for line in output_calls:
        for term in sensitive_terms:
            assert term not in line.lower()


def test_readme_documents_local_validation_command():
    readme = read_text("README.md")

    assert "python check_project.py" in readme
