# coding=utf-8
import configparser
import logging
import smtplib
import socket

try:
    import peewee
except Exception:
    peewee = None

from PyQt5.QtWidgets import QMessageBox


MENSAJE_BASE_DATOS = "No se pudo conectar con la base de datos."
MENSAJE_SMTP = "No se pudo enviar el correo. Revisa la configuracion SMTP."
MENSAJE_TIMEOUT = "La operacion demoro demasiado. Reintenta en unos minutos."
MENSAJE_AFIP = "AFIP no esta respondiendo correctamente."
MENSAJE_CERTIFICADO = "Falta configurar el certificado digital."
MENSAJE_SISTEMA_INI = "Falta completar una configuracion en sistema.ini."
MENSAJE_GENERICO = "Ocurrio un problema al procesar el comprobante. El detalle quedo registrado en el log."


def _texto_excepcion(excepcion):
    if excepcion is None:
        return ""
    return "{} {}".format(excepcion.__class__.__name__, excepcion).lower()


def _es_error_base_datos(excepcion, texto):
    if peewee is not None and isinstance(excepcion, peewee.PeeweeException):
        return True
    indicadores = (
        "database",
        "base de datos",
        "mysql",
        "peewee",
        "operationalerror",
        "integrityerror",
        "interfaceerror",
    )
    return any(indicador in texto for indicador in indicadores)


def _es_error_smtp(excepcion, texto):
    if isinstance(excepcion, smtplib.SMTPException):
        return True
    indicadores = ("smtp", "smtplib", "sendmail", "correo", "email")
    return any(indicador in texto for indicador in indicadores)


def _es_timeout(excepcion, texto):
    if isinstance(excepcion, (TimeoutError, socket.timeout)):
        return True
    indicadores = ("timeout", "timed out", "tiempo de espera")
    return any(indicador in texto for indicador in indicadores)


def _es_error_afip(texto):
    indicadores = (
        "afip",
        "arca",
        "wsfe",
        "wsaa",
        "fedummy",
        "pyafipws",
        "caesolicitar",
        "login cms",
        "service.asmx",
    )
    return any(indicador in texto for indicador in indicadores)


def _es_error_certificado(texto):
    indicadores = (
        "certificado",
        "certificate",
        "cert_",
        "privatekey",
        ".crt",
        ".key",
        "cms.cert",
        "untrusted",
    )
    return any(indicador in texto for indicador in indicadores)


def _es_error_sistema_ini(excepcion, texto):
    if isinstance(excepcion, configparser.Error):
        return True
    indicadores = (
        "sistema.ini",
        "nosectionerror",
        "nooptionerror",
        "falta configurar",
        "configuracion",
    )
    return any(indicador in texto for indicador in indicadores)


def traducir_excepcion(excepcion):
    texto = _texto_excepcion(excepcion)

    if _es_error_certificado(texto):
        return MENSAJE_CERTIFICADO
    if _es_error_smtp(excepcion, texto):
        return MENSAJE_SMTP
    if _es_error_sistema_ini(excepcion, texto):
        return MENSAJE_SISTEMA_INI
    if _es_error_afip(texto):
        return MENSAJE_AFIP
    if _es_error_base_datos(excepcion, texto):
        return MENSAJE_BASE_DATOS
    if _es_timeout(excepcion, texto):
        return MENSAJE_TIMEOUT
    return MENSAJE_GENERICO


def _registrar_detalle_tecnico(titulo, detalle_tecnico):
    if not detalle_tecnico:
        return
    if isinstance(detalle_tecnico, BaseException):
        logging.error(
            "%s - detalle tecnico",
            titulo,
            exc_info=(
                detalle_tecnico.__class__,
                detalle_tecnico,
                detalle_tecnico.__traceback__,
            ),
        )
    else:
        logging.error("%s - detalle tecnico: %s", titulo, detalle_tecnico)


def _mostrar(titulo, mensaje, icono, botones=QMessageBox.Ok, auto_cerrar_segundos=None):
    msg = QMessageBox()
    msg.setIcon(icono)
    msg.setText(mensaje)
    msg.setWindowTitle(titulo)
    msg.setStandardButtons(botones)
    if auto_cerrar_segundos:
        msg.timeout = auto_cerrar_segundos
        msg.autoClose = True
    return msg.exec_()


def mostrar_info(titulo, mensaje):
    return _mostrar(titulo, mensaje, QMessageBox.Information)


def mostrar_ok(titulo, mensaje):
    return _mostrar(titulo, mensaje, QMessageBox.Information)


def mostrar_advertencia(titulo, mensaje):
    return _mostrar(titulo, mensaje, QMessageBox.Warning)


def mostrar_error(titulo, mensaje, detalle_tecnico=None):
    _registrar_detalle_tecnico(titulo, detalle_tecnico)
    return _mostrar(titulo, mensaje, QMessageBox.Critical)


def confirmar_accion(titulo, mensaje):
    return _mostrar(titulo, mensaje, QMessageBox.Question, QMessageBox.Ok | QMessageBox.Cancel)
