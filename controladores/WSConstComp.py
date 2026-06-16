from controladores.FE import FEv1
from libs.Utiles import inicializar_y_capturar_excepciones, LeerIni
from pyafipws.wscdc import WSCDC


class WSConstComp(WSCDC):

    cert_prod = ''
    privatekey_prod = ''
    cert_homo = ''
    empresa = 1
    privatekey_homo = ''
    Cuit = ''

    def __init__(self):
        WSCDC.__init__(self)

    @inicializar_y_capturar_excepciones
    def Comprobar(self, *args, **kwargs):

        cbte_modo = kwargs['cbte_modo']  # modalidad de emision: CAI, CAE, CAEA
        cuit_emisor = kwargs['cuit_emisor'].replace('-', '')  # proveedor
        pto_vta = kwargs['pto_vta']  # punto de venta habilitado en AFIP
        cbte_tipo = kwargs['cbte_tipo']  # 1: factura A (ver tabla de parametros)
        cbte_nro = kwargs['cbte_nro']  # numero de factura
        cbte_fch = kwargs['cbte_fch']  # fecha en formato aaaammdd
        cod_autorizacion = kwargs['cod_autorizacion']  # numero de CAI, CAE o CAEA
        # if cbte_modo == 'CAI':
        #     imp_total = "0"  # importe total
        #     doc_tipo_receptor = ""  # CUIT (obligatorio Facturas A o M)
        #     doc_nro_receptor = ""  # numero de CUIT del cliente
        # else:
        imp_total = kwargs['imp_total']  # importe total
        doc_tipo_receptor = kwargs['doc_tipo_receptor']  # CUIT (obligatorio Facturas A o M)
        doc_nro_receptor = kwargs['doc_nro_receptor'].replace('-', '')  # numero de CUIT del cliente

        wsfev1 = FEv1()
        wsfev1.cert_prod = self.cert_prod
        wsfev1.privatekey_prod = self.privatekey_prod
        wsfev1.empresa = self.empresa
        wsfev1.cert_homo = self.cert_homo
        wsfev1.privatekey_homo = self.privatekey_homo
        wsfev1.Cuit = self.Cuit

        ta = wsfev1.Autenticar(service='wscdc')
        self.SetTicketAcceso(ta_string=ta)
        # self.Cuit = LeerIni(clave='cuit', key='WSCDC') #cuit de la empresa/persona
        if LeerIni(clave='homo') == 'N':
            self.WSDL = LeerIni(clave='url_prod', key='WSCDC')
            self.Conectar("", self.WSDL)
        else:
            self.Conectar()

        # if cbte_modo == 'CAI':
        #     ok = self.ConstatarComprobante(cbte_modo, cuit_emisor, pto_vta, cbte_tipo,
        #                         cbte_nro, cbte_fch, imp_total, cod_autorizacion)
        # else:
        self.ConstatarComprobante(cbte_modo, cuit_emisor, pto_vta, cbte_tipo,
                                cbte_nro, cbte_fch, imp_total, cod_autorizacion,
                                doc_tipo_receptor, doc_nro_receptor)

        return self.Resultado == 'A'