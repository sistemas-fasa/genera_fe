from peewee import AutoField, ForeignKeyField, IntegerField, DecimalField

from modelos.Encabezado import Encabezado
from modelos.ModeloBase import ModeloBase, BitBooleanField


class IVA(ModeloBase):

    idiva = AutoField()
    #nrocontrol = ForeignKeyField(Encabezado, column_name='nrocontrol')
    ivaid = IntegerField(default=5)
    baseimp = DecimalField(max_digits=12, decimal_places=4)
    importe = DecimalField(max_digits=12, decimal_places=4)
    transferido = BitBooleanField()
    #nrelacion = IntegerField(default=0)
    nrelacion = ForeignKeyField(Encabezado, column_name='nrelacion')

    class Meta:
        table_name = "iva"