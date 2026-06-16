import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import datetime
import logging
import traceback
import mimetypes
import time
from dotenv import load_dotenv
from peewee import fn

from modelos.EmailsPendientes import EmailPendiente
from modelos.ModeloBase import ModeloBase
from modelos.ParametrosSistema import ParamSist
from modelos.Empresas import Empresa

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO)


def _limpiar_config_smtp(valor):
    """Normaliza campos SMTP copiados con saltos de linea o espacios."""
    if valor is None:
        return valor
    return str(valor).replace('\r', '').replace('\n', '').strip()


def reactivar_emails_retrasados():
    """Reactiva correos en estado 'retrasado' cuyo momento de reintento ya llegó."""
    try:
        ahora_tmp = datetime.datetime.now()
        reactivated = EmailPendiente.update(
            estado='pendiente',
            procesando_desde=None
        ).where(
            (EmailPendiente.estado == 'retrasado') &
            (EmailPendiente.procesando_desde <= ahora_tmp)
        ).execute()
        if reactivated:
            logging.info(f"♻️ Reactivados {reactivated} emails retrasados cuya hora de reintento llegó")
        return reactivated
    except Exception:
        logging.exception("⚠️ Error al reactivar emails retrasados")
        return 0


def encolar_email(destinatario, asunto, cuerpo_html=None, cuerpo_texto=None, 
                  adjunto_ruta=None, adjunto_nombre=None, cc=None, cco=None, quien_envia=None):
    """
    Función helper para encolar un email pendiente desde cualquier parte del sistema.
    
    Args:
        destinatario: Email del destinatario (o varios separados por coma)
        asunto: Asunto del email
        cuerpo_html: Contenido HTML del email (opcional)
        cuerpo_texto: Contenido en texto plano (opcional)
        adjunto_ruta: Ruta al archivo adjunto (opcional)
        adjunto_nombre: Nombre del archivo adjunto (opcional)
        cc: Emails en copia (separados por coma) (opcional)
        cco: Emails en copia oculta (separados por coma) (opcional)
        quien_envia: Email del remitente personalizado (opcional, si no se usa el configurado)
    
    Returns:
        EmailPendiente: El registro creado
    """
    email = EmailPendiente.create(
        destinatario=destinatario,
        asunto=asunto,
        cuerpo_html=cuerpo_html,
        cuerpo_texto=cuerpo_texto,
        adjunto_ruta=adjunto_ruta,
        adjunto_nombre=adjunto_nombre,
        cc=cc,
        cco=cco,
        quien_envia=quien_envia
    )
    logging.info(f"📥 Email encolado ID {email.id} para {destinatario}")
    return email


def _parsear_destinatarios(destinatarios_str):
    """Parsea un string de destinatarios separados por coma a una lista"""
    if not destinatarios_str:
        return []
    return [d.strip() for d in destinatarios_str.split(',') if d.strip()]


def _notificar_fallo_final(email_registro, error_msg):
    """
    Encola un email de notificación cuando un email alcanza el máximo de intentos.
    El email se envía al administrador configurado en parámetros del sistema.
    """
    try:
        email_admin = ParamSist.ObtenerParametro("EMAIL_ADMIN_NOTIFICACIONES")
        if not email_admin:
            logging.warning("⚠️ No hay EMAIL_ADMIN_NOTIFICACIONES configurado para notificar fallos")
            return
        
        asunto = f"⚠️ Fallo de envío de email ID {email_registro.id}"
        
        cuerpo_html = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background-color: #e74c3c; color: white; padding: 15px; border-radius: 5px 5px 0 0;">
                    <h2 style="margin: 0;">⚠️ Fallo de Envío de Email</h2>
                </div>
                <div style="background-color: #f9f9f9; padding: 20px; border: 1px solid #ddd; border-top: none;">
                    <p>Un email ha fallado después de {email_registro.intentos} intentos y no se volverá a reintentar.</p>
                    
                    <h3 style="color: #2c3e50; border-bottom: 1px solid #ddd; padding-bottom: 10px;">Detalles del Email</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px; font-weight: bold; width: 120px;">ID:</td>
                            <td style="padding: 8px;">{email_registro.id}</td>
                        </tr>
                        <tr style="background-color: #f5f5f5;">
                            <td style="padding: 8px; font-weight: bold;">Destinatario:</td>
                            <td style="padding: 8px;">{email_registro.destinatario}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; font-weight: bold;">Asunto:</td>
                            <td style="padding: 8px;">{email_registro.asunto}</td>
                        </tr>
                        <tr style="background-color: #f5f5f5;">
                            <td style="padding: 8px; font-weight: bold;">Creado:</td>
                            <td style="padding: 8px;">{email_registro.creado_en}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; font-weight: bold;">Intentos:</td>
                            <td style="padding: 8px;">{email_registro.intentos}</td>
                        </tr>
                    </table>
                    
                    <h3 style="color: #c0392b; border-bottom: 1px solid #ddd; padding-bottom: 10px; margin-top: 20px;">Último Error</h3>
                    <pre style="background-color: #2c3e50; color: #ecf0f1; padding: 15px; border-radius: 5px; overflow-x: auto; font-size: 12px;">{error_msg[:1000]}</pre>
                    
                    <p style="margin-top: 20px; color: #7f8c8d; font-size: 12px;">
                        Este es un mensaje automático del sistema de envío de emails.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Encolar la notificación (sin CC/CCO para evitar loops)
        encolar_email(
            destinatario=email_admin,
            asunto=asunto,
            cuerpo_html=cuerpo_html,
            cuerpo_texto=f"Fallo de envío de email ID {email_registro.id} a {email_registro.destinatario}. Error: {error_msg[:500]}"
        )
        logging.info(f"📧 Notificación de fallo encolada para {email_admin}")
        
    except Exception as e:
        logging.error(f"❌ Error al encolar notificación de fallo: {e}")


# Función de envío (ejecutada en hilo)
def enviar_email_en_hilo(email_id):
    # Cada hilo debe tener su propia conexión a la DB (Peewee no es thread-safe por defecto)
    db = ModeloBase().getDb()
    email_registro = None
    
    try:
        # Reconectar en cada hilo
        if db.is_closed():
            db.connect()
        
        # BLOQUEO OPTIMISTA: Intentar marcar el registro como "procesando" de forma atómica
        # Solo actualiza si el estado es 'pendiente' y procesando_desde es NULL
        ahora = datetime.datetime.now()
        rows_updated = EmailPendiente.update(
            procesando_desde=ahora
        ).where(
            (EmailPendiente.id == email_id) &
            (EmailPendiente.estado == 'pendiente') &
            (EmailPendiente.intentos < 3) &
            (EmailPendiente.procesando_desde.is_null())
        ).execute()
        
        # Si no se actualizó ninguna fila, otro hilo ya está procesando este email
        if rows_updated == 0:
            # Verificar estado real para debugging
            try:
                estado_actual = EmailPendiente.get_by_id(email_id)
                logging.debug(f"⏭️ Correo ID {email_id} no reclamado. Estado: {estado_actual.estado}, intentos: {estado_actual.intentos}, procesando_desde: {estado_actual.procesando_desde}")
            except:
                pass
            return
            
        # Ahora sí, obtenemos el registro con seguridad de que somos los únicos procesándolo
        email_registro = EmailPendiente.get_by_id(email_id)
        
        logging.info(f"🔒 Correo ID {email_id} reclamado para procesamiento")

        logging.info(f"📧 Preparando envío de correo a {email_registro.destinatario} (ID: {email_id})")

        # Crear mensaje con estructura multipart/mixed -> multipart/alternative para el body
        msg = MIMEMultipart('mixed')
        msg['To'] = email_registro.destinatario
        msg['Subject'] = email_registro.asunto
        
        # Agregar CC si existe
        if email_registro.cc:
            msg['Cc'] = email_registro.cc
        
        # Nota: BCC no se agrega como header, solo se incluye en la lista de destinatarios

        # Parte alternativa para texto/HTML
        alternative = MIMEMultipart('alternative')
        if email_registro.cuerpo_texto:
            alternative.attach(MIMEText(email_registro.cuerpo_texto, 'plain', 'utf-8'))
        if email_registro.cuerpo_html:
            alternative.attach(MIMEText(email_registro.cuerpo_html, 'html', 'utf-8'))

        msg.attach(alternative)

        # Adjunto (si existe) - soporta múltiples rutas separadas por coma
        if email_registro.adjunto_ruta:
            rutas = [r.strip() for r in str(email_registro.adjunto_ruta).split(',') if r.strip()]
            for idx, ruta in enumerate(rutas, start=1):
                ruta_adjunto = os.path.abspath(ruta)
                logging.info(f"🔍 Comprobando adjunto: {ruta_adjunto}")
                if os.path.isfile(ruta_adjunto):
                    try:
                        mimetype, _ = mimetypes.guess_type(ruta_adjunto)
                        if mimetype:
                            maintype, subtype = mimetype.split('/', 1)
                        else:
                            maintype, subtype = 'application', 'octet-stream'

                        with open(ruta_adjunto, "rb") as f:
                            part = MIMEBase(maintype, subtype)
                            part.set_payload(f.read())
                        encoders.encode_base64(part)

                        # Determinar nombre de archivo: si solo hay uno y se indicó adjunto_nombre, usarlo
                        if len(rutas) == 1 and email_registro.adjunto_nombre:
                            filename = email_registro.adjunto_nombre
                        else:
                            filename = email_registro.adjunto_nombre or os.path.basename(ruta_adjunto)

                        # Evitar duplicados si se adjuntan varios archivos con el mismo nombre
                        if len(rutas) > 1:
                            base, ext = os.path.splitext(filename)
                            filename = f"{base}_{idx}{ext}"

                        part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
                        msg.attach(part)
                        logging.info(f"📎 Adjunto preparado: {ruta_adjunto} (nombre: {filename})")
                    except Exception as att_e:
                        logging.error(f"❌ Error al procesar adjunto {ruta_adjunto}: {att_e}\n{traceback.format_exc()}")
                else:
                    logging.warning(f"⚠️ Ruta de adjunto no encontrada: {ruta_adjunto}")

        # Parsear todos los destinatarios (To + CC + BCC)
        destinatarios_lista = _parsear_destinatarios(email_registro.destinatario)
        destinatarios_lista.extend(_parsear_destinatarios(email_registro.cc))
        destinatarios_lista.extend(_parsear_destinatarios(email_registro.cco))
        # Validar que haya al menos un destinatario
        if not destinatarios_lista:
            err = "No hay destinatarios definidos para el email"
            logging.error(f"❌ {err} ID {email_id}")
            try:
                EmailPendiente.update(
                    intentos=email_registro.intentos + 1,
                    ultimo_error=err,
                    procesando_desde=None,
                    estado='fallido'
                ).where(EmailPendiente.id == email_id).execute()
            except Exception:
                logging.exception("Error al actualizar estado por falta de destinatarios")
            return
        
        # Determinar configuración SMTP: primero intentar leer desde modelo Empresa, si no usar .env
        smtp_host = os.getenv('SMTP_HOST')
        smtp_port = int(os.getenv('SMTP_PORT')) if os.getenv('SMTP_PORT') else None
        smtp_user = os.getenv('SMTP_USER')
        smtp_password = os.getenv('SMTP_PASSWORD')
        smtp_from = os.getenv('SMTP_FROM')
        smtp_use_tls = os.getenv('SMTP_USE_TLS', '1') == '1'

        try:
            # Seleccionar la empresa asociada al email pendiente (empresa_id)
            empresa = None
            if hasattr(email_registro, 'empresa_id') and email_registro.empresa_id:
                try:
                    empresa = Empresa.get_or_none(Empresa.codigo == int(email_registro.empresa_id))
                except Exception:
                    empresa = None

            # Si no hay empresa asociada, usar la primera como fallback (compatibilidad)
            if not empresa:
                empresa = Empresa.select().first()

            if empresa:
                if empresa.servidor_correo:
                    smtp_host = empresa.servidor_correo
                if empresa.puerto:
                    try:
                        smtp_port = int(empresa.puerto)
                    except Exception:
                        pass
                if empresa.usuario_correo:
                    smtp_user = empresa.usuario_correo
                    if not smtp_from:
                        smtp_from = empresa.usuario_correo
                if empresa.pass_correo:
                    smtp_password = empresa.pass_correo
        except Exception:
            logging.exception("⚠️ No se pudo leer configuración de Empresa para SMTP, usando .env si está disponible")

        smtp_host = _limpiar_config_smtp(smtp_host)
        smtp_user = _limpiar_config_smtp(smtp_user)
        smtp_password = _limpiar_config_smtp(smtp_password)
        smtp_from = _limpiar_config_smtp(smtp_from)

        # Asegurar From: debe ser el mismo que el usuario SMTP cuando esté disponible
        if smtp_user:
            smtp_from = smtp_user
        else:
            smtp_from = smtp_from or os.getenv('SMTP_FROM') or ''
        
        # Si el email tiene especificado quien_envia, usarlo para From y Reply-To
        # En caso contrario, usar el smtp_from configurado
        if email_registro.quien_envia:
            email_from = email_registro.quien_envia.strip()
            logging.info(f"📧 Usando quien_envia personalizado: {email_from}")
        else:
            email_from = smtp_from
        
        # Establecer From y Reply-To en el mensaje
        msg['From'] = email_from
        msg['Reply-To'] = email_from

        logging.info(f"🔗 Conectando a servidor SMTP: {smtp_host}:{smtp_port or ''}")
        logging.info(f"ℹ️ Empresa seleccionada: {empresa.codigo if empresa else None} - {getattr(empresa, 'nombre', '')}")
        logging.info(f"ℹ️ SMTP config: host={smtp_host} port={smtp_port} user={smtp_user} from={smtp_from} has_pass={bool(smtp_password)}")

        # Si no hay host SMTP configurado, marcar como fallido con detalle
        if not smtp_host:
            err = f"No hay servidor SMTP configurado para empresa {getattr(empresa, 'codigo', 'N/A')}"
            logging.error(f"❌ {err} ID {email_id}")
            try:
                EmailPendiente.update(
                    intentos=email_registro.intentos + 1,
                    ultimo_error=err,
                    procesando_desde=None,
                    estado='fallido'
                ).where(EmailPendiente.id == email_id).execute()
            except Exception:
                logging.exception("Error al actualizar estado por falta de SMTP_HOST")
            return
        logging.info(f"📬 Destinatarios: {destinatarios_lista}")

        # --- Control de tasa por hora (por empresa) ---
        try:
            try:
                limit_str = ParamSist.ObtenerParametro('EMAIL_LIMIT_PER_HOUR', '')
                limit_per_hour = int(limit_str) if limit_str else int(os.getenv('SMTP_HOUR_LIMIT', '200'))
            except Exception:
                limit_per_hour = int(os.getenv('SMTP_HOUR_LIMIT', '200'))

            ahora_lim = datetime.datetime.now()
            ventana = ahora_lim - datetime.timedelta(hours=1)
            empresa_code = getattr(email_registro, 'empresa_id', None)

            sent_count = EmailPendiente.select().where(
                (EmailPendiente.empresa_id == empresa_code) &
                (EmailPendiente.estado == 'enviado') &
                (EmailPendiente.enviado_en >= ventana)
            ).count()

            if sent_count >= limit_per_hour:
                earliest = EmailPendiente.select(EmailPendiente.enviado_en).where(
                    (EmailPendiente.empresa_id == empresa_code) &
                    (EmailPendiente.estado == 'enviado') &
                    (EmailPendiente.enviado_en >= ventana)
                ).order_by(EmailPendiente.enviado_en.asc()).limit(1).first()

                if earliest and earliest.enviado_en:
                    next_available = earliest.enviado_en + datetime.timedelta(hours=1, seconds=10)
                else:
                    next_available = ahora_lim + datetime.timedelta(minutes=15)

                EmailPendiente.update(
                    estado='retrasado',
                    procesando_desde=next_available,
                    ultimo_error=f"Reprogramado por límite horario ({sent_count}/{limit_per_hour})"
                ).where(EmailPendiente.id == email_id).execute()

                logging.warning(f"⏳ Límite horario alcanzado ({sent_count}/{limit_per_hour}). Email ID {email_id} reprogramado para {next_available}")
                return
        except Exception:
            logging.exception("⚠️ Error al comprobar límite horario de envíos; se continuará normalmente")

        # Implementar reintentos locales para errores de límite de envío (SMTP 554)
        # No incrementamos el contador persistente `intentos` mientras hacemos
        # estos reintentos cortos; si tras los reintentos locales sigue fallando
        # se procede a la lógica normal de aumentar `intentos`.
        rate_limit_delays = [60, 300, 900]  # 1m, 5m, 15m
        max_rate_attempts = len(rate_limit_delays) + 1
        send_success = False

        for attempt_idx in range(1, max_rate_attempts + 1):
            # Puerto 465 requiere SSL directo, otros puertos usan STARTTLS
            use_ssl = smtp_port == 465

            if smtp_port:
                smtp_conn_args = (smtp_host, int(smtp_port))
            else:
                smtp_conn_args = (smtp_host,)

            server = None
            try:
                if use_ssl:
                    logging.info(f"🔐 Usando SMTP_SSL para puerto {smtp_port}")
                    server = smtplib.SMTP_SSL(*smtp_conn_args, timeout=60)
                else:
                    logging.info(f"🔓 Usando SMTP para puerto {smtp_port or 'default'}")
                    server = smtplib.SMTP(*smtp_conn_args, timeout=60)
                    if smtp_use_tls:
                        try:
                            server.starttls()
                        except Exception:
                            logging.exception("⚠️ Error al iniciar TLS en servidor SMTP")

                # Hacer login solo si hay usuario/clave
                if smtp_user and smtp_password:
                    try:
                        pass_preview = f"{smtp_password[:3]}...{smtp_password[-3:]}" if len(smtp_password) > 6 else "***"
                        logging.info(f"🔑 Intentando login como '{smtp_user}' con password '{pass_preview}' (len={len(smtp_password)})")
                        server.login(smtp_user, smtp_password)
                        logging.info(f"✓ Login SMTP exitoso como {smtp_user}")
                    except Exception:
                        logging.exception(f"❌ Falló login SMTP - Usuario: '{smtp_user}' - Verifica las credenciales en la tabla 'empresas' (codigo={getattr(empresa, 'codigo', 'N/A')})")
                        raise

                # sendmail requiere una LISTA de destinatarios, no un string con comas
                logging.info(f"📤 Enviando mensaje - From: '{msg['From']}' Reply-To: '{msg['Reply-To']}' To: {destinatarios_lista} (attempt {attempt_idx}/{max_rate_attempts})")
                server.sendmail(smtp_from, destinatarios_lista, msg.as_string())
                logging.info(f"✓ Mensaje enviado exitosamente en intento {attempt_idx}")
                send_success = True
                break

            except smtplib.SMTPDataError as sde:
                # Código SMTP (por ejemplo 554) y mensaje
                smtp_code = None
                try:
                    smtp_code = sde.smtp_code
                except Exception:
                    # fallback a args
                    if sde.args and len(sde.args) >= 1:
                        smtp_code = sde.args[0]

                err_text = sde.smtp_error if hasattr(sde, 'smtp_error') else str(sde)
                logging.error(f"❌ SMTPDataError (code={smtp_code}) al enviar correo ID {email_id}: {err_text}")

                # Si es un error por límite (554) intentamos reintentar tras esperar
                if smtp_code == 554 or (isinstance(err_text, (bytes, bytearray)) and b'exced' in err_text.lower()) or ('exced' in str(err_text).lower() or 'limite' in str(err_text).lower()):
                    if attempt_idx < max_rate_attempts:
                        delay = rate_limit_delays[attempt_idx - 1]
                        logging.warning(f"⏱️ Límite SMTP detectado. Esperando {delay}s antes de reintentar (intento {attempt_idx}/{max_rate_attempts})")
                        try:
                            server.quit()
                        except:
                            pass
                        time.sleep(delay)
                        continue
                    else:
                        logging.error(f"⚠️ Excedido reintentos por límite SMTP tras {max_rate_attempts} intentos")
                        # dejar que la excepción provoque la lógica de actualización de intentos más abajo
                        raise
                else:
                    # Otros códigos de SMTPDataError: no retry específico
                    raise

            finally:
                try:
                    if server:
                        server.quit()
                except Exception:
                    pass

        if not send_success:
            # Si no se envió tras los reintentos, lanzar excepción para caer en el manejo general
            raise Exception("Fallo de envío tras reintentos por límite/errores SMTP")

        # Actualizar estado - éxito (actualización atómica para evitar race conditions)
        EmailPendiente.update(
            estado='enviado',
            enviado_en=datetime.datetime.now(),
            procesando_desde=None,
            ultimo_error=None
        ).where(
            EmailPendiente.id == email_id
        ).execute()
        logging.info(f"✅ Correo enviado a {email_registro.destinatario} (ID: {email_id})")

    except Exception as e:
        error_msg = f"{e}\n{traceback.format_exc()}"
        logging.error(f"❌ Error al enviar correo ID {email_id}: {error_msg}")
        
        if email_registro:
            try:
                nuevos_intentos = email_registro.intentos + 1
                nuevo_estado = 'fallido' if nuevos_intentos >= 3 else 'pendiente'
                
                # UPDATE atómico para evitar race conditions
                EmailPendiente.update(
                    intentos=nuevos_intentos,
                    ultimo_error=error_msg[:2000],
                    procesando_desde=None,  # CRÍTICO: liberar para reintento
                    estado=nuevo_estado
                ).where(
                    EmailPendiente.id == email_id
                ).execute()
                
                logging.info(f"🔄 Intento {nuevos_intentos}/3 para correo ID {email_id}, estado: {nuevo_estado}")
                
                if nuevos_intentos >= 3:
                    # Notificar al administrador del fallo final
                    _notificar_fallo_final(email_registro, error_msg)
            except Exception as save_error:
                logging.error(f"❌ Error al actualizar registro ID {email_id}: {save_error}")
                # Intentar limpiar procesando_desde como último recurso
                try:
                    EmailPendiente.update(procesando_desde=None).where(EmailPendiente.id == email_id).execute()
                except:
                    pass
    finally:
        # Asegurar que procesando_desde se limpia si algo salió mal
        try:
            # Verificar si el email sigue en procesando sin estado final
            email_check = EmailPendiente.get_by_id(email_id)
            if email_check.estado == 'pendiente' and email_check.procesando_desde is not None:
                logging.warning(f"⚠️ Limpiando procesando_desde huérfano para email ID {email_id}")
                EmailPendiente.update(procesando_desde=None).where(EmailPendiente.id == email_id).execute()
        except Exception as cleanup_error:
            logging.error(f"Error en limpieza final de email ID {email_id}: {cleanup_error}")
        
        # Cerrar conexión del hilo
        if db and not db.is_closed():
            db.close()
