import peewee
from libs.Utiles import limpiar_namespaces_y_pretty
from modelos.Encabezado import Encabezado
from modelos.ModeloBase import ModeloBase


class Respuesta(ModeloBase):
    
    id = peewee.AutoField(primary_key=True)
    nrelacion = peewee.ForeignKeyField(Encabezado, backref='respuestas', column_name='nrelacion')
    xmlrequest = peewee.TextField()
    xmlresponse = peewee.TextField()
    error = peewee.TextField()
    
    def save(self, *args, **kwargs):
        if self.xmlrequest:
            self.xmlrequest = limpiar_namespaces_y_pretty(self.xmlrequest)
        if self.xmlresponse:
            self.xmlresponse = limpiar_namespaces_y_pretty(self.xmlresponse)
        return super().save(*args, **kwargs)