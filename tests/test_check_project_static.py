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


def test_check_project_documents_production_validation_command():
    readme = read_text("README.md")

    assert "python check_project.py --production" in readme
    assert "produccion Windows" in readme
    assert "ejecutable" in readme
    assert "No conecta a AFIP" in readme
    assert "No conecta a DB" in readme
    assert "No envia emails" in readme


def test_check_project_has_production_cli_and_strict_validations():
    source = CHECK_PROJECT.read_text(encoding="utf-8")

    required_fragments = [
        "argparse",
        '"--production"',
        '"--prod"',
        "Modo: PRODUCCION WINDOWS",
        "Resultado: FALLÓ PRODUCCION",
        "Resultado: OK PRODUCCION",
        "dist/main.exe",
        "dist/genera_fe.exe",
        "dist/GeneraFE.exe",
        "main.exe",
        "genera_fe.exe",
        "GeneraFE.exe",
        "homo",
        '"N"',
        "base",
        "mysql",
        "afip_timeout_segundos",
        "<COMMIT_SHA_PROBADO>",
        "re.fullmatch",
        "{40}",
    ]

    for fragment in required_fragments:
        assert fragment in source


def test_check_project_promotes_local_warnings_to_production_errors():
    source = CHECK_PROJECT.read_text(encoding="utf-8")

    assert "warn_or_error" in source
    assert "production" in source


def test_check_project_exposes_structured_diagnostic_results_without_secrets():
    import check_project

    results = check_project.collect_diagnostic_results()

    assert results
    assert all(result.nivel in {"OK", "WARN", "ERROR"} for result in results)
    assert all(result.mensaje for result in results)

    expected_messages = [
        "Python detectado",
        "Modo",
        "Host de base de datos",
        "Base configurada",
        "sistema.ini",
        ".env",
        "Certificados",
        "PyAfipWs",
        "SMTP",
        "Estado AFIP",
        "Ruta de logs",
    ]
    messages = "\n".join(result.mensaje for result in results)
    for expected in expected_messages:
        assert expected in messages

    visible_text = "\n".join(
        "{}\n{}".format(result.mensaje, result.detalle) for result in results
    ).lower()
    forbidden_terms = ["password", "privatekey", "token", "sign"]
    for term in forbidden_terms:
        assert term not in visible_text


def test_main_view_has_diagnostic_button_and_controller_opens_panel():
    main_view_source = read_text("vistas/Main.py")
    main_controller_source = read_text("controladores/Main.py")

    assert "btnDiagnostico" in main_view_source
    assert "Estado del sistema" in main_view_source
    assert "AbrirDiagnostico" in main_controller_source
    assert "PanelDiagnostico" in main_controller_source
    assert "btnDiagnostico.clicked.connect(self.AbrirDiagnostico)" in main_controller_source
