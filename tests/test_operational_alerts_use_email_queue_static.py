import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN_CONTROLLER = ROOT / "controladores" / "Main.py"
INFORMA_CAEA = ROOT / "controladores" / "InformaCAEA.py"
ENTRYPOINT = ROOT / "main.py"

COLA = ("enviar_correo_alerta_operativa", "encolar_email")


def _tree(path):
    return ast.parse(path.read_text(encoding="utf-8"))


def _function_def(path, name):
    for node in ast.walk(_tree(path)):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"No se encontro la funcion {name} en {path.relative_to(ROOT)}")


def _calls_in(node):
    """Nombres de todo lo invocado dentro de un nodo AST."""
    names = []
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        if isinstance(child.func, ast.Name):
            names.append(child.func.id)
        elif isinstance(child.func, ast.Attribute):
            names.append(child.func.attr)
    return names


def _calls_reaching_queue(path, function_name, _vistos=None):
    """Llamadas de una funcion siguiendo una delegacion de nivel.

    Asi el test sigue exigiendo que el flujo termine en la cola aunque la
    llamada se haya movido a un helper propio del metodo.
    """
    calls = _calls_in(_function_def(path, function_name))

    if any(name in calls for name in COLA):
        return calls

    _vistos = set() if _vistos is None else _vistos
    if function_name in _vistos:
        return calls
    _vistos.add(function_name)

    for name in list(calls):
        if not name.startswith("_") or name.startswith("__"):
            continue
        try:
            calls.extend(_calls_reaching_queue(path, name, _vistos))
        except AssertionError:
            continue
    return calls


def _imported_names(path):
    names = set()
    for node in ast.walk(_tree(path)):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                names.add(alias.asname or alias.name)
    return names


def test_alerta_operativa_encola_email_y_no_envia_smtp_directo():
    calls = _calls_in(_function_def(MAIN_CONTROLLER, "enviar_correo_alerta_operativa"))

    assert "encolar_email" in calls
    assert "envia_correo" not in calls


def test_flujos_operativos_de_error_usan_helper_o_cola_de_emails():
    for function_name in ("GeneraCAE", "GeneraCAEA", "_notificar_estado_afip"):
        calls = _calls_reaching_queue(MAIN_CONTROLLER, function_name)

        assert "envia_correo" not in calls
        assert any(name in calls for name in COLA), (
            "{} no llega a la cola de emails ni delegando en otro metodo".format(function_name)
        )


def test_informa_caea_y_entrypoint_no_importan_envia_correo():
    assert "envia_correo" not in _imported_names(INFORMA_CAEA)
    assert "envia_correo" not in _imported_names(ENTRYPOINT)


def test_no_quedan_envios_smtp_directos_en_flujos_operativos():
    for path in (MAIN_CONTROLLER, INFORMA_CAEA, ENTRYPOINT):
        calls = _calls_in(_tree(path))

        assert "envia_correo" not in calls