import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN_CONTROLLER = ROOT / "controladores" / "Main.py"
MAIN_VIEW = ROOT / "vistas" / "Main.py"


def _tree(path):
    return ast.parse(path.read_text(encoding="utf-8"))


def _function_def(path, name):
    for node in ast.walk(_tree(path)):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"No se encontro la funcion {name} en {path.relative_to(ROOT)}")


def _called_attributes(node):
    calls = []

    class CallVisitor(ast.NodeVisitor):
        def visit_Call(self, child):
            if isinstance(child.func, ast.Attribute):
                calls.append(child.func.attr)
            self.generic_visit(child)

    CallVisitor().visit(node)
    return calls


def test_vista_principal_expone_paneles_operativos_afip_y_emails():
    view_source = MAIN_VIEW.read_text(encoding="utf-8")

    for attr in (
        "lblAfipEstado",
        "lblAfipAppServer",
        "lblAfipDbServer",
        "lblAfipAuthServer",
        "lblAfipUltimaVerificacion",
        "lblAfipMensaje",
        "lblEmailsEstado",
        "lblEmailsPendientes",
        "lblEmailsRetrasados",
        "lblEmailsFallidos",
        "lblEmailsMensaje",
    ):
        assert f"self.{attr}" in view_source

    assert "Estado AFIP" in view_source
    assert "Estado emails" in view_source


def test_controlador_refresca_estado_operativo_durante_el_ciclo():
    controller_source = MAIN_CONTROLLER.read_text(encoding="utf-8")
    ciclo = _function_def(MAIN_CONTROLLER, "_ejecutar_ciclo_procesamiento")
    verificar_afip = _function_def(MAIN_CONTROLLER, "VerificarEstadoAFIP")
    enviar_emails = _function_def(MAIN_CONTROLLER, "EnviaCorreos")
    toggle_emails = _function_def(MAIN_CONTROLLER, "ToggleEnvioEmails")

    assert "def _actualizar_estado_operativo_afip" in controller_source
    assert "def _actualizar_estado_operativo_emails" in controller_source
    assert "def _resumen_estado_emails" in controller_source

    assert "_actualizar_estado_operativo_afip" in _called_attributes(verificar_afip)
    assert "_actualizar_estado_operativo_emails" in _called_attributes(enviar_emails)
    assert "_actualizar_estado_operativo_emails" in _called_attributes(toggle_emails)
    assert "_actualizar_estado_operativo_emails" in _called_attributes(ciclo)

