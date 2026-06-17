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


def _calls_in_function(path, name):
    calls = []

    class CallVisitor(ast.NodeVisitor):
        def visit_Call(self, node):
            func = node.func
            if isinstance(func, ast.Name):
                calls.append(func.id)
            elif isinstance(func, ast.Attribute):
                calls.append(func.attr)
            self.generic_visit(node)

    CallVisitor().visit(_function_def(path, name))
    return calls


def test_grilla_principal_expone_columnas_administrativas():
    source = MAIN_VIEW.read_text(encoding="utf-8")
    expected_headers = [
        "Hora",
        "Estado",
        "Punto de venta",
        "Tipo",
        "Numero",
        "CAE / CAEA",
        "Vencimiento",
        "Mensaje / error",
    ]

    for header in expected_headers:
        assert header in source


def test_controlador_centraliza_formato_y_color_de_filas_de_grilla():
    source = MAIN_CONTROLLER.read_text(encoding="utf-8")

    assert "def _item_grilla_comprobante(" in source
    assert "def _color_estado_grilla(" in source
    assert "QColor(221, 244, 223)" in source
    assert "QColor(255, 242, 204)" in source
    assert "QColor(255, 218, 214)" in source
    assert "QColor(232, 234, 237)" in source


def test_puntos_de_carga_usan_item_formateado_y_color_por_estado():
    calls = []
    for function_name in [
        "CreaFE",
        "GeneraCAEA",
        "Constatacion",
        "ObtieneDatosCUIT",
        "ImpresionFactura",
        "EnviaCorreos",
    ]:
        calls.extend(_calls_in_function(MAIN_CONTROLLER, function_name))

    assert calls.count("_item_grilla_comprobante") >= 7
    assert calls.count("_color_estado_grilla") >= 6
