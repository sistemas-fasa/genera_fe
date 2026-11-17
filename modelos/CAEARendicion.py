# coding=utf-8
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 3, or (at your option) any later
# version.
from datetime import datetime

import peewee

from modelos.ModeloBase import ModeloBase, BitBooleanField


# Estados de una fila de la bitacora. La misma convencion de una letra que usa
# la tabla CAEA ("" pendiente, 'P' procesado).
ESTADO_PENDIENTE = ''
ESTADO_EN_CURSO = 'C'
ESTADO_TERMINADO = 'T'
ESTADO_CON_ERRORES = 'E'


class CAEARendicion(ModeloBase):
    """Bitacora del rendido de CAEA: una fila por empresa, periodo, orden y ptovta.

    ARCA exige informar, dentro de los 8 dias corridos posteriores al cierre de
    la quincena, tanto los comprobantes como los puntos de venta que no
    tuvieron movimiento. El proceso es largo y se puede cortar a mitad; sin esta
    bitacora no hay forma de saber que quedo pendiente ni de no informar dos
    veces lo mismo.
    """

    id = peewee.AutoField()
    empresa_id = peewee.IntegerField(default=1)
    periodo = peewee.CharField(max_length=6, default='')
    orden = peewee.CharField(max_length=1, default='')
    ptovta = peewee.CharField(max_length=4, default='')
    caea = peewee.CharField(max_length=14, default='')
    estado = peewee.CharField(max_length=1, default=ESTADO_PENDIENTE)
    sin_movimiento = BitBooleanField(default=0)
    comprobantes_total = peewee.IntegerField(default=0)
    comprobantes_ok = peewee.IntegerField(default=0)
    comprobantes_error = peewee.IntegerField(default=0)
    fecha_inicio = peewee.DateTimeField(null=True)
    fecha_fin = peewee.DateTimeField(null=True)
    ultimo_error = peewee.TextField(null=True)

    class Meta:
        table_name = 'caea_rendicion'
        indexes = (
            (('empresa_id', 'periodo', 'orden', 'ptovta'), True),
        )

    @classmethod
    def asegurar_tabla(cls):
        cls._meta.database.create_tables([cls], safe=True)

    @classmethod
    def obtener(cls, empresa_id, periodo, orden, ptovta, crear=True):
        """Fila de la bitacora para esa clave, creandola si hace falta."""
        fila = cls.select().where(
            cls.empresa_id == empresa_id,
            cls.periodo == periodo,
            cls.orden == orden,
            cls.ptovta == ptovta,
        ).first()
        if fila is not None or not crear:
            return fila
        return cls.create(
            empresa_id=empresa_id,
            periodo=periodo,
            orden=orden,
            ptovta=ptovta,
        )

    @classmethod
    def listar(cls, empresa_id=None, periodo=None, orden=None):
        consulta = cls.select()
        if empresa_id is not None:
            consulta = consulta.where(cls.empresa_id == empresa_id)
        if periodo is not None:
            consulta = consulta.where(cls.periodo == periodo)
        if orden is not None:
            consulta = consulta.where(cls.orden == orden)
        return list(consulta.order_by(cls.periodo.desc(), cls.orden.desc(), cls.ptovta))