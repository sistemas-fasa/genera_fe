# coding=utf-8
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 3, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTIBILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
from peewee import AutoField, CharField, DateField, DecimalField, TextField, ForeignKeyField

from modelos.Empresas import Empresa
from modelos.ModeloBase import ModeloBase, BitBooleanField


class Constatacion(ModeloBase):
    idconstatacion = AutoField(primary_key=True, db_column='idConstatacion')
    cbtemodo = CharField(max_length=4)
    cuitemisor = CharField(max_length=11)
    cbtetipo = CharField(max_length=3)
    ptovta = CharField(max_length=5)
    cbtenro = CharField(max_length=8)
    fechacbte = DateField()
    imptotal = DecimalField(decimal_places=2, max_digits=12)
    codaut = CharField(max_length=14) #CAE / CAEA
    #datos del que recibe la factura
    doctiporec = CharField(max_length=2)
    docnrorec = CharField(max_length=11)
    obs = TextField()
    errmsg = TextField()
    resultado = CharField(max_length=1)
    listo = BitBooleanField(default=0)
    excepcion = TextField()
    fechaconsulta = DateField()
    usuarioconsulta = CharField(max_length=30)
    empresa = ForeignKeyField(Empresa, default=1, column_name='empresa')

    class Meta:
        table_name = "constatacion"
