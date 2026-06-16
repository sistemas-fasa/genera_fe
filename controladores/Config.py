from PyQt5.QtWidgets import QApplication

from controladores.ControladorBase import ControladorBase
from vistas.Config import ConfigView


class ConfigController(ControladorBase):

    def __init__(self):
        super(ConfigController, self).__init__()
        self.view = ConfigView()
        self.view.initUi()
        self.conectarWidgets()

    def conectarWidgets(self):
        self.view.btnCerrar.clicked.connect(self.Cerrar)

    def Cerrar(self):
        QApplication.exit(1)
