from datetime import date, datetime
from pathlib import Path
import ast
import subprocess
import sys

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


class QueryCAEADinamicaFake:
    def __init__(self, modelo):
        self.modelo = modelo
        self.condiciones = None

    def where(self, *condiciones):
        self.condiciones = condiciones
        self.modelo.consultas.append(condiciones)
        return self

    def first(self):
        esperados = {campo: valor for campo, operador, valor in self.condiciones if operador == "=="}
        for registro in self.modelo.creados:
            if all(registro.get(campo) == valor for campo, valor in esperados.items()):
                if registro.get("CAEA"):
                    return type("RegistroCAEA", (), registro)()
        return None


class CAEAModelDinamicoFake(CAEAModelFake):
    def __init__(self):
        self.creados = []
        self.consultas = []

    def select(self):
        return QueryCAEADinamicaFake(self)


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


def test_fecha_simulada_segunda_quincena_solicita_una_vez_y_luego_es_idempotente():
    from controladores.CAEAProgramado import solicitar_caea_si_corresponde

    modelo = CAEAModelDinamicoFake()
    fe = FEv1Fake()
    fe.Orden = "2"
    fe.FchVigDesde = date(2026, 6, 16)
    fe.FchVigHasta = date(2026, 6, 30)
    fe.FchTopeInf = date(2026, 7, 5)
    fe.FchProceso = datetime(2026, 6, 25, 10, 30)
    fe.Obs = ""
    emails = []

    primer_registro = solicitar_caea_si_corresponde(
        empresa_id=1,
        fecha=date(2026, 6, 25),
        caea_model=modelo,
        fe_factory=lambda: fe,
        notificador=emails.append,
        ptovta_resolver=lambda empresa_id: "9999",
    )
    segundo_registro = solicitar_caea_si_corresponde(
        empresa_id=1,
        fecha=date(2026, 6, 25),
        caea_model=modelo,
        fe_factory=lambda: fe,
        notificador=emails.append,
        ptovta_resolver=lambda empresa_id: "0001",
    )

    assert primer_registro.CAEA == "12345678901234"
    assert segundo_registro is None
    assert fe.calls == [("202606", "2")]
    assert len(modelo.creados) == 1
    assert modelo.creados[0]["empresa"] == 1
    assert modelo.creados[0]["periodo"] == "202606"
    assert modelo.creados[0]["orden"] == "2"
    assert modelo.creados[0]["ptovta"] == "9999"
    assert emails == [primer_registro]
    assert modelo.consultas[0] == (
        ("periodo", "==", "202606"),
        ("orden", "==", "2"),
        ("empresa", "==", 1),
        ("CAEA", "!=", ""),
    )
    assert all(("ptovta", "==", "9999") not in consulta for consulta in modelo.consultas)
    assert all(("ptovta", "==", "0001") not in consulta for consulta in modelo.consultas)


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
    assert "QTimer.singleShot(1000, self._verificar_caea_programado)" in main_source
    assert "def _verificar_caea_programado(self):" in main_source
    assert "No se pudo verificar/solicitar CAEA programado al iniciar" in main_source
    assert "CAEA_NOTIFICACION_EMAIL=sistemas@ferreteriaavenida.com.ar" in env_example


def _function_def(path, name):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError("No se encontro la funcion {}".format(name))


def _called_names(node):
    names = []
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        if isinstance(child.func, ast.Name):
            names.append(child.func.id)
        elif isinstance(child.func, ast.Attribute):
            names.append(child.func.attr)
    return names


def test_main_no_verifica_caea_sincronicamente_en_constructor():
    root = Path(__file__).resolve().parents[1]
    main_path = root / "controladores" / "Main.py"
    init = _function_def(main_path, "__init__")
    verificar = _function_def(main_path, "_verificar_caea_programado")

    assert "solicitar_caea_si_corresponde" not in _called_names(init)
    assert "singleShot" in _called_names(init)
    assert "solicitar_caea_si_corresponde" in _called_names(verificar)


def test_verificacion_caea_programada_mantiene_try_except_y_log():
    root = Path(__file__).resolve().parents[1]
    main_path = root / "controladores" / "Main.py"
    main_source = main_path.read_text(encoding="utf-8")
    verificar = _function_def(main_path, "_verificar_caea_programado")
    source = ast.get_source_segment(main_source, verificar)

    assert any(isinstance(node, ast.Try) for node in ast.walk(verificar))
    assert "logging.exception(\"No se pudo verificar/solicitar CAEA programado al iniciar\")" in source


def test_fev1_caea_usa_timeout_y_falla_si_no_conecta():
    root = Path(__file__).resolve().parents[1]
    fe_path = root / "controladores" / "FE.py"
    fe_source = fe_path.read_text(encoding="utf-8")
    solicitar = ast.get_source_segment(fe_source, _function_def(fe_path, "SolicitarCAEA"))
    informar = ast.get_source_segment(fe_source, _function_def(fe_path, "InformarCAEASinMovimiento"))

    assert "timeout=_afip_timeout()" in solicitar
    assert "if not ok:" in solicitar
    assert "raise RuntimeError(self.Excepcion)" in solicitar
    assert "timeout=_afip_timeout()" in informar
    assert "if not ok:" in informar
    assert "raise RuntimeError(self.Excepcion)" in informar


def test_script_caea_programado_dry_run_permita_fecha_simulada_sin_afip_ni_email():
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "probar_caea_programado.py"

    resultado = subprocess.run(
        [
            sys.executable,
            str(script),
            "--empresa",
            "1",
            "--fecha",
            "2026-06-25",
            "--dry-run",
        ],
        cwd=str(root),
        text=True,
        capture_output=True,
        check=False,
    )

    assert resultado.returncode == 0
    assert "Fecha simulada: 2026-06-25" in resultado.stdout
    assert "Periodo: 202606" in resultado.stdout
    assert "Orden: 2" in resultado.stdout
    assert "Corresponde solicitar: si" in resultado.stdout
    assert "Buscaria CAEA existente: si" in resultado.stdout
    assert "Solicitaria AFIP si no existe CAEA: si" in resultado.stdout
    assert "Enviaria email si registra CAEA nuevo: si" in resultado.stdout
    assert "No se llamo a AFIP, no se escribio en base y no se envio email." in resultado.stdout


def test_script_caea_programado_exige_confirmacion_para_ejecucion_real():
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "probar_caea_programado.py"

    resultado = subprocess.run(
        [sys.executable, str(script), "--empresa", "1", "--fecha", "2026-06-25"],
        cwd=str(root),
        text=True,
        capture_output=True,
        check=False,
    )

    assert resultado.returncode != 0
    assert "--confirmar" in resultado.stderr
    assert "puede llamar a AFIP real" in resultado.stderr
