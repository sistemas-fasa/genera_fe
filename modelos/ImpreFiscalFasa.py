# coding=utf-8
import peewee

from modelos.ModeloBase import ModeloBaseFASA


class ImpreFiscalFasa(ModeloBaseFASA):
    idImpreFiscal = peewee.AutoField()
    maquina = peewee.CharField(max_length=30, null=True)
    ptovtafac = peewee.CharField(max_length=4, null=True)
    ptovtaticket = peewee.CharField(max_length=4, null=True)
    detalle = peewee.CharField(max_length=200, default='')
    impresora = peewee.CharField(max_length=50, default='')
    empresa_id = peewee.IntegerField(default=1)

    @classmethod
    def buscar(cls, maquina, empresa_id):
        return cls.select().where(
            cls.maquina == maquina,
            cls.empresa_id == empresa_id,
        ).first()

    @classmethod
    def listar_por_empresa(cls, empresa_id):
        return list(cls.select().where(cls.empresa_id == empresa_id))

    @classmethod
    def listar_por_maquinas(cls, empresa_id, maquinas):
        return list(cls.select().where(
            cls.empresa_id == empresa_id,
            cls.maquina.in_(maquinas),
        ))

    class Meta:
        table_name = 'imprefiscal'
