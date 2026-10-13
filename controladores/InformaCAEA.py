from PyQt5.QtWidgets import QApplication

from controladores.ControladorBase import ControladorBase
from controladores.Main import MainController
from controladores.RendirCAEA import rendir
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
        """Delega en el servicio de rendido.

        Antes esta pantalla reimplementaba el recorrido:tomaba un solo ptovta,
        instanciaba un MainController por cada CAEA encontrado (cada uno abre
        su propia MainView) y dejaba el CAEA sin marcar como procesado si
        un comprobante fallaba, porque el for de CAEA estaba por fuera del de
        los comprobantes.
        """
        periodo = self.view.layoutParametros.cPeriodo
        orden = str(self.view.txtOrden.text()).strip()
        ptovta = str(self.view.txtPtoVta.text()).zfill(4)

        # MainController construye su MainView al instanciarse: uno solo y
        # reutilizado para toda la corrida.
        controlador = MainController()
        controlador.grabaxml = True

        try:
            resumen = rendir(
                periodo,
                orden,
                empresa_id=1,
                ptovta=ptovta,
                controlador=controlador,
            )
            print(resumen["mensaje"])
        except Exception as exc:
            print("Error al rendir el CAEA: {}".format(exc))

        self.Cerrar()