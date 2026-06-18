from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


def read_workflow():
    return WORKFLOW.read_text(encoding="utf-8")


def test_ci_workflow_exists():
    assert WORKFLOW.exists()


def test_ci_workflow_runs_on_pull_requests_and_pushes_to_main():
    workflow = read_workflow()

    assert "pull_request:" in workflow
    assert "push:" in workflow
    assert "branches:" in workflow
    assert "- main" in workflow


def test_ci_workflow_uses_current_github_actions_python_setup():
    workflow = read_workflow()

    assert "actions/checkout@v4" in workflow
    assert "actions/setup-python@v5" in workflow
    assert 'python-version: "3.11"' in workflow


def test_ci_workflow_runs_safe_static_validation_commands():
    workflow = read_workflow()

    expected_commands = [
        "python -m compileall -q .",
        "python -m pytest",
        "tests/test_github_actions_ci_static.py",
        "tests/test_check_project_static.py",
        "tests/test_pyafipws_strategy_static.py",
        "tests/test_afip_config_static.py",
        "tests/test_modelobase_config_static.py",
        "tests/test_operational_alerts_use_email_queue_static.py",
        "tests/test_operational_values_not_hardcoded_static.py",
        "tests/test_no_secret_logging_static.py",
        "tests/test_informa_caea_static.py",
        "tests/test_emails_pendientes_schema_migration_static.py",
        "tests/test_contingencia_caea.py",
        "tests/test_contingencia_caea_main_static.py",
        "tests/test_contingencia_caea_static.py",
        "tests/test_contingencia_caea_controlada_script.py",
        "python check_project.py",
    ]

    for command in expected_commands:
        assert command in workflow


def test_ci_workflow_does_not_use_runtime_only_dependencies_or_real_config():
    workflow = read_workflow()

    forbidden_fragments = [
        "requirements-pyafipws.txt",
        "sistema.ini",
        "AFIP_CERT",
        "AFIP_KEY",
        "AFIP_PASSWORD",
        "password",
        "token",
        "privatekey",
    ]

    for fragment in forbidden_fragments:
        assert fragment.lower() not in workflow.lower()
