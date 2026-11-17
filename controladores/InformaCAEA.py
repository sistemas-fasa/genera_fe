# coding=utf-8
"""Rendido de CAEA desde el GUI principal de main.exe.

Antes este modulo era el entrypoint de informacaea.py y cerraba toda la
aplicacion al terminar. Ahora es un dialogo modal del proceso principal: el
rendido corre en un worker con un MainController sin timers ni widgets, asi
que la generacion de CAE del ciclo principal NO se detiene.
"""
import logging
from concurrent.futures import ThreadPoolExecutor

from PyQt5.QtCore import QObject, pyqtSignal

from controladores.CAEAProgramado import (
    calcular_periodo_orden_actual,
    quincena_anterior,
)
from controladores.ControladorBase import ControladorBase
from controladores.Main import MainController
from controladores.RendirCAEA import rendir
from libs.Avisos import mostrar_advertencia, mostrar_error
from libs.VistaStub import VistaStub
from modelos.ModeloBase import ModeloBase
from vistas.InformaCAEA import InfromaCAEAView


class InformaCAEAController(ControladorBase, QObject):

    # Hereda de QObject para que PyQt entregue la senal en el hilo GUI (donde
    # se crea el dialogo) aunque el emit venga del hilo worker.
    terminado = pyqtSignal(object)

    def __init__(self, controlador=None, executor=None):
        ControladorBase.__init__(self)
        QObject.__init__(self)
        self.view = InfromaCAEAView()
        self.view.initUi()
        self.conectarWidgets()
        self.model = ModeloBase()
        self.model.getDb()
        self.controlador = controlador
        self._executor = executor or ThreadPoolExecutor(max_workers=1)
        self._future = None
        self.terminado.connect(self._al_terminar)

        periodo, orden = calcular_periodo_orden_actual()
        periodo, orden = quincena_anterior(periodo, orden)
        self.view.layoutParametros.lineEditAnio.setValue(int(periodo[:4]))
        self.view.layoutParametros.lineEditMes.setValue(int(periodo[4:]))
        self.view.txtOrden.setText(orden)
        self.view.lblResultado.setText("")

    def conectarWidgets(self):
        self.view.btnCerrar.clicked.connect(self.Cerrar)
        self.view.btnIniciar.clicked.connect(self.Informa)

    def Cerrar(self):
        # Antes se cerraba todo el sistema, no solo este dialogo.
        self.view._want_to_close = True
        self.view.close()

    def Informa(self):
        periodo = self.view.layoutParametros.cPeriodo
        orden = str(self.view.txtOrden.text()).strip()
        ptovta = str(self.view.txtPtoVta.text()).strip()
        if (periodo, orden) == calcular_periodo_orden_actual():
            mostrar_advertencia(
                "Rendir CAEA",
                "Esa es la quincena actual: todavia no cerro. "
                "Rinda la quincena anterior.",
            )
            return
        if self._future is not None and not self._future.done():
            return
        self.view.btnIniciar.setEnabled(False)
        self.view.lblResultado.setText("Rendiendo CAEA...")
        self._future = self._executor.submit(
            self._rendir_y_avisar, periodo, orden, ptovta
        )

    def _rendir(self, periodo, orden, ptovta):
        """Corre en el worker: no toca ningun widget de Qt."""
        try:
            controlador = self.controlador
            if controlador is None:
                controlador = MainController(view=VistaStub(), modo_servicio=True)
            return rendir(
                periodo,
                orden,
                empresa_id=1,
                ptovta=ptovta or None,
                controlador=controlador,
            )
        except Exception as exc:
            logging.exception("No se pudo rendir el CAEA desde el GUI")
            return {
                "periodo": periodo,
                "orden": str(orden),
                "ok": False,
                "mensaje": str(exc),
                "detalle": [],
            }

    def _rendir_y_avisar(self, periodo, orden, ptovta):
        resumen = self._rendir(periodo, orden, ptovta)
        self.terminado.emit(resumen)

    def _al_terminar(self, resumen):
        self.view.btnIniciar.setEnabled(True)
        self.view.lblResultado.setText(resumen.get("mensaje", ""))
        if not resumen.get("ok"):
            mostrar_error("Rendido de CAEA", resumen.get("mensaje", ""))
