from peewee import AutoField, ForeignKeyField, IntegerField, CharField, DecimalField

from modelos.Encabezado import Encabezado
from modelos.ModeloBase import ModeloBase, BitBooleanField


class Tributo(ModeloBase):

    id = AutoField()
    #nrocontrol = ForeignKeyField(Encabezado, column_name='nrocontrol')
    tributoid = IntegerField(default=99)
    descripcion = CharField(max_length=100, default='')
    baseimp = DecimalField(max_digits=12, decimal_places=4, default=0)
    alic = DecimalField(max_digits=12, decimal_places=4, default=3.31)
    importe = DecimalField(max_digits=12, decimal_places=4, default=0)
    transferido = BitBooleanField()
    #nrelacion = IntegerField(default=0)
    nrelacion = ForeignKeyField(Encabezado, column_name='nrelacion')

    class Meta:
        table_name = 'tributo'