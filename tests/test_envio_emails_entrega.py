"""
Tests de regresión para los problemas de "figura enviado pero el cliente no
recibe el comprobante".

Casos cubiertos:
  1. Las rutas de adjunto se guardan absolutas al encolar (no relativas al CWD).
  2. Encolar con un adjunto inexistente falla en vez de encolar un mail mudo.
  3. Al enviar, un adjunto declarado pero ausente aborta en vez de enviarse sin
     el PDF y quedar en estado 'enviado'.
  4. Los destinatarios se deduplican.
  5. El mensaje incluye Date y Message-ID.
  6. Los rechazos parciales de sendmail no se marcan como 'enviado'.
"""

import os
import smtplib
import sys
import tempfile
import unittest
from contextlib import ExitStack
from unittest import mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from controladores import EnvioEmailsPendientes as EEP  # noqa: E402

BASE = os.path.dirname(os.path.abspath(__file__))
ARCHIVO_EXISTENTE = os.path.abspath(os.path.join(BASE, "..", "main.py"))
ARCHIVO_AUSENTE = os.path.join(BASE, "no_existe_este_archivo.pdf")


class TestNormalizacionRutasAdjuntos(unittest.TestCase):
    def test_ruta_relativa_se_absolutiza(self):
        # Reproduce el caso real: la ruta se encola relativa al directorio donde
        # vivia el PDF y se resuelve despues desde otro CWD, donde ya no existe.
        # Absolutizar en el momento del encolado es lo que evita perderlo.
        cwd_original = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            dir_facturas = os.path.join(tmp, "facturas")
            os.mkdir(dir_facturas)
            pdf = os.path.join(dir_facturas, "003-0019-00013158.pdf")
            with open(pdf, "wb") as fh:
                fh.write(b"%PDF-1.4")

            try:
                os.chdir(dir_facturas)
                relativa = os.path.relpath(pdf, dir_facturas)
                self.assertFalse(os.path.isabs(relativa))
                self.assertTrue(os.path.isfile(relativa))

                # Absolutizar aqui (al encolar) es lo que salva el adjunto.
                correcta = EEP._normalizar_ruta_adjunto(relativa)

                # Cambio de contexto: la misma relativa ya no resuelve, y
                # absolutizarla tarde produce una ruta que NO existe.
                os.chdir(tmp)
                self.assertFalse(
                    os.path.isfile(relativa),
                    "el test no reproduce el fallo si la relativa sigue funcionando",
                )
                tardia = EEP._normalizar_ruta_adjunto(relativa)

                self.assertTrue(os.path.isabs(correcta))
                self.assertTrue(os.path.isfile(correcta))
                self.assertEqual(os.path.normcase(correcta), os.path.normcase(pdf))
                # Esta es la ruta que terminaba persistida sin encontrar el archivo.
                self.assertFalse(os.path.isfile(tardia))
            finally:
                os.chdir(cwd_original)

    def test_multiples_rutas_separan_faltantes(self):
        rutas, faltantes = EEP._normalizar_rutas_adjuntos(
            "{},{}".format(ARCHIVO_EXISTENTE, ARCHIVO_AUSENTE)
        )

        self.assertEqual(len(rutas), 2)
        self.assertTrue(all(os.path.isabs(r) for r in rutas))
        self.assertEqual(faltantes, [ARCHIVO_AUSENTE])

    def test_sin_adjunto_no_falla(self):
        self.assertEqual(EEP._normalizar_rutas_adjuntos(None), ([], []))
        self.assertEqual(EEP._normalizar_rutas_adjuntos(""), ([], []))

    def test_comas_finales_se_ignoran(self):
        rutas, faltantes = EEP._normalizar_rutas_adjuntos(
            "{},".format(ARCHIVO_EXISTENTE)
        )
        self.assertEqual(rutas, [ARCHIVO_EXISTENTE])
        self.assertEqual(faltantes, [])


class TestEncolarEmailAdjuntos(unittest.TestCase):
    def test_encolar_absolutiza_el_adjunto(self):
        with tempfile.TemporaryDirectory() as tmp:
            dir_facturas = os.path.join(tmp, "facturas")
            os.mkdir(dir_facturas)
            pdf = os.path.join(dir_facturas, "003-0019-00013158.pdf")
            with open(pdf, "wb") as fh:
                fh.write(b"%PDF-1.4")

            cwd_original = os.getcwd()
            try:
                os.chdir(dir_facturas)
                with mock.patch.object(EEP.EmailPendiente, "create") as create:
                    EEP.encolar_email(
                        destinatario="cliente@dominio.com",
                        asunto="Comprobante",
                        adjunto_ruta="003-0019-00013158.pdf",
                        adjunto_nombre="003-0019-00013158.pdf",
                    )
            finally:
                os.chdir(cwd_original)

        guardado = create.call_args.kwargs["adjunto_ruta"]
        self.assertTrue(os.path.isabs(guardado))
        self.assertEqual(os.path.normcase(guardado), os.path.normcase(pdf))

    def test_encolar_falla_si_el_adjunto_no_existe(self):
        with mock.patch.object(EEP.EmailPendiente, "create") as create:
            with self.assertRaises(FileNotFoundError):
                EEP.encolar_email(
                    destinatario="cliente@dominio.com",
                    asunto="Comprobante",
                    adjunto_ruta="facturas\\no-existe-este.pdf",
                )
        create.assert_not_called()

    def test_encolar_sin_adjunto_sigue_funcionando(self):
        with mock.patch.object(EEP.EmailPendiente, "create") as create:
            EEP.encolar_email(
                destinatario="cliente@dominio.com",
                asunto="Aviso",
                cuerpo_texto="Hola",
            )
        self.assertIsNone(create.call_args.kwargs["adjunto_ruta"])


class TestParseoDestinatarios(unittest.TestCase):
    def test_deduplica_y_limpia_vacios(self):
        crudo = "a@x.com, b@y.com ,a@x.com,,"
        self.assertEqual(EEP._parsear_destinatarios(crudo), ["a@x.com", "b@y.com"])

    def test_deduplica_sin_distinguir_mayusculas(self):
        crudo = "Cliente@X.com,cliente@x.com"
        self.assertEqual(EEP._parsear_destinatarios(crudo), ["Cliente@X.com"])

    def test_vacio_devuelve_lista_vacia(self):
        self.assertEqual(EEP._parsear_destinatarios(""), [])
        self.assertEqual(EEP._parsear_destinatarios(None), [])


class _SMTPStub:
    """Servidor SMTP mínimo: no abre conexión y registra lo que se le envía."""

    def __init__(self, rechazados=None):
        self.rechazados = rechazados or {}
        self.enviados = []

    def sendmail(self, envelope_from, to_addrs, msg):
        self.enviados.append((envelope_from, to_addrs, msg))
        return dict(self.rechazados)

    def login(self, user, password):
        return (235, b"OK")

    def starttls(self, *args, **kwargs):
        return (220, b"OK")

    def quit(self):
        pass

    close = quit


class _RegistroFalso:
    def __init__(self, adjunto_ruta=None, destinatario="cliente@dominio.com"):
        self.id = 1
        self.destinatario = destinatario
        self.asunto = "Comprobante"
        self.cuerpo_html = "<p>Comprobante</p>"
        self.cuerpo_texto = "Comprobante"
        self.adjunto_ruta = adjunto_ruta
        self.adjunto_nombre = "003-0019-00013158.pdf"
        self.cc = None
        self.cco = None
        self.quien_envia = "ventas@ferreteriaavenida.com.ar"
        self.intentos = 0
        self.estado = "pendiente"
        self.procesando_desde = None
        self.empresa_id = 1
        self.creado_en = None
        self.enviado_en = None


class _Escenario:
    """Ejecuta enviar_email_en_hilo con DB, Empresa y SMTP simulados."""

    def __init__(self, registro, smtp):
        self.registro = registro
        self.smtp = smtp
        self.estados_persistidos = []

    def __enter__(self):
        db = mock.Mock()
        db.is_closed.return_value = False

        empresa = mock.Mock()
        empresa.codigo = 1
        empresa.nombre = "FASA"
        empresa.servidor_correo = "smtp.test"
        empresa.puerto = 465
        empresa.usuario_correo = "ventas@ferreteriaavenida.com.ar"
        empresa.pass_correo = "clave"

        empresas = mock.Mock()
        empresas.select.return_value.first.return_value = empresa

        cadena = mock.MagicMock()
        # execute() -> 1 fila: el hilo logra reclamar el registro
        cadena.where.return_value.execute.return_value = 1

        def _update(**kwargs):
            if "estado" in kwargs:
                self.estados_persistidos.append(kwargs["estado"])
            return cadena

        self._stack = ExitStack()
        self._stack.enter_context(
            mock.patch.object(
                EEP, "ModeloBase", return_value=mock.Mock(getDb=lambda: db)
            )
        )
        self._stack.enter_context(mock.patch.object(EEP, "Empresa", empresas))
        self._stack.enter_context(mock.patch.object(EEP, "ParamSist"))
        self._stack.enter_context(
            mock.patch.object(
                EEP.EmailPendiente, "get_by_id", return_value=self.registro
            )
        )
        self._stack.enter_context(
            mock.patch.object(EEP.EmailPendiente, "update", side_effect=_update)
        )

        select_mock = self._stack.enter_context(
            mock.patch.object(EEP.EmailPendiente, "select")
        )
        select_mock.return_value.where.return_value.count.return_value = 0

        self._stack.enter_context(
            mock.patch.object(smtplib, "SMTP_SSL", return_value=self.smtp)
        )
        self._stack.enter_context(
            mock.patch.object(smtplib, "SMTP", return_value=self.smtp)
        )
        self._stack.enter_context(
            mock.patch.dict(os.environ, {"SMTP_HOUR_LIMIT": "200"})
        )
        return self

        self._stack = ExitStack()
        self._stack.enter_context(
            mock.patch.object(
                EEP, "ModeloBase", return_value=mock.Mock(getDb=lambda: db)
            )
        )
        self._stack.enter_context(mock.patch.object(EEP, "Empresa", empresas))
        self._stack.enter_context(mock.patch.object(EEP, "ParamSist"))
        self._stack.enter_context(
            mock.patch.object(
                EEP.EmailPendiente, "get_by_id", return_value=self.registro
            )
        )

        update_mock = mock.patch.object(
            EEP.EmailPendiente, "update", side_effect=_update
        )
        update_mock.start()
        self._stack.enter_context(update_mock)
        # update(...).where(...).execute() -> 1 fila en el reclamo inicial
        self._stack.enter_context(
            mock.patch.object(
                mock.MagicMock(return_value=1), "where", return_value=mock.MagicMock()
            )
        )

        select_mock = mock.patch.object(EEP.EmailPendiente, "select")
        self._stack.enter_context(select_mock)
        select_mock.start().return_value.where.return_value.count.return_value = 0

        self._stack.enter_context(
            mock.patch.object(smtplib, "SMTP_SSL", return_value=self.smtp)
        )
        self._stack.enter_context(
            mock.patch.object(smtplib, "SMTP", return_value=self.smtp)
        )
        self._stack.enter_context(
            mock.patch.dict(os.environ, {"SMTP_HOUR_LIMIT": "200"})
        )
        return self

    def __exit__(self, *exc_info):
        return self._stack.__exit__(*exc_info)

    def ejecutar(self):
        EEP.enviar_email_en_hilo(self.registro.id)
        return self


class TestEnvioAdjuntoInexistente(unittest.TestCase):
    def test_adjunto_ausente_aborta_el_envio(self):
        registro = _RegistroFalso(
            adjunto_ruta="facturas\\000-0000-00000000inexistente.pdf"
        )
        smtp = _SMTPStub()

        with _Escenario(registro, smtp) as esc:
            esc.ejecutar()

        self.assertEqual(smtp.enviados, [], "el mail salió sin su adjunto")
        self.assertNotIn("enviado", esc.estados_persistidos)

    def test_adjunto_presente_se_envia(self):
        registro = _RegistroFalso(adjunto_ruta=ARCHIVO_EXISTENTE)
        smtp = _SMTPStub()

        with _Escenario(registro, smtp) as esc:
            esc.ejecutar()

        self.assertEqual(len(smtp.enviados), 1)
        cuerpo = smtp.enviados[0][2]
        self.assertIn("Message-ID", cuerpo)
        self.assertIn("Date", cuerpo)
        self.assertIn("filename=", cuerpo)
        self.assertIn("enviado", esc.estados_persistidos)


class TestRechazosParciales(unittest.TestCase):
    def test_rechazo_parcial_no_marca_enviado(self):
        registro = _RegistroFalso(destinatario="a@x.com,b@y.com")
        smtp = _SMTPStub(rechazados={"b@y.com": (550, b"No such user")})

        with _Escenario(registro, smtp) as esc:
            esc.ejecutar()

        self.assertNotIn(
            "enviado",
            esc.estados_persistidos,
            "un rechazo parcial no puede quedar como enviado",
        )

    def test_envio_aceptado_siempre_marca_enviado(self):
        registro = _RegistroFalso()
        smtp = _SMTPStub()

        with _Escenario(registro, smtp) as esc:
            esc.ejecutar()

        self.assertIn("enviado", esc.estados_persistidos)


if __name__ == "__main__":
    unittest.main(verbosity=2)
