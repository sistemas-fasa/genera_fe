# coding=utf-8
import logging
from contextlib import contextmanager
from datetime import datetime

from controladores.CAEAProgramado import calcular_periodo_orden_actual
from modelos.CAEA import CAEA
from modelos.ImpreFiscalContingenciaFasa import ImpreFiscalContingenciaFasa
from modelos.ImpreFiscalFasa import ImpreFiscalFasa
from modelos.PtoVtaFasa import PtoVtaFasa


FALLBACK_PUNTOS_CAEA = {
    '0018': '0022',
    '0019': '0021',
    '0020': '0023',
}


@contextmanager
def _sin_transaccion():
    yield


def normalizar_ptovta(ptovta):
    texto = '' if ptovta is None else str(ptovta).strip()
    if texto.isdigit():
        return texto.zfill(4)
    return texto


def _buscar_ptovta(ptovta_model, **filtros):
    buscar = getattr(ptovta_model, 'buscar', None)
    if buscar:
        return buscar(**filtros)

    query = ptovta_model.select()
    condiciones = []
    if filtros.get('ptovta') is not None:
        condiciones.append(ptovta_model.ptovta == filtros['ptovta'])
    if filtros.get('empresa_id') is not None:
        condiciones.append(ptovta_model.empresa_id == filtros['empresa_id'])
    if filtros.get('ubicacion') is not None:
        condiciones.append(ptovta_model.ubicacion == filtros['ubicacion'])
    if filtros.get('tipo') is not None:
        condiciones.append(ptovta_model.tipo == filtros['tipo'])
    if condiciones:
        query = query.where(*condiciones)
    return query.first()


def _buscar_imprefiscal(imprefiscal_model, maquina, empresa_id):
    buscar = getattr(imprefiscal_model, 'buscar', None)
    if buscar:
        return buscar(maquina, empresa_id)
    return imprefiscal_model.select().where(
        imprefiscal_model.maquina == maquina,
        imprefiscal_model.empresa_id == empresa_id,
    ).first()


def _buscar_contingencia_activa(contingencia_model, maquina, empresa_id):
    buscar = getattr(contingencia_model, 'buscar_activa', None)
    if buscar:
        return buscar(maquina, empresa_id)
    return contingencia_model.select().where(
        contingencia_model.maquina == maquina,
        contingencia_model.empresa_id == empresa_id,
        contingencia_model.activa == True,
    ).first()


def _asegurar_tabla_contingencia(contingencia_model):
    asegurar = getattr(contingencia_model, 'asegurar_tabla', None)
    if asegurar:
        asegurar()


def _atomic(database, imprefiscal_model):
    if database is not None:
        return database.atomic()
    model_db = getattr(getattr(imprefiscal_model, '_meta', None), 'database', None)
    if model_db is not None:
        return model_db.atomic()
    return _sin_transaccion()


def _tipo(registro):
    return (getattr(registro, 'tipo', '') or '').strip().upper()


def _fecha_base(fecha=None):
    if fecha is None:
        return datetime.now().date()
    if isinstance(fecha, datetime):
        return fecha.date()
    return fecha


def _fecha_en_rango(fecha, desde, hasta):
    if not desde or not hasta:
        return True
    if isinstance(desde, datetime):
        desde = desde.date()
    if isinstance(hasta, datetime):
        hasta = hasta.date()
    return desde <= fecha <= hasta


def obtener_punto_caea_equivalente(ptovta_ws, empresa_id, ptovta_model=None):
    ptovta_model = ptovta_model or PtoVtaFasa
    ptovta_normalizado = normalizar_ptovta(ptovta_ws)
    actual = _buscar_ptovta(
        ptovta_model,
        ptovta=ptovta_normalizado,
        empresa_id=empresa_id,
    )
    if not actual:
        raise RuntimeError(
            "No se encontro punto de venta {} para empresa {}".format(
                ptovta_normalizado,
                empresa_id,
            )
        )
    if _tipo(actual) == 'A':
        return ptovta_normalizado

    ubicacion = (getattr(actual, 'ubicacion', '') or '').strip()
    if ubicacion:
        por_ubicacion = _buscar_ptovta(
            ptovta_model,
            empresa_id=empresa_id,
            ubicacion=ubicacion,
            tipo='A',
        )
        if por_ubicacion:
            return normalizar_ptovta(getattr(por_ubicacion, 'ptovta', ''))

    fallback = FALLBACK_PUNTOS_CAEA.get(ptovta_normalizado)
    if fallback:
        registro_fallback = _buscar_ptovta(
            ptovta_model,
            ptovta=fallback,
            empresa_id=empresa_id,
            tipo='A',
        )
        if registro_fallback:
            return fallback

    raise RuntimeError(
        "No se pudo resolver punto CAEA para {} empresa {}".format(
            ptovta_normalizado,
            empresa_id,
        )
    )


def hay_caea_vigente(empresa_id, fecha=None, caea_model=None):
    caea_model = caea_model or CAEA
    fecha = _fecha_base(fecha)
    periodo, orden = calcular_periodo_orden_actual(fecha)
    registro = caea_model.select().where(
        caea_model.periodo == periodo,
        caea_model.orden == orden,
        caea_model.empresa == empresa_id,
        caea_model.CAEA != '',
    ).first()
    if not registro:
        return False
    return _fecha_en_rango(
        fecha,
        getattr(registro, 'fchvigdesde', None),
        getattr(registro, 'fchvighasta', None),
    )


def activar_modo_caea(
        maquina,
        empresa_id,
        motivo='',
        imprefiscal_model=None,
        ptovta_model=None,
        contingencia_model=None,
        database=None,
        caea_existente=None):
    imprefiscal_model = imprefiscal_model or ImpreFiscalFasa
    ptovta_model = ptovta_model or PtoVtaFasa
    contingencia_model = contingencia_model or ImpreFiscalContingenciaFasa
    maquina = (maquina or '').strip()
    if not maquina:
        raise RuntimeError("No se pudo determinar la maquina para activar contingencia CAEA")

    caea_existente = caea_existente or hay_caea_vigente
    if not caea_existente(empresa_id):
        raise RuntimeError("No hay CAEA vigente para empresa {}. No se cambia imprefiscal.".format(empresa_id))

    _asegurar_tabla_contingencia(contingencia_model)
    activa = _buscar_contingencia_activa(contingencia_model, maquina, empresa_id)
    if activa:
        logging.info(
            "Contingencia CAEA ya activa para maquina %s empresa %s",
            maquina,
            empresa_id,
        )
        return activa

    imprefiscal = _buscar_imprefiscal(imprefiscal_model, maquina, empresa_id)
    if not imprefiscal:
        raise RuntimeError(
            "No se encontro imprefiscal para maquina {} empresa {}".format(
                maquina,
                empresa_id,
            )
        )

    ptovtafac_original = normalizar_ptovta(getattr(imprefiscal, 'ptovtafac', ''))
    ptovtaticket_original = normalizar_ptovta(getattr(imprefiscal, 'ptovtaticket', ''))
    ptovtafac_caea = obtener_punto_caea_equivalente(ptovtafac_original, empresa_id, ptovta_model)
    ptovtaticket_caea = obtener_punto_caea_equivalente(ptovtaticket_original, empresa_id, ptovta_model)

    with _atomic(database, imprefiscal_model):
        respaldo = contingencia_model.create(
            maquina=maquina,
            empresa_id=empresa_id,
            ptovtafac_original=ptovtafac_original,
            ptovtaticket_original=ptovtaticket_original,
            ptovtafac_caea=ptovtafac_caea,
            ptovtaticket_caea=ptovtaticket_caea,
            activa=True,
            fecha_activacion=datetime.now(),
            fecha_restauracion=None,
            motivo=motivo or '',
        )
        imprefiscal.ptovtafac = ptovtafac_caea
        imprefiscal.ptovtaticket = ptovtaticket_caea
        imprefiscal.save()

    logging.warning(
        "Contingencia CAEA activada para maquina %s empresa %s: fac %s->%s ticket %s->%s",
        maquina,
        empresa_id,
        ptovtafac_original,
        ptovtafac_caea,
        ptovtaticket_original,
        ptovtaticket_caea,
    )
    return respaldo


def restaurar_modo_ws(
        maquina,
        empresa_id,
        imprefiscal_model=None,
        contingencia_model=None,
        database=None):
    imprefiscal_model = imprefiscal_model or ImpreFiscalFasa
    contingencia_model = contingencia_model or ImpreFiscalContingenciaFasa
    maquina = (maquina or '').strip()
    _asegurar_tabla_contingencia(contingencia_model)
    activa = _buscar_contingencia_activa(contingencia_model, maquina, empresa_id)
    if not activa:
        return None

    imprefiscal = _buscar_imprefiscal(imprefiscal_model, maquina, empresa_id)
    if not imprefiscal:
        raise RuntimeError(
            "No se encontro imprefiscal para restaurar maquina {} empresa {}".format(
                maquina,
                empresa_id,
            )
        )

    with _atomic(database, imprefiscal_model):
        imprefiscal.ptovtafac = normalizar_ptovta(activa.ptovtafac_original)
        imprefiscal.ptovtaticket = normalizar_ptovta(activa.ptovtaticket_original)
        imprefiscal.save()
        activa.activa = False
        activa.fecha_restauracion = datetime.now()
        activa.save()

    logging.info(
        "Contingencia CAEA restaurada para maquina %s empresa %s: fac %s ticket %s",
        maquina,
        empresa_id,
        imprefiscal.ptovtafac,
        imprefiscal.ptovtaticket,
    )
    return activa


def contingencia_activa(maquina, empresa_id, contingencia_model=None):
    contingencia_model = contingencia_model or ImpreFiscalContingenciaFasa
    return _buscar_contingencia_activa(contingencia_model, (maquina or '').strip(), empresa_id) is not None
