import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "controladores" / "InformaCAEA.py"
SERVICIO = ROOT / "controladores" / "RendirCAEA.py"


def _tree(path):
    return ast.parse(path.read_text(encoding="utf-8"))


def _calls(path, nombre):
    """Llamadas por nombre o por atributo: tanto f(x) como a.f(x)."""
    encontradas = []
    for node in ast.walk(_tree(path)):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id == nombre:
            encontradas.append(node)
        elif isinstance(func, ast.Attribute) and func.attr == nombre:
            encontradas.append(node)
    return encontradas


def test_informe_caea_sin_movimiento_usa_caea_del_registro_actual():
    """La logica de rendido vive en el servicio, no en la pantalla."""
    llamadas = _calls(SERVICIO, "InformarCAEASinMovimiento")

    assert len(llamadas) == 1
    # La pantalla ya no la invoca: el servicio es el unico que la llama.
    assert not _calls(SOURCE, "InformarCAEASinMovimiento")


def test_ptovta_sin_movimiento_se_informa_con_el_caea_de_la_variable_caea():
    """Si se mandara el ptovta en vez del CAEA, ARCA rechaza el aviso."""
    llamadas = _calls(SERVICIO, "InformarCAEASinMovimiento")
    segundo_argumento = ast.unparse(llamadas[0].args[1])

    assert segundo_argumento == "caea"


def test_mensaje_de_error_incluye_xml_request_y_response_decodificados():
    """Sin el XML no se puede saber por que reboto AFIP."""
    fuente = SERVICIO.read_text(encoding="utf-8")

    assert "XML_REQUEST:" in fuente
    assert "XML_RESPONSE:" in fuente
    assert 'DeCodifica(getattr(controlador, "xml_request", "") or "")' in fuente
    assert 'DeCodifica(getattr(controlador, "xml_response", "") or "")' in fuente


def test_la_pantalla_delega_en_el_servicio_y_no_reimplementa_el_recorrido():
    fuente = SOURCE.read_text(encoding="utf-8")

    assert "from controladores.RendirCAEA import rendir" in fuente
    assert len(_calls(SOURCE, "rendir")) == 1
    # Que no quede la logica vieja duplicada en la pantalla.
    assert _calls(SOURCE, "CreaFE") == []
    assert _calls(SOURCE, "CAEA") == []


def test_la_pantalla_no_abre_un_maincontroller_por_comprobante():
    """MainController construye su MainView al instanciarse."""
    fuente = SOURCE.read_text(encoding="utf-8")

    assert len(_calls(SOURCE, "MainController")) == 1