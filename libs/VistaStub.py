# coding=utf-8
"""Vista sin widgets para ejecutar CreaFE fuera del hilo GUI.

MainController.CreaFE solo usa self.view.gridFacturas (rowCount, removeRow y
AgregaItem). Este stub evita construir widgets Qt en un hilo worker y evita
mostrar una segunda ventana.
"""


class GrillaStub:

    def rowCount(self):
        return 0

    def removeRow(self, fila):
        pass

    def AgregaItem(self, **kwargs):
        pass


class VistaStub:

    def __init__(self):
        self.gridFacturas = GrillaStub()
