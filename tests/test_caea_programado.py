from datetime import date, datetime
from pathlib import Path

import pytest


class CampoFake:
    def __init__(self, nombre):
        self.nombre = nombre

    def __eq__(self, otro):
        return (self.nombre, "==", otro)

    def __ne__(self, otro):
        return (self.nombre, "!=", otro)


class QueryFake:
    def __init__(self, resultado=None):
        self.resultado = resultado
        self.condiciones = None

    def where(self, *condiciones):
        self.condiciones = condiciones
        return self

    def first(self):
        return self.resultado


class CAEAModelFake:
    periodo = CampoFake("periodo")
    orden = CampoFake("orden")
    empresa = CampoFake("empresa")
    CAEA = CampoFake("CAEA")
    ptovta = CampoFake("ptovta")

    def __init__(self, query_resultado=None):
        self.query = QueryFake(query_resultado)
        self.creados = []

    def select(self):
        return self.query

    def create(self, **datos):
        self.creados.append(datos)
        return type("RegistroCAEA", (), datos)()


class FEv1Fake:
    def __init__(self, caea="12345678901234", falla=False):
        self.calls = []
        self.falla = falla
        self.CAEA = caea
        self.Periodo = "202606"
        self.Orden = "1"
        self.FchVigDesde = date(2026, 6, 1)
        self.FchVigHasta = date(2026, 6, 15)
        self.FchTopeInf = date(2026, 6, 20)
        self.FchProceso = datetime(2026, 6, 10, 9, 30)
        self.Obs = "OK"

    def SolicitarCAEA(self, periodo, orden):
        self.calls.append((periodo, orden))
        if self.falla:
            raise RuntimeError("AFIP caido")
        return self.CAEA


def test_ventanas_de_fecha_para_solicitud_caea():
    from controladores.CAEAProgramado import calcular_periodo_orden_actual, corresponde_solicitar_caea

    casos = [
        (date(2026, 6, 9), False, ("202606", "1")),
        (date(2026, 6, 10), True, ("202606", "1")),
        (date(2026, 6, 15), True, ("202606", "1")),
        (date(2026, 6, 16), False, ("202606", "2")),
        (date(2026, 6, 25), True, ("202606", "2")),
        (date(2026, 7, 26), True, ("202607", "2")),
        (date(2026, 2, 23), True, ("202602", "2")),
        (date(2028, 2, 24), True, ("202802", "2")),
    ]

    for fecha, corresponde, periodo_orden in casos:
        assert calcular_periodo_orden_actual(fecha) == periodo_orden
        assert corresponde_solicitar_caea(fecha) is corresponde


def test_idempotencia_no_usa_ptovta_para_detectar_caea_existente():
    from controladores.CAEAProgramado import caea_ya_existe

    modelo = CAEAModelFake(query_resultado=object())

    assert caea_ya_existe("202606", "1", 1, caea_model=modelo) is True
    assert ("ptovta", "==", "") not in modelo.query.condiciones
    assert modelo.query.condiciones == (
        ("periodo", "==", "202606"),
        ("orden", "==", "1"),
        ("empresa", "==", 1),
        ("CAEA", "!=", ""),
    )


def test_si_ya_existe_caea_no_llama_afip_ni_encola_email():
    from controladores.CAEAProgramado import solicitar_caea_si_corresponde

    modelo = CAEAModelFake(query_resultado=object())
    fe = FEv1Fake()
    emails = []

    resultado = solicitar_caea_si_corresponde(
        empresa_id=1,
        fecha=date(2026, 6, 10),
        caea_model=modelo,
        fe_factory=lambda: fe,
        notificador=emails.append,
    )

    assert resultado is None
    assert fe.calls == []
    assert emails == []
    assert modelo.creados == []


def test_si_corresponde_y_no_existe_solicita_guarda_y_notifica_una_vez():
    from controladores.CAEAProgramado import solicitar_caea_si_corresponde

    modelo = CAEAModelFake(query_resultado=None)
    fe = FEv1Fake()
    emails = []

    registro = solicitar_caea_si_corresponde(
        empresa_id=1,
        fecha=date(2026, 6, 10),
        caea_model=modelo,
        fe_factory=lambda: fe,
        notificador=emails.append,
        ptovta_resolver=lambda empresa_id: "0001",
    )

    assert fe.calls == [("202606", "1")]
    assert registro.CAEA == "12345678901234"
    assert modelo.creados[0]["empresa"] == 1
    assert modelo.creados[0]["periodo"] == "202606"
    assert modelo.creados[0]["orden"] == "1"
    assert modelo.creados[0]["ptovta"] == "0001"
    assert emails == [registro]


def test_no_corresponde_por_fecha_no_consulta_afip_ni_email():
    from controladores.CAEAProgramado import solicitar_caea_si_corresponde

    modelo = CAEAModelFake(query_resultado=None)
    fe = FEv1Fake()
    emails = []

    assert solicitar_caea_si_corresponde(
        empresa_id=1,
        fecha=date(2026, 6, 9),
        caea_model=modelo,
        fe_factory=lambda: fe,
        notificador=emails.append,
    ) is None
    assert fe.calls == []
    assert emails == []
    assert modelo.creados == []


def test_fallo_de_email_no_impide_devolver_caea_guardado(caplog):
    from controladores.CAEAProgramado import solicitar_caea_si_corresponde

    modelo = CAEAModelFake(query_resultado=None)
    fe = FEv1Fake()

    def notificador(_registro):
        raise RuntimeError("SMTP sin configurar")

    registro = solicitar_caea_si_corresponde(
        empresa_id=1,
        fecha=date(2026, 6, 10),
        caea_model=modelo,
        fe_factory=lambda: fe,
        notificador=notificador,
    )

    assert registro.CAEA == "12345678901234"
    assert "No se pudo encolar notificacion de CAEA obtenido" in caplog.text


def test_modelo_caea_declara_campos_reales_transferido_y_nrelacion():
    source = (Path(__file__).resolve().parents[1] / "modelos" / "CAEA.py").read_text(encoding="utf-8")

    assert "transferido = BitBooleanField" in source
    assert "nrelacion = IntegerField" in source


def test_main_invoca_caea_programado_sin_romper_arranque_y_env_example_documenta_destino():
    root = Path(__file__).resolve().parents[1]
    main_source = (root / "controladores" / "Main.py").read_text(encoding="utf-8")
    env_example = (root / ".env.example").read_text(encoding="utf-8")

    assert "from controladores.CAEAProgramado import solicitar_caea_si_corresponde" in main_source
    assert "solicitar_caea_si_corresponde(empresa_id=1)" in main_source
    assert "No se pudo verificar/solicitar CAEA programado al iniciar" in main_source
    assert "CAEA_NOTIFICACION_EMAIL=sistemas@ferreteriaavenida.com.ar" in env_example
