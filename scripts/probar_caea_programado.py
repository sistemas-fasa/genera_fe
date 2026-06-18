# coding=utf-8
import argparse
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from controladores.CAEAProgramado import (  # noqa: E402
    calcular_periodo_orden_actual,
    corresponde_solicitar_caea,
    solicitar_caea_si_corresponde,
)


def _si_no(valor):
    return "si" if valor else "no"


def _fecha_arg(valor):
    try:
        return datetime.strptime(valor, "%Y-%m-%d").date()
    except ValueError:
        raise argparse.ArgumentTypeError("La fecha debe tener formato YYYY-MM-DD")


def _parser():
    parser = argparse.ArgumentParser(
        description="Prueba controlada del flujo CAEA programado con fecha simulada."
    )
    parser.add_argument("--empresa", type=int, required=True, help="ID de empresa a evaluar.")
    parser.add_argument("--fecha", type=_fecha_arg, required=True, help="Fecha simulada YYYY-MM-DD.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="No llama a AFIP, no escribe en base y no encola email.",
    )
    parser.add_argument(
        "--confirmar",
        action="store_true",
        help="Confirma una ejecucion real. Puede llamar a AFIP, guardar CAEA y encolar email.",
    )
    return parser


def _imprimir_plan(empresa, fecha, dry_run):
    periodo, orden = calcular_periodo_orden_actual(fecha)
    corresponde = corresponde_solicitar_caea(fecha)
    print("Dry-run: {}".format(_si_no(dry_run)))
    print("Empresa: {}".format(empresa))
    print("Fecha simulada: {}".format(fecha.isoformat()))
    print("Periodo: {}".format(periodo))
    print("Orden: {}".format(orden))
    print("Corresponde solicitar: {}".format(_si_no(corresponde)))
    print("Buscaria CAEA existente: {}".format(_si_no(corresponde)))
    print("Solicitaria AFIP si no existe CAEA: {}".format(_si_no(corresponde)))
    print("Enviaria email si registra CAEA nuevo: {}".format(_si_no(corresponde)))
    return corresponde


def main(argv=None):
    args = _parser().parse_args(argv)

    if not args.dry_run and not args.confirmar:
        print(
            "Ejecucion real bloqueada: puede llamar a AFIP real, escribir en base y encolar email. "
            "Use --confirmar para continuar o --dry-run para solo simular.",
            file=sys.stderr,
        )
        return 2

    corresponde = _imprimir_plan(args.empresa, args.fecha, args.dry_run)

    if args.dry_run:
        print("No se llamo a AFIP, no se escribio en base y no se envio email.")
        return 0

    if not corresponde:
        print("Fuera de ventana CAEA: no se ejecuta solicitud real.")
        return 0

    registro = solicitar_caea_si_corresponde(empresa_id=args.empresa, fecha=args.fecha)
    if registro is None:
        print("No se solicito CAEA: ya existe localmente o la fecha no corresponde.")
        return 0

    print("CAEA registrado: {}".format(getattr(registro, "CAEA", "")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
