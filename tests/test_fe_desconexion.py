import errno
from unittest.mock import Mock

import pytest

from controladores.FE import FEv1


@pytest.fixture
def wsfe(monkeypatch):
    monkeypatch.setattr("libs.Utiles.mostrar_error", Mock())
    ws = FEv1.__new__(FEv1)
    ws.cuit_emisor = "30500000001"
    ws.Token = "token"
    ws.Sign = "firma"
    ws.reintentos = 1
    ws.params_in = {}
    ws.client = Mock()
    return ws


def test_ultimo_comprobante_reintenta_un_reset(wsfe):
    consulta = wsfe.client.FECompUltimoAutorizado
    consulta.side_effect = [
        ConnectionResetError(errno.ECONNRESET, "conexión interrumpida"),
        {"FECompUltimoAutorizadoResult": {"CbteNro": 0}},
    ]

    assert wsfe.UltimoComprobante() == "0"
    assert consulta.call_count == 2
    assert wsfe.LanzarExcepciones is False


def test_ultimo_comprobante_conserva_el_reset_si_se_agotan_los_intentos(wsfe):
    consulta = wsfe.client.FECompUltimoAutorizado
    consulta.side_effect = ConnectionResetError(errno.ECONNRESET, "conexión interrumpida")

    assert wsfe.UltimoComprobante() is None
    assert consulta.call_count == 3
    assert "ConnectionResetError" in wsfe.Excepcion
    assert wsfe.LanzarExcepciones is False
