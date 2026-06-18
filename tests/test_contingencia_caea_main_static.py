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


def test_main_importa_contingencia_caea_y_socket_hostname():
    source = _source()

    assert "import socket" in source
    assert "from controladores.ContingenciaCAEA import activar_modo_caea, restaurar_modo_ws" in source


def test_main_resuelve_maquina_y_empresa_para_contingencia_sin_hardcodear_rutas():
    source = _source()
    resolver_maquina = ast.get_source_segment(source, _function_def("_maquina_imprefiscal_contingencia"))
    resolver_empresa = ast.get_source_segment(source, _function_def("_empresa_imprefiscal_contingencia"))

    assert "maquina_imprefiscal" in resolver_maquina
    assert "MAQUINA_IMPREFISCAL" in resolver_maquina
    assert "socket.gethostname()" in resolver_maquina
    assert "empresa_imprefiscal" in resolver_empresa
    assert "EMPRESA_IMPREFISCAL" in resolver_empresa
    assert "return 1" in resolver_empresa
    assert ("H:" + "\\") not in source
    assert ("X:" + "\\") not in source


def test_verificar_estado_afip_sincroniza_contingencia_segun_disponibilidad():
    verificar = _function_def("VerificarEstadoAFIP")
    sincronizar = _function_def("_sincronizar_contingencia_caea")

    assert "_sincronizar_contingencia_caea" in _called_names(verificar)
    llamadas = _called_names(sincronizar)
    assert "activar_modo_caea" in llamadas
    assert "restaurar_modo_ws" in llamadas
