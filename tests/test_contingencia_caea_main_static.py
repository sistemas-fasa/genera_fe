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


def test_main_importa_contingencia_caea_multimaquina_sin_socket_hostname():
    source = _source()

    assert "import socket" not in source
    assert "socket.gethostname" not in source
    assert (
        "from controladores.ContingenciaCAEA import activar_modo_caea_para_maquinas, restaurar_modo_ws_para_empresa"
        in source
    )


def test_main_resuelve_alcance_de_maquinas_con_default_todas_y_legacy():
    source = _source()
    resolver_maquinas = ast.get_source_segment(source, _function_def("_maquinas_imprefiscal_contingencia"))
    resolver_empresa = ast.get_source_segment(source, _function_def("_empresa_imprefiscal_contingencia"))

    assert "maquinas_imprefiscal" in resolver_maquinas
    assert "MAQUINAS_IMPREFISCAL" in resolver_maquinas
    assert "os.getenv('MAQUINAS_IMPREFISCAL')" in resolver_maquinas
    assert "maquina_imprefiscal" in resolver_maquinas
    assert "MAQUINA_IMPREFISCAL" in resolver_maquinas
    assert "os.getenv('MAQUINA_IMPREFISCAL')" in resolver_maquinas
    assert "resolver_alcance_maquinas_imprefiscal" in resolver_maquinas
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
    assert "activar_modo_caea_para_maquinas" in llamadas
    assert "restaurar_modo_ws_para_empresa" in llamadas
