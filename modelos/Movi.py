# coding=utf-8
from datetime import datetime

import peewee

from modelos.ModeloBase import ModeloBaseFASA, BitBooleanField
from modelos.Pagos import Pago


class Movi(ModeloBaseFASA):

    idmovi = peewee.AutoField()
    contado = peewee.CharField(max_length=2, default='N')
    codigo = peewee.CharField(max_length=2, default='F')
    clase = peewee.CharField(max_length=1, default='')
    comp = peewee.CharField(max_length=12, default='')
    zona = peewee.CharField(max_length=1, default='0')
    cliente = peewee.CharField(max_length=4, default='0001')
    nombre = peewee.CharField(max_length=30, default='')
    fecha = peewee.DateField(default=datetime.now().date())
    fechaven = peewee.DateField(default='0000-00-00')
    fechaent = peewee.DateField(default='0000-00-00')
    fechaimpu = peewee.DateField(default='0000-00-00')
    fecha1venc = peewee.DateField(default='0000-00-00')
    tipo = peewee.CharField(max_length=1, default='')
    descuento = peewee.DecimalField(max_digits=12, decimal_places=3)
    interno = peewee.DecimalField(max_digits=12, decimal_places=3)
    exento = peewee.DecimalField(max_digits=12, decimal_places=3)
    iva = peewee.DecimalField(max_digits=12, decimal_places=3)
    alicuota = peewee.DecimalField(max_digits=12, decimal_places=3)
    percepcion = peewee.DecimalField(max_digits=12, decimal_places=3)
    percepciondgr = peewee.DecimalField(max_digits=12, decimal_places=3)
    neto = peewee.DecimalField(max_digits=12, decimal_places=3)
    saldo = peewee.DecimalField(max_digits=12, decimal_places=3)
    mensaje1 = peewee.CharField(max_length=30, default='')
    mensaje2 = peewee.CharField(max_length=30, default='')
    mensaje3 = peewee.CharField(max_length=30, default='')
    mensaje4 = peewee.CharField(max_length=30, default='')
    pago = peewee.ForeignKeyField(Pago, default='00', db_column='pago')
    cuotapago = peewee.IntegerField(default=1)
    vendedor = peewee.CharField(max_length=2, default='00')
    moneda = peewee.CharField(max_length=1, default='P')
    provincia = peewee.CharField(max_length=2, default='01')
    suc_de = peewee.CharField(max_length=5, default='00001')
    coniva = peewee.CharField(max_length=1, default='')
    buso = peewee.CharField(max_length=1, default='')
    obs = peewee.CharField(max_length=30, default='')
    lugar = peewee.CharField(max_length=25, default='')
    usuario = peewee.CharField(max_length=30, default='', db_column='_usuario')
    fechagraba = peewee.DateField(default=datetime.now().date(), db_column='_fecha')
    hora = peewee.CharField(default=str(datetime.now().time())[:8], db_column='_hora')
    regiva = peewee.CharField(max_length=1, default='')
    percept = peewee.DecimalField(max_digits=12, decimal_places=3)
    neto_neto = peewee.DecimalField(max_digits=12, decimal_places=3)
    neto_a = peewee.DecimalField(max_digits=12, decimal_places=3)
    neto_b = peewee.DecimalField(max_digits=12, decimal_places=3)
    autorizo = peewee.CharField(max_length=30, default='')
    localidad = peewee.CharField(max_length=4, default='')
    caja = peewee.CharField(max_length=2, default='')
    # exportado = BitBooleanField(default=b'\00')
    sucursal = peewee.IntegerField(default=0)
    reparte = peewee.CharField(default='', max_length=2)
    tipocomp = peewee.CharField(default='', max_length=2)
    # cae = peewee.CharField(default='', max_length=15)
    # venccae = peewee.DateField(default='0000-00-00')
    # concepto = peewee.CharField(default='', max_length=1)
    # desde = peewee.DateField(default='0000-00-00')
    # hasta = peewee.DateField(default='0000-00-00')

    class Meta:
        table_name = 'movi'