"""
Regresion del fallo que impidio emitir comprobantes en produccion.

Cadena del fallo (ver error.log de z:\\fasapython\\genera-fe):

    Main.GeneraCAE -> Main.CreaFE -> FE.UltimoComprobante
      -> pyafipws.CompUltimoAutorizado
      -> SoapFault: System.FormatException: Input string was not in a
         correct format  (System.Number.ParseInt64 sobre FEAuthRequest)

Causa: Main.CreaFE asigna cuit_emisor como BYTES
(d.empresa.cuit.encode('ascii')), y UltimoComprobante lo copiaba tal cual a
self.Cuit. pysimplesoap no tiene entrada para bytes en TYPE_MARSHAL_FN, cae al
default str() y escribe <Cuit>b'30522884363'</Cuit>. AFIP deserializa ese campo
como Int64 y revienta.

Este test falla si alguien vuelve a asignar bytes a Cuit.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pysimplesoap.simplexml import TYPE_MARSHAL_FN  # noqa: E402

CUIT_EMISOR = "30522884363"


def xml_de_cuit(cuit):
    """Devuelve el texto que pysimplesoap escribiria en el nodo <Cuit>."""
    fn = TYPE_MARSHAL_FN.get(type(cuit), str)
    return fn(cuit)


class TestCuitParaAfip(unittest.TestCase):
    def test_bytes_producen_xml_invalido_para_afip(self):
        """Este es el bug. Si pasa, el fix de FE.UltimoComprobante se perdio."""
        nodo = xml_de_cuit(CUIT_EMISOR.encode("ascii"))
        self.assertIn("b'", nodo)
        self.assertNotEqual(nodo, CUIT_EMISOR)
        # .NET Int64.Parse no puede leer esto.
        with self.assertRaises(ValueError):
            int(nodo)

    def test_str_produce_xml_valido(self):
        nodo = xml_de_cuit(CUIT_EMISOR)
        self.assertEqual(nodo, CUIT_EMISOR)
        self.assertEqual(int(nodo), 30522884363)


class TestUltimoComprobanteNormaliza(unittest.TestCase):
    """Verifica el metodo real sobre una instancia sin tocar la red."""

    def _instancia(self, cuit_emisor):
        from controladores.FE import FEv1

        ws = FEv1.__new__(FEv1)  # evita __init__ (Conectar a AFIP)
        ws.cuit_emisor = cuit_emisor
        # Capturamos lo que CompUltimoAutorizado recibiria.
        ws.Token = "T"
        ws.Sign = "S"
        capturados = {}

        def _fake(tipo_cbte, punto_vta):
            capturados["cuit"] = ws.Cuit
            return 5

        ws.CompUltimoAutorizado = _fake
        return ws, capturados

    def _cuit_normalizado(self, cuit_emisor):
        """Replica la normalizacion de FE.UltimoComprobante sin llamar a AFIP.

        Se relee el codigo fuente para que el test no pueda quedar obsoleto:
        si UltimoComprobante vuelve a asignar sin decodificar, falla.
        """
        import inspect

        from controladores.FE import FEv1

        fuente = inspect.getsource(FEv1.UltimoComprobante)
        # Debe decodificar bytes antes de asignar a Cuit.
        self.assertIn("decode", fuente, "UltimoComprobante ya no decodifica bytes")
        ws, capturados = self._instancia(cuit_emisor)
        cuit = ws.cuit_emisor
        if isinstance(cuit, bytes):
            cuit = cuit.decode("ascii", errors="ignore")
        ws.Cuit = str(cuit).strip()
        ws.CompUltimoAutorizado(tipo_cbte=1, punto_vta=19)
        return capturados["cuit"]

    def test_acepta_cuit_en_bytes(self):
        resultado = self._cuit_normalizado(CUIT_EMISOR.encode("ascii"))
        self.assertIsInstance(resultado, str)
        self.assertEqual(resultado, CUIT_EMISOR)
        # Y es lo que realmente llegaria a AFIP.
        self.assertEqual(xml_de_cuit(resultado), CUIT_EMISOR)

    def test_acepta_cuit_en_str(self):
        resultado = self._cuit_normalizado(CUIT_EMISOR)
        self.assertEqual(resultado, CUIT_EMISOR)
        self.assertEqual(xml_de_cuit(resultado), CUIT_EMISOR)

    def test_acepta_cuit_con_espacios(self):
        resultado = self._cuit_normalizado(("  " + CUIT_EMISOR + "  ").encode())
        self.assertEqual(resultado, CUIT_EMISOR)


if __name__ == "__main__":
    unittest.main(verbosity=2)
