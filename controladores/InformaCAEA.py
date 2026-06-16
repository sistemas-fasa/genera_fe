import os
from datetime import datetime

from PyQt5.QtWidgets import QApplication

from controladores.ControladorBase import ControladorBase
from controladores.FE import FEv1
from controladores.Main import MainController
from libs.Utiles import envia_correo, DeCodifica
from modelos.CAEA import CAEA
from modelos.Encabezado import Encabezado
from modelos.ModeloBase import ModeloBase
from vistas.InformaCAEA import InfromaCAEAView


class InformaCAEAController(ControladorBase):

    lProcesa = True
    cae = ''
    vencecae = ''
    errmsg = ''
    resultado = ''
    motivoobs = ''
    comprobante = ''

    def __init__(self):
        super(InformaCAEAController, self).__init__()
        self.view = InfromaCAEAView()
        self.view.initUi()
        self.conectarWidgets()
        self.model = ModeloBase()
        self.model.getDb()

    def conectarWidgets(self):
        self.view.btnCerrar.clicked.connect(self.Cerrar)
        self.view.btnIniciar.clicked.connect(self.Informa)

    def Cerrar(self):
        self.lProcesa = False
        QApplication.exit(1)

    def Informa(self):
        caea = CAEA.select().where(CAEA.periodo == self.view.layoutParametros.cPeriodo,
                                   CAEA.orden == str(self.view.txtOrden.text()),
                                   CAEA.estado == '')
        ptovta = str(self.view.txtPtoVta.text()).zfill(4)

        for c in caea:
            encabeza = Encabezado.select().where(Encabezado.puntovta == ptovta,
                                                 Encabezado.tipows == 'A',
                                                 Encabezado.cae == c.CAEA)
            if encabeza.count() == 0:
                wsfe = FEv1()
                wsfe.InformarCAEASinMovimiento(ptovta, c.CAEA)
            else:
                controlador = MainController()
                controlador.grabaxml = True
                for d in encabeza:
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
                        envia_correo(to_address='oscar@ferreteriaavenida.com.ar',
                                     from_address='info@ferreteriaavenida.com.ar',
                                     subject='Error al generar FE',
                                      message=(
                                          "Error: {}\n"
                                          "Motivo/Obs: {}\n\n"
                                          "XML request:\n{}\n\n"
                                          "XML response:\n{}"
                                      ).format(
                                          DeCodifica(controlador.errmsg or ""),
                                          DeCodifica(controlador.motivoobs or ""),
                                          DeCodifica(controlador.xml_request or ""),
                                          DeCodifica(controlador.xml_response or "")
                                      ),
                                      password_email=os.getenv('FASA_ERROR_EMAIL_PASSWORD') or os.getenv('SMTP_PASSWORD', ''))
                    d.save()
            caeaupdate = CAEA.get_by_id(c.idCAEA)
            caeaupdate.estado = 'P'
            caeaupdate.save()
        self.Cerrar()
