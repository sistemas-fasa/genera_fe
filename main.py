#!/usr/bin/env python

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

#Punto de Inicio del sistema
from PyQt5.QtWidgets import QApplication

__author__ = "Jose Oscar Vogel <oscarvogel@gmail.com>"
__copyright__ = "Copyright (C) 2018 Jose Oscar Vogel"
__license__ = "GPL 3.0"
__version__ = "0.1"

import logging
import os
import sys
from datetime import datetime

from libs.Utiles import initialize_logger

from controladores.FE import FEv1
from controladores.Main import MainController, _email_alerta_fe_from, _email_alerta_fe_to, enviar_correo_alerta_operativa
from libs.Utiles import LeerIni, FechaMysql, envia_correo, DeCodifica
from modelos.Encabezado import Encabezado


def inicio():
    # logging.basicConfig(filename=join(LeerIni("iniciosistema"), 'errors.log'), level=logging.DEBUG,
    #                     format='%(asctime)s %(message)s',
    #                     datefmt='%m/%d/%Y %I:%M:%S %p')
    initialize_logger(LeerIni("iniciosistema"))
    if LeerIni(clave='homo') == 'S':
        print("Sistema en modo homologacion")
    else:
        print("Sistema en modo produccion")
    # Instancia para iniciar una aplicación
    args = []
    #args = ['', '-style', 'Cleanlooks']
    app = QApplication(args)
    ex = MainController()
    ex.run()
    
    sys.exit(app.exec_())

if __name__ == "__main__":

    if "--caea" in sys.argv:
        periodo = FechaMysql()[:6]

        if FechaMysql()[-2:] > '15':
            orden = '2'
        else:
            orden = '1'

        wsfe = FEv1()
        caea = wsfe.SolicitarCAEA(periodo, orden)
        print("CAEA {} periodo {} orden {} FchVigDesde {} FchVigHasta {} FchTopeInf {} FchProceso {}".
              format(caea, wsfe.Periodo, wsfe.Orden, wsfe.FchVigDesde, wsfe.FchVigHasta,
                     wsfe.FchTopeInf, wsfe.FchProceso))
    elif "--informacaea" in sys.argv:
        punto_vta = sys.argv[sys.argv.index("--informacaea")+1]
        caea = sys.argv[sys.argv.index("--informacaea") + 2]

        data = Encabezado.select().where(Encabezado.resultado == 'A',
                                         Encabezado.tipows == 'A',
                                         Encabezado.puntovta == punto_vta,
                                         Encabezado.cae == caea)
        if data.count() == 0:
            wsfe = FEv1()
            wsfe.InformarCAEASinMovimiento(punto_vta, caea)
        else:
            controlador = MainController()
            for d in data:
                print("Procesando factura {}-{}".format(d.puntovta, d.cbtenro))
                ok = controlador.CreaFE(d, caea=True)
                if ok:
                    d.cae = controlador.cae
                    d.resultado = controlador.resultado
                    d.cbtenro = str(controlador.comprobante).zfill(8)
                    d.vencecae = datetime.strptime(controlador.vencecae, '%Y%m%d')
                else:
                    d.resultado = controlador.resultado
                    d.errmsg = controlador.errmsg
                    d.motivoobs = controlador.motivoobs
                    d.vencecae = datetime.today()
                    enviar_correo_alerta_operativa(
                        to_address=_email_alerta_fe_to(),
                        from_address=_email_alerta_fe_from(),
                        subject='Error al generar FE',
                        message="Error: {} {}".format(DeCodifica(controlador.errmsg),
                                                      DeCodifica(controlador.motivoobs)),
                        password_email=os.getenv('FASA_ERROR_EMAIL_PASSWORD') or os.getenv('SMTP_PASSWORD', '')
                    )
                d.save()
    else:
        inicio()
