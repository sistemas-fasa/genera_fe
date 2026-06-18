# coding=utf-8
from datetime import datetime

import peewee

from modelos.ModeloBase import ModeloBaseFASA, BitBooleanField


class ImpreFiscalContingenciaFasa(ModeloBaseFASA):
    id = peewee.AutoField()
    maquina = peewee.CharField(max_length=30)
    empresa_id = peewee.IntegerField()
    ptovtafac_original = peewee.CharField(max_length=4)
    ptovtaticket_original = peewee.CharField(max_length=4)
    ptovtafac_caea = peewee.CharField(max_length=4)
    ptovtaticket_caea = peewee.CharField(max_length=4)
    activa = BitBooleanField(default=1)
    fecha_activacion = peewee.DateTimeField(default=datetime.now)
    fecha_restauracion = peewee.DateTimeField(null=True)
    motivo = peewee.CharField(max_length=250, default='')

    @classmethod
    def asegurar_tabla(cls):
        cls._meta.database.create_tables([cls], safe=True)

    @classmethod
    def buscar_activa(cls, maquina, empresa_id):
        return cls.select().where(
            cls.maquina == maquina,
            cls.empresa_id == empresa_id,
            cls.activa == True,
        ).first()

    class Meta:
        table_name = 'imprefiscal_contingencia'
        indexes = (
            (('maquina', 'empresa_id', 'activa'), False),
        )
