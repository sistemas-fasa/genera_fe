# coding=utf-8
import datetime
import logging
import os
from os.path import abspath

from libs import Ventanas
from libs.Utiles import LeerIni, ubicacion_sistema, inicializar_y_capturar_excepciones
from pyafipws.wsaa import WSAA
from pyafipws.wsfecred import WSFECred

TIMEOUT = 15

class WsFECred(WSFECred):

    # def __init__(self):
    #     WSFECred.__init__(self)
    #     if LeerIni(clave='homo') != 'S':
    #         self.WSDL = LeerIni(clave='url_prod', key='WSFEv1')

    #crea ticket de acceso verificando que ya no tenga abierto uno
    Cuit = ''
    privatekey_homo = LeerIni(clave="privatekey_homo", key="WSAA")
    cert_homo = LeerIni(clave="cert_homo", key="WSAA")
    url_homo = LeerIni(clave='url_homo', key='WSAA')
    # cacert = "conf/afip_ca_info.crt"
    cacert = True
    cert_prod = LeerIni(clave="cert_prod", key="WSAA")
    privatekey_prod = LeerIni(clave="privatekey_prod", key="WSAA")
    url_prod = LeerIni(clave='url_prod', key='WSAA')
    cuit_emisor = LeerIni(clave='cuit', key='WSFEv1')
    empresa = 1 ##empresa por defecto

    def CreaTA(self):
        ta = self.Autenticar()
        return ta

    @inicializar_y_capturar_excepciones
    def Autenticar(self, *args, **kwargs):
        if 'service' in kwargs:
            service = kwargs['service']
        else:
            service = 'wsfecred'
        wsaa = WSAA()
        archivo = ubicacion_sistema() + service + '-ta.xml'
        try:
            file = open(archivo, "r")
            ta = file.read()
            file.close()
        except:
            ta = ''

        if ta == '': #si no existe el archivo se solicita un ticket
            solicitar = True
        else:
            ok = wsaa.AnalizarXml(ta)
            expiracion = wsaa.ObtenerTagXml("expirationTime")
            solicitar = wsaa.Expirado(expiracion) #si el ticket esta vencido se solicita uno nuevo
            logging.info("Fecha expiracion de ticket acceso {}".format(expiracion))

        if solicitar:
            #Generar un Ticket de Requerimiento de Acceso(TRA)
            tra = wsaa.CreateTRA(service=service)
            #Generar el mensaje firmado(CMS)
            if LeerIni(clave='homo') == 'S':#homologacion
                cms = wsaa.SignTRA(tra, self.cert_homo, self.privatekey_homo)
                ok = wsaa.Conectar("", self.url_homo)  # Homologación
            else:
                if not os.path.isfile(abspath(self.cert_prod)) or not os.path.isfile(abspath(self.privatekey_prod)):
                    logging.error("no existen los certificado {} key {} ".format(
                        self.cert_prod, self.privatekey_prod
                    ))
                cms = wsaa.SignTRA(tra, abspath(self.cert_prod), abspath(self.privatekey_prod))
                ok = wsaa.Conectar("", self.url_prod, cacert=self.cacert, timeout=TIMEOUT) #Produccion

            #Llamar al web service para autenticar
            ta = wsaa.LoginCMS(cms)

            #Grabo el ticket de acceso para poder reutilizarlo
            file = open(archivo, 'w')
            logging.debug("Ticket de acceso WSAA obtenido para servicio %s", service)
            file.write(ta)
            file.close()

        # devuelvo el ticket de acceso
        #print "Ticket acceso: {}".format(ta)
        return ta

    def ConsultarMontoObligado(self, cuit_consultada, cuit_emisor):
        if isinstance(cuit_emisor, bytes):
            self.Cuit = cuit_emisor.decode()
        else:
            self.Cuit = cuit_emisor
        cuit_consultada = cuit_consultada.replace('-', '')
        if LeerIni(clave='homo') == 'S':
            self.Conectar("")
        else:
            self.Conectar("", wsdl=self.WSDL)
        tafce = self.Autenticar()
        self.SetTicketAcceso(tafce)
        minimo = self.ConsultarMontoObligadoRecepcion(cuit_consultada) or 0
        if self.ErrMsg:
            Ventanas.showMsgAutoClose("Sistema", self.ErrMsg)
        return self.Resultado == 'S', minimo

    @inicializar_y_capturar_excepciones
    def ConsultarMontoObligadoRecepcion(self, cuit_consultada, fecha_emision=None):
        "Conocer la obligación respecto a la emisión o recepción de Facturas de Créditos"
        if not fecha_emision:
            fecha_emision = datetime.datetime.today().strftime("%Y-%m-%d")
        response = self.client.consultarMontoObligadoRecepcion(
                            authRequest={
                                'token': self.Token, 'sign': self.Sign,
                                'cuitRepresentada': self.Cuit,
                            },
                            cuitConsultada=cuit_consultada,
                            fechaEmision=fecha_emision,
                        )
        ret = response.get('consultarMontoObligadoRecepcionReturn')
        if ret:
            self.__analizar_errores(ret)
            self.__analizar_observaciones(ret)
            self.__analizar_evento(ret)
            self.Resultado = ret['obligado']
            return ret.get('montoDesde')

    def __analizar_errores(self, ret):
        "Comprueba y extrae errores si existen en la respuesta XML"
        self.Errores = [err['codigoDescripcion'] for err in ret.get('arrayErrores', [])]
        self.ErroresFormato = [err['codigoDescripcionString'] for err in ret.get('arrayErroresFormato', [])]
        errores = self.Errores + self.ErroresFormato
        self.ErrCode = ' '.join(["%(codigo)s" % err for err in errores])
        self.ErrMsg = '\n'.join(["%(codigo)s: %(descripcion)s" % err for err in errores])

    def __analizar_observaciones(self, ret):
        "Comprueba y extrae observaciones si existen en la respuesta XML"
        self.Observaciones = [obs["codigoDescripcion"] for obs in ret.get('arrayObservaciones', [])]
        self.Obs = '\n'.join(["%(codigo)s: %(descripcion)s" % obs for obs in self.Observaciones])

    def __analizar_evento(self, ret):
        "Comprueba y extrae el wvento informativo si existen en la respuesta XML"
        evt = ret.get('evento')
        if evt:
            self.Eventos = [evt]
            self.Evento = "%(codigo)s: %(descripcion)s" % evt
