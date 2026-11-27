"""Consulta un CAEA en la base local y en WSFE usando un ticket existente."""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from controladores.CAEAProgramado import _fe_factory_default, caea_ya_existe


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--empresa", required=True, type=int)
    parser.add_argument("--periodo", required=True)
    parser.add_argument("--orden", required=True, choices=("1", "2"))
    parser.add_argument("--ticket", type=Path, help="Ruta a un ticket vigente copiado.")
    parser.add_argument("--solicitar", action="store_true", help="Pide el CAEA en producción si WSFE responde 602.")
    args = parser.parse_args()
    if len(args.periodo) != 6 or not args.periodo.isascii() or not args.periodo.isdigit():
        parser.error("El período debe tener formato YYYYMM.")
    if not 1 <= int(args.periodo[4:]) <= 12:
        parser.error("El mes del período debe estar entre 01 y 12.")

    from libs.Utiles import LeerIni, LeerTimeoutAFIP, ubicacion_sistema

    if LeerIni(clave="homo") != "N":
        parser.error("Ejecutar desde la carpeta de Genera FE configurada para producción.")

    ticket_path = args.ticket or Path(ubicacion_sistema()) / f"wsfe-{args.empresa}-ta.xml"
    try:
        ticket = ticket_path.read_text(encoding="utf-8")
        vencimiento = datetime.fromisoformat(ElementTree.fromstring(ticket).findtext(
            "./header/expirationTime", default=""
        ))
        if vencimiento.tzinfo is None or vencimiento <= datetime.now().astimezone():
            parser.error("El ticket de acceso existente no está vigente.")
    except (OSError, ValueError, ElementTree.ParseError):
        parser.error("No se pudo leer un ticket de acceso válido para esa empresa.")

    wsfe = _fe_factory_default(args.empresa)
    existe_local = caea_ya_existe(args.periodo, args.orden, args.empresa)
    print(f"Empresa {args.empresa} | CUIT final {wsfe.cuit_emisor[-4:]} | {args.periodo} orden {args.orden}")
    print(f"CAEA en base local: {'sí' if existe_local else 'no'}")
    if not wsfe.Conectar("", wsdl=wsfe.WSDL, cacert=True, timeout=LeerTimeoutAFIP()):
        print("No se pudo conectar con WSFE.", file=sys.stderr)
        return 2
    wsfe.SetTicketAcceso(ta_string=ticket)
    wsfe.Cuit = wsfe.cuit_emisor
    if wsfe.CAEAConsultar(args.periodo, args.orden):
        print("WSFE: CAEA encontrado.")
        return 0
    print(f"WSFE: CAEA no recuperado. Código: {wsfe.ErrCode or 'sin código'}. {wsfe.ErrMsg or ''}")
    if args.solicitar and not existe_local and wsfe.ErrCode == "602":
        from controladores.FE import _fecha_respuesta_wsfe

        hora = datetime.now().astimezone().isoformat()
        caea = wsfe.CAEASolicitar(args.periodo, args.orden)
        print(f"Hora de solicitud: {hora} | fecha WSFE: {_fecha_respuesta_wsfe(wsfe.XmlResponse)}")
        if caea:
            print("WSFE: CAEA emitido. Pendiente de registrar en la base local.")
            return 0
        print(f"WSFE: solicitud sin CAEA. Código: {wsfe.ErrCode or 'sin código'}. {wsfe.ErrMsg or ''}")
        if wsfe.CAEAConsultar(args.periodo, args.orden):
            print("WSFE: CAEA encontrado en la consulta posterior. Pendiente de registrar en la base local.")
            return 0
        print(f"Consulta posterior: código {wsfe.ErrCode or 'sin código'}. {wsfe.ErrMsg or ''}")
        return 2
    return 1 if wsfe.ErrCode == "602" else 2


if __name__ == "__main__":
    sys.exit(main())
