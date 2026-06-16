# coding=utf-8
import peewee

from modelos.ModeloBase import ModeloBase


class Pago(ModeloBase):
    pago = peewee.CharField(max_length=2, primary_key=True, db_column='pago')
    detalle = peewee.CharField(max_length=30, default='')

    class Meta:
        table_name = 'pagos'