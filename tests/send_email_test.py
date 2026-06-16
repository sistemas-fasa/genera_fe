import os
import sys
import logging
import pathlib
from dotenv import load_dotenv
import datetime

# Añadir la raíz del proyecto al sys.path para que los imports funcionen
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Cargar .env si existe
load_dotenv()

# Ajustar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

# Verificación de variables SMTP necesarias
required = ['SMTP_HOST', 'SMTP_PORT', 'SMTP_USER', 'SMTP_PASSWORD', 'SMTP_FROM']
missing = [v for v in required if not os.getenv(v)]
if missing:
    print("Faltan variables de entorno SMTP: {}".format(', '.join(missing)))
    print("Colócalas en un archivo .env o exportalas antes de ejecutar el test.")
    print("Ejemplo .env:\nSMTP_HOST=smtp.example.com\nSMTP_PORT=587\nSMTP_USER=miusuario\nSMTP_PASSWORD=mipassword\nSMTP_FROM=mi@dominio.com")
    raise SystemExit(1)

# Importar componentes de la app
from modelos.ModeloBase import ModeloBase
from modelos.EmailsPendientes import EmailPendiente
from controladores.EnvioEmailsPendientes import enviar_email_en_hilo

# Preparar DB
db = ModeloBase().getDb()
if db.is_closed():
    db.connect()

# Crear directorio de pruebas y archivo adjunto
here = os.path.dirname(os.path.abspath(__file__))
att_dir = os.path.join(here, 'attachments')
os.makedirs(att_dir, exist_ok=True)
adjunto_path = os.path.join(att_dir, 'adjunto_prueba.txt')
with open(adjunto_path, 'w', encoding='utf-8') as f:
    f.write('Contenido de prueba para verificar envío de adjunto.\n')
    f.write('Fecha: {}'.format(datetime.datetime.now()))

# Crear registro EmailPendiente
to_address = os.getenv('TEST_TO') or os.getenv('SMTP_FROM')
email = EmailPendiente.create(
    destinatario=to_address,
    asunto='Prueba envío con adjunto',
    cuerpo_texto='Este es un correo de prueba con adjunto generado por tests/send_email_test.py',
    cuerpo_html='<p>Este es un <b>correo de prueba</b> con adjunto.</p>',
    adjunto_ruta=adjunto_path,
    adjunto_nombre='prueba_adjunto.txt'
)

print('Creado EmailPendiente ID={}'.format(email.id))

# Ejecutar el envío (llamamos directamente a la función que se usa en los hilos)
try:
    enviar_email_en_hilo(email.id)
except Exception as e:
    logging.error('Error al ejecutar enviar_email_en_hilo: %s', e, exc_info=True)

# Recargar registro y mostrar estado
email_ref = EmailPendiente.get_by_id(email.id)
print('Estado final: {}, Intentos: {}, Enviado_en: {}'.format(email_ref.estado, email_ref.intentos, email_ref.enviado_en))

# Nota: el script deja el archivo adjunto en tests/attachments y el registro en la DB para inspección manual.
