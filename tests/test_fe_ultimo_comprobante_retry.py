import pytest


class FakeFE:
    WSDL = "https://servicios1.afip.gov.ar/wsfev1/service.asmx?WSDL"
    cuit_emisor = b"20111111112"
    LanzarExcepciones = True

    def __init__(self, errores):
        self.errores = list(errores)
        self.intentos_comp_ultimo = 0
        self.conexiones = 0
        self.autenticaciones = 0

    def Conectar(self, *args, **kwargs):
        self.conexiones += 1
        return True

    def Autenticar(self):
        self.autenticaciones += 1
        return "<ta />"

    def SetTicketAcceso(self, ta):
        self.ta = ta

    def CompUltimoAutorizado(self, tipo_cbte, punto_vta):
        self.intentos_comp_ultimo += 1
        if self.errores:
            raise self.errores.pop(0)
        return 123


def test_ultimo_comprobante_reintenta_una_vez_si_afip_corta_conexion(monkeypatch):
    from controladores.FE import FEv1
    import libs.Utiles as utiles

    monkeypatch.setattr(utiles, "mostrar_error", lambda *args, **kwargs: None)
    fake = FakeFE([ConnectionResetError(10054, "conexion interrumpida por host remoto")])

    ultimo = FEv1.UltimoComprobante(fake, tipo=1, ptovta=18)

    assert ultimo == 123
    assert fake.intentos_comp_ultimo == 2
    assert fake.conexiones == 2
    assert fake.autenticaciones == 2


def test_ultimo_comprobante_no_reintenta_errores_no_transitorios(monkeypatch):
    from controladores.FE import FEv1
    import libs.Utiles as utiles

    monkeypatch.setattr(utiles, "mostrar_error", lambda *args, **kwargs: None)
    fake = FakeFE([ValueError("error funcional")])

    with pytest.raises(ValueError):
        FEv1.UltimoComprobante(fake, tipo=1, ptovta=18)

    assert fake.intentos_comp_ultimo == 1
    assert fake.conexiones == 1
    assert fake.autenticaciones == 1
