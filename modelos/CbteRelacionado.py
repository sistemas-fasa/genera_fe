# coding=utf-8

# comprobantes relacionados para las notas de credito
from peewee import AutoField, ForeignKeyField, CharField, IntegerField

from modelos.Encabezado import Encabezado
from modelos.ModeloBase import ModeloBase


class CbteRel(ModeloBase):

    idcbterel = AutoField()
    #nrocontrol = ForeignKeyField(Encabezado, column_name='nrocontrol')
    tipocbte = CharField(max_length=3, default='')
    ptovta = CharField(max_length=4, default='')
    nrocbte = CharField(max_length=8, default='')
    #nrelacion = IntegerField(default=0)
    nrelacion = ForeignKeyField(Encabezado, column_name='nrelacion')

    class Meta:
        table_name = 'cbterel'