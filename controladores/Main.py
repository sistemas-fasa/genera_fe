# coding=utf-8
import calendar
from concurrent.futures import ThreadPoolExecutor
import os
import traceback
import logging
import time
from datetime import datetime, timedelta

import peewee
from PyQt5.QtWidgets import QApplication
from peewee import fn

from controladores.ConsultaPadronAfip import PadronAfip
from controladores.ControladorBase import ControladorBase
from controladores.EnvioEmailsPendientes import enviar_email_en_hilo, encolar_email, reactivar_emails_retrasados
from controladores.FCE import WsFECred
from controladores.FE import FEv1
from controladores.ImpresionComprobantes import ImpresionComprobantesController
from controladores.WSConstComp import WSConstComp
from libs.Utiles import LeerIni, FechaMysql, envia_correo, DeCodifica, inicializar_y_capturar_excepciones, desencriptar, \
    check_url
from modelos.CAEA import CAEA
from modelos.CUIT import CUIT
from modelos.CbteRelacionado import CbteRel
from modelos.Constataciones import Constatacion
from modelos.EmailsPendientes import EmailPendiente
from modelos.Encabezado import Encabezado
from modelos.IVA import IVA
from modelos.ImpresionComprobantes import Cabfact
from modelos.ModeloBase import ModeloBase
from modelos.Movi import Movi
from modelos.ParametrosSistema import ParamSist
from modelos.Respuestas import Respuesta
from modelos.Tributo import Tributo
from pyafipws import wsfev1
from vistas.Main import MainView


def _normalizar_texto_config(valor):
    if valor is None:
        return ''
    if isinstance(valor, bytes):
        return valor.decode('ascii', errors='ignore').strip()
    return str(valor).strip()


def _email_admin_notificaciones():
    return _normalizar_texto_config(
        LeerIni(clave='email_admin_notificaciones') or
        ParamSist.ObtenerParametro('EMAIL_ADMIN_NOTIFICACIONES')
    )


def _email_alerta_fe_to():
    return _normalizar_texto_config(
        LeerIni(clave='email_alerta_fe_to') or
        LeerIni(clave='to_address', key='email') or
        _email_admin_notificaciones()
    )


def _email_alerta_fe_from():
    return _normalizar_texto_config(
        LeerIni(clave='email_alerta_fe_from') or
        LeerIni(clave='from_address', key='email') or
        os.getenv('SMTP_FROM')
    )


def enviar_correo_alerta_operativa(to_address, from_address, subject, message, password_email):
    if not _normalizar_texto_config(to_address):
        logging.warning("No se envio alerta operativa por email: falta destinatario configurado")
        return False

    envia_correo(
        to_address=to_address,
        from_address=from_address,
        subject=subject,
        message=message,
        password_email=password_email
    )
    return True


class MainController(ControladorBase):

    lProcesa = True
    cae = ''
    vencecae = ''
    errmsg = ''
    resultado = ''
    motivoobs = ''
    comprobante = ''
    xml_response = ''
    xml_request = ''
    grabaxml = False
    cuit = LeerIni(clave='cuit', key='WSFEv1')
    NOTAS_CREDITO_DEBITO = ['003', '008', '013', '002', '007', '012', '202', '203']
    afip_disponible = None
    afip_estados = None
    afip_ultima_verificacion = None
    afip_intervalo_verificacion = timedelta(minutes=2)

    def __init__(self):
        super(MainController, self).__init__()
        self.view = MainView()
        self.view.initUi()
        self.conectarWidgets()
        self.model = ModeloBase()
        self.model.getDb()
        self.afip_intervalo_verificacion = self._leer_intervalo_verificacion_afip()
        self._email_executor = ThreadPoolExecutor(max_workers=5)
        self._email_futures = {}
        destinatario, cc = self._destinatarios_alerta_afip()
        logging.info(
            "Monitor AFIP inicializado - intervalo de verificacion: %s minuto(s)",
            int(self.afip_intervalo_verificacion.total_seconds() // 60)
        )
        logging.info(
            "Monitor AFIP destinatarios - to: %s | cc: %s",
            destinatario,
            cc or 'sin cc'
        )
        if self._debe_notificar_arranque_afip():
            self._notificar_arranque_monitor_afip(destinatario, cc)
        else:
            logging.info("Monitor AFIP arranque - notificacion por email deshabilitada por configuracion")

    def _leer_intervalo_verificacion_afip(self):
        valor_ini = LeerIni(clave='afip_intervalo_verificacion_minutos')
        try:
            minutos = int(valor_ini) if valor_ini else 2
            if minutos < 1:
                minutos = 1
        except (TypeError, ValueError):
            minutos = 2
        return timedelta(minutes=minutos)

    def _destinatarios_alerta_afip(self):
        destinatario = _normalizar_texto_config(
            LeerIni(clave='afip_alerta_to') or _email_admin_notificaciones()
        )
        cc = _normalizar_texto_config(LeerIni(clave='afip_alerta_cc'))
        return destinatario, cc

    def _debe_notificar_arranque_afip(self):
        valor = (LeerIni(clave='afip_notificar_arranque') or 'S').strip().upper()
        return valor == 'S'

    def _notificar_arranque_monitor_afip(self, destinatario, cc):
        if not destinatario:
            logging.warning("Monitor AFIP arranque - no se envia email porque falta destinatario configurado")
            return

        momento = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        asunto = 'Monitor AFIP iniciado'
        mensaje = (
            'Se inicio el monitor de estado de servicios AFIP.\n\n'
            'Fecha/Hora: {}\n'
            'Intervalo de verificacion: {} minuto(s)\n\n'
            'Este aviso se envia automaticamente al iniciar el sistema.'
        ).format(
            momento,
            int(self.afip_intervalo_verificacion.total_seconds() // 60)
        )

        encolar_email(
            destinatario=destinatario,
            asunto=asunto,
            cuerpo_texto=mensaje,
            cc=cc
        )

    def conectarWidgets(self):
        self.view.btnCerrar.clicked.connect(self.Cerrar)
        self.view.btnIniciar.clicked.connect(self.GeneraFE)
        self.view.btnToggleEmails.clicked.connect(self.ToggleEnvioEmails)
        self._actualizar_boton_emails()

    def _envio_emails_activo(self):
        return ParamSist.ObtenerParametro('ENVIO_EMAILS_ACTIVO', 'S').strip().upper() != 'N'

    def _actualizar_boton_emails(self):
        activo = self._envio_emails_activo()
        if activo:
            self.view.btnToggleEmails.setText('Emails: ACTIVO')
            self.view.btnToggleEmails.setStyleSheet('')
        else:
            self.view.btnToggleEmails.setText('Emails: PAUSADO')
            self.view.btnToggleEmails.setStyleSheet('background-color: #e67e22; color: white;')

    def ToggleEnvioEmails(self):
        activo = self._envio_emails_activo()
        nuevo_valor = 'N' if activo else 'S'
        ParamSist.GuardarParametro('ENVIO_EMAILS_ACTIVO', nuevo_valor)
        self._actualizar_boton_emails()
        if nuevo_valor == 'S':
            logging.info("✅ Envío de emails activado - se procesarán los correos pendientes")
        else:
            logging.info("⏸️ Envío de emails pausado - los correos se acumularán en estado 'pendiente'")

    def Cerrar(self):
        self.lProcesa = False
        try:
            self._email_executor.shutdown(wait=False, cancel_futures=True)
        except Exception:
            logging.exception("Error cerrando executor de emails")
        QApplication.exit(1)

    @inicializar_y_capturar_excepciones
    def GeneraFE(self, *args, **kwargs):
        self.view.btnIniciar.setEnabled(False)
        #hay_internet = check_url('http://www.google.com.ar')
        # hay_internet = True
        while self.lProcesa:
            QApplication.processEvents()
            afip_online = self.VerificarEstadoAFIP()
            if afip_online:
                self.GeneraCAE() #si tenemos internet obtenemos CAE
            else:
                self.view.lblProcesamiento.setText("AFIP no disponible. Reintentando...")
            self.ImpresionFactura()
            self.GeneraCAEA() #en caso de que no haya internet usamos el CAEA
            # self.Constatacion()
            # self.ObtieneDatosCUIT()
            self.EnviaCorreos()
            time.sleep(0.5)

    def _estado_dummy_afip(self):
        estados = {
            'AppServer': '',
            'DbServer': '',
            'AuthServer': ''
        }

        try:
            wsfe = FEv1()
            if LeerIni(clave='homo') == 'S':
                ok = wsfe.Conectar("")
            else:
                wsdl_prod = LeerIni(clave='url_prod', key='WSFEv1')
                ok = wsfe.Conectar("", wsdl_prod)

            if not ok:
                logging.warning("No se pudo conectar a WSFEv1 para FEDummy: %s", wsfe.Excepcion)
                return False, estados

            ok_dummy = wsfe.Dummy()
            estados['AppServer'] = (wsfe.AppServerStatus or '').upper()
            estados['DbServer'] = (wsfe.DbServerStatus or '').upper()
            estados['AuthServer'] = (wsfe.AuthServerStatus or '').upper()

            disponible = bool(ok_dummy) and all(valor == 'OK' for valor in estados.values())
            return disponible, estados
        except Exception as e:
            logging.warning("Error verificando FEDummy AFIP: %s", e)
            return False, estados

    def _notificar_estado_afip(self, disponible, estados=None, estados_anteriores=None):
        destinatario, cc = self._destinatarios_alerta_afip()
        if not destinatario:
            logging.warning("Monitor AFIP estado - no se envia email porque falta destinatario configurado")
            return

        momento = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        estados = estados or {}
        estados_anteriores = estados_anteriores or {}
        detalle_estados = (
            'AppServer: {}\nDbServer: {}\nAuthServer: {}'
        ).format(
            estados.get('AppServer', 'N/D'),
            estados.get('DbServer', 'N/D'),
            estados.get('AuthServer', 'N/D')
        )
        detalle_estados_anteriores = (
            'AppServer: {}\nDbServer: {}\nAuthServer: {}'
        ).format(
            estados_anteriores.get('AppServer', 'N/D'),
            estados_anteriores.get('DbServer', 'N/D'),
            estados_anteriores.get('AuthServer', 'N/D')
        )

        if disponible:
            asunto = 'AFIP recuperado - servicios en linea'
            mensaje = (
                'Se detecto cambio de estado en servicios AFIP (FEDummy).\n\n'
                'Fecha/Hora: {}\n'
                'Estado anterior:\n{}\n\n'
                'Estado de servidores:\n{}\n\n'
                'Este aviso se envia automaticamente ante cambio de estado.'
            ).format(momento, detalle_estados_anteriores, detalle_estados)
        else:
            asunto = 'ALERTA: AFIP fuera de linea'
            mensaje = (
                'Se detecto cambio de estado en servicios AFIP (FEDummy).\n\n'
                'Fecha/Hora: {}\n'
                'Estado anterior:\n{}\n\n'
                'Estado de servidores:\n{}\n\n'
                'Este aviso se envia automaticamente ante cambio de estado.'
            ).format(momento, detalle_estados_anteriores, detalle_estados)

        encolar_email(
            destinatario=destinatario,
            asunto=asunto,
            cuerpo_texto=mensaje,
            cc=cc
        )

    def VerificarEstadoAFIP(self):
        ahora = datetime.now()
        if self.afip_ultima_verificacion and (ahora - self.afip_ultima_verificacion) < self.afip_intervalo_verificacion:
            return self.afip_disponible if self.afip_disponible is not None else True

        disponible, estados = self._estado_dummy_afip()
        logging.info(
            "AFIP FEDummy estado - AppServer: %s | DbServer: %s | AuthServer: %s | disponible: %s",
            estados.get('AppServer', 'N/D'),
            estados.get('DbServer', 'N/D'),
            estados.get('AuthServer', 'N/D'),
            'SI' if disponible else 'NO'
        )

        estados_anteriores = self.afip_estados
        hubo_cambio_estados = estados_anteriores is not None and estados != estados_anteriores
        if hubo_cambio_estados:
            logging.warning(
                "Cambio detectado en estado AFIP - anterior: %s | nuevo: %s",
                estados_anteriores,
                estados
            )
            self._notificar_estado_afip(
                disponible=disponible,
                estados=estados,
                estados_anteriores=estados_anteriores
            )

        self.afip_estados = estados
        self.afip_disponible = disponible

        self.afip_ultima_verificacion = ahora
        return self.afip_disponible if self.afip_disponible is not None else True

    def CreaFE(self, d, caea = None):
        ok = True
        cbterel = None
        wsfev1 = FEv1()
        wsfev1.cuit_emisor = d.empresa.cuit.encode('ascii')
        self.cuit = wsfev1.cuit_emisor
        if LeerIni(clave='homo') == 'N': #produccion
            # wsfev1.cert_prod = d.empresa.crt.strip().encode('ascii')
            # wsfev1.privatekey_prod = d.empresa.key.strip().encode('ascii')
            wsfev1.cert_prod = d.empresa.crt.strip()
            wsfev1.privatekey_prod = d.empresa.key.strip()

        wsfev1.empresa = d.empresa.codigo
        ta = wsfev1.Autenticar()
        #Setear tocken y sign de autorizacion(ticket de accesso, pasos previos)
        wsfev1.SetTicketAcceso(ta)
        #Conectar al Servicio Web de Facturacion
        #Produccion usar: *-- ok = WSFE.Conectar("", "https://servicios1.afip.gov.ar/wsfev1/service.asmx?WSDL") & & Producción
        if LeerIni(clave='homo') == 'S':
            wsfev1.Cuit = _normalizar_texto_config(
                LeerIni(clave='afip_cuit_homologacion') or wsfev1.cuit_emisor
            )
            ok = wsfev1.Conectar("") #Homologacion
        else:
            wsfev1.Cuit = _normalizar_texto_config(self.cuit)  # CUIT del emisor (debe estar registrado en la AFIP)
            ok = wsfev1.Conectar("", "https://servicios1.afip.gov.ar/wsfev1/service.asmx?WSDL")

        concepto = d.concepto
        tipo_doc = d.tipodoc
        punto_vta = d.puntovta
        # if d.empresa.emitefce: #si emite FCE controla el monto obligado
        #     obligado, minimo = WsFECred().ConsultarMontoObligado(d.nrodoc, self.cuit)
        #     if obligado and minimo < d.imptotal:
        #         tipo_cbte = str(int(d.tipocbte) + 200).zfill(3)
        #     else:
        #         tipo_cbte = d.tipocbte
        # else:
        #     tipo_cbte = d.tipocbte
        # el tipo de comprobante lo tiene que guardar correctamente el sistema que pide la generacion
        tipo_cbte = d.tipocbte
        nro_doc = d.nrodoc
        cbt_desde = int(wsfev1.UltimoComprobante(tipo=tipo_cbte, ptovta=punto_vta)) + 1
        cbt_hasta = cbt_desde
        imp_total = str(round(d.imptotal, 2))
        imp_tot_conc = "0.00"
        imp_neto = str(round(d.impneto, 2))
        imp_iva = str(round(d.impiva, 2))
        imp_trib = str(round(d.imptrib,2))
        impto_liq_rni = "0.00"
        imp_op_ex = str(round(d.impopex, 2))
        # fecha_cbte_str: YYYYMMDD string for AFIP; fecha_cbte_date: date object for comparisons
        fecha_cbte = FechaMysql(d.fechacbte)
        fecha_cbte_date = d.fechacbte
        # Fechas del periodo del servicio facturado (solo si concepto > 1)
        if concepto in [wsfev1.SERVICIOS, wsfev1.PRODUCTOYSERVICIOS]:
            fecha_serv_desde = fecha_cbte
            fecha_serv_hasta = fecha_cbte
            fecha_venc_pago = fecha_cbte
        else:
            fecha_serv_desde = ""
            fecha_serv_hasta = ""
            fecha_venc_pago = ""

        if int(tipo_cbte) in [201]:
            if fecha_cbte_date < datetime.today().date():
                fecha_venc_pago = FechaMysql(datetime.today().date())
            else:
                fecha_venc_pago = fecha_cbte

        moneda_id = "PES"
        moneda_ctz = "1.000"

        condicion_iva_receptor = d.condicion_iva_receptor_id
        
        #Llamo al WebService de Autorizacion para obtener el CAE
        wsfev1.CrearFactura(concepto, tipo_doc, nro_doc, tipo_cbte, punto_vta,
                cbt_desde, cbt_hasta, imp_total, imp_tot_conc, imp_neto,
                imp_iva, imp_trib, imp_op_ex, fecha_cbte, fecha_venc_pago,
                fecha_serv_desde, fecha_serv_hasta,
                moneda_id, moneda_ctz, 
                condicion_iva_receptor_id=condicion_iva_receptor)

        #tributo = Tributo.select().where(Tributo.nrocontrol == d.nrocontrol)
        tributo = Tributo.select().where(Tributo.nrelacion == d.nrelacion)
        for t in tributo:
            idimp = t.tributoid
            detalle = t.descripcion
            base_imp = round(t.baseimp, 2)
            alicuota = round(t.alic, 2)
            importe = str(round(t.importe, 2))
            wsfev1.AgregarTributo(tributo_id=idimp, desc=detalle, base_imp=base_imp,
                                  alic=alicuota, importe=importe)

        #iva = IVA.select().where(IVA.nrocontrol == d.nrocontrol)
        iva = IVA.select().where(IVA.nrelacion == d.nrelacion)
        for i in iva:
            id = i.ivaid
            base_imp = round(i.baseimp, 2)
            iva = round(i.importe, 2)
            wsfev1.AgregarIva(id, base_imp, iva)

        #cbterel = CbteRel.select().where(CbteRel.nrocontrol == d.nrocontrol)
        cbterel = CbteRel.select().where(CbteRel.nrelacion == d.nrelacion)
        if len(cbterel) == 0 and tipo_cbte in self.NOTAS_CREDITO_DEBITO:
            wsfev1.AgregarPeriodoComprobantesAsociados(
                fecha_desde=fecha_cbte,
                fecha_hasta=fecha_cbte
            )
            logging.warning(
                "NC/ND sin comprobante relacionado: se informa periodo asociado para nrelacion %s",
                d.nrelacion
            )
        else:
            for c in cbterel:
                tipo = c.tipocbte
                pto_vta = c.ptovta
                nro = c.nrocbte
                try:
                    movi = Movi.get(
                        Movi.tipocomp == tipo,
                        Movi.comp == '{}{}'.format(pto_vta, nro)
                    )
                    fecha_cbte_rel = FechaMysql(movi.fecha)
                except peewee.DoesNotExist:
                    fecha_cbte_rel = FechaMysql()
                print("Fecha cbte rel {}".format(fecha_cbte_rel))
                if pto_vta in ['0010', '0001', '0004']:
                    wsfev1.AgregarPeriodoComprobantesAsociados(
                        fecha_desde=fecha_cbte_rel,
                        fecha_hasta=fecha_cbte_rel
                    )
                else:
                    if int(tipo_cbte) in [202, 203]:
                        wsfev1.AgregarCmpAsoc(tipo, pto_vta, nro, fecha=fecha_cbte_rel, cuit=int(self.cuit))
                    else:
                        wsfev1.AgregarCmpAsoc(tipo, pto_vta, nro, fecha=fecha_cbte_rel)

        if int(tipo_cbte) in [201]:
            # ➕ Agregar el opcional RG (ID 27)
            # Valores válidos: "SCA" o "ADC"
            tipo_opcion = "SCA"  # Sistema de circulacion abierto
            # tipo_opcion = "ADC"  # Agente de deposito colectivo

            #debe tener cargado esos datos si no rechaza
            wsfev1.AgregarOpcional(2101, d.empresa.cbufce) #CBU
            wsfev1.AgregarOpcional(2102, d.empresa.aliasfce) # alias
                
            wsfev1.AgregarOpcional(
                opcional_id=27,        # ID obligatorio para FCE tipo Factura
                valor=tipo_opcion      # "SCA" o "ADC"
            )

        if caea:
            wsfev1.EstablecerCampoFactura('caea', d.cae)
            cae = wsfev1.CAEARegInformativo()
            #logging.warning(wsfev1.xml_request, wsfev1.xml_response)
            if self.grabaxml:
                f = open("xmlrequest.xml", "wb")
                f.write(wsfev1.xml_request)
                f.close()

                f = open("xmlresponse.xml", "wb")
                f.write(wsfev1.xml_response)
                f.close()
                respuesta = Respuesta()
                respuesta.nrelacion = d.nrelacion
                respuesta.xmlrequest = wsfev1.xml_request
                respuesta.xmlresponse = wsfev1.xml_response
                respuesta.error = wsfev1.ErrMsg
                respuesta.save()

            self.xml_response = wsfev1.xml_response
            self.xml_request = wsfev1.xml_request
        else:
            #SolicitoCAE:
            cae = wsfev1.CAESolicitar()
            self.xml_response = wsfev1.xml_response
            self.xml_request = wsfev1.xml_request
            respuesta = Respuesta()
            respuesta.nrelacion = d.nrelacion
            respuesta.xmlrequest = wsfev1.xml_request
            respuesta.xmlresponse = wsfev1.xml_response
            respuesta.error = wsfev1.ErrMsg
            respuesta.save()

        self.resultado = wsfev1.Resultado or ''
        if wsfev1.ErrMsg:
            #Ventanas.showAlert("Sistema", "ERROR {}".format(wsfev1.ErrMsg))
            self.resultado = 'E'
            self.errmsg = f'{wsfev1.ErrMsg} - {wsfev1.Obs}'
            self.xml_response = wsfev1.xml_response
            self.xml_request = wsfev1.xml_request
            ok = False
            item = [
                punto_vta, '', '', '', f'{wsfev1.ErrMsg} - {wsfev1.Obs}'
            ]
        else:
            if wsfev1.Resultado == 'R':
                #Ventanas.showAlert("Sistema", "Motivo de rechazo {}".format(wsfev1.Obs))
                self.xml_response = wsfev1.xml_response
                self.xml_request = wsfev1.xml_request
                self.motivoobs = wsfev1.Obs
                item = [
                    punto_vta, '', '', '', wsfev1.Obs
                ]
                ok = False
            else:
                self.cae = cae
                self.vencecae = wsfev1.Vencimiento
                self.comprobante = cbt_desde
                item = [
                    punto_vta, str(cbt_desde).zfill(8), cae, wsfev1.Vencimiento, ''
                ]
                print("Vencimiento cae {}".format(wsfev1.Vencimiento))

        if self.view.gridFacturas.rowCount() > 10:
            self.view.gridFacturas.removeRow(0)

        self.view.gridFacturas.AgregaItem(items=item)
        return ok

    def ObtieneCAEA(self):
        dia = datetime.now().day
        periodo = FechaMysql()[:6]
        obtener = True
        if dia < 15:
            orden = '1'
            if dia + 5 == 15:
                obtener = True
        else:
            orden = '2'
            if dia + 5 == calendar.monthrange(int(periodo[:4]), int(periodo[4:6]))[1]:
                obtener = True

        if obtener:
            try:
                data = CAEA.select().where(CAEA.periodo == periodo,
                                           CAEA.orden == orden).get()
            except CAEA.DoesNotExist:
                print("caea no existe")
                wsfe = FEv1()
                wsfe.SolicitarCAEA(periodo, orden)
                caea = CAEA()
                caea.CAEA = wsfe.CAEA
                caea.periodo = wsfe.Periodo
                caea.orden = wsfe.Orden
                caea.fchvigdesde = wsfe.FchVigDesde
                caea.fchvighasta = wsfe.FchVigHasta
                caea.fchproceso = wsfe.FchProceso
                caea.fchtopeinf = wsfe.FchTopeInf
                caea.obs = wsfe.Obs
                caea.empresa = 1 #ferreteria por ahora tengo que ver como hacer para las otras empresas
                caea.save()

    def GeneraCAE(self):
        data = Encabezado.select().where(Encabezado.resultado == '',
                                         Encabezado.listo == True,
                                         Encabezado.tipows == 'WS')
        total = data.count() or 1
        i = 1.
        to_address = _email_alerta_fe_to()
        from_email = _email_alerta_fe_from()
        if LeerIni(clave='password_email', key='email'):
            password_email = desencriptar(LeerIni(clave='password_email', key='email'), LeerIni('key'))
        else:
            password_email = os.getenv('FASA_ERROR_EMAIL_PASSWORD') or os.getenv('SMTP_PASSWORD', '')

        for d in data:
            try:
                self.view.lblProcesamiento.setText("Procesando comprobante {} de {}".format(i, total))
                self.view.avance.actualizar(i / total * 100)
                ok = self.CreaFE(d)
                if ok:
                    d.cae = self.cae
                    d.resultado = self.resultado
                    d.cbtenro = str(self.comprobante).zfill(8)
                    d.vencecae = datetime.strptime(self.vencecae, '%Y%m%d')
                else:
                    d.resultado = self.resultado if self.resultado else 'E'
                    d.errmsg = self.errmsg
                    d.motivoobs = self.motivoobs
                    d.vencecae = datetime.today()
                    d.motivoobs = self.xml_response
                    if LeerIni(clave='homo') == 'N':
                        enviar_correo_alerta_operativa(
                            to_address=to_address,
                            from_address=from_email,
                            subject='Error al generar FE',
                            message="Error: {} {}".format(DeCodifica(self.errmsg),
                                                          DeCodifica(self.motivoobs)),
                            password_email=password_email
                        )
                d.save()
                i += 1
            except Exception as e:
                d.resultado = 'E'
                d.errmsg = "Error: {}".format(e)
                d.vencecae = datetime.today()
                d.errorprog = traceback.format_exc()
                d.save()
                print ("Error: {}".format(e))
                enviar_correo_alerta_operativa(
                    to_address=to_address,
                    from_address=from_email,
                    subject='Error al generar FE',
                    message="Error: {} {}".format(e, traceback.format_exc()),
                    password_email=password_email
                )

        self.view.lblProcesamiento.setText("Sin comprobantes para procesar")
        self.view.avance.actualizar(100)

    #genera facturas con CAEA para el caso de que no haya internet
    def GeneraCAEA(self):
        data = Encabezado.select().where(Encabezado.resultado == '',
                                         Encabezado.listo == True,
                                         Encabezado.tipows == 'A')
        total = data.count() or 1
        i = 1.
        dia = datetime.now().day
        periodo = FechaMysql()[:6]
        if dia <= 15:
            orden = '1'
        else:
            orden = '2'
        datacaea = CAEA.select().where(CAEA.periodo == periodo,
                                    CAEA.orden == orden).get()

        for d in data:
            self.view.lblProcesamiento.setText("Procesando comprobante {} de {}".format(i, total))
            self.view.avance.actualizar(i / total * 100)

            try:
                encabeza = Encabezado.select(fn.MAX(Encabezado.cbtenro)).\
                    where(Encabezado.puntovta == d.puntovta, Encabezado.tipocbte == d.tipocbte).scalar()
                d.cbtenro = str(int(encabeza if encabeza else '0') + 1).zfill(8)
                d.cae = datacaea.CAEA
                d.vencecae = datacaea.fchtopeinf
                d.resultado = 'A'
                d.save()
                item = [
                    d.puntovta, d.cbtenro, d.cae, d.vencecae, ''
                ]
                if self.view.gridFacturas.rowCount() > 10:
                    self.view.gridFacturas.removeRow(0)

                self.view.gridFacturas.AgregaItem(items=item)
            except CAEA.DoesNotExist:
                d.resultado = 'E'
                d.errmsg = 'No existe CAEA para el periodo y orden'
                d.vencecae = datetime.today()
                d.save()
                enviar_correo_alerta_operativa(
                    to_address=_email_alerta_fe_to(),
                    from_address=_email_alerta_fe_from(),
                    subject='Error al generar FE con CAEA',
                    message="Error: {}".format(d.errmsg),
                    password_email=os.getenv('FASA_ERROR_EMAIL_PASSWORD') or os.getenv('SMTP_PASSWORD', '')
                )

    def Constatacion(self):
        data = Constatacion.select().where(
            Constatacion.resultado == '',
            Constatacion.listo == True
        )
        total = data.count() or 1
        i = 1.
        wsdc = WSConstComp()

        for d in data:
            if ParamSist.ObtenerParametro("CONSTATACION_COMPROBANTES") == "S":
                if LeerIni(clave='homo') == 'N':  # produccion
                    # wsdc.cert_prod = d.empresa.crt.strip().encode('ascii')
                    # wsdc.privatekey_prod = d.empresa.key.strip().encode('ascii')
                    wsdc.cert_prod = d.empresa.crt.strip()
                    wsdc.privatekey_prod = d.empresa.key.strip()
                else:
                    wsdc.cert_homo = LeerIni(clave='cert_homo', key='WSAA')
                    wsdc.privatekey_homo = LeerIni(clave='privatekey_homo', key='WSAA')
                    if not wsdc.cert_homo or not wsdc.privatekey_homo:
                        logging.error(
                            "Constatacion homologacion sin cert_homo/privatekey_homo configurados en WSAA"
                        )
                        continue
                wsdc.empresa = d.empresa.codigo
                wsdc.Cuit = d.empresa.cuit
                self.view.lblProcesamiento.setText("Constatando comprobante {} de {}".format(i, total))
                self.view.avance.actualizar(i / total * 100)
                try:
                    ok = wsdc.Comprobar(
                        cbte_modo = d.cbtemodo,
                        cuit_emisor = d.cuitemisor,
                        pto_vta = d.ptovta,
                        cbte_tipo = d.cbtetipo,
                        cbte_nro = d.cbtenro,
                        cbte_fch = FechaMysql(d.fechacbte),
                        imp_total = d.imptotal,
                        cod_autorizacion = d.codaut,
                        doc_tipo_receptor = d.doctiporec,
                        doc_nro_receptor = d.docnrorec
                    )
                    if ok:
                        d.resultado = 'A'
                        d.obs = ''
                        # padron = PadronAfip()
                        # ok = padron.ConsultarPersona(cuit=d.cuitemisor)
                        # if not ok:
                        #     d.resultado = 'R'
                        #     d.obs = "Error de constancia, verifique el cuit"
                    else:
                        d.resultado = wsdc.Resultado
                        d.errmsg = wsdc.ErrMsg
                        d.obs = wsdc.Obs
                except:
                    d.resultado = 'E'
                    d.listo = False
                    d.excepcion = traceback.format_exc()
            else:
                d.resultado = 'A'
                d.obs = 'No se estan validando los datos debido a los parametros establecidos'
                d.listo = False
            item = [
                d.ptovta, d.cbtenro, d.codaut, d.fechacbte, 'Constatacion'
            ]
            if self.view.gridFacturas.rowCount() > 10:
                self.view.gridFacturas.removeRow(0)

            self.view.gridFacturas.AgregaItem(items=item)
            d.save()

    def ObtieneDatosCUIT(self):

        cuit_consultar = CUIT.select().where(
            CUIT.listo == True,
            CUIT.resultado == ''
        )
        for cuit in cuit_consultar:
            item = [
                cuit.cuit_consultado, '', '', '', 'Consulta CUIT'
            ]
            if self.view.gridFacturas.rowCount() > 10:
                self.view.gridFacturas.removeRow(0)
            self.view.gridFacturas.AgregaItem(items=item)
            if ParamSist.ObtenerParametro("CONSULTA_CUIT") == "S":
                padron = PadronAfip()
                padron.Cuit = cuit.empresa.cuit
                padron.cert_prod = cuit.empresa.crt
                padron.privatekey_prod = cuit.empresa.key
                padron.empresa = cuit.empresa.codigo
                padron.cuit_emisor = cuit.empresa.cuit.encode('ascii')
                try:
                    ok = padron.ConsultarPersona(cuit=str(cuit.cuit_consultado).replace("-", ""))
                    if not ok:
                        cuit.resultado = "R"
                        cuit.errmsg = padron.errores[:100]
                    else:
                        cuit.localidad = padron.localidad
                        cuit.denominacion = padron.denominacion.replace(',', '')
                        cuit.provincia = padron.provincia
                        cuit.tipo_doc = padron.tipo_doc
                        cuit.estado = padron.estado
                        cuit.direccion = padron.direccion
                        cuit.cp = padron.cod_postal
                        cuit.ret_iva = padron.imp_iva
                        cuit.monotributo = padron.monotributo
                        cuit.empleador = padron.empleador
                        cuit.resultado = "A"
                except:
                    cuit.resultado = "E"
                    cuit.errmsg = padron.errores

                wsfecred = WsFECred()
                try:
                    if cuit.empresa.emitefce:
                        wsfecred.Cuit = cuit.empresa.cuit
                        wsfecred.cert_prod = cuit.empresa.crt
                        wsfecred.privatekey_prod = cuit.empresa.key
                        wsfecred.empresa = cuit.empresa.codigo
                        wsfecred.cuit_emisor = cuit.empresa.cuit.encode('ascii')
                        obligado, minimo = wsfecred.ConsultarMontoObligado(str(cuit.cuit_consultado).replace("-", ""),
                                                                           cuit.empresa.cuit)
                        cuit.monto_obligado = minimo
                        cuit.fce = obligado
                        if wsfecred.ErrMsg:
                            cuit.errmsg = wsfecred.ErrMsg
                    else:
                        cuit.monto_obligado = 0
                        cuit.fce = 0
                except:
                    cuit.resultado = "E"
                    cuit.errmsg = wsfecred.ErrMsg
            else:
                cuit.resultado = "A"
            cuit.listo = False
            cuit.save()

    def ImpresionFactura(self):
        facturas = Cabfact.select().where(
            Cabfact.listo == True
        )
        for f in facturas:
            try:
                controlador = ImpresionComprobantesController()
                controlador.nrelacion = f.nrelacion
                controlador.idcabfact = f.idcabfact
                # controlador.imprime(nrelacion=f.nrelacion, idcabfact=f.idcabfact)
                controlador.start()
                # controlador.join()
                f.listo = False
                f.save()
            except Exception as e:
                f.error = "Error: {}".format(e)
                f.save()
            item = [
                '', '', f.razon_social, '', 'Genera Comprobante'
            ]
            if self.view.gridFacturas.rowCount() > 10:
                self.view.gridFacturas.removeRow(0)
            self.view.gridFacturas.AgregaItem(item)
            
    def EnviaCorreos(self):
        if not self._envio_emails_activo():
            return

        reactivar_emails_retrasados()

        # Limpiar tareas finalizadas para no acumular referencias ni reenviar IDs en curso
        for email_id, future in list(self._email_futures.items()):
            if future.done():
                try:
                    future.result()
                except Exception:
                    logging.exception(f"Error en tarea de envío de email ID {email_id}")
                self._email_futures.pop(email_id, None)

        # Obtener correos pendientes que no estén siendo procesados actualmente
        # y que no tengan un timestamp de procesamiento reciente (últimos 5 minutos)
        cinco_minutos_atras = datetime.now() - timedelta(minutes=5)
        pendientes = EmailPendiente.select().where(
            (EmailPendiente.estado == 'pendiente') &
            (EmailPendiente.intentos < 3) &
            ((EmailPendiente.procesando_desde.is_null()) | 
             (EmailPendiente.procesando_desde < cinco_minutos_atras))
        )
        ids_pendientes = [e.id for e in pendientes]
        
        if self.view.gridFacturas.rowCount() > 10:
            self.view.gridFacturas.removeRow(0)

        if not ids_pendientes:
            return

        ids_a_enviar = [email_id for email_id in ids_pendientes if email_id not in self._email_futures]
        if not ids_a_enviar:
            return

        logging.info(f"Encontrados {len(ids_pendientes)} correos pendientes. Encolando {len(ids_a_enviar)} nuevos.")
        self.view.gridFacturas.AgregaItem(items=[
            '', '', f'Enviando {len(ids_a_enviar)} correos pendientes...', '', ''
        ])

        # Ejecutar en paralelo reutilizando un único pool para evitar crear hilos/conexiones sin control
        for email_id in ids_a_enviar:
            self._email_futures[email_id] = self._email_executor.submit(enviar_email_en_hilo, email_id)
