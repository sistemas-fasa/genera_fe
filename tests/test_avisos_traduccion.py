# coding=utf-8
import smtplib
import socket

import peewee

from libs.Avisos import traducir_excepcion


def test_traduce_error_base_datos():
    mensaje = traducir_excepcion(peewee.OperationalError("could not connect to mysql"))

    assert mensaje == "No se pudo conectar con la base de datos."


def test_traduce_error_smtp():
    mensaje = traducir_excepcion(smtplib.SMTPAuthenticationError(535, b"auth failed"))

    assert mensaje == "No se pudo enviar el correo. Revisa la configuracion SMTP."


def test_traduce_timeout():
    mensaje = traducir_excepcion(socket.timeout("timed out"))

    assert mensaje == "La operacion demoro demasiado. Reintenta en unos minutos."


def test_traduce_error_afip():
    mensaje = traducir_excepcion(RuntimeError("WSFEv1 FEDummy no respondio"))

    assert mensaje == "AFIP no esta respondiendo correctamente."


def test_prioriza_falta_de_sistema_ini_sobre_wsfe():
    mensaje = traducir_excepcion(RuntimeError("Falta configurar [WSFEv1] url_prod en sistema.ini"))

    assert mensaje == "Falta completar una configuracion en sistema.ini."


def test_prioriza_certificado_sobre_configuracion_generica():
    mensaje = traducir_excepcion(RuntimeError("Falta configurar cert_prod/privatekey_prod"))

    assert mensaje == "Falta configurar el certificado digital."
