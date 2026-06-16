from peewee import CharField, TextField, IntegerField, DateTimeField
import datetime
from modelos.ModeloBase import ModeloBase


class EmailPendiente(ModeloBase):
    destinatario = CharField(max_length=255, index=True)
    quien_envia = CharField(max_length=255, null=True)  # opcional, si no se usa el por defecto
    cc = CharField(max_length=500, null=True)              # Copia carbón (múltiples separados por coma)
    cco = CharField(max_length=500, null=True)             # Copia carbón oculta (múltiples separados por coma)
    asunto = CharField(max_length=255)
    cuerpo_html = TextField(null=True)         # HTML opcional
    cuerpo_texto = TextField(null=True)        # alternativa en texto plano (opcional)
    adjunto_ruta = CharField(max_length=512, null=True)  # ruta física al archivo adjunto en el servidor
    adjunto_nombre = CharField(max_length=255, null=True)  # nombre con el que se enviará el adjunto
    intentos = IntegerField(default=0)
    estado = CharField(max_length=20, default='pendiente')  # 'pendiente', 'enviado', 'fallido'
    procesando_desde = DateTimeField(null=True)  # timestamp cuando un hilo comenzó a procesar este email
    ultimo_error = TextField(null=True)          # mensaje del último error ocurrido
    creado_en = DateTimeField(default=datetime.datetime.now())
    enviado_en = DateTimeField(null=True)
    empresa_id = IntegerField(default=1)  # ID de la empresa emisora

    class Meta:
        table_name = 'emails_pendientes'