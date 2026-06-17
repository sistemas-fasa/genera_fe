# coding=utf-8
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QGroupBox

from libs.BarraProgreso import Avance
from libs.Botones import BotonCerrarFormulario, Boton
from libs.Etiquetas import EtiquetaTitulo, Etiqueta
from libs.Grillas import Grilla
from libs.Utiles import LeerIni
from vistas.VistaBase import VistaBase


class MainView(VistaBase):

    def initUi(self):
        self.setGeometry(150, 150, 650, 450)
        self.setWindowTitle('Factura Electronica - Servidor MySql {}'.format(LeerIni(clave='host')))
        self.layoutPpal = QVBoxLayout(self)
        self.lblTitulo = EtiquetaTitulo(texto="{}-{}".format(
            LeerIni(clave="nombre_sistema"), LeerIni(clave='EMPRESA', key='FACTURA')))
        self.layoutPpal.addWidget(self.lblTitulo)

        self.avance = Avance()
        self.layoutPpal.addWidget(self.avance)

        self.lblProcesamiento = Etiqueta()
        self.layoutPpal.addWidget(self.lblProcesamiento)

        self.grpAfip = QGroupBox('Estado AFIP')
        layoutAfip = QVBoxLayout(self.grpAfip)
        self.lblAfipEstado = Etiqueta(texto='AFIP: Sin verificar', tamanio=10)
        self.lblAfipAppServer = Etiqueta(texto='AppServer: N/D', tamanio=10)
        self.lblAfipDbServer = Etiqueta(texto='DbServer: N/D', tamanio=10)
        self.lblAfipAuthServer = Etiqueta(texto='AuthServer: N/D', tamanio=10)
        self.lblAfipUltimaVerificacion = Etiqueta(texto='Ultima verificacion: N/D', tamanio=10)
        self.lblAfipMensaje = Etiqueta(texto='', tamanio=10)
        layoutAfip.addWidget(self.lblAfipEstado)
        layoutAfip.addWidget(self.lblAfipAppServer)
        layoutAfip.addWidget(self.lblAfipDbServer)
        layoutAfip.addWidget(self.lblAfipAuthServer)
        layoutAfip.addWidget(self.lblAfipUltimaVerificacion)
        layoutAfip.addWidget(self.lblAfipMensaje)

        self.grpEmails = QGroupBox('Estado emails')
        layoutEmails = QVBoxLayout(self.grpEmails)
        self.lblEmailsEstado = Etiqueta(texto='Emails: ACTIVO', tamanio=10)
        self.lblEmailsPendientes = Etiqueta(texto='Pendientes: 0', tamanio=10)
        self.lblEmailsRetrasados = Etiqueta(texto='Retrasados: 0', tamanio=10)
        self.lblEmailsFallidos = Etiqueta(texto='Fallidos: 0', tamanio=10)
        self.lblEmailsMensaje = Etiqueta(texto='', tamanio=10)
        layoutEmails.addWidget(self.lblEmailsEstado)
        layoutEmails.addWidget(self.lblEmailsPendientes)
        layoutEmails.addWidget(self.lblEmailsRetrasados)
        layoutEmails.addWidget(self.lblEmailsFallidos)
        layoutEmails.addWidget(self.lblEmailsMensaje)

        layoutEstados = QHBoxLayout()
        layoutEstados.addWidget(self.grpAfip)
        layoutEstados.addWidget(self.grpEmails)
        self.layoutPpal.addLayout(layoutEstados)

        self.gridFacturas = Grilla()
        cabeceras = [
            'Pto Vta', 'Comprobante', 'CAE', 'Vence Cae', 'Errores'
        ]
        self.gridFacturas.ArmaCabeceras(cabeceras=cabeceras)
        self.layoutPpal.addWidget(self.gridFacturas)

        self.btnCerrar = BotonCerrarFormulario()
        self.btnIniciar = Boton(texto='Iniciar', imagen='imagenes/Accept.png')
        self.btnPausar = Boton(texto='Pausar', imagen='imagenes/Stop.png')
        self.btnPausar.setEnabled(False)
        self.btnToggleEmails = Boton(texto='Emails: ACTIVO', imagen='imagenes/Accept.png')
        layoutBotones = QHBoxLayout()
        layoutBotones.addWidget(self.btnIniciar)
        layoutBotones.addWidget(self.btnPausar)
        layoutBotones.addWidget(self.btnToggleEmails)
        layoutBotones.addWidget(self.btnCerrar)

        self.layoutPpal.addLayout(layoutBotones)
