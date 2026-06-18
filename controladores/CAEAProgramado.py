# coding=utf-8
import calendar
import html
import logging
import os
from datetime import date, datetime

from dotenv import load_dotenv


CAEA_NOTIFICACION_EMAIL_DEFAULT = "sistemas@ferreteriaavenida.com.ar"

load_dotenv()


def _fecha_base(fecha=None):
    if fecha is None:
        return date.today()
    if isinstance(fecha, datetime):
        return fecha.date()
    return fecha


def calcular_periodo_orden_actual(fecha=None):
    """
    Devuelve (periodo, orden).
    periodo: YYYYMM
    orden: '1' o '2'
    """
    fecha = _fecha_base(fecha)
    periodo = "{:04d}{:02d}".format(fecha.year, fecha.month)
    orden = "1" if fecha.day <= 15 else "2"
    return periodo, orden


def corresponde_solicitar_caea(fecha=None):
    """
    Devuelve True si corresponde intentar solicitud automatica:
    - dias 10 al 15 inclusive para orden 1;
    - ultimos 5 dias del mes hasta fin de mes inclusive para orden 2.
    """
    fecha = _fecha_base(fecha)
    ultimo_dia = calendar.monthrange(fecha.year, fecha.month)[1]
    inicio_segunda_ventana = ultimo_dia - 5
    return 10 <= fecha.day <= 15 or inicio_segunda_ventana <= fecha.day <= ultimo_dia


def _caea_model_default():
    from modelos.CAEA import CAEA

    return CAEA


def _fe_factory_default():
    from controladores.FE import FEv1

    return FEv1


def _encolar_email_default(*args, **kwargs):
    from controladores.EnvioEmailsPendientes import encolar_email

    return encolar_email(*args, **kwargs)


def caea_ya_existe(periodo, orden, empresa_id, caea_model=None):
    """
    True si ya existe CAEA no vacio para periodo/orden/empresa.
    No usa ptovta como parte de la clave.
    """
    caea_model = caea_model or _caea_model_default()
    return caea_model.select().where(
        caea_model.periodo == periodo,
        caea_model.orden == orden,
        caea_model.empresa == empresa_id,
        caea_model.CAEA != "",
    ).first() is not None


def obtener_ptovta_referencia_caea(empresa_id):
    """
    Devuelve un ptovta de referencia para guardar en la tabla local.
    El repo no tiene modelo de puntos de venta; se conserva compatibilidad local
    guardando vacio sin disparar solicitudes por punto de venta.
    """
    return ""


def _texto(valor):
    if valor is None:
        return ""
    return str(valor)


def _html_escape(valor):
    return html.escape(_texto(valor), quote=True)


def _formato_fecha(valor):
    if not valor:
        return ""
    try:
        return valor.strftime("%d/%m/%Y")
    except AttributeError:
        return _texto(valor)


def _formato_fecha_hora(valor):
    if not valor:
        return ""
    try:
        return valor.strftime("%d/%m/%Y %H:%M:%S")
    except AttributeError:
        return _texto(valor)


def _fila_html(etiqueta, valor, destacado=False):
    valor_html = _html_escape(valor)
    estilo_valor = "font-weight:bold;"
    if destacado:
        estilo_valor += " font-size:18px;"
    return """
          <tr>
            <td style="padding:10px; border-bottom:1px solid #e5e7eb; color:#6b7280;">{}</td>
            <td style="padding:10px; border-bottom:1px solid #e5e7eb; {}">{}</td>
          </tr>""".format(
        _html_escape(etiqueta),
        estilo_valor,
        valor_html,
    )


def _destinatario_notificacion_caea():
    return (os.getenv("CAEA_NOTIFICACION_EMAIL") or CAEA_NOTIFICACION_EMAIL_DEFAULT).strip()


def enviar_notificacion_caea_obtenido(caea_registro, encolador=None):
    periodo = _texto(getattr(caea_registro, "periodo", ""))
    orden = _texto(getattr(caea_registro, "orden", ""))
    empresa = _texto(getattr(caea_registro, "empresa_id", "") or getattr(caea_registro, "empresa", ""))
    registrado_en = getattr(caea_registro, "registrado_en", None) or datetime.now()
    obs = _texto(getattr(caea_registro, "obs", ""))
    quincena = "Primera quincena" if orden == "1" else "Segunda quincena"

    filas = [
        _fila_html("Empresa", empresa),
        _fila_html("Periodo", periodo),
        _fila_html("Orden / quincena", "{} - {}".format(orden, quincena)),
        _fila_html("Numero de CAEA", getattr(caea_registro, "CAEA", ""), destacado=True),
        _fila_html("Vigencia desde", _formato_fecha(getattr(caea_registro, "fchvigdesde", ""))),
        _fila_html("Vigencia hasta", _formato_fecha(getattr(caea_registro, "fchvighasta", ""))),
        _fila_html("Fecha tope informe", _formato_fecha(getattr(caea_registro, "fchtopeinf", ""))),
        _fila_html("Proceso AFIP", _formato_fecha_hora(getattr(caea_registro, "fchproceso", ""))),
        _fila_html("Registrado localmente", _formato_fecha_hora(registrado_en)),
    ]
    if obs:
        filas.append(_fila_html("Observaciones", obs))

    cuerpo_html = """<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>CAEA obtenido</title>
</head>
<body style="margin:0; padding:0; background:#f3f4f6; font-family:Arial, Helvetica, sans-serif; color:#111827;">
  <div style="max-width:680px; margin:0 auto; padding:24px;">
    <div style="background:#ffffff; border-radius:14px; overflow:hidden; border:1px solid #e5e7eb;">
      <div style="background:#e30613; color:#ffffff; padding:20px 24px;">
        <h1 style="margin:0; font-size:22px;">CAEA obtenido correctamente</h1>
        <p style="margin:6px 0 0; font-size:14px;">Sistema de Facturacion Electronica FASA</p>
      </div>
      <div style="padding:24px;">
        <p style="font-size:15px; margin-top:0;">
          Se obtuvo y registro correctamente un CAEA para el periodo/quincena correspondiente.
        </p>
        <table style="width:100%; border-collapse:collapse; font-size:14px;">
{}
        </table>
        <p style="margin-top:20px; font-size:13px; color:#6b7280;">
          Esta es una notificacion automatica del sistema de Facturacion Electronica FASA. No responder este correo.
        </p>
      </div>
    </div>
  </div>
</body>
</html>""".format(
        "".join(filas)
    )

    asunto = "CAEA obtenido - Periodo {} Orden {}".format(periodo, orden)
    encolador = encolador or _encolar_email_default
    return encolador(
        destinatario=_destinatario_notificacion_caea(),
        asunto=asunto,
        cuerpo_html=cuerpo_html,
        cuerpo_texto=(
            "CAEA obtenido correctamente\n"
            "Empresa: {}\nPeriodo: {}\nOrden: {}\nCAEA: {}\n"
            "Vigencia desde: {}\nVigencia hasta: {}\nTope informe: {}\nProceso AFIP: {}\nRegistrado: {}"
        ).format(
            empresa,
            periodo,
            orden,
            _texto(getattr(caea_registro, "CAEA", "")),
            _formato_fecha(getattr(caea_registro, "fchvigdesde", "")),
            _formato_fecha(getattr(caea_registro, "fchvighasta", "")),
            _formato_fecha(getattr(caea_registro, "fchtopeinf", "")),
            _formato_fecha_hora(getattr(caea_registro, "fchproceso", "")),
            _formato_fecha_hora(registrado_en),
        ),
    )


def solicitar_caea_si_corresponde(
        empresa_id=1,
        fecha=None,
        caea_model=None,
        fe_factory=None,
        notificador=None,
        ptovta_resolver=obtener_ptovta_referencia_caea):
    """
    Punto de entrada idempotente.
    Si no corresponde por fecha, no hace nada.
    Si ya existe CAEA para periodo/orden/empresa, no llama a AFIP.
    Si falta, llama una sola vez a AFIP, guarda un solo registro y envia email.
    """
    if not corresponde_solicitar_caea(fecha):
        return None

    caea_model = caea_model or _caea_model_default()
    fe_factory = fe_factory or _fe_factory_default()
    notificador = notificador or enviar_notificacion_caea_obtenido
    periodo, orden = calcular_periodo_orden_actual(fecha)
    if caea_ya_existe(periodo, orden, empresa_id, caea_model=caea_model):
        return None

    wsfe = fe_factory()
    wsfe.SolicitarCAEA(periodo, orden)
    if not getattr(wsfe, "CAEA", ""):
        raise RuntimeError("AFIP no devolvio CAEA para periodo/orden")

    registrado_en = datetime.now()
    caea_registro = caea_model.create(
        CAEA=wsfe.CAEA,
        periodo=getattr(wsfe, "Periodo", None) or periodo,
        orden=getattr(wsfe, "Orden", None) or orden,
        fchvigdesde=getattr(wsfe, "FchVigDesde", None),
        fchvighasta=getattr(wsfe, "FchVigHasta", None),
        fchtopeinf=getattr(wsfe, "FchTopeInf", None),
        fchproceso=getattr(wsfe, "FchProceso", None),
        obs=getattr(wsfe, "Obs", "") or "",
        empresa=empresa_id,
        ptovta=ptovta_resolver(empresa_id) or "",
    )
    caea_registro.registrado_en = registrado_en

    try:
        notificador(caea_registro)
    except Exception:
        logging.exception("No se pudo encolar notificacion de CAEA obtenido")

    return caea_registro
