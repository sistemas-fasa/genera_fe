import ast
from pathlib import Path


SOURCE = Path(__file__).resolve().parents[1] / "controladores" / "InformaCAEA.py"


def _tree():
    return ast.parse(SOURCE.read_text(encoding="utf-8"))


def test_informe_caea_sin_movimiento_usa_caea_del_registro_actual():
    calls = [
        node
        for node in ast.walk(_tree())
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "InformarCAEASinMovimiento"
    ]

    assert len(calls) == 1
    assert ast.dump(calls[0].args[1]) == ast.dump(
        ast.Attribute(value=ast.Name(id="c", ctx=ast.Load()), attr="CAEA", ctx=ast.Load())
    )


def test_mensaje_de_error_incluye_xml_request_y_response_decodificados():
    source = SOURCE.read_text(encoding="utf-8")

    assert "XML request:" in source
    assert "XML response:" in source
    assert "DeCodifica(controlador.xml_request or \"\")" in source
    assert "DeCodifica(controlador.xml_response or \"\")" in source
