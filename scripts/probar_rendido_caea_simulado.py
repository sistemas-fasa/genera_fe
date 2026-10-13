# coding=utf-8
r"""Prueba del rendido por CAEA contra la base real, con ARCA simulado.

Los tests de tests/test_rendir_caea.py usan modelos fake: no tocan peewee ni
MySQL, asi que la rama de ARCA **respondiendo 'A'** no llego a ejecutarse
nunca. Ese es el unico hueco que queda, porque en homologacion no hay ningun
punto de venta habilitado para CAEA (ARCA responde 1204) y no se pueden
crear.

Este script corre el servicio de verdad, con los modelos peewee reales y los
registros de verdad en la base, pero inyectando un controlador simulado que
responde como responderia ARCA si aceptara el comprobante. No llama a AFIP:
todo lo que toca en la base lo puso y lo borra el propio script.

    python .\scripts\probar_rendido_caea_simulado.py
    python .\scripts\probar_rendido_caea_simulado.py --periodo 202610 --orden 1
    python .\scripts\probar_rendido_caea_simulado.py --dejar

Por defecto limpia al terminar lo que creo. Con --dejar deja las filas para
que puedas mirarlas a mano.
"""
import argparse
import sys
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from controladores.RendirCAEA import (  # noqa: E402
    ESTADO_TERMINADO,
    contar_pendientes,
    rendir_ptovta,
)
from modelos.CAEA import CAEA  # noqa: E402
from modelos.Encabezado import Encabezado  # noqa: E402
from modelos.IVA import IVA  # noqa: E402


# Alto y a mano: choca con cualquier nrelacion real.
NRELACION = 99000003
PTOVTA = "0022"
NETO = "81124.01"
IVA_21 = "17036.04"
TOTAL = "98160.05"


class ControladorSimulado:
    """Imita a MainController.CreaFE cuando ARCA acepta con CAEA.

    Lo importante: en el regimen CAEA ARCA no devuelve un CAE propio,
    devuelve el Resultado de validar el comprobante contra el CAEA. Asi que
    self.cae sigue siendo el CAEA.
    """

    def __init__(self, numero_otorgado=1):
        self.llamadas = []
        self.cae = ""
        self.comprobante = 0
        self.resultado = ""
        self.errmsg = ""
        self.motivoobs = ""
        # Vacio a proposito: Main.CreaFE no define vencimiento para CAEA, asi
        # que el servicio tiene que caer al fchtopeinf del propio CAEA.
        self.vencecae = ""
        self.xml_request = "<req/>"
        self.xml_response = "<res/>"
        self.numero_otorgado = numero_otorgado

    def CreaFE(self, encabezado, caea=None):
        self.llamadas.append((encabezado.puntovta, encabezado.cbtenro, caea))
        self.cae = encabezado.cae
        # Como el comprobante entra con cbtenro 00000000, un numero distinto
        # prueba que el servicio pisa el campo con lo que devolvio ARCA y no
        # que se lo deja como estaba.
        self.comprobante = self.numero_otorgado
        self.resultado = "A"
        return True


class FESimulada:
    def __init__(self):
        self.sin_movimiento = []

    def InformarCAEASinMovimiento(self, ptovta, caea):
        self.sin_movimiento.append((ptovta, caea))


def _chequeo(nombre, condicion, detalle=""):
    marca = "OK  " if condicion else "FALLA"
    print("  [{}] {}{}".format(marca, nombre, (" -> " + detalle) if detalle else ""))
    return bool(condicion)


def _crear_comprobante(registro_caea):
    encabezado = Encabezado.create(
        nrelacion=NRELACION,
        fechacbte=date.today(),
        tipocbte="001",
        puntovta=PTOVTA,
        cbtenro="00000000",
        tipodoc="80",
        nrodoc="20263390777",
        imptotal=TOTAL,
        impneto=NETO,
        impiva=IVA_21,
        imptrib=0,
        impopex=0,
        imptotconc=0,
        cae=registro_caea.CAEA,
        vencecae=registro_caea.fchtopeinf,
        resultado="",
        motivoobs="",
        errcode="",
        errmsg="",
        transferido=False,
        empresa=1,
        concepto=1,
        errorprog="",
        listo=True,
        tipows="A",
        condicion_iva_receptor_id=1,
    )
    IVA.create(nrelacion=NRELACION, ivaid=5, baseimp=NETO, importe=IVA_21)
    return encabezado


def _limpiar():
    db = Encabezado._meta.database
    db.execute_sql("DELETE FROM iva WHERE nrelacion=%s", (NRELACION,))
    db.execute_sql(
        "DELETE FROM {} WHERE nrelacion=%s".format(Encabezado._meta.table_name),
        (NRELACION,),
    )


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Prueba el rendido por CAEA con ARCA simulado, en la base real."
    )
    hoy = date.today()
    periodo = hoy.strftime("%Y%m")
    orden = "1" if hoy.day <= 15 else "2"
    parser.add_argument("--periodo", default=periodo)
    parser.add_argument("--orden", default=orden)
    parser.add_argument("--ptovta", default=PTOVTA)
    parser.add_argument(
        "--dejar",
        action="store_true",
        help="No borra el comprobante simulado al terminar.",
    )
    args = parser.parse_args(argv)

    registro_caea = CAEA.select().where(
        CAEA.periodo == args.periodo,
        CAEA.orden == str(args.orden),
        CAEA.empresa == 1,
        CAEA.CAEA != "",
    ).first()
    if registro_caea is None:
        print("No hay CAEA para {} orden {}. Pedilo primero.".format(
            args.periodo, args.orden))
        return 1

    print("Periodo {} orden {} | CAEA {} | ptovta {}".format(
        args.periodo, args.orden, registro_caea.CAEA, args.ptovta))
    print()
    print("Se simula que ARCA responde Resultado=A. No se llama a AFIP.")
    print()

    _limpiar()
    encabezado = _crear_comprobante(registro_caea)
    ncontrol = encabezado.nrocontrol
    controlador = ControladorSimulado()
    fe = FESimulada()

    print("1) El servicio tiene que ver el comprobante en la cola")
    cola = contar_pendientes(
        args.periodo, str(args.orden), empresa_id=1, ptovta=args.ptovta
    )
    pendientes = cola[0]["pendientes"] if cola else 0
    _chequeo("la cola real ve 1 pendiente (no la bitacora)", pendientes == 1,
             "pendientes={}".format(pendientes))

    print()
    print("2) Primera corrida: ARCA responde A")
    resumen = rendir_ptovta(
        args.periodo,
        str(args.orden),
        args.ptovta,
        empresa_id=1,
        controlador_factory=lambda: controlador,
        fe_factory=lambda: fe,
    )
    _chequeo("ok == True", resumen["ok"] is True)
    _chequeo("1 informado, 0 errores",
             resumen["ok_count"] == 1 and resumen["error_count"] == 0,
             "ok={} err={}".format(resumen["ok_count"], resumen["error_count"]))

    fila = Encabezado.get_by_id(ncontrol)
    _chequeo("resultado == 'A'", fila.resultado == "A", repr(fila.resultado))
    _chequeo("cae conserva el CAEA (ARCA no devuelve CAE propio)",
             fila.cae == registro_caea.CAEA, fila.cae)
    _chequeo("cbtenro quedo en 8 digitos", len(fila.cbtenro) == 8, fila.cbtenro)
    _chequeo("cbtenro se pisa con el numero que devolvio ARCA",
             fila.cbtenro == "00000001", fila.cbtenro)
    _chequeo("vencecae cae al fchtopeinf del CAEA",
             str(fila.vencecae) == str(registro_caea.fchtopeinf),
             "{} vs {}".format(fila.vencecae, registro_caea.fchtopeinf))
    _chequeo("no quedo XML de error pegado", not (fila.errorprog or "").strip())

    fila_bitacora = _bitacora(args.periodo, str(args.orden), args.ptovta)
    if fila_bitacora is not None:
        _chequeo("bitacora en TERMINADO", fila_bitacora.estado == ESTADO_TERMINADO,
                 repr(fila_bitacora.estado))
        _chequeo("bitacora: total=1 ok=1 err=0",
                 fila_bitacora.comprobantes_total == 1
                 and fila_bitacora.comprobantes_ok == 1
                 and fila_bitacora.comprobantes_error == 0,
                 "{}/{}/{}".format(fila_bitacora.comprobantes_total,
                                   fila_bitacora.comprobantes_ok,
                                   fila_bitacora.comprobantes_error))

    print()
    print("3) Segunda corrida: no tiene que reenviar nada")
    resumen2 = rendir_ptovta(
        args.periodo,
        str(args.orden),
        args.ptovta,
        empresa_id=1,
        controlador_factory=lambda: controlador,
        fe_factory=lambda: fe,
    )
    _chequeo("no llamo de nuevo a ARCA", len(controlador.llamadas) == 1,
             "llamadas={}".format(len(controlador.llamadas)))
    _chequeo("marca ya_informado", resumen2.get("ya_informado") is True)
    _chequeo("no lo declaro sin movimiento", resumen2["sin_movimiento"] is False)

    print()
    print("4) La cola quedo vacia")
    cola2 = contar_pendientes(
        args.periodo, str(args.orden), empresa_id=1, ptovta=args.ptovta
    )
    _chequeo("0 pendientes", (cola2[0]["pendientes"] if cola2 else 0) == 0)

    if args.dejar:
        print()
        print("Dejado en la base: ncontrol={} nrelacion={}".format(ncontrol, NRELACION))
    else:
        _limpiar()
        for f in _bitacora_todas(args.periodo, str(args.orden)):
            f.delete_instance()
        print()
        print("Limpio el comprobante simulado y su bitacora.")

    return 0


def _bitacora(periodo, orden, ptovta):
    from modelos.CAEARendicion import CAEARendicion

    return CAEARendicion.select().where(
        CAEARendicion.periodo == periodo,
        CAEARendicion.orden == orden,
        CAEARendicion.ptovta == ptovta,
    ).first()


def _bitacora_todas(periodo, orden):
    from modelos.CAEARendicion import CAEARendicion

    return list(CAEARendicion.select().where(
        CAEARendicion.periodo == periodo,
        CAEARendicion.orden == orden,
    ))


if __name__ == "__main__":
    raise SystemExit(main())