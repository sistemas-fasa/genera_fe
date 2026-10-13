# coding=utf-8
"""Rinde una quincena de CAEA desde linea de comandos.

Recorre solo los puntos de venta habilitados para CAEA, deja bitacora en
caea_rendicion y avisa por correo. Reemplaza tener que completar a mano la
pantalla de informacaea.py.

    python .\rendir_caea.py --periodo 202606 --orden 1 --dry-run
    python .\rendir_caea.py --periodo 202606 --orden 1 --confirmar
"""
import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from controladores.CAEAProgramado import calcular_periodo_orden_actual  # noqa: E402
from controladores.RendirCAEA import (  # noqa: E402
    ESTADO_TERMINADO,
    contar_pendientes,
    listar_ptovta_caea,
    obtener_caea,
    rendir,
    resumir,
)

COMANDO_MIGRACION = r"python .\migrations\ensure_caea_rendicion_schema.py"


def _periodo_arg(valor):
    valor = str(valor).strip()
    if len(valor) != 6 or not valor.isdigit():
        raise argparse.ArgumentTypeError("El periodo debe tener formato YYYYMM")
    return valor


def _orden_arg(valor):
    valor = str(valor).strip()
    if valor not in ("1", "2"):
        raise argparse.ArgumentTypeError("El orden debe ser 1 o 2")
    return valor


def _parser():
    parser = argparse.ArgumentParser(
        description="Rinde el CAEA de una quincena sin intervencion manual."
    )
    parser.add_argument(
        "--periodo",
        type=_periodo_arg,
        help="Periodo YYYYMM. Si se omite usa el de hoy.",
    )
    parser.add_argument(
        "--orden",
        type=_orden_arg,
        help="Quincena 1 o 2. Si se omite usa la que corresponde a hoy.",
    )
    parser.add_argument("--empresa", type=int, default=1, help="ID de empresa.")
    parser.add_argument(
        "--ptovta", help="Informa solo ese punto de venta, en vez de todos."
    )
    parser.add_argument(
        "--todos",
        action="store_true",
        help="Vuelve a procesar tambien los ptovta que ya quedaron terminados.",
    )
    parser.add_argument(
        "--estado",
        action="store_true",
        help="Solo muestra el estado del rendido y sale.",
    )
    parser.add_argument(
        "--sin-aviso",
        action="store_true",
        help="No encola el email de resumen.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="No llama a AFIP, no escribe en base y no encola email.",
    )
    parser.add_argument(
        "--confirmar",
        action="store_true",
        help="Confirma una ejecucion real. Puede llamar a AFIP y escribir en base.",
    )
    return parser


def _periodo_y_orden(args):
    if args.periodo and args.orden:
        return args.periodo, args.orden
    if args.periodo and not args.orden:
        raise SystemExit("Falta --orden para el periodo {}".format(args.periodo))
    if args.orden and not args.periodo:
        raise SystemExit("Falta --periodo para el orden {}".format(args.orden))

    from datetime import date

    periodo, orden = calcular_periodo_orden_actual(date.today())
    return args.periodo or periodo, args.orden or orden


def _tabla_faltante(exc):
    """Devuelve el nombre de la tabla faltante, o None si el error es otro.

    MySQL responde 1146 cuando la tabla todavia no existe. Sin esto el CLI
    tiraba un traceback de peewee y no decia que faltaba correr la migracion.
    """
    texto = str(exc)
    if "1146" not in texto and "doesn't exist" not in texto:
        return None
    for tabla in ("caea_rendicion", "caea"):
        if tabla in texto:
            return tabla
    return "desconocida"


def _avisar_tabla_faltante(tabla):
    if tabla == "caea_rendicion":
        print(
            "Falta la tabla caea_rendicion en la base. Corre la migracion "
            "una vez y volve a intentar:\n"
            "    {}".format(COMANDO_MIGRACION),
            file=sys.stderr,
        )
    else:
        print("Falta la tabla {} en la base.".format(tabla), file=sys.stderr)


def _imprimir_estado(periodo, orden, empresa):
    filas = resumir(periodo, orden, empresa_id=empresa, solo_pendientes=False)
    if not filas:
        print("Sin bitacora para {} orden {}. Nada rindido todavia.".format(periodo, orden))
        return
    print("{:>6} {:>5} {:>9} {:>6} {:>5} {:>5}".format(
        "ptovta", "caea", "estado", "total", "ok", "err"
    ))
    for fila in filas:
        print("{:>6} {:>5} {:>9} {:>6} {:>5} {:>5}".format(
            fila.ptovta,
            "si" if fila.sin_movimiento else "-",
            fila.estado or "-",
            fila.comprobantes_total,
            fila.comprobantes_ok,
            fila.comprobantes_error,
        ))


_qapp = None


def _controlador_factory():
    """MainController, que construye su MainView al instanciarse.

    Qt aborta el proceso si se crea un QWidget sin QApplication, asi que sin
    esto el CLI moria con SIGABRT apenasbiologyaba el primer comprobante
    pendiente. No se corre el event loop: los timers del controlador quedan
    inertes y el CLI no dispara el ciclo de procesamiento.
    """
    global _qapp
    from PyQt5.QtWidgets import QApplication

    if _qapp is None:
        _qapp = QApplication([])
    from controladores.Main import MainController

    return MainController()


def _imprimir_cola(periodo, orden, empresa):
    """La cola real que se va a informar, no la bitacora.

    La bitacora arranca vacia en cada quincena, asi que un dry-run de una
    quincena nueva no mostraba nada aunque tuviera cientos de pendientes.
    """
    filas = contar_pendientes(periodo, orden, empresa_id=empresa)
    if not filas:
        print("  (no hay CAEA para {} orden {})".format(periodo, orden))
        return
    total = sum(f["pendientes"] for f in filas)
    for f in filas:
        print("  {}: {} pendiente(s)".format(f["ptovta"], f["pendientes"]))
    print("  Total a informar: {}".format(total))


def main(argv=None):
    args = _parser().parse_args(argv)
    try:
        return _correr(args)
    except Exception as exc:  # noqa: BLE001 - se re-lanza si no es tabla faltante
        tabla = _tabla_faltante(exc)
        if tabla is None:
            raise
        _avisar_tabla_faltante(tabla)
        return 3


def _correr(args):
    periodo, orden = _periodo_y_orden(args)

    if args.estado:
        _imprimir_estado(periodo, orden, args.empresa)
        return 0

    if not args.dry_run and not args.confirmar:
        print(
            "Ejecucion real bloqueada: puede llamar a AFIP y escribir en base. "
            "Use --confirmar para continuar o --dry-run para solo simular.",
            file=sys.stderr,
        )
        return 2

    print("Periodo: {} orden {}".format(periodo, orden))
    print("Empresa: {}".format(args.empresa))

    caea = obtener_caea(periodo, orden, args.empresa)
    if caea is None:
        print("No hay CAEA registrado para {} orden {}.".format(periodo, orden))
        return 1
    print("CAEA: {}".format(caea.CAEA))

    if args.ptovta:
        puntos = [args.ptovta]
    else:
        puntos = listar_ptovta_caea(args.empresa)
    print("Puntos de venta: {}".format(", ".join(puntos) or "ninguno"))

    if args.dry_run:
        print()
        print("Dry-run. No se llamo a AFIP, no se escribio en base y no se envio email.")
        print()
        print("Comprobantes pendientes de informar:")
        _imprimir_cola(periodo, orden, args.empresa)
        print()
        print("Bitacora de rendidos anteriores:")
        filas = resumir(periodo, orden, args.empresa, solo_pendientes=False)
        if not filas:
            print("  (vacia: esta quincena todavia no se rindio)")
        for fila in filas:
            print(
                "  {} estado={} ok={} err={}".format(
                    fila.ptovta,
                    fila.estado or "-",
                    fila.comprobantes_ok,
                    fila.comprobantes_error,
                )
            )
        return 0

    resumen = rendir(
        periodo,
        orden,
        empresa_id=args.empresa,
        ptovta=args.ptovta,
        solo_pendientes=not args.todos,
        avisar=not args.sin_aviso,
        controlador_factory=_controlador_factory,
    )

    print()
    print(resumen["mensaje"])
    return 0 if resumen["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())