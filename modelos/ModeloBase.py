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

#Modelo base del cual derivan todos los modelos del sistema

__author__ = "Jose Oscar Vogel <oscarvogel@gmail.com>"
__copyright__ = "Copyright (C) 2018 Jose Oscar Vogel"
__license__ = "GPL 3.0"
__version__ = "0.1"

from peewee import MySQLDatabase, Model, Field, BooleanField, SqliteDatabase

from libs.Utiles import LeerIni, desencriptar


def _leer_base_config():
    return (LeerIni(clave='base') or 'mysql').strip().lower()


def _crear_mysql_database(nombre_base):
    key = LeerIni('key')
    password_encrypted = LeerIni('password')
    usuario = LeerIni("usuario")
    host = LeerIni("host")

    if not key or not password_encrypted:
        raise RuntimeError("Faltan key/password en sistema.ini para configurar MySQL")
    if not nombre_base or not usuario or not host:
        raise RuntimeError("Faltan basedatos/usuario/host en sistema.ini para configurar MySQL")

    password = desencriptar(str.encode(password_encrypted), str.encode(key))
    return MySQLDatabase(
        nombre_base,
        user=usuario,
        password=password,
        host=host,
        port=3306
    )


if _leer_base_config() == 'sqlite':
    db = SqliteDatabase('sistema.db')
    # En modo sqlite se reutiliza la misma DB para evitar errores de configuracion;
    # el uso real de dbfasa en sqlite queda limitado a pruebas.
    dbfasa = db
else:
    db = _crear_mysql_database(LeerIni("basedatos"))
    dbfasa = _crear_mysql_database("fasa")

class ModeloBase(Model):

    def __init__(self, *args, **kwargs):
        super(ModeloBase, self).__init__(*args, **kwargs)

    def getDb(self):
        return db

    def connect(self):
        db.connect(reuse_if_open=True)

    """A base model that will use our MySQL database"""
    class Meta:
        database = db


class BitBooleanField(BooleanField):
    field_type = 'Bit'

    def db_value(self, value):
        if isinstance(db, SqliteDatabase):
            if value is None:
                return None
            return bool(value)
        return value

    def python_value(self, value):
        if isinstance(db, SqliteDatabase):
            if value is None:
                return None
            return bool(value)
        if value is None:
            return None
        if isinstance(value, bytes):
            return value == b'\x01'
        return bool(value)
    
class ModeloBaseFASA(Model):

    def __init__(self, *args, **kwargs):
        super(ModeloBaseFASA, self).__init__(*args, **kwargs)

    def getDb(self):
        return dbfasa

    def connect(self):
        dbfasa.connect(reuse_if_open=True)

    """A base model that will use our MySQL database"""
    class Meta:
        database = dbfasa
