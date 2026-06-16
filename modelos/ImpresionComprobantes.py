import peewee

from modelos.ModeloBase import ModeloBase, BitBooleanField


class Cabfact(ModeloBase):

    idcabfact = peewee.AutoField(db_column='idcabfact')
    nrelacion = peewee.IntegerField(default=0)
    razon_social = peewee.CharField(max_length=100, default='')
    tipo_iva = peewee.CharField(max_length=80, default='')
    domicilio = peewee.CharField(max_length=100, default='')
    kg_total = peewee.DecimalField(max_digits=12, decimal_places=2, default=0)
    cond_vta = peewee.CharField(max_length=100, default='')
    vendedor = peewee.CharField(max_length=80, default='')
    cajero = peewee.CharField(max_length=80, default='')
    observaciones = peewee.TextField(default='')
    idmovi = peewee.IntegerField(default=0)
    mensaje1 = peewee.CharField(max_length=65, default='')
    mensaje2 = peewee.CharField(max_length=65, default='')
    mensaje3 = peewee.CharField(max_length=65, default='')
    carpeta_guardado = peewee.CharField(max_length=150, default='')
    listo = BitBooleanField(default=0)
    error = peewee.TextField(default='')
    correos = peewee.TextField(default='')
    remitente = peewee.CharField(max_length=100, default='')
    rem_rel = peewee.CharField(max_length=50, default='')
    mensaje_html = peewee.TextField(default='')

class Detfact(ModeloBase):

    iddetfact = peewee.AutoField(db_column='iddetfact')
    idcabfact = peewee.ForeignKeyField(Cabfact, db_column='idcabfact')
    cantidad = peewee.DecimalField(max_digits=12, decimal_places=4, default=0)
    codigo = peewee.CharField(max_length=8, default='')
    unidad = peewee.CharField(max_length=8, default='')
    detalle = peewee.CharField(max_length=100, default='')
    detext = peewee.TextField(default='')
    alicuota = peewee.DecimalField(max_digits=6, decimal_places=2, default=0)
    unitario = peewee.DecimalField(max_digits=12, decimal_places=4, default=0)
    total = peewee.DecimalField(max_digits=12, decimal_places=4, default=0)
    iva = peewee.DecimalField(max_digits=12, decimal_places=4, default=0)
    dgr = peewee.DecimalField(max_digits=12, decimal_places=4, default=0)