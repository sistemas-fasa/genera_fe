import os
import sys

from fpdf import FPDF, Template

from libs.Utiles import inicializar_y_capturar_excepciones, LeerIni, imagen, FormatoFecha
from modelos.ParametrosSistema import ParamSist

__version__ = "1.0"
DEBUG = LeerIni("debug") == 'S'

class PyFPDF(FPDF):

    def EncabezadoEmpresa(self, imprimex=True):
        #logo
        logo = ParamSist.ObtenerParametro("LOGO_ENCABEZADO")
        if logo:
            self.image(imagen(logo), 0, 0, 33)
        #titulo
        #fuente
        self.set_font('Courier', '', 15)
        self.set_xy(30, 0)
        self.set_font_size(10.)
        self.cell(0,4, ParamSist.ObtenerParametro('EMPRESA'), border=0)
        self.set_x(100)
        if imprimex:
            self.set_font_size(20.)
            self.cell(0,4, "(X)", border=0)
        self.set_font_size(8.)
        self.set_x(120)
        self.cell(0,4,u"Tel: {} CUIT: {}".format(ParamSist.ObtenerParametro("TELEFONO_EMPRESA"),
                                                ParamSist.ObtenerParametro('CUIT_EMPRESA')),border=0,ln=5)
        self.set_x(30)
        self.cell(35,4,u"{}".format(ParamSist.ObtenerParametro('DOMICILIO_EMPRESA')),border=0, ln=5)
        self.set_x(120)
        if imprimex:
            self.set_font_size(6.)
            self.cell(0, 4, u"Documento no valido como factura", border=0)
        self.set_font_size(10.)
        self.set_x(160)
        self.cell(0, 4, u"{}".format(ParamSist.ObtenerParametro('TIPO_RESP_EMPRESA')), border=0, ln=1)
        self.set_x(30)
        self.cell(35, 4, u'Ingreso Brutos: {}'.format(ParamSist.ObtenerParametro("IIBB_EMPRESA")), ln=1)

    def PiePagina(self):
        self.ln(4)
        self.line(0, self.get_y(), 230, self.get_y())
        self.set_x(5)
        self.cell(210,4, u"{}".format(ParamSist.ObtenerParametro('DOMICILIO_EMPRESA')),border=0, ln=1, align='C')
        self.set_x(5)
        self.cell(210,4, u"{}".format(ParamSist.ObtenerParametro('LOCALIDAD_EMPRESA')), border=0, ln=1, align='C')
        self.set_x(5)
        self.cell(210, 4, u"Tel: {} Email: {} Web: {}".format(ParamSist.ObtenerParametro("TELEFONO_EMPRESA"),
                                            ParamSist.ObtenerParametro('EMAIL_EMPRESA'),
                                            ParamSist.ObtenerParametro('WEB_EMPRESA')), border=0, ln=1, align='C')


class PyFPDFPlantilla(FPDF):

    def __init__(self):
        super().__init__()
        self.title = ''
        self.logo = None
        self.email_empresa = ''
        self.telefono_empresa = ''
        self.inicio_actividades = ''
        self.cond_iva = ''
        self.IIBB = ''
        self.membrete2 = ''
        self.CAE = ''
        self.Exception = self.Traceback = ""
        self.InstallDir = LeerIni('iniciosistema')
        if sys.platform == "win32":
            self.Locale = "Spanish_Argentina.1252"
        elif sys.platform == "linux2":
            self.Locale = "es_AR.utf8"
        else:
            # plataforma no soportada aun (jython?), emular
            self.Locale = None
        self.FmtCantidad = self.FmtPrecio = "0.2"
        self.CUIT = ''
        self.elements = []
        self.datos = []
        self.pdf = {}
        self.comprobante = {}
        self.pagina_web = ''
        self.empresa = ''
        self.membrete1 = ''
        self.LanzarExcepciones = True

    @inicializar_y_capturar_excepciones
    def CrearPlantilla(self, papel="A4", orientacion="portrait"):
        "Iniciar la creación del archivo PDF"

        # sanity check:
        for field in self.elements:
            # si la imagen no existe, eliminar nombre para que no falle fpdf
            if field['type'] == 'I' and not os.path.exists(field["text"]):
                # ajustar rutas relativas a las imágenes predeterminadas:
                if os.path.exists(os.path.join(self.InstallDir, field["text"])):
                    field['text'] = os.path.join(self.InstallDir, field["text"])
                else:
                    field['text'] = ""

        # genero el renderizador con propiedades del PDF
        t = Template(elements=self.elements,
                     format=papel, orientation=orientacion,
                     title="%s " % self.title,
                     author="CUIT %s" % self.CUIT,
                     subject="CAE %s" % self.CAE,
                     keywords=self.empresa,
                     creator=' %s ' % __version__,)
        self.template = t
        return True

    @inicializar_y_capturar_excepciones
    def CargarFormato(self, archivo="factura.csv"):
        "Cargo el formato de campos a generar desde una planilla CSV"

        # si no encuentro archivo, lo busco en el directorio predeterminado:
        if not os.path.exists(archivo):
            archivo = os.path.join(self.InstallDir, "plantillas", os.path.basename(archivo))

        if DEBUG:
            print("abriendo archivo ", archivo)

        for lno, linea in enumerate(open(archivo.encode('latin1')).readlines()):
            if DEBUG:
                print("procesando linea ", lno, linea)
            args = []
            for i, v in enumerate(linea.split(";")):
                if not v.startswith("'"):
                    v = v.replace(",", ".")
                else:
                    v = v  # .decode('latin1')
                if v.strip() == '':
                    v = None
                else:
                    v = eval(v.strip())
                args.append(v)
            self.AgregarCampo(*args)
        return True

    @inicializar_y_capturar_excepciones
    def AgregarCampo(self, nombre, tipo, x1, y1, x2, y2,
                     font="Arial", size=12,
                     bold=False, italic=False, underline=False,
                     foreground=0x000000, background=0xFFFFFF,
                     align="L", text="", priority=0, **kwargs):
        "Agrego un campo a la plantilla"
        # convierto colores de string (en hexadecimal)
        if isinstance(foreground, str):
            foreground = int(foreground, 16)
        if isinstance(background, str):
            background = int(background, 16)
        ##if isinstance(text, str): text = text.encode("latin1")
        field = {
            'name': nombre,
            'type': tipo,
            'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
            'font': font, 'size': size,
            'bold': bold, 'italic': italic, 'underline': underline,
            'foreground': foreground, 'background': background,
            'align': align, 'text': text, 'priority': priority}
        field.update(kwargs)
        self.elements.append(field)
        return True

    @inicializar_y_capturar_excepciones
    def GenerarPDF(self, archivo="", *args, **kwargs):
        "Generar archivo de salida en formato PDF"
        if not archivo:
            dest = "S"  # devolver buffer (string)
        else:
            dest = "F"  # guardar en archivo
        return self.template.render(archivo, dest)

    def AgregarDato(self, campo, valor, pagina='T'):
        "Agrego un dato a la factura (internamente)"
        self.datos.append({'campo': campo, 'valor': valor, 'pagina': pagina})
        return True

    @inicializar_y_capturar_excepciones
    def ProcesarPlantilla(self, num_copias=1, lineas_max=36, qty_pos='izq', hojas=1, on_page=None):
        "Generar el PDF según la factura creada y plantilla cargada"
        f = self.template
        try:
            hojas = int(hojas)
            if hojas < 1:
                hojas = 1
        except Exception:
            hojas = 1
        copias = {1: 'Original', 2: 'Duplicado', 3: 'Triplicado'}
        comprobante = self.comprobante

        for copia in range(1, num_copias + 1):
            # completo campos y hojas
            for hoja in range(1, hojas + 1):
                f.add_page()
                f.set('copia', copias.get(copia, "Adicional %s" % copia))
                f.set('hoja', str(hoja))
                f.set('hojas', str(hojas))
                f.set('Pagina', 'Pagina %s de %s' % (hoja, hojas))

                # establezco datos según configuración:
                for d in self.datos:
                    if d['pagina'] == 'P' and hoja != 1:
                        continue
                    if d['pagina'] == 'U' and hojas != hoja:
                        # no es la última hoja
                        continue
                    f.set(d['campo'], d['valor'])
                    for k, v in list(comprobante.items()):
                        f.set(k, v)

                # Permite completar campos dinámicos por cada hoja
                if callable(on_page):
                    on_page(f, hoja, hojas)

    @inicializar_y_capturar_excepciones
    def MostrarPDF(self, archivo, imprimir=False):
        if sys.platform.startswith(("linux", 'java')):
            os.system("evince ""%s""" % archivo)
        else:
            operation = imprimir and "print" or ""
            os.startfile(archivo, operation)
        return True

    @inicializar_y_capturar_excepciones
    def Cabecera(self, *args, **kwargs):
        import logging
        logger = logging.getLogger('sistema')
        
        logo = self.logo
        logger.info("PyFPDF.Cabecera() - logo original: %r", logo)
        
        logo = imagen(logo)
        logger.info("PyFPDF.Cabecera() - logo tras imagen(): %r, existe: %s", logo, os.path.isfile(logo) if logo else False)
        
        if os.path.isfile(logo):
            self.AgregarDato("Logo", logo)
            logger.info("PyFPDF.Cabecera() - Logo agregado a datos: %r", logo)
        else:
            logger.warning("PyFPDF.Cabecera() - Logo NO agregado (no es archivo válido): %r", logo)

        self.AgregarDato("EMPRESA", "Razon social: {}".format(self.empresa))
        self.AgregarDato("MEMBRETE1", "Domicilio Comercial: {}".format(self.membrete1))
        self.AgregarDato("MEMBRETE2", self.membrete2)
        self.AgregarDato("CUIT", self.CUIT)
        self.AgregarDato("IIBB", self.IIBB)
        self.AgregarDato("IVA", "Condicion frente al IVA: {}".format(self.cond_iva))
        self.AgregarDato("INICIO", "Fecha inicio actividades: {}".format(
            FormatoFecha(self.inicio_actividades, formato='dma')
        ))

    @inicializar_y_capturar_excepciones
    def PiePagina(self, *args, **kwargs):
        ok = self.AgregarDato("DOMICILIO_PIEPAGINA",
                              "Domicilio Comercial: {}".format(self.membrete1))
        ok = self.AgregarDato("DOMICILIO_PIEPAGINA_1",
                              "Domicilio Comercial: {}".format(self.membrete2))
        self.AgregarDato("DOMICILIO_PIEPAGINA_2",
                         u"Tel: {} Email: {} Web: {}".format(self.telefono_empresa,
                                            self.email_empresa,
                                            self.pagina_web))
    @inicializar_y_capturar_excepciones
    def EstableceCampo(self, campo='', valor='', *args, **kwargs):
        f = self.template
        # Persistir valor para que se aplique a todas las hojas durante ProcesarPlantilla
        self.comprobante[campo] = valor
        # Si ya existe una página activa, también setearlo inmediatamente
        if getattr(f, 'pg_no', 0):
            f.set(campo, valor)