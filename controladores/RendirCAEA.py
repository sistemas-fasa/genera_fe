# coding=utf-8
"""Rendido de CAEA sin interfaz.

Reemplaza el flujo manual de informacaea.py: en vez de que alguien tipee
periodo, orden y punto de venta en una ventana PyQt, el servicio recorre solo
todos los puntos de venta habilitados para CAEA y deja bitacora de que hizo.

ARCA exige informar, dentro de los 8 dias corridos posteriores al cierre de la
quincena, tanto los comprobantes emitidos como los puntos de venta que no
tuvieron movimiento. El proceso es largo y se puede cortar a mitad, asi que
todo lo que hace queda registrado en caea_rendicion y se puede retomar.

Los modelos y las fabricas se inyectan para que el servicio se pueda probar sin
AFIP, sin base y sin PyQt.
"""
import logging
import os
from datetime import datetime

from libs.Utiles import DeCodifica


ESTADO_PENDIENTE = ""
ESTADO_EN_CURSO = "C"
ESTADO_TERMINADO = "T"
ESTADO_CON_ERRORES = "E"


def _caea_model():
    from modelos.CAEA import CAEA

    return CAEA


def _rendicion_model():
    from modelos.CAEARendicion import CAEARendicion

    return CAEARendicion


def _ptovta_model():
    from modelos.PtoVtaFasa import PtoVtaFasa

    return PtoVtaFasa


def _encabezado_model():
    from modelos.Encabezado import Encabezado

    return Encabezado


def _fe_factory():
    from controladores.FE import FEv1

    return FEv1


def _controlador_factory():
    # Import perezoso: solo hace falta si hay comprobantes que informar, y
    # arrastra PyQt.
    from controladores.Main import MainController

    return MainController()


def _encolar_email_default(destinatario, asunto, cuerpo_texto):
    from controladores.EnvioEmailsPendientes import encolar_email

    return encolar_email(
        destinatario=destinatario,
        asunto=asunto,
        cuerpo_texto=cuerpo_texto,
    )


def _destinatario_default():
    return (
        os.getenv("CAEA_NOTIFICACION_EMAIL") or "sistemas@ferreteriaavenida.com.ar"
    ).strip()


def normalizar_ptovta(ptovta):
    texto = "" if ptovta is None else str(ptovta).strip()
    if texto.isdigit():
        return texto.zfill(4)
    return texto


def obtener_caea(periodo, orden, empresa_id=1, caea_model=None):
    """CAEA no vacio para esa quincena, o None."""
    caea_model = caea_model or _caea_model()
    return (
        caea_model.select()
        .where(
            caea_model.periodo == periodo,
            caea_model.orden == str(orden),
            caea_model.empresa == empresa_id,
            caea_model.CAEA != "",
        )
        .first()
    )


def listar_ptovta_caea(empresa_id=1, ptovta_model=None):
    """Puntos de venta habilitados para emitir con CAEA.

    Son los de tipo 'A': los que corresponden al Controlador Fiscal no pueden
    llevar CAEA.
    """
    ptovta_model = ptovta_model or _ptovta_model()
    consulta = ptovta_model.select().where(ptovta_model.tipo == "A")
    if empresa_id is not None and hasattr(ptovta_model, "empresa_id"):
        consulta = consulta.where(ptovta_model.empresa_id == empresa_id)
    return [normalizar_ptovta(getattr(fila, "ptovta", "")) for fila in consulta]


def _marcar_terminado(fila, total, ok, errores, ultimo_error, ahora):
    fila.comprobantes_total = total
    fila.comprobantes_ok = ok
    fila.comprobantes_error = errores
    fila.estado = ESTADO_CON_ERRORES if errores else ESTADO_TERMINADO
    fila.fecha_fin = ahora
    if ultimo_error:
        fila.ultimo_error = ultimo_error[:2000]
    fila.save()
    return fila


def rendir_ptovta(
    periodo,
    orden,
    ptovta,
    empresa_id=1,
    caea_model=None,
    rendicion_model=None,
    encabezado_model=None,
    fe_factory=None,
    controlador_factory=None,
    controlador=None,
):
    """Informa un punto de venta. Devuelve el resumen de esa fila.

    Si se pasa un controlador ya construido se reutiliza: MainController crea
    una MainView al instanciarse, asi que la pantalla informacaea.py no puede
    dejar que el servicio arme el suyo propio.
    """
    caea_model = caea_model or _caea_model()
    rendicion_model = rendicion_model or _rendicion_model()
    encabezado_model = encabezado_model or _encabezado_model()
    fe_factory = fe_factory or _fe_factory
    ptovta = normalizar_ptovta(ptovta)
    ahora = datetime.now()

    registro_caea = obtener_caea(periodo, orden, empresa_id, caea_model=caea_model)
    if registro_caea is None:
        return {
            "ptovta": ptovta,
            "ok": False,
            "motivo": "No hay CAEA para periodo {} orden {}".format(periodo, orden),
            "total": 0,
            "ok_count": 0,
            "error_count": 0,
            "sin_movimiento": False,
        }

    caea = registro_caea.CAEA
    fila = rendicion_model.obtener(empresa_id, periodo, str(orden), ptovta)
    fila.caea = caea
    fila.estado = ESTADO_EN_CURSO
    fila.fecha_inicio = ahora
    fila.save()

    # Solo los que siguen sin resultado. El comprobante conserva el CAEA en el
    # campo cae (en el regimen CAEA no hay un CAE por comprobante), asi que sin
    # este filtro la consulta matchearia tambien los ya informados y los volveria
    # a mandar a ARCA.
    encabezados = encabezado_model.select().where(
        encabezado_model.puntovta == ptovta,
        encabezado_model.tipows == "A",
        encabezado_model.cae == caea,
        encabezado_model.resultado == "",
    )
    total = encabezados.count()
    errores = 0
    ultimo_error = ""

    if total == 0:
        if fila.comprobantes_ok or fila.comprobantes_error:
            # Este ptovta ya informo comprobantes con este CAEA y ahora no
            # queda ninguno pendiente. Declarar "sin movimiento" aca seria
            # falso, y ARCA lo rechaza.
            fila.estado = ESTADO_TERMINADO
            fila.fecha_fin = datetime.now()
            fila.save()
            return {
                "ptovta": ptovta,
                "ok": True,
                "motivo": "",
                "total": fila.comprobantes_total,
                "ok_count": fila.comprobantes_ok,
                "error_count": fila.comprobantes_error,
                "sin_movimiento": False,
                "ya_informado": True,
            }

        # Punto de venta habilitado que no emitio nada: hay que informarlo
        # igual, porque ARCA exige declarar los que no tuvieron movimiento.
        try:
            fe_factory().InformarCAEASinMovimiento(ptovta, caea)
            fila.sin_movimiento = True
            fila.save()
        except Exception:
            logging.exception(
                "No se pudo informar el CAEA sin movimiento de %s", ptovta
            )
            errores += 1
            ultimo_error = "sin movimiento: {}".format(ptovta)
            _marcar_terminado(fila, 0, 0, errores, ultimo_error, datetime.now())
            return {
                "ptovta": ptovta,
                "ok": False,
                "motivo": ultimo_error,
                "total": 0,
                "ok_count": 0,
                "error_count": errores,
                "sin_movimiento": False,
            }
        _marcar_terminado(fila, 0, 0, 0, "", datetime.now())
        return {
            "ptovta": ptovta,
            "ok": True,
            "motivo": "",
            "total": 0,
            "ok_count": 0,
            "error_count": 0,
            "sin_movimiento": True,
        }

    controlador = controlador
    for encabezado in encabezados:
        try:
            if controlador is None:
                controlador = (controlador_factory or _controlador_factory)()
            ok = controlador.CreaFE(encabezado, caea=True)
            if ok:
                # En el regimen CAEA ARCA no devuelve un CAE propio: devuelve el
                # CAEA validado. Lo que marca el resultado del comprobante es el
                # Resultado que respondio AFIP.
                encabezado.cae = controlador.cae
                encabezado.resultado = controlador.resultado
                encabezado.cbtenro = str(controlador.comprobante).zfill(8)
                # AFIP no define vencimiento para CAEA: se usa la fecha tope de
                # informe del propio CAEA.
                encabezado.vencecae = (
                    datetime.strptime(controlador.vencecae, "%Y%m%d")
                    if controlador.vencecae
                    else registro_caea.fchtopeinf
                )
            else:
                encabezado.resultado = controlador.resultado or "E"
                encabezado.errmsg = controlador.errmsg
                encabezado.motivoobs = controlador.motivoobs
                encabezado.vencecae = datetime.today()
                # El CAEA se deja puesto: era valido, lo que no valido fue el
                # comprobante.
                encabezado.errorprog = (
                    "XML_REQUEST:\n{}\n\nXML_RESPONSE:\n{}".format(
                        getattr(controlador, "xml_request", "") or "",
                        getattr(controlador, "xml_response", "") or "",
                    )
                )
                errores += 1
                ultimo_error = (
                    "{pv} {nro}: {err}\nXML_REQUEST:\n{req}\n\nXML_RESPONSE:\n{res}".format(
                        pv=encabezado.puntovta,
                        nro=encabezado.cbtenro,
                        err=DeCodifica(
                            controlador.errmsg or controlador.motivoobs or ""
                        ),
                        req=DeCodifica(getattr(controlador, "xml_request", "") or ""),
                        res=DeCodifica(getattr(controlador, "xml_response", "") or ""),
                    )
                )
            encabezado.save()
        except Exception as exc:
            # Un comprobante que falla no puede abortar el resto del ptovta.
            errores += 1
            ultimo_error = "{} {}".format(encabezado.puntovta, exc)
            logging.exception("No se pudo informar el comprobante con CAEA")

    ok_count = total - errores
    _marcar_terminado(fila, total, ok_count, errores, ultimo_error, datetime.now())
    return {
        "ptovta": ptovta,
        "ok": errores == 0,
        "motivo": ultimo_error,
        "total": total,
        "ok_count": ok_count,
        "error_count": errores,
        "sin_movimiento": False,
    }


def resumir(periodo, orden, empresa_id=1, solo_pendientes=True, rendicion_model=None):
    """Estado del rendido de esa quincena, ptovta por ptovta."""
    rendicion_model = rendicion_model or _rendicion_model()
    filas = rendicion_model.listar(
        empresa_id=empresa_id, periodo=periodo, orden=str(orden)
    )
    if solo_pendientes:
        filas = [f for f in filas if f.estado != ESTADO_TERMINADO]
    return filas


def rendir(
    periodo,
    orden,
    empresa_id=1,
    ptovta=None,
    solo_pendientes=True,
    caea_model=None,
    rendicion_model=None,
    ptovta_model=None,
    encabezado_model=None,
    fe_factory=None,
    controlador_factory=None,
    controlador=None,
    notificador=None,
    avisar=True,
):
    """Rinde la quincena. Devuelve un resumen con el detalle por ptovta.

    Con ptovta=None recorre todos los puntos de venta habilitados para CAEA.
    Es idempotente: las filas de la bitacora que ya quedaron terminadas no se
    vuelven a procesar.
    """
    caea_model = caea_model or _caea_model()
    rendicion_model = rendicion_model or _rendicion_model()
    ptovta_model = ptovta_model or _ptovta_model()

    if ptovta:
        puntos = [normalizar_ptovta(ptovta)]
    else:
        puntos = listar_ptovta_caea(empresa_id, ptovta_model=ptovta_model)

    if not puntos:
        return {
            "periodo": periodo,
            "orden": str(orden),
            "ok": False,
            "detalle": [],
            "mensaje": "No hay puntos de venta habilitados para CAEA",
            "omitidos": [],
        }

    omitidos = []
    detalle = []
    for punto in puntos:
        fila = rendicion_model.obtener(
            empresa_id, periodo, str(orden), punto, crear=True
        )
        if solo_pendientes and fila.estado == ESTADO_TERMINADO:
            omitidos.append(punto)
            continue
        detalle.append(
            rendir_ptovta(
                periodo,
                orden,
                punto,
                empresa_id=empresa_id,
                caea_model=caea_model,
                rendicion_model=rendicion_model,
                encabezado_model=encabezado_model,
                fe_factory=fe_factory,
                controlador_factory=controlador_factory,
                controlador=controlador,
            )
        )

    resumen = {
        "periodo": periodo,
        "orden": str(orden),
        "ok": all(d["ok"] for d in detalle) if detalle else True,
        "detalle": detalle,
        "omitidos": omitidos,
        "mensaje": _mensaje_resumen(detalle, omitidos),
    }

    if avisar:
        enviar_resumen(resumen, notificador=notificador)
    return resumen


def _mensaje_resumen(detalle, omitidos):
    if not detalle:
        return "Nada pendiente para informar."
    lineas = []
    for item in detalle:
        if item["ok"] and item["sin_movimiento"]:
            lineas.append("  {}: sin movimiento, informado.".format(item["ptovta"]))
        elif item["ok"]:
            lineas.append(
                "  {}: {} comprobante(s) informado(s).".format(
                    item["ptovta"], item["ok_count"]
                )
            )
        else:
            lineas.append(
                "  {}: {} error(es). {}".format(
                    item["ptovta"], item["error_count"], item["motivo"]
                )
            )
    if omitidos:
        lineas.append("  ya terminados: {}".format(", ".join(omitidos)))
    return "\n".join(lineas)


def enviar_resumen(resumen, destinatario=None, notificador=None):
    encolar = notificador or _encolar_email_default
    destinatario = destinatario or _destinatario_default()
    if not destinatario:
        logging.warning("No se aviso el resumen de CAEA: falta destinatario")
        return False
    cuerpo = "Periodo {p} orden {o}\n\n{m}".format(
        p=resumen["periodo"], o=resumen["orden"], m=resumen["mensaje"]
    )
    estado = "OK" if resumen["ok"] else "con errores"
    return encolar(
        destinatario=destinatario,
        asunto="Rendido de CAEA {} {} - {}".format(
            resumen["periodo"], resumen["orden"], estado
        ),
        cuerpo_texto=cuerpo,
    )