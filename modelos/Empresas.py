from peewee import AutoField, CharField, DateField, IntegerField, TextField

from modelos.ModeloBase import ModeloBase, BitBooleanField

CUIT = {
    1:'30522884363',
    2:'30710940262',
    3:'30708792892'
}

class Empresa(ModeloBase):

    codigo = AutoField()
    nombre = CharField(max_length=30, default='')
    basedatos = CharField(max_length=30, default='')
    cuit = CharField(max_length=13)
    crt = CharField(max_length=100)
    key = CharField(max_length=100)
    emitefce = BitBooleanField(default=0)
    cbufce = CharField(max_length=22, default='')
    aliasfce = CharField(max_length=100, default='')
    logo = CharField(max_length=150, default='')
    inicio_actividades = DateField()
    servidor_correo = CharField(max_length=100, default='')
    usuario_correo = CharField(max_length=100, default='')
    pass_correo = CharField(max_length=100, default='')
    puerto = IntegerField(default=0)
    firma_correo = TextField(default='')
    imagen_cta_bacaria = CharField(max_length=255, default='')

    class Meta:
        table_name = 'empresas'