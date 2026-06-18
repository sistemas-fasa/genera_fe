from datetime import datetime
import sys

import pytest


@pytest.fixture(autouse=True)
def _forzar_modelobase_sqlite(monkeypatch):
    import libs.Utiles as utiles

    def leer_ini(clave=None, key=None):
        if clave == "base":
            return "sqlite"
        return ""

    monkeypatch.setattr(utiles, "LeerIni", leer_ini)
    for modulo in [
        "controladores.ContingenciaCAEA",
        "modelos.ModeloBase",
        "modelos.CAEA",
        "modelos.ImpreFiscalFasa",
        "modelos.ImpreFiscalContingenciaFasa",
        "modelos.PtoVtaFasa",
    ]:
        sys.modules.pop(modulo, None)


class RegistroFake:
    def __init__(self, **datos):
        self.__dict__.update(datos)
        self.guardados = 0

    def save(self):
        self.guardados += 1


class PtoVtaFake:
    def __init__(self, registros):
        self.registros = [RegistroFake(**registro) for registro in registros]

    def buscar(self, ptovta=None, empresa_id=None, ubicacion=None, tipo=None):
        for registro in self.registros:
            if ptovta is not None and registro.ptovta != ptovta:
                continue
            if empresa_id is not None and registro.empresa_id != empresa_id:
                continue
            if ubicacion is not None and registro.ubicacion != ubicacion:
                continue
            if tipo is not None and registro.tipo != tipo:
                continue
            return registro
        return None


class ImpreFiscalFake:
    def __init__(self, registros):
        self.registros = [RegistroFake(**registro) for registro in registros]

    def buscar(self, maquina, empresa_id):
        for registro in self.registros:
            if registro.maquina == maquina and registro.empresa_id == empresa_id:
                return registro
        return None


class ContingenciaFake:
    tabla_asegurada = False

    def __init__(self):
        self.creados = []

    def asegurar_tabla(self):
        self.tabla_asegurada = True

    def buscar_activa(self, maquina, empresa_id):
        for registro in self.creados:
            if registro.maquina == maquina and registro.empresa_id == empresa_id and registro.activa:
                return registro
        return None

    def create(self, **datos):
        registro = RegistroFake(id=len(self.creados) + 1, **datos)
        self.creados.append(registro)
        return registro


class DBFake:
    def __init__(self):
        self.atomic_calls = 0

    def atomic(self):
        db = self

        class Atomic:
            def __enter__(self):
                db.atomic_calls += 1

            def __exit__(self, exc_type, exc, tb):
                return False

        return Atomic()


def _ptovtas_base():
    return PtoVtaFake([
        {"ptovta": "0018", "ubicacion": "CERAMICAS", "tipo": "WS", "empresa_id": 1},
        {"ptovta": "0019", "ubicacion": "CENTRO", "tipo": "WS", "empresa_id": 1},
        {"ptovta": "0020", "ubicacion": "CAPIOVY", "tipo": "WS", "empresa_id": 1},
        {"ptovta": "0021", "ubicacion": "CENTRO", "tipo": "A", "empresa_id": 1},
        {"ptovta": "0022", "ubicacion": "CERAMICAS", "tipo": "A", "empresa_id": 1},
        {"ptovta": "0023", "ubicacion": "CAPIOVY", "tipo": "A", "empresa_id": 1},
    ])


def test_resuelve_punto_caea_por_misma_ubicacion():
    from controladores.ContingenciaCAEA import obtener_punto_caea_equivalente

    assert obtener_punto_caea_equivalente("19", 1, ptovta_model=_ptovtas_base()) == "0021"
    assert obtener_punto_caea_equivalente("0018", 1, ptovta_model=_ptovtas_base()) == "0022"


def test_resuelve_fallback_y_valida_que_exista_como_tipo_a():
    from controladores.ContingenciaCAEA import obtener_punto_caea_equivalente

    ptovtas = PtoVtaFake([
        {"ptovta": "0019", "ubicacion": "CENTRO", "tipo": "WS", "empresa_id": 1},
        {"ptovta": "0021", "ubicacion": "OTRA", "tipo": "A", "empresa_id": 1},
    ])

    assert obtener_punto_caea_equivalente("0019", 1, ptovta_model=ptovtas) == "0021"

    sin_fallback_valido = PtoVtaFake([
        {"ptovta": "0019", "ubicacion": "CENTRO", "tipo": "WS", "empresa_id": 1},
        {"ptovta": "0021", "ubicacion": "OTRA", "tipo": "WS", "empresa_id": 1},
    ])
    with pytest.raises(RuntimeError, match="No se pudo resolver punto CAEA"):
        obtener_punto_caea_equivalente("0019", 1, ptovta_model=sin_fallback_valido)


def test_activar_modo_caea_actualiza_imprefiscal_respalda_y_es_idempotente():
    from controladores.ContingenciaCAEA import activar_modo_caea

    imprefiscal = ImpreFiscalFake([
        {"maquina": "CAJA-01", "empresa_id": 1, "ptovtafac": "0019", "ptovtaticket": "0018"},
    ])
    contingencias = ContingenciaFake()
    db = DBFake()

    primer_respaldo = activar_modo_caea(
        "CAJA-01",
        1,
        motivo="AFIP no responde",
        imprefiscal_model=imprefiscal,
        ptovta_model=_ptovtas_base(),
        contingencia_model=contingencias,
        database=db,
        caea_existente=lambda empresa_id: True,
    )
    segundo_respaldo = activar_modo_caea(
        "CAJA-01",
        1,
        motivo="AFIP sigue sin responder",
        imprefiscal_model=imprefiscal,
        ptovta_model=_ptovtas_base(),
        contingencia_model=contingencias,
        database=db,
        caea_existente=lambda empresa_id: True,
    )

    registro = imprefiscal.buscar("CAJA-01", 1)
    assert registro.ptovtafac == "0021"
    assert registro.ptovtaticket == "0022"
    assert len(contingencias.creados) == 1
    assert segundo_respaldo is primer_respaldo
    assert primer_respaldo.ptovtafac_original == "0019"
    assert primer_respaldo.ptovtaticket_original == "0018"
    assert primer_respaldo.ptovtafac_caea == "0021"
    assert primer_respaldo.ptovtaticket_caea == "0022"
    assert primer_respaldo.motivo == "AFIP no responde"
    assert contingencias.tabla_asegurada is True
    assert db.atomic_calls == 1


def test_activar_modo_caea_exige_caea_existente_y_no_cambia_parcialmente():
    from controladores.ContingenciaCAEA import activar_modo_caea

    imprefiscal = ImpreFiscalFake([
        {"maquina": "CAJA-01", "empresa_id": 1, "ptovtafac": "0019", "ptovtaticket": "0018"},
    ])
    contingencias = ContingenciaFake()

    with pytest.raises(RuntimeError, match="No hay CAEA vigente"):
        activar_modo_caea(
            "CAJA-01",
            1,
            imprefiscal_model=imprefiscal,
            ptovta_model=_ptovtas_base(),
            contingencia_model=contingencias,
            caea_existente=lambda empresa_id: False,
        )

    registro = imprefiscal.buscar("CAJA-01", 1)
    assert registro.ptovtafac == "0019"
    assert registro.ptovtaticket == "0018"
    assert contingencias.creados == []


def test_restaurar_modo_ws_vuelve_a_puntos_originales_y_cierra_respaldo():
    from controladores.ContingenciaCAEA import restaurar_modo_ws

    imprefiscal = ImpreFiscalFake([
        {"maquina": "CAJA-01", "empresa_id": 1, "ptovtafac": "0021", "ptovtaticket": "0022"},
    ])
    contingencias = ContingenciaFake()
    respaldo = contingencias.create(
        maquina="CAJA-01",
        empresa_id=1,
        ptovtafac_original="0019",
        ptovtaticket_original="0018",
        ptovtafac_caea="0021",
        ptovtaticket_caea="0022",
        activa=True,
        fecha_activacion=datetime(2026, 6, 18, 12, 0),
        fecha_restauracion=None,
        motivo="AFIP no responde",
    )
    db = DBFake()

    resultado = restaurar_modo_ws(
        "CAJA-01",
        1,
        imprefiscal_model=imprefiscal,
        contingencia_model=contingencias,
        database=db,
    )

    registro = imprefiscal.buscar("CAJA-01", 1)
    assert resultado is respaldo
    assert registro.ptovtafac == "0019"
    assert registro.ptovtaticket == "0018"
    assert respaldo.activa is False
    assert respaldo.fecha_restauracion is not None
    assert db.atomic_calls == 1


def test_restaurar_sin_contingencia_activa_no_falla():
    from controladores.ContingenciaCAEA import restaurar_modo_ws

    contingencias = ContingenciaFake()

    assert restaurar_modo_ws(
        "CAJA-01",
        1,
        imprefiscal_model=ImpreFiscalFake([]),
        contingencia_model=contingencias,
    ) is None
    assert contingencias.tabla_asegurada is True
