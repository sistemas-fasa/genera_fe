import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "controladores" / "Main.py"


def _source():
    return MAIN.read_text(encoding="utf-8")


def _function_def(name):
    tree = ast.parse(_source())
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError("No se encontro la funcion {}".format(name))


def _called_names(node):
    names = []
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        if isinstance(child.func, ast.Name):
            names.append(child.func.id)
        elif isinstance(child.func, ast.Attribute):
            names.append(child.func.attr)
    return names


def _imported_from(node, module):
    """Nombres importados de un modulo dado, via AST y no por texto."""
    names = []
    for child in ast.walk(node):
        if isinstance(child, ast.ImportFrom) and child.module == module:
            names.extend(alias.name for alias in child.names)
    return names


def _getenv_literals(node):
    """Literales pasados como primer argumento de os.getenv dentro del nodo."""
    valores = []
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        func = child.func
        es_getenv = (
            isinstance(func, ast.Attribute)
            and func.attr == "getenv"
            and isinstance(func.value, ast.Name)
            and func.value.id == "os"
        )
        if not es_getenv or not child.args:
            continue
        primero = child.args[0]
        if isinstance(primero, ast.Constant) and isinstance(primero.value, str):
            valores.append(primero.value)
    return valores


def test_main_importa_contingencia_caea_multimaquina_sin_socket_hostname():
    source = _source()
    tree = ast.parse(source)

    assert "import socket" not in source
    assert "socket.gethostname" not in source
    assert not [
        alias
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
        if alias.name == "socket"
    ]
    importados = _imported_from(tree, "controladores.ContingenciaCAEA")
    assert "activar_modo_caea_para_maquinas" in importados
    assert "restaurar_modo_ws_para_empresa" in importados


def test_main_resuelve_alcance_de_maquinas_con_default_todas_y_legacy():
    resolver_maquinas = _function_def("_maquinas_imprefiscal_contingencia")
    resolver_empresa = _function_def("_empresa_imprefiscal_contingencia")
    source = _source()

    maquinas_src = ast.get_source_segment(source, resolver_maquinas)
    empresa_src = ast.get_source_segment(source, resolver_empresa)

    assert "maquinas_imprefiscal" in maquinas_src
    assert "MAQUINAS_IMPREFISCAL" in maquinas_src
    assert "maquina_imprefiscal" in maquinas_src
    assert "MAQUINA_IMPREFISCAL" in maquinas_src
    assert "resolver_alcance_maquinas_imprefiscal" in maquinas_src

    env_maquinas = _getenv_literals(resolver_maquinas)
    assert "MAQUINAS_IMPREFISCAL" in env_maquinas
    assert "MAQUINA_IMPREFISCAL" in env_maquinas

    assert "empresa_imprefiscal" in empresa_src
    assert "EMPRESA_IMPREFISCAL" in empresa_src
    assert "return 1" in empresa_src
    assert ("H:" + "\\") not in source
    assert ("X:" + "\\") not in source


def test_verificar_estado_afip_sincroniza_contingencia_segun_disponibilidad():
    verificar = _function_def("VerificarEstadoAFIP")
    sincronizar = _function_def("_sincronizar_contingencia_caea")

    assert "_sincronizar_contingencia_caea" in _called_names(verificar)
    llamadas = _called_names(sincronizar)
    assert "activar_modo_caea_para_maquinas" in llamadas
    assert "restaurar_modo_ws_para_empresa" in llamadas
