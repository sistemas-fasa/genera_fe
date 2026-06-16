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
from peewee import AutoField, CharField, DateField, TextField, ForeignKeyField, DateTimeField

from modelos.Empresas import Empresa
from modelos.ModeloBase import ModeloBase


class CAEA(ModeloBase):

    idCAEA = AutoField()
    CAEA = CharField(max_length=14, default='')
    periodo = CharField(max_length=6, default='')
    orden = CharField(max_length=1, default='')
    fchvigdesde = DateField()
    fchvighasta = DateField()
    fchtopeinf = DateField()
    fchproceso = DateTimeField()
    obs = TextField(default='')
    empresa = ForeignKeyField(Empresa, db_column='empresa')
    ptovta = CharField(max_length=4, default='')
    estado = CharField(max_length=1, default='')

    class Meta:
        table_name = 'caea'