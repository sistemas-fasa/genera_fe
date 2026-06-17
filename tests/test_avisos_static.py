# coding=utf-8
import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AVISOS = ROOT / "libs" / "Avisos.py"
VENTANAS = ROOT / "libs" / "Ventanas.py"
UTILES = ROOT / "libs" / "Utiles.py"
MAIN = ROOT / "controladores" / "Main.py"


def parse(path):
    return ast.parse(path.read_text(encoding="utf-8"))


def function_names(path):
    return {
        node.name
        for node in ast.walk(parse(path))
        if isinstance(node, ast.FunctionDef)
    }


def source(path):
    return path.read_text(encoding="utf-8")


def test_avisos_expone_helpers_publicos_y_traductor():
    assert AVISOS.exists()
    funciones = function_names(AVISOS)

    assert {
        "mostrar_info",
        "mostrar_ok",
        "mostrar_advertencia",
        "mostrar_error",
        "confirmar_accion",
        "traducir_excepcion",
    }.issubset(funciones)


def test_avisos_contiene_mensajes_administrativos_sin_detalle_tecnico():
    contenido = source(AVISOS)

    assert "No se pudo conectar con la base de datos." in contenido
    assert "AFIP no esta respondiendo correctamente." in contenido
    assert "No se pudo enviar el correo. Revisa la configuracion SMTP." in contenido
    assert "Falta configurar el certificado digital." in contenido
    assert "Ocurrio un problema al procesar el comprobante. El detalle quedo registrado en el log." in contenido
    assert "logging.exception" in contenido or "logging.error" in contenido


def test_ventanas_mantiene_api_existente_delegando_en_avisos():
    contenido = source(VENTANAS)

    assert {"showAlert", "showConfirmation", "showMsgAutoClose"}.issubset(function_names(VENTANAS))
    assert "libs.Avisos" in contenido or "from libs import Avisos" in contenido
    assert "mostrar_info" in contenido
    assert "confirmar_accion" in contenido


def test_captura_global_usa_mensaje_amigable_y_deja_detalle_en_log():
    contenido = source(UTILES)

    assert "traducir_excepcion" in contenido
    assert "mostrar_error" in contenido
    assert "logging.exception" in contenido
    assert "self.Traceback" in contenido


def test_main_controller_usa_avisos_para_errores_del_ciclo_principal():
    contenido = source(MAIN)

    assert "mostrar_error" in contenido
    assert "traducir_excepcion" in contenido
    assert "Error procesando ciclo principal" in contenido
