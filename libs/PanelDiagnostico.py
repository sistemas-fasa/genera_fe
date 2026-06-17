# coding=utf-8
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView

from libs.Botones import BotonCerrarFormulario
from libs.Etiquetas import EtiquetaTitulo


class PanelDiagnostico(QDialog):

    def __init__(self, resultados, parent=None):
        QDialog.__init__(self, parent)
        self.resultados = resultados
        self.setWindowTitle("Estado del sistema")
        self.setMinimumSize(760, 420)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(EtiquetaTitulo(texto="Estado del sistema"))

        self.tabla = QTableWidget()
        self.tabla.setColumnCount(3)
        self.tabla.setHorizontalHeaderLabels(["Nivel", "Mensaje", "Detalle"])
        self.tabla.setRowCount(len(self.resultados))
        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla.verticalHeader().setVisible(False)

        for fila, resultado in enumerate(self.resultados):
            self._agregar_item(fila, 0, resultado.nivel)
            self._agregar_item(fila, 1, resultado.mensaje)
            self._agregar_item(fila, 2, resultado.detalle)

        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        layout.addWidget(self.tabla)

        self.btnCerrar = BotonCerrarFormulario()
        self.btnCerrar.clicked.connect(self.accept)
        layout.addWidget(self.btnCerrar, alignment=Qt.AlignRight)

    def _agregar_item(self, fila, columna, texto):
        item = QTableWidgetItem(texto or "")
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        if columna == 0:
            item.setTextAlignment(Qt.AlignCenter)
            item.setToolTip("OK, WARN o ERROR")
        self.tabla.setItem(fila, columna, item)
