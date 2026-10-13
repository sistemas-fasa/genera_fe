import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "controladores" / "Main.py"


def _source():
    return MAIN.read_text(encoding="utf-8")


def _tree():
    return ast.parse(_source())


def _function_def(name):
    for node in ast.walk(_tree()):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError("No se encontro la funcion {}".format(name))


def _called_attrs(node):
    """Nombres de metodos invocados dentro del nodo."""
    names = []
    for child in ast.walk(node):
        if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
            names.append(child.func.attr)
    return names


def test_genera_caea_no_usa_get_sobre_caea():
    """Un .get() sin CAEA para el periodo levanta DoesNotExist."""
    genera = _function_def("GeneraCAEA")

    assert "get" not in _called_attrs(genera)


def test_genera_caea_usa_first_y_corta_si_no_hay_caea():
    genera = _function_def("GeneraCAEA")
    llamadas = _called_attrs(genera)

    assert "first" in llamadas

    # Debe existir una guarda explicita que devuelva antes del for.
    guardas_none = [
        node
        for node in ast.walk(genera)
        if isinstance(node, ast.If)
        and any(
            isinstance(hijo, ast.Compare)
            and any(isinstance(op, ast.Is) for op in hijo.ops)
            and isinstance(hijo.left, ast.Name)
            and hijo.left.id.endswith("caea")
            for hijo in ast.walk(node)
        )
        and any(isinstance(b, ast.Return) for b in ast.walk(node))
    ]
    assert guardas_none, "GeneraCAEA debe cortar el ciclo cuando no hay CAEA"


def test_genera_caea_no_tiene_handler_muerto_de_doesnotexist():
    """El handler vivia dentro del for y era inalcanzable: el .get() estaba
    fuera del try. Si vuelve, deja de ser codigo muerto."""
    genera = _function_def("GeneraCAEA")

    handlers = [node for node in ast.walk(genera) if isinstance(node, ast.ExceptHandler)]

    # Cubre tanto CAEA.DoesNotExist (ast.Attribute) como DoesNotExist (ast.Name).
    atributos = {
        hijo.attr
        for handler in handlers
        if handler.type is not None
        for hijo in ast.walk(handler.type)
        if isinstance(hijo, ast.Attribute)
    }
    nombres = {
        hijo.id
        for handler in handlers
        if handler.type is not None
        for hijo in ast.walk(handler.type)
        if isinstance(hijo, ast.Name)
    }

    assert atributos.isdisjoint({"DoesNotExist"})
    assert nombres.isdisjoint({"DoesNotExist", "CAEA"})


def test_genera_caea_no_marca_error_cuando_falta_caea():
    """Marcar resultado='E' dejaba el comprobante muerto: GeneraCAE solo mira
    tipows='WS', asi que una fila tipows='A' con resultado='E' no se vuelve a
    procesar nunca."""
    genera = _function_def("GeneraCAEA")

    valores = []
    asigna_resultado = False
    for node in ast.walk(genera):
        if not isinstance(node, ast.Assign):
            continue
        escribe_resultado = any(
            isinstance(hijo, ast.Attribute)
            and hijo.attr == "resultado"
            and isinstance(hijo.ctx, ast.Store)
            for hijo in node.targets
        )
        if not escribe_resultado:
            continue
        asigna_resultado = True
        for hijo in ast.walk(node.value):
            if isinstance(hijo, ast.Constant) and isinstance(hijo.value, str):
                valores.append(hijo.value)

    assert asigna_resultado, "GeneraCAEA debe seguir escribiendo el resultado"
    assert "E" not in valores


def test_alerta_de_caea_ausente_esta_limitada_en_frecuencia():
    """El timer corre cada 500ms: avisar en cada pasada inundaria la cola."""
    alerta = _function_def("_alertar_caea_ausente")
    tree = _tree()

    constantes = [
        node.targets[0].id
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Name)
        and node.value.func.id == "timedelta"
    ]
    assert "INTERVALO_ALERTA_CAEA_AUSENTE" in constantes

    source = ast.get_source_segment(_source(), alerta)
    assert "INTERVALO_ALERTA_CAEA_AUSENTE" in source
    assert "Return" in ast.dump(alerta) or "return" in source


def test_genera_caea_sigue_llamando_al_avisador_de_caea_ausente():
    genera = _function_def("GeneraCAEA")
    llamadas = [
        node.func.attr
        for node in ast.walk(genera)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    ]

    assert "_alertar_caea_ausente" in llamadas