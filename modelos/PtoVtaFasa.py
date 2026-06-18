# coding=utf-8
import peewee

from modelos.ModeloBase import ModeloBaseFASA, BitBooleanField


class PtoVtaFasa(ModeloBaseFASA):
    ptovta = peewee.CharField(max_length=4, default='')
    ubicacion = peewee.CharField(max_length=50, default='')
    tipo = peewee.CharField(max_length=2, default='')
    vencimiento = peewee.DateField(default='0000-00-00')
    ultnumero = peewee.CharField(max_length=8, default='')
    aviso = BitBooleanField(default=0)
    empresa_id = peewee.IntegerField(null=True)

    @classmethod
    def buscar(cls, ptovta=None, empresa_id=None, ubicacion=None, tipo=None):
        filtros = []
        if ptovta is not None:
            filtros.append(cls.ptovta == ptovta)
        if empresa_id is not None:
            filtros.append(cls.empresa_id == empresa_id)
        if ubicacion is not None:
            filtros.append(cls.ubicacion == ubicacion)
        if tipo is not None:
            filtros.append(cls.tipo == tipo)
        query = cls.select()
        if filtros:
            query = query.where(*filtros)
        return query.first()

    class Meta:
        table_name = 'ptovtas'
        primary_key = False
        indexes = (
            (('ptovta', 'empresa_id'), True),
        )
