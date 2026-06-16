from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout

from libs.Botones import Boton, BotonCerrarFormulario
from libs.EntradaTexto import EntradaTexto
from libs.Etiquetas import EtiquetaTitulo, Etiqueta
from vistas.VistaBase import VistaBase


class ConfigView(VistaBase):

    def initUi(self):
        self.setWindowTitle("Configuracion del sistema")
        layoutPpal = QVBoxLayout(self)
        lblTitulo = EtiquetaTitulo(texto=self.windowTitle())
        layoutPpal.addWidget(lblTitulo)

        layoutLinea1 = QHBoxLayout()
        lblInicioSistema = Etiqueta(texto='Inicio Sistema')
        self.textInicioSistema = EntradaTexto()
        layoutLinea1.addWidget(lblInicioSistema)
        layoutLinea1.addWidget(self.textInicioSistema)
        layoutPpal.addLayout(layoutLinea1)

        layoutBotones = QHBoxLayout()
        self.btnGraba = Boton(imagen='imagenes/guardar.png', texto='Guardar')
        self.btnCerrar = BotonCerrarFormulario()
        layoutBotones.addWidget(self.btnGraba)
        layoutBotones.addWidget(self.btnCerrar)
        layoutPpal.addLayout(layoutBotones)
