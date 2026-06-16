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
from PyQt4.QtGui import QHBoxLayout, QVBoxLayout

from libs.Botones import BotonCerrarFormulario, Boton
from libs.EntradaTexto import EntradaTexto
from libs.Etiquetas import Etiqueta
from libs.Spinner import Periodo
from vistas.VistaBase import VistaBase

class InfromaCAEAView(VistaBase):

    def initUi(self):
        self.setGeometry(150, 150, 500, 150)
        self.layoutPpal = QVBoxLayout(self)

        self.layoutParametros = Periodo(texto='Periodo')
        lblOrden = Etiqueta(texto="Orden")
        self.txtOrden = EntradaTexto(inputmask='9')
        self.layoutParametros.addWidget(lblOrden)
        self.layoutParametros.addWidget(self.txtOrden)
        self.layoutPpal.addLayout(self.layoutParametros)
        lblPtoVta = Etiqueta(texto="Pto Vta")
        self.txtPtoVta = EntradaTexto(inputmask='9999')
        self.layoutParametros.addWidget(lblPtoVta)
        self.layoutParametros.addWidget(self.txtPtoVta)

        self.btnCerrar = BotonCerrarFormulario()
        self.btnIniciar = Boton(texto='Iniciar', imagen='imagenes/Accept.png')
        layoutBotones = QHBoxLayout()
        layoutBotones.addWidget(self.btnIniciar)
        layoutBotones.addWidget(self.btnCerrar)

        self.layoutPpal.addLayout(layoutBotones)