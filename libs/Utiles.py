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

#Utilidades varias necesarias en el sistema

import calendar
import http.client
import platform
import tempfile
import urllib.parse
from email.mime.text import MIMEText
from smtplib import SMTP
from logging.handlers import RotatingFileHandler

import xml.etree.ElementTree as ET
from xml.dom import minidom
import re


from PyQt5 import QtGui
from PyQt5.QtWidgets import QFileDialog

__author__ = "Jose Oscar Vogel <oscarvogel@gmail.com>"
__copyright__ = "Copyright (C) 2018 Jose Oscar Vogel"
__license__ = "GPL 3.0"
__version__ = "0.1"


import datetime
import hashlib
import logging
import os
import sys
import traceback
import uuid

if platform.system() == 'Windows':
    import win32api

from configparser import ConfigParser
from functools import wraps

from cryptography.fernet import Fernet
from os.path import join
from sys import argv

from libs import Ventanas

#necesario porque en mysql tengo definido el campo boolean como bit

def EsVerdadero(valor):
    return valor == b'\01'

#abro el archivo con el programa por defecto en windows
#tendria que ver como hacerlo en Linux
def AbrirArchivo(cArchivo=None):
    if cArchivo:
        win32api.ShellExecute(0, "open", cArchivo, None, ".", 0)

#leo el archivo de configuracion del sistema
#recibe la clave y el key a leer en caso de que tenga mas de una seccion el archivo
def LeerIni(clave=None, key=None):
    retorno = ''
    Config = ConfigParser()
    Config.read("sistema.ini")
    try:
        if not key:
            key = 'param'
        retorno = Config.get(key, clave)
    except:
        #Ventanas.showAlert("Sistema", "No existe la seccion {}".format(clave))
        pass
    return retorno


def LeerTimeoutAFIP(default=30):
    valor = LeerIni(clave="afip_timeout_segundos")
    try:
        timeout = int(valor) if valor else default
        return max(timeout, 1)
    except (TypeError, ValueError):
        return default


def GrabarIni(clave=None, key=None, valor=''):

    if not clave or not key:

        return

    Config = ConfigParser()

    Config.read('sistema.ini')

    cfgfile = open("sistema.ini",'wb')

    Config.set(key, clave, valor)

    Config.write(cfgfile)

    cfgfile.close()



def ubicacion_sistema():
    cUbicacion = LeerIni("iniciosistema") or os.path.dirname(argv[0])
    return cUbicacion



def imagen(archivo):
    archivoImg = ubicacion_sistema() + join("imagenes", archivo)
    if os.path.exists(archivoImg):
        return archivoImg
    else:
        return ""

def icono_sistema():
    cIcono = QtGui.QIcon(imagen("logo.ico"))

    return cIcono

def hash_password(password):
    # uuid is used to generate a random number
    salt = uuid.uuid4().hex
    return hashlib.sha256(salt.encode() + password.encode()).hexdigest() + ':' + salt

def check_password(hashed_password, user_password):
    password, salt = hashed_password.split(':')
    return hashlib.sha256(salt.encode() + user_password.encode()).hexdigest()


def encriptar(password):
    key = Fernet.generate_key()
    cipher_suite = Fernet(key)
    cipher_text = cipher_suite.encrypt(password)
    return cipher_text, key

def desencriptar(encrypted_data, key):
    cipher_suite = Fernet(key)
    plain_text = cipher_suite.decrypt(encrypted_data)
    return plain_text

def inicializar_y_capturar_excepciones(func):

    "Decorador para inicializar y capturar errores"
    @wraps(func)
    def capturar_errores_wrapper(self, *args, **kwargs):
        try:
            # inicializo (limpio variables)
            self.Traceback = self.Excepcion = ""
            return func(self, *args, **kwargs)
        except Exception as e:
            ex = traceback.format_exception( sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2])
            self.Traceback = ''.join(ex)
            self.Excepcion = traceback.format_exception_only( sys.exc_info()[0], sys.exc_info()[1])[0]
            logging.debug(self.Traceback)
            Ventanas.showMsgAutoClose("Error", "Se ha producido un error \n{}".format(self.Excepcion))
            if self.LanzarExcepciones:
                raise
        finally:
            pass
    return capturar_errores_wrapper



def validar_cuit(cuit):
    # validaciones minimas
    if len(cuit) != 13 or cuit[2] != "-" or cuit[11] != "-":
        return False
    base = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    cuit = cuit.replace("-", "") # remuevo las barras
    # calculo el digito verificador:
    aux = 0
    for i in range(10):
        aux += int(cuit[i])* base[i]
    aux = 11 - (aux - (int(aux / 11)* 11))
    if aux == 11:
        aux = 0
    if aux == 10:
        aux = 9
    return aux == int(cuit[10])

def FechaMysql(fecha=None):
    if not fecha:
        fecha = datetime.datetime.today()
    retorno = fecha.strftime('%Y%m%d')
    return retorno

def HoraMysql(hora=None):
    if not hora:
        hora = datetime.datetime.now()
    retorno = hora.strftime('%H:%M:%S')
    return retorno

def InicioMes(dFecha=None):
    if not dFecha:
        dFecha = datetime.date.today()
    return dFecha.replace(day=1)

def FinMes(hFecha=None):
    if not hFecha:
        hFecha = datetime.date.today()
    return hFecha.replace(day = calendar.monthrange(hFecha.year, hFecha.month)[1])

def GuardarArchivo(caption="Guardar archivo", directory="", filter="", filename=""):
    #dialog = QFileDialog()
    #dialog.selectFile(filename)
    #dialog.setDirectory(directory)
    #dialog.setAcceptMode(QFileDialog.AcceptSave)
    #dialog.setFileMode(filter)
    cArchivo = QFileDialog.getSaveFileName(caption=caption,
                                           directory=join(directory, filename),
                                           filter=filter)
    #dialog.exec_()
    #cArchivo = dialog.selectedFiles()[0]
    return cArchivo if cArchivo else ''

def Normaliza(valor):
    valor = DeCodifica(valor)
    return valor.replace('Ñ','N').replace('ñ','n').replace('º','')

def DeCodifica(dato):
    return "{}".format(bytearray(dato, 'latin-1', errors='ignore').decode('utf-8','ignore'))


def envia_correo(from_address = '', to_address = '', message = '', subject = '', password_email = '', to_cc='', smtp_email=''):
    if not smtp_email:
        if LeerIni(clave='smtp_email', key='email'):
            smtp_email = desencriptar(LeerIni(clave='smtp_email', key='email'), key=LeerIni(clave='key_email', key='email'))
        else:
            smtp_email = 'mail.ferreteriaavenida.com.ar'
    mime_message = MIMEText(message)
    mime_message["From"] = from_address
    mime_message["To"] = to_address
    mime_message["Subject"] = subject
    if to_cc:
        mime_message["Cc"] = to_cc
    smtp = SMTP(smtp_email, 587)
    smtp.ehlo()
    smtp.login(from_address, password_email)
    smtp.sendmail(from_address, [to_address, to_cc], mime_message.as_string())
    smtp.quit()

# funcion que se encarga de obtener respuesta del estatus del servidor web
def get_server_status_code(url):
    # descarga sólo el encabezado de una URL y devolver el código de estado del servidor.
    host, path = urllib.parse.urlparse(url)[1:3]
    try:
        conexion = http.client.HTTPConnection(host)
        conexion.request('HEAD', path)
        return conexion.getresponse().status
    except Exception:
        return None

# función que se encarga de checkear que exista la url a guardar
def check_url(url):
    # Comprobar si existe un URL sin necesidad de descargar todo el archivo. Sólo comprobar el encabezado URL.
    # variable que se encarga de traer las respuestas
    codigo = [http.client.OK, http.client.FOUND, http.client.MOVED_PERMANENTLY]
    return get_server_status_code(url) in codigo

def initialize_logger(output_dir):
    # Ensure output directory exists
    try:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
    except Exception as e:
        print(f"ERROR: No se pudo crear directorio de logs {output_dir}: {e}")
        output_dir = os.path.dirname(__file__) or '.'

    logger = logging.getLogger()
    
    # Limpiar handlers existentes para evitar duplicados
    logger.handlers.clear()
    
    logger.setLevel(logging.INFO)  # Cambiado de DEBUG a INFO para que info.log reciba mensajes

    # Console handler (INFO+)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch_formatter = logging.Formatter("%(levelname)s - %(message)s")
    ch.setFormatter(ch_formatter)
    logger.addHandler(ch)

    # Filter to allow records up to a maximum level (inclusive)
    class MaxLevelFilter(logging.Filter):
        def __init__(self, max_level):
            super().__init__()
            self.max_level = max_level

        def filter(self, record):
            return record.levelno <= self.max_level

    # Info file handler (INFO and WARNING) - rotating, max 100 MB
    info_path = os.path.join(output_dir, "info.log")
    info_max_bytes = 100 * 1024 * 1024
    try:
        ih = RotatingFileHandler(info_path, mode='a', maxBytes=info_max_bytes, backupCount=5, encoding='utf-8', delay=False)
        ih.setLevel(logging.INFO)
        ih.addFilter(MaxLevelFilter(logging.WARNING))
        ih_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s", datefmt='%Y-%m-%d %H:%M:%S')
        ih.setFormatter(ih_formatter)
        logger.addHandler(ih)
        print(f"✓ Info log configurado: {info_path}")
    except Exception as e:
        print(f"ERROR: No se pudo crear info.log en {info_path}: {e}")

    # Error file handler (ERROR+) - rotating to avoid large single-file errors
    error_path = os.path.join(output_dir, "error.log")
    try:
        eh = RotatingFileHandler(error_path, mode='a', maxBytes=10 * 1024 * 1024, backupCount=5, encoding='utf-8', delay=False)
        eh.setLevel(logging.ERROR)
        eh_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s", datefmt='%Y-%m-%d %H:%M:%S')
        eh.setFormatter(eh_formatter)
        logger.addHandler(eh)
        print(f"✓ Error log configurado: {error_path}")
    except Exception as e:
        print(f"ERROR: No se pudo crear error.log en {error_path}: {e}")

    logger.info('Logger initialized. Info log: %s (max %d bytes), Error log: %s', info_path, info_max_bytes, error_path)

def getFileName(filename='pdf', base=False):

    tf = tempfile.NamedTemporaryFile(prefix=filename, mode='w+b')
    if base:
        return os.path.basename(tf.name)
    return tf.name


def FormatoFecha(fecha=datetime.datetime.today(), formato='largo'):

    retorno = ''
    if isinstance(fecha, (str)):
        retorno = fecha
    else:
        if formato == 'largo':
            retorno = datetime.datetime.strftime(fecha,'%d %b %Y')
        elif formato == 'corto':
            retorno = datetime.datetime.strftime(fecha, '%d-%b')
        elif formato == 'dma':
            retorno = datetime.datetime.strftime(fecha, '%d/%m/%Y')
        elif formato == 'afip':
            retorno = datetime.datetime.strftime(fecha, '%d-%m-%Y')

    return retorno

def num_after_point(x):
    s = str(float(x))
    if not '.' in s:
        return 0
    return len(s) - s.index('.') - 1


def limpiar_namespaces_y_pretty(xml_str):
    # Decodificar si viene como bytes
    if isinstance(xml_str, bytes):
        xml_str = xml_str.decode('utf-8')
    # Eliminar los xmlns:* y xsi:* del XML
    xml_str = re.sub(r'\sxmlns(:\w+)?="[^"]+"', '', xml_str)
    xml_str = re.sub(r'\sxsi(:\w+)?="[^"]+"', '', xml_str)

    # Eliminar prefijos como soap:
    xml_str = re.sub(r'<(/?)(\w+):', r'<\1', xml_str)
    
    # Parsear con ElementTree
    root = ET.fromstring(xml_str)

    # Pretty print
    def pretty_print(elem):
        rough_string = ET.tostring(elem, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")

    return pretty_print(root)
