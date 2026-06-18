# coding=utf-8
"""
Prueba controlada y side-effect free de la contingencia CAEA.

Este script usa modelos fake en memoria y fuerza imports en modo sqlite antes
de cargar los controladores. No lee configuraciones reales, no abre conexiones
a la base productiva, no llama AFIP y no crea tablas ni registros reales.
"""
import logging
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _forzar_imports_sin_db_real():
    import libs.Utiles as utiles

    def leer_ini(clave=None, key=None):
        if clave == "base":
            return "sqlite"
        return ""

    utiles.LeerIni = leer_ini


_forzar_imports_sin_db_real()

from controladores.ContingenciaCAEA import activar_modo_caea, restaurar_modo_ws  # noqa: E402


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
    def __init__(self):
        self.registro = RegistroFake(
            maquina="CAJA-CONTROLADA",
            empresa_id=1,
            ptovtafac="0019",
            ptovtaticket="0018",
        )

    def buscar(self, maquina, empresa_id):
        if self.registro.maquina == maquina and self.registro.empresa_id == empresa_id:
            return self.registro
        return None


class ContingenciaFake:
    def __init__(self):
        self.creados = []
        self.tabla_asegurada = False

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


def _ptovtas_simulados():
    return PtoVtaFake([
        {"ptovta": "0019", "ubicacion": "CENTRO", "tipo": "WS", "empresa_id": 1},
        {"ptovta": "0018", "ubicacion": "CERAMICAS", "tipo": "WS", "empresa_id": 1},
        {"ptovta": "0021", "ubicacion": "CENTRO", "tipo": "A", "empresa_id": 1},
        {"ptovta": "0022", "ubicacion": "CERAMICAS", "tipo": "A", "empresa_id": 1},
    ])


def _estado_imprefiscal(registro):
    return "ptovtafac={} ptovtaticket={}".format(registro.ptovtafac, registro.ptovtaticket)


def main():
    logging.disable(logging.CRITICAL)
    maquina = "CAJA-CONTROLADA"
    empresa_id = 1
    imprefiscal = ImpreFiscalFake()
    ptovtas = _ptovtas_simulados()
    contingencias = ContingenciaFake()
    db = DBFake()
    caea_vigente = lambda _empresa_id: True

    print("Prueba controlada de contingencia CAEA")
    print("Sin DB real, sin AFIP real, sin email real.")
    print("CAEA vigente simulado: si")
    print("imprefiscal inicial: {}".format(_estado_imprefiscal(imprefiscal.registro)))

    print("AFIP disponible=False -> activar contingencia")
    activar_modo_caea(
        maquina,
        empresa_id,
        motivo="Prueba controlada",
        imprefiscal_model=imprefiscal,
        ptovta_model=ptovtas,
        contingencia_model=contingencias,
        database=db,
        caea_existente=caea_vigente,
    )
    print("imprefiscal despues de activar: {}".format(_estado_imprefiscal(imprefiscal.registro)))

    print("AFIP disponible=True -> restaurar WS")
    restaurar_modo_ws(
        maquina,
        empresa_id,
        imprefiscal_model=imprefiscal,
        contingencia_model=contingencias,
        database=db,
    )
    print("imprefiscal despues de restaurar: {}".format(_estado_imprefiscal(imprefiscal.registro)))

    assert imprefiscal.registro.ptovtafac == "0019"
    assert imprefiscal.registro.ptovtaticket == "0018"
    assert len(contingencias.creados) == 1
    assert contingencias.creados[0].activa is False
    assert db.atomic_calls == 2

    print("Resultado: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
