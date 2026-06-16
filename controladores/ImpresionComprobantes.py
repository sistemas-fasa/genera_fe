import os
import time
import logging
from ftplib import FTP
from os.path import join
from pathlib import Path
from threading import Thread

from PyQt5 import QtCore
from PyQt5.QtCore import QThread
from peewee import DoesNotExist

from controladores.FE import PyQRv1
from controladores.PyFPDF import PyFPDFPlantilla
from controladores.pyemail import PyEmail
from libs.Utiles import getFileName, FormatoFecha, num_after_point, FechaMysql, LeerIni
import textwrap
from modelos.CbteRelacionado import CbteRel
from modelos.Encabezado import Encabezado
from modelos.ImpresionComprobantes import Cabfact, Detfact
from modelos.ParametrosSistema import ParamSist


class ImpresionComprobantesController(QThread):

    LETRA = {
        '001': 'A',
        '002': 'A',
        '003': 'A',
        '006': 'B',
        '007': 'B',
        '008': 'B',
    }
    TIPO_CBTE = {
        '001': 'FACTURA',
        '002': 'DEBITO',
        '003': 'CREDITO',
        '006': 'FACTURA',
        '007': 'DEBITO',
        '008': 'CREDITO',
    }

    totales = {
        'dgr':0,
        'iva21':0,
        'iva105':0,
        'neto':0,
        'iva_contenido':0
    }
    idmovi = 0
    _detalle_paginas = None
    _hojas_detalle = 1

    taskFinished = QtCore.pyqtSignal()
    notifyProgress = QtCore.pyqtSignal(int)
    nrelacion = 0
    idcabfact = 0

    def run(self, *args, **kwargs):
        self.elimina_archivos_viejos()
        try:
            encabeza = Encabezado.get(
                Encabezado.nrelacion == self.nrelacion
            )
        except DoesNotExist:
            return

        impre = PyFPDFPlantilla()
        self.totales = {
            'dgr': 0,
            'iva21': 0,
            'iva105': 0,
            'neto': 0,
            'iva_contenido':0
        }
        cArchivo = getFileName("{}-{}-{}".format(
            encabeza.tipocbte, encabeza.puntovta, encabeza.cbtenro
        ), True)
        cab = Cabfact.get(
            Cabfact.idcabfact == self.idcabfact
        )
        if cab.carpeta_guardado.strip():
            if not os.path.isdir(cab.carpeta_guardado.strip()):
                os.mkdir(cab.carpeta_guardado.strip())
            cArchivoPDF = join(cab.carpeta_guardado, '{}.pdf'.format(cArchivo))
        else:
            cArchivoPDF = join('pdf', '{}.pdf'.format(cArchivo))

        impre.CUIT = 'CUIT: {}'.format(encabeza.empresa.cuit)
        impre.IIBB = 'IIBB: {}'.format(encabeza.empresa.cuit)
        impre.inicio_actividades = encabeza.empresa.inicio_actividades
        impre.logo = encabeza.empresa.logo
        # Registrar valor de logo en el logging del sistema (valor crudo + existencia)
        logger = logging.getLogger('sistema')
        logo_val = getattr(impre, 'logo', None)
        logo_exists = False
        try:
            if isinstance(logo_val, str) and logo_val:
                logo_exists = os.path.exists(logo_val)
        except Exception:
            logo_exists = False
        logger.info("Impre.logo=%r exists=%s", logo_val, logo_exists)
        logger.info("Llamando a impre.Cabecera() con logo=%r", impre.logo)
        impre.Cabecera()
        self.CreaQR(impre, encabeza)
        plantilla = ParamSist.ObtenerParametro("PLANTILLA_COMPROBANTE")
        if plantilla and os.path.isfile(plantilla):
            impre.CargarFormato(plantilla)
        else:
            impre.CargarFormato('plantillas/factura.csv')
        impre.CrearPlantilla()
        self.encabezado_comprobante(impre, encabeza)
        self.detalle_comprobante(impre)
        self.pie_comprobante(impre, encabeza)
        impre.ProcesarPlantilla(
            hojas=self._hojas_detalle,
            on_page=self._set_campos_pagina_detalle
        )
        impre.GenerarPDF(cArchivoPDF)
        if cab.correos:
            self.envia_correo(cArchivoPDF, encabeza)
        # self.sube_ftp_fasa(cArchivoPDF, "{}-{}-{}.pdf".format(
        #     encabeza.tipocbte, encabeza.puntovta, encabeza.cbtenro
        # ))
        self.taskFinished.emit()

    def encabezado_comprobante(self, impre, encabeza):
        impre.EstableceCampo('TipoCBTE', encabeza.tipocbte)
        impre.EstableceCampo('LETRA', self.LETRA[encabeza.tipocbte])
        impre.EstableceCampo('ComprobanteEx.L', self.TIPO_CBTE[encabeza.tipocbte])
        impre.EstableceCampo('Fecha', FormatoFecha(encabeza.fechacbte, formato='dma'))
        impre.EstableceCampo('Numero', '{}-{}'.format(encabeza.puntovta, encabeza.cbtenro))

        cab = Cabfact.get(
            Cabfact.idcabfact == self.idcabfact
        )
        self.idmovi = cab.idmovi
        impre.EstableceCampo('Cliente.Nombre', '{}'.format(cab.razon_social))
        impre.EstableceCampo('Cliente.CUIT', '{}'.format(encabeza.nrodoc))
        impre.EstableceCampo('Cliente.Domicilio', '{}'.format(cab.domicilio))
        impre.EstableceCampo('iva_cli', '{}'.format(cab.tipo_iva))
        impre.EstableceCampo('forma_pago', '{}'.format(cab.cond_vta))
        impre.EstableceCampo('kg_total.value', '{}'.format(cab.kg_total))
        impre.EstableceCampo('obs.value', '{}'.format(cab.observaciones if cab.observaciones else ''))
        impre.EstableceCampo('vendedor.value', '{}'.format(cab.vendedor))
        impre.EstableceCampo('cajero.value', '{}'.format(cab.cajero))

        cbterel = CbteRel.select().where(
            CbteRel.nrelacion == encabeza.nrelacion
        )
        relacionado = ''
        for c in cbterel:
            relacionado += '{}-{}'.format(c.ptovta, c.nrocbte)

        if cab.rem_rel:
            impre.EstableceCampo('cbte-rel.value', cab.rem_rel.strip())
            impre.EstableceCampo('cbte-rel.label', 'Rem. Fact.')
        else:
            impre.EstableceCampo('cbte-rel.value', relacionado)

        # impre.AgregarCampo("empresa", 'T', 150, 350, 0, 0,
        #                     size=70, rotate=45, foreground=0x808080, priority=-1, text="{}".format(encabeza.empresa.nombre))

    def detalle_comprobante(self, impre):
        detalles = Detfact.select().where(
            Detfact.idcabfact == self.idcabfact
        )
        lineas = []
        logger = logging.getLogger('sistema')

        def _wrap_to_slots(impre_obj, texto, start_line, max_slots=35, slot_base='Item.Descripcion'):
            # localizar campo base en la plantilla para estimar ancho y tamaño de fuente
            elems = {e['name']: e for e in getattr(impre_obj, 'elements', [])}
            base = elems.get(slot_base) or elems.get(f"{slot_base}01")
            if base:
                slot_width = float(base.get('x2', 0)) - float(base.get('x1', 0))
                font_size = float(base.get('size', 8))
            else:
                # fallback empírico
                slot_width = 78.0
                font_size = 8.0
            # aproximación: chars per line
            try:
                width_chars = max(20, int((slot_width / (font_size * 0.35))))
            except Exception:
                width_chars = 60

            texto = (texto or '').replace('\r\n', '\n').replace('\r', '\n')
            parts = []
            for p in texto.split('\n'):
                wrapped = textwrap.wrap(p, width=width_chars) or ['']
                parts.extend(wrapped)
            # limitar a los slots disponibles desde start_line
            max_allowed = max_slots - (start_line - 1)
            return parts[:max_allowed]

        for det in detalles:
            self.totales['iva21'] += float(det.iva) if det.alicuota == 21 else 0
            self.totales['iva105'] += float(det.iva) if det.alicuota == 10.5 else 0
            self.totales['dgr'] += float(det.dgr)
            self.totales['neto'] += float(det.total)
            self.totales['iva_contenido'] += (det.total - (det.total / (1+(det.alicuota/100))))
            logger.debug("IVA Contenido: %s", self.totales['iva_contenido'])

            descripcion = f'{det.detext if det.detext else det.detalle}'.strip()
            wrapped_lines = _wrap_to_slots(impre, descripcion, 1, max_slots=999999)

            if not wrapped_lines:
                wrapped_lines = ['']

            for idx, wline in enumerate(wrapped_lines):
                item_linea = {
                    'descripcion': wline,
                    'primera_linea': idx == 0,
                }
                # la primera línea contiene los datos del item (cantidad, codigo, precio, importes)
                if idx == 0:
                    item_linea.update({
                        'cantidad': round(det.cantidad, num_after_point(det.cantidad)),
                        'unidad': det.unidad,
                        'codigo': det.codigo,
                        'precio': round(det.unitario, 2),
                        'alicuota': det.alicuota,
                        'importe_iva': round(det.iva, 2),
                        'importe': round(det.total, 2),
                    })
                lineas.append(item_linea)

        lineas_por_hoja = 35
        if not lineas:
            self._detalle_paginas = [[]]
        else:
            self._detalle_paginas = [
                lineas[i:i + lineas_por_hoja]
                for i in range(0, len(lineas), lineas_por_hoja)
            ]
        self._hojas_detalle = max(1, len(self._detalle_paginas))

    def _set_campos_pagina_detalle(self, template, hoja, hojas):
        # limpiar slots de items para evitar arrastre entre páginas
        for i in range(1, 36):
            num_key = str(i).zfill(2)
            template.set('Item.nro_{}'.format(num_key), '')
            template.set('Item.Cantidad{}'.format(num_key), '')
            template.set('Item.Unidad{}'.format(num_key), '')
            template.set('Item.Codigo{}'.format(num_key), '')
            template.set('Item.Precio{}'.format(num_key), '')
            template.set('Item.AlicuotaIva{}'.format(num_key), '')
            template.set('Item.ImporteIva{}'.format(num_key), '')
            template.set('Item.Importe{}'.format(num_key), '')
            template.set('Item.Descripcion{}'.format(num_key), '')

        pagina_items = []
        pagina_idx = hoja - 1
        if self._detalle_paginas and 0 <= pagina_idx < len(self._detalle_paginas):
            pagina_items = self._detalle_paginas[pagina_idx]

        for i, item in enumerate(pagina_items, start=1):
            num_key = str(i).zfill(2)
            template.set('Item.Descripcion{}'.format(num_key), item.get('descripcion', ''))
            if item.get('primera_linea'):
                template.set('Item.nro_{}'.format(num_key), num_key)
                template.set('Item.Cantidad{}'.format(num_key), item.get('cantidad', ''))
                template.set('Item.Unidad{}'.format(num_key), item.get('unidad', ''))
                template.set('Item.Codigo{}'.format(num_key), item.get('codigo', ''))
                template.set('Item.Precio{}'.format(num_key), item.get('precio', ''))
                template.set('Item.AlicuotaIva{}'.format(num_key), item.get('alicuota', ''))
                template.set('Item.ImporteIva{}'.format(num_key), item.get('importe_iva', ''))
                template.set('Item.Importe{}'.format(num_key), item.get('importe', ''))

    def pie_comprobante(self, impre, encabeza):
        impre.EstableceCampo('DGR.value', round(self.totales['dgr'], 2))
        impre.EstableceCampo('IVA10.5', round(self.totales['iva105'], 2))
        impre.EstableceCampo('IVA21', round(self.totales['iva21'], 2))
        impre.EstableceCampo('subtotal', round(self.totales['neto'], 2))
        impre.EstableceCampo('TOTAL', round(
            self.totales['neto'] +
            self.totales['iva105'] +
            self.totales['iva21'] +
            self.totales['dgr'],
            2))
        impre.EstableceCampo('CAE', encabeza.cae)
        impre.EstableceCampo('CAE.Vencimiento', FormatoFecha(encabeza.vencecae, formato='dma'))
        impre.EstableceCampo('CodigoBarras', '{}{}{}{}{}'.format(
            encabeza.empresa.cuit, encabeza.tipocbte, encabeza.puntovta, encabeza.cae, FechaMysql(encabeza.fechacbte)
        ))
        impre.EstableceCampo('CodigoBarrasLegible','{}{}{}{}{}'.format(
            encabeza.empresa.cuit, encabeza.tipocbte, encabeza.puntovta, encabeza.cae, FechaMysql(encabeza.fechacbte)
        ))
        impre.EstableceCampo('idmovi', self.idmovi)
        impre.EstableceCampo('idmovi.codigobarras', self.idmovi)
        cab = Cabfact.get(
            Cabfact.idcabfact == self.idcabfact
        )
        impre.EstableceCampo('motivos_ds1', cab.mensaje1)
        impre.EstableceCampo('motivos_ds2', cab.mensaje2)
        impre.EstableceCampo('motivos_ds3', cab.mensaje3)
        impre.EstableceCampo('cuentas', encabeza.empresa.imagen_cta_bacaria)
        if self.LETRA[encabeza.tipocbte] == 'B':
            impre.EstableceCampo('titulo_ley_27743', 'Regimen de Transparencia Fiscal al Consumidor (LEY 27.743)')
            impre.EstableceCampo('datos_ley_27743', f'IVA Contenido: ${round(self.totales["iva_contenido"], 2)}')

    def envia_correo(self, cArchivoPDF, encabeza):
        from controladores.EnvioEmailsPendientes import encolar_email
        from modelos.ParametrosSistema import ParamSist
        
        cab = Cabfact.get(
            Cabfact.idcabfact == self.idcabfact
        )
        
        # Preparar destinatarios
        destinatario = cab.correos
        
        # CC configurable desde parámetros del sistema (con fallback al hardcodeado)
        cc_facturas = ParamSist.ObtenerParametro("EMAIL_CC_FACTURAS")
        if not cc_facturas:
            cc_facturas = "fe@ferreteriaavenida.com.ar"
        
        # Preparar asunto
        motivo = "Se envia comprobante electronico adjunto {}".format(cab.razon_social)
        
        # Preparar cuerpo del mensaje
        if cab.mensaje_html:
            cuerpo_html = cab.mensaje_html
        elif encabeza.empresa.firma_correo:
            cuerpo_html = encabeza.empresa.firma_correo
        else:
            cuerpo_html = "<p>Se envía comprobante electrónico adjunto</p>"
        
        # Encolar el email en lugar de enviarlo directamente
        try:
            encolar_email(
                destinatario=destinatario,
                asunto=motivo,
                cuerpo_html=cuerpo_html,
                cuerpo_texto="Se envía comprobante electrónico adjunto",
                adjunto_ruta=cArchivoPDF,
                adjunto_nombre=os.path.basename(cArchivoPDF),
                cco=cc_facturas,  # Usar CCO en lugar de CC para que el cliente no vea
                quien_envia=cab.remitente if cab.remitente else None # Usar remitente personalizado si está definido
            )
        except Exception as e:
            cab.error = f"Error al encolar email: {e}"
            cab.save()

    def elimina_archivos_viejos(self):
        workdir = os.path.abspath('pdf')
        now = time.time()
        old = now - 7 * 24 * 60 * 60

        try:
            for f in os.listdir(workdir):
                path = os.path.join(workdir, f)
                if os.path.isfile(path):
                    stat = os.stat(path)
                    if stat.st_ctime < old:
                        os.remove(path) # uncomment when you will sure :)
        except:
            pass

    def sube_ftp_fasa(self, archivo, archivo_ftp):
        # file_path = Path(os.path.abspath(archivo))
        file_path = str(os.path.abspath(archivo))

        with FTP('ferreteriaavenida.com.ar', 'reventa@ferreteriaavenida.com.ar', 'Hor298') as ftp, open(file_path, 'rb') as file:
            ftp.cwd('facturas/')
            try:
                ftp.delete(archivo_ftp)
            except:
                pass
            ftp.storbinary('STOR {}'.format(archivo_ftp), file)
            # ftp.rename(file_path, archivo_ftp)

    def CreaQR(self, impre, encabeza):
        pyqr = PyQRv1()
        pyqr.CrearArchivo()
        ver = 1
        fecha = FormatoFecha(encabeza.fechacbte, formato='afip')
        cuit = ParamSist.ObtenerParametro("CUIT_EMPRESA").replace('-', '')
        if not cuit:
            cuit = LeerIni(clave='cuit', key='WSFEv1').replace('-', '')
        pto_vta = encabeza.puntovta
        tipo_cmp = encabeza.tipocbte
        nro_cmp = encabeza.cbtenro
        importe = round(encabeza.imptotal, 2)
        moneda_id = "PES"
        moneda_ctz = "1.000"
        tipo_doc_rec = encabeza.tipodoc
        nro_doc_rec = encabeza.nrodoc.replace('-', '')
        tipo_cod_aut = 'E' if encabeza.tipows.strip() == 'WS' else 'A'
        cod_aut = encabeza.cae
        url = pyqr.GenerarImagen(
            ver, fecha, cuit, pto_vta, tipo_cmp, nro_cmp,
            importe, moneda_id, moneda_ctz, tipo_doc_rec, nro_doc_rec,
            tipo_cod_aut, cod_aut
        )
        impre.AgregarDato("QR", pyqr.Archivo)

