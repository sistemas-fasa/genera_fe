import peewee

from modelos.Empresas import Empresa
from modelos.ModeloBase import ModeloBase, BitBooleanField


class CUIT(ModeloBase):

    id = peewee.AutoField()
    cuit_consultado = peewee.CharField(max_length=13, default='')
    denominacion = peewee.CharField(max_length=100, default='')
    tipo_doc = peewee.CharField(max_length=2, default='')
    estado = peewee.CharField(max_length=30, default='')
    direccion = peewee.CharField(max_length=100, default='')
    localidad = peewee.CharField(max_length=100, default='')
    provincia = peewee.CharField(max_length=100, default='')
    cp = peewee.CharField(max_length=10, default='')
    monotributo = peewee.CharField(max_length=1, default='')
    ret_iva = peewee.CharField(max_length=1, default='')
    empleador = peewee.CharField(max_length=1, default='')
    resultado = peewee.CharField(max_length=1, default='')
    errmsg = peewee.CharField(max_length=250, default='')
    transferido = BitBooleanField()
    empresa = peewee.ForeignKeyField(Empresa, default=1, column_name='empresa')
    errorprog = peewee.TextField()
    listo = BitBooleanField()
    fce = BitBooleanField(default=0)
    monto_obligado = peewee.DecimalField(max_digits=12, decimal_places=2, default=0)
