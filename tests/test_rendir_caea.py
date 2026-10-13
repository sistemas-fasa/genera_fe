"""Tests del servicio de rendido de CAEA, sin AFIP, sin base y sin PyQt."""
from datetime import date

from controladores.RendirCAEA import (
    ESTADO_CON_ERRORES,
    ESTADO_TERMINADO,
    listar_ptovta_caea,
    obtener_caea,
    rendir,
    rendir_ptovta,
)


CAEA = "71234567890123"


class CampoFake:
    def __init__(self, nombre):
        self.nombre = nombre

    def __eq__(self, otro):
        return (self.nombre, "==", otro)

    def __ne__(self, otro):
        return (self.nombre, "!=", otro)


def _filtrar(filas, condiciones):
    salida = list(filas)
    for nombre, operador, valor in condiciones:
        if operador == "==":
            salida = [f for f in salida if getattr(f, nombre) == valor]
        elif operador == "!=":
            salida = [f for f in salida if getattr(f, nombre) != valor]
    return salida


class SeleccionFake:
    def __init__(self, filas):
        self.filas = filas
        self.condiciones = []

    def where(self, *condiciones):
        # peewee encadena los where con AND, no los reemplaza.
        self.condiciones.extend(condiciones)
        return self

    def count(self):
        return len(_filtrar(self.filas, self.condiciones))

    def first(self):
        filtrados = _filtrar(self.filas, self.condiciones)
        return filtrados[0] if filtrados else None

    def __iter__(self):
        return iter(_filtrar(self.filas, self.condiciones))


class RegistroCAEAFake:
    def __init__(self, caea=CAEA, periodo="202606", orden="1"):
        self.CAEA = caea
        self.periodo = periodo
        self.orden = orden
        self.empresa = 1
        self.fchtopeinf = date(2026, 6, 20)


class CAEAModelFake:
    periodo = CampoFake("periodo")
    orden = CampoFake("orden")
    empresa = CampoFake("empresa")
    CAEA = CampoFake("CAEA")

    def __init__(self, registros=None):
        self.registros = registros if registros is not None else [RegistroCAEAFake()]

    def select(self):
        return SeleccionFake(self.registros)


class FilaRendicion:
    def __init__(self, empresa_id, periodo, orden, ptovta):
        self.empresa_id = empresa_id
        self.periodo = periodo
        self.orden = orden
        self.ptovta = ptovta
        self.caea = ""
        self.estado = ""
        self.sin_movimiento = False
        self.comprobantes_total = 0
        self.comprobantes_ok = 0
        self.comprobantes_error = 0
        self.fecha_inicio = None
        self.fecha_fin = None
        self.ultimo_error = ""
        self.guardados = 0

    def save(self):
        self.guardados += 1


class RendicionModelFake:
    def __init__(self):
        self.filas = {}

    def _clave(self, empresa_id, periodo, orden, ptovta):
        return (empresa_id, periodo, str(orden), ptovta)

    def obtener(self, empresa_id, periodo, orden, ptovta, crear=True):
        clave = self._clave(empresa_id, periodo, orden, ptovta)
        if clave not in self.filas and crear:
            self.filas[clave] = FilaRendicion(empresa_id, periodo, orden, ptovta)
        return self.filas.get(clave)

    def listar(self, empresa_id=None, periodo=None, orden=None):
        return list(self.filas.values())


class EncabezadoFake:
    def __init__(self, puntovta, cbtenro, cae):
        self.puntovta = puntovta
        self.cbtenro = cbtenro
        self.cae = cae
        self.tipows = "A"
        self.resultado = ""
        self.errmsg = ""
        self.motivoobs = ""
        self.vencecae = None
        self.errorprog = ""
        self.guardados = 0

    def save(self):
        self.guardados += 1


class EncabezadoModelFake:
    puntovta = CampoFake("puntovta")
    tipows = CampoFake("tipows")
    cae = CampoFake("cae")

    def __init__(self, encabezados):
        self.filas = encabezados

    def select(self):
        return SeleccionFake(self.filas)


class PtoVtaFake:
    def __init__(self, ptovta, tipo="A", empresa_id=1):
        self.ptovta = ptovta
        self.tipo = tipo
        self.empresa_id = empresa_id


class PtoVtaModelFake:
    ptovta = CampoFake("ptovta")
    tipo = CampoFake("tipo")
    empresa_id = CampoFake("empresa_id")

    def __init__(self, filas):
        self.filas = filas

    def select(self):
        return SeleccionFake(self.filas)


class FEFake:
    def __init__(self, falla=False):
        self.informados = []
        self.falla = falla

    def InformarCAEASinMovimiento(self, ptovta, caea):
        if self.falla:
            raise RuntimeError("AFIP no responde")
        self.informados.append((ptovta, caea))


class ControladorFake:
    def __init__(self, errores=()):
        self.llamadas = []
        self.errores = set(errores)
        self.cae = ""
        self.comprobante = 0
        self.resultado = ""
        self.errmsg = ""
        self.motivoobs = ""
        self.vencecae = ""
        self.xml_request = ""
        self.xml_response = ""

    def CreaFE(self, encabezado, caea=None):
        self.llamadas.append((encabezado.puntovta, encabezado.cbtenro, caea))
        if encabezado.cbtenro in self.errores:
            self.resultado = "E"
            self.errmsg = "Codigo 600"
            self.motivoobs = "CAE ya informado"
            self.xml_request = "<req/>"
            self.xml_response = "<res/>"
            return False
        self.cae = ("71" + encabezado.cbtenro.rjust(12, "0"))[:14]
        self.comprobante = int(encabezado.cbtenro)
        self.resultado = "A"
        self.vencecae = "20260620"
        return True


def _base(encabezados=(), errores=(), fe_falla=False):
    """Para rendir_ptovta, que no necesita el catalogo de puntos de venta.

    Devuelve {"kwargs": ..., "spies": ...} para no pasar los espías como
    argumentos al servicio.
    """
    encabezado_model = EncabezadoModelFake(list(encabezados))
    controlador = ControladorFake(errores)
    fe = FEFake(falla=fe_falla)
    kwargs = {
        "caea_model": CAEAModelFake(),
        "rendicion_model": RendicionModelFake(),
        "encabezado_model": encabezado_model,
        "fe_factory": lambda: fe,
        "controlador_factory": lambda: controlador,
    }
    spies = {
        "fe": fe,
        "controlador": controlador,
        "encabezados": encabezado_model.filas,
    }
    return {"kwargs": kwargs, "spies": spies}


def _rindir(encabezados=(), ptovtas=None, **extra):
    """Para rendir, que ademas necesita el catalogo de puntos de venta."""
    base = _base(encabezados)
    kwargs = base["kwargs"]
    kwargs["ptovta_model"] = PtoVtaModelFake(
        ptovtas if ptovtas is not None else [PtoVtaFake("0022")]
    )
    kwargs["avisar"] = False
    kwargs.update(extra)
    return {"kwargs": kwargs, "spies": base["spies"]}


def test_ptovta_sin_comprobantes_se_declara_sin_movimiento():
    """ARCA exige declarar tambien los puntos de venta que no emitieron."""
    piezas = _base(encabezados=[])

    resumen = rendir_ptovta("202606", "1", "0022", **piezas["kwargs"])

    assert resumen["ok"] is True
    assert resumen["sin_movimiento"] is True
    assert piezas["spies"]["fe"].informados == [("0022", CAEA)]
    # Sin comprobantes no hace falta instanciar el controlador.
    assert piezas["spies"]["controlador"].llamadas == []

    fila = piezas["kwargs"]["rendicion_model"].obtener(
        1, "202606", "1", "0022", crear=False
    )
    assert fila.sin_movimiento is True
    assert fila.estado == ESTADO_TERMINADO


def test_comprobantes_se_informan_y_guardan_el_cae_real():
    piezas = _base(
        encabezados=[
            EncabezadoFake("0022", "00000001", CAEA),
            EncabezadoFake("0022", "00000002", CAEA),
        ]
    )

    resumen = rendir_ptovta("202606", "1", "0022", **piezas["kwargs"])

    assert resumen["ok"] is True
    assert resumen["ok_count"] == 2
    assert resumen["error_count"] == 0
    assert piezas["spies"]["fe"].informados == []

    informado = piezas["spies"]["encabezados"][0]
    assert informado.resultado == "A"
    assert informado.cae == "71000000000001"
    assert informado.guardados == 1


def test_el_cae_guardado_no_es_el_numero_de_caea():
    """El campo cae guardaba el numero de CAEA, indistinguible de un CAE."""
    piezas = _base(encabezados=[EncabezadoFake("0022", "00000007", CAEA)])

    rendir_ptovta("202606", "1", "0022", **piezas["kwargs"])

    informado = piezas["spies"]["encabezados"][0]
    assert informado.cae != CAEA
    assert len(informado.cae) == 14
    assert informado.cae.startswith("7")


def test_un_comprobante_rechazado_no_aborta_el_resto_del_ptovta():
    piezas = _base(
        encabezados=[
            EncabezadoFake("0022", "00000001", CAEA),
            EncabezadoFake("0022", "00000002", CAEA),
            EncabezadoFake("0022", "00000003", CAEA),
        ],
        errores=("00000002",),
    )

    resumen = rendir_ptovta("202606", "1", "0022", **piezas["kwargs"])

    assert resumen["ok"] is False
    assert resumen["ok_count"] == 2
    assert resumen["error_count"] == 1

    fallido = piezas["spies"]["encabezados"][1]
    assert fallido.resultado == "E"
    # El XML queda guardado para poder ver por que reboto AFIP.
    assert "XML_REQUEST:" in fallido.errorprog
    assert "<req/>" in fallido.errorprog

    fila = piezas["kwargs"]["rendicion_model"].obtener(
        1, "202606", "1", "0022", crear=False
    )
    assert fila.estado == ESTADO_CON_ERRORES
    assert fila.comprobantes_total == 3
    assert fila.comprobantes_ok == 2
    assert fila.comprobantes_error == 1
    assert "XML_REQUEST:" in fila.ultimo_error


def test_sin_caea_no_se_informa_nada():
    piezas = _base()
    piezas["kwargs"]["caea_model"] = CAEAModelFake(registros=[])

    resumen = rendir_ptovta("202606", "1", "0022", **piezas["kwargs"])

    assert resumen["ok"] is False
    assert "No hay CAEA" in resumen["motivo"]
    assert piezas["spies"]["fe"].informados == []
    assert piezas["kwargs"]["rendicion_model"].filas == {}


def test_afip_caido_en_el_sin_movimiento_queda_registrado():
    piezas = _base(encabezados=[], fe_falla=True)

    resumen = rendir_ptovta("202606", "1", "0022", **piezas["kwargs"])

    assert resumen["ok"] is False
    assert resumen["error_count"] == 1

    fila = piezas["kwargs"]["rendicion_model"].obtener(
        1, "202606", "1", "0022", crear=False
    )
    assert fila.estado == ESTADO_CON_ERRORES
    assert fila.sin_movimiento is False


def test_rindir_recorre_todos_los_ptovta_de_caea():
    piezas = _rindir(
        encabezados=[EncabezadoFake("0022", "00000001", CAEA)],
        ptovtas=[
            PtoVtaFake("0022"),
            PtoVtaFake("0021"),
            PtoVtaFake("0023"),
            PtoVtaFake("0001", tipo="C"),
        ],
    )

    resumen = rendir("202606", "1", empresa_id=1, **piezas["kwargs"])

    assert sorted(d["ptovta"] for d in resumen["detalle"]) == ["0021", "0022", "0023"]
    assert resumen["ok"] is True
    # Los de tipo C no van: son del Controlador Fiscal.
    assert all(d["ptovta"] != "0001" for d in resumen["detalle"])


def test_rindir_es_idempotente_no_reprocesa_lo_terminado():
    piezas = _rindir(encabezados=[EncabezadoFake("0022", "00000001", CAEA)])
    controlador = piezas["spies"]["controlador"]

    primera = rendir("202606", "1", empresa_id=1, **piezas["kwargs"])
    assert len(primera["detalle"]) == 1
    assert len(controlador.llamadas) == 1

    segunda = rendir("202606", "1", empresa_id=1, **piezas["kwargs"])

    assert segunda["detalle"] == []
    assert segunda["omitidos"] == ["0022"]
    # No se volvio a llamar a AFIP.
    assert len(controlador.llamadas) == 1


def test_rindir_con_todos_no_declara_sin_movimiento_lo_ya_informado():
    """Al reprocesar, los comprobantes ya tienen el CAE real y la consulta por
    numero de CAEA viene vacia. No hay que declarar "sin movimiento" un punto
    de venta que si emitio."""
    piezas = _rindir(encabezados=[EncabezadoFake("0022", "00000001", CAEA)])
    controlador = piezas["spies"]["controlador"]
    fe = piezas["kwargs"]["fe_factory"]()

    rendir("202606", "1", empresa_id=1, **piezas["kwargs"])
    segunda = rendir(
        "202606", "1", empresa_id=1, solo_pendientes=False, **piezas["kwargs"]
    )

    assert len(segunda["detalle"]) == 1
    assert segunda["detalle"][0].get("ya_informado") is True
    assert segunda["detalle"][0]["sin_movimiento"] is False
    assert fe.informados == []
    assert len(controlador.llamadas) == 1


def test_se_avisa_con_un_resumen_del_rendido():
    enviados = []
    piezas = _rindir(
        encabezados=[],
        ptovtas=[PtoVtaFake("0022")],
        avisar=True,
        notificador=lambda **kwargs: enviados.append(kwargs),
    )

    rendir("202606", "1", empresa_id=1, **piezas["kwargs"])

    assert len(enviados) == 1
    cuerpo = enviados[0]["cuerpo_texto"]
    assert "202606" in cuerpo
    assert "0022" in cuerpo
    assert "sin movimiento" in cuerpo


def test_obtener_caea_ignora_los_registros_vacios():
    modelo = CAEAModelFake(registros=[RegistroCAEAFake(caea="")])

    assert obtener_caea("202606", "1", 1, caea_model=modelo) is None


def test_listar_ptovta_caea_solo_toma_los_de_tipo_a():
    filas = [PtoVtaFake("22"), PtoVtaFake("23"), PtoVtaFake("1", tipo="C")]

    resultado = listar_ptovta_caea(1, ptovta_model=PtoVtaModelFake(filas))

    assert resultado == ["0022", "0023"]