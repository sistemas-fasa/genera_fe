"""Tests de regresión: From alineado por empresa y cascada de emails de error.

Dos fallos de producción:
  1. El .env tiene SMTP_FROM=info@fasa.ar, pero la empresa 1 autentica en
     smtp-relay.gmail.com como sistemas@ferreteriaavenida.com.ar. Como el
     From se resolvía antes que el usuario_correo de la empresa, el relay de
     Google rechazaba el MAIL FROM con 550 5.7.0.
  2. _notificar_fallo_final() encolaba un email sin empresa_id ni quien_envia;
     esa notificación también fallaba y encolaba otra -> 315.064 emails.
"""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from controladores import EnvioEmailsPendientes as EEP  # noqa: E402

PREFIJO_NOTIFICACION = "⚠️ Fallo de envío de email ID "


class EmailFake:
    def __init__(self, id=1, asunto="Pago anticipado", empresa_id=1):
        self.id = id
        self.asunto = asunto
        self.destinatario = "oscar@ferreteriaavenida.com.ar"
        self.intentos = 3
        self.creado_en = "2026-11-17 10:00:00"
        self.empresa_id = empresa_id


class TestResolucionFrom(unittest.TestCase):
    def test_usuario_empresa_gana_sobre_smtp_from_del_env(self):
        resultado = EEP._resolver_remitente(
            None,
            "info@fasa.ar",
            "sistemas@ferreteriaavenida.com.ar",
            "sistemas@ferreteriaavenida.com.ar",
        )
        self.assertEqual(resultado, "sistemas@ferreteriaavenida.com.ar")

    def test_quien_envia_explicito_gana(self):
        resultado = EEP._resolver_remitente(
            "ventas@ferreteriaavenida.com.ar",
            "info@fasa.ar",
            "sistemas@ferreteriaavenida.com.ar",
            "sistemas@ferreteriaavenida.com.ar",
        )
        self.assertEqual(resultado, "ventas@ferreteriaavenida.com.ar")

    def test_sin_usuario_empresa_cae_en_smtp_from(self):
        resultado = EEP._resolver_remitente(
            None, "info@fasa.ar", "", "otro@ejemplo.com"
        )
        self.assertEqual(resultado, "info@fasa.ar")


class TestCascadaNotificaciones(unittest.TestCase):
    def _notificar(self, email):
        with mock.patch.object(
            EEP.ParamSist, "ObtenerParametro", return_value="admin@ejemplo.com"
        ), mock.patch.object(EEP, "encolar_email") as encolar:
            EEP._notificar_fallo_final(email, "550 relay denied")
        return encolar

    def test_notificacion_que_falla_no_genera_otra_notificacion(self):
        email = EmailFake(id=99, asunto=PREFIJO_NOTIFICACION + "42")
        encolar = self._notificar(email)
        encolar.assert_not_called()

    def test_fallo_normal_si_encola_y_hereda_empresa(self):
        email = EmailFake(id=7, asunto="Pago anticipado", empresa_id=2)
        encolar = self._notificar(email)
        encolar.assert_called_once()
        self.assertEqual(encolar.call_args.kwargs.get("empresa_id"), 2)
        self.assertIn("7", encolar.call_args.kwargs["asunto"])


if __name__ == "__main__":
    unittest.main()
