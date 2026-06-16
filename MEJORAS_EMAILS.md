# Mejoras al Sistema de Envío de Emails

## Resumen de Funcionalidades Implementadas

Se han implementado 4 mejoras principales al sistema de envío de emails pendientes:

### 1. ✅ Persistencia de Errores
- Campo `ultimo_error` en la tabla `emails_pendientes`
- Guarda el mensaje completo de error (incluyendo traceback) del último intento fallido
- Facilita el diagnóstico de problemas sin necesidad de revisar logs

### 2. ✅ Soporte para CC y BCC
- Campos `cc` y `cco` en la tabla `emails_pendientes`
- Permite enviar copias carbón y copias carbón ocultas
- Soporta múltiples destinatarios separados por comas

### 3. ✅ Integración con Sistema de Facturación
- El envío de facturas ahora usa la cola de `EmailsPendientes`
- Unifica todo el envío de emails en un solo mecanismo
- CC de facturas configurable mediante parámetro `EMAIL_CC_FACTURAS`

### 4. ✅ Notificación de Fallos Finales
- Cuando un email alcanza 3 intentos fallidos, se envía notificación al administrador
- Email administrativo configurable mediante parámetro `EMAIL_ADMIN_NOTIFICACIONES`
- Incluye detalles completos del error y del email fallido

---

## Archivos Modificados

| Archivo | Descripción |
|---------|-------------|
| `modelos/EmailsPendientes.py` | Agregados campos `cc`, `cco`, `ultimo_error` |
| `migrations/add_cc_cco_error_fields.py` | Script de migración para crear los nuevos campos |
| `controladores/EnvioEmailsPendientes.py` | Funciones nuevas y lógica mejorada |
| `controladores/ImpresionComprobantes.py` | Migrado a usar la cola de emails |

---

## Configuración Requerida

### Parámetros del Sistema

Ejecuta estos comandos en Python para configurar los nuevos parámetros:

```python
from modelos.ParametrosSistema import ParamSist

# Email del administrador para recibir notificaciones de fallos
ParamSist.GuardaParametro("EMAIL_ADMIN_NOTIFICACIONES", "admin@ferreteriaavenida.com.ar")

# Email CC para facturas (opcional, por defecto usa fe@ferreteriaavenida.com.ar)
ParamSist.GuardaParametro("EMAIL_CC_FACTURAS", "fe@ferreteriaavenida.com.ar")
```

---

## Uso de las Nuevas Funcionalidades

### Función `encolar_email()` - Helper para Crear Emails

Esta función simplifica la creación de emails pendientes desde cualquier parte del código:

```python
from controladores.EnvioEmailsPendientes import encolar_email

# Ejemplo básico
email = encolar_email(
    destinatario="cliente@ejemplo.com",
    asunto="Factura Electrónica #12345",
    cuerpo_html="<h1>Factura</h1><p>Adjunta su factura</p>",
    cuerpo_texto="Factura adjunta"
)

# Ejemplo con CC y BCC
email = encolar_email(
    destinatario="cliente@ejemplo.com",
    asunto="Presupuesto #250905",
    cuerpo_html="<p>Su presupuesto adjunto</p>",
    cc="gerencia@empresa.com, ventas@empresa.com",
    cco="auditoria@empresa.com"
)

# Ejemplo con adjunto
email = encolar_email(
    destinatario="cliente@ejemplo.com",
    asunto="Factura con PDF",
    cuerpo_html="<p>Factura adjunta</p>",
    adjunto_ruta="pdf/factura-001-00012345.pdf",
    adjunto_nombre="Factura_12345.pdf"
)
```

### Parámetros de `encolar_email()`

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `destinatario` | str | ✅ Sí | Email del destinatario principal (o varios separados por coma) |
| `asunto` | str | ✅ Sí | Asunto del email |
| `cuerpo_html` | str | ❌ No | Contenido HTML del email |
| `cuerpo_texto` | str | ❌ No | Contenido en texto plano (alternativo al HTML) |
| `adjunto_ruta` | str | ❌ No | Ruta física al archivo adjunto |
| `adjunto_nombre` | str | ❌ No | Nombre con el que aparecerá el adjunto |
| `cc` | str | ❌ No | Emails en copia (separados por coma) |
| `cco` | str | ❌ No | Emails en copia oculta (separados por coma) |

---

## Verificación de Errores

### Consultar Emails Fallidos con su Error

```python
from modelos.EmailsPendientes import EmailPendiente

# Ver emails fallidos con detalles del error
emails_fallidos = EmailPendiente.select().where(
    EmailPendiente.estado == 'fallido'
)

for email in emails_fallidos:
    print(f"ID: {email.id}")
    print(f"Destinatario: {email.destinatario}")
    print(f"Asunto: {email.asunto}")
    print(f"Intentos: {email.intentos}")
    print(f"Error: {email.ultimo_error}")
    print("-" * 50)
```

### Reintentar un Email Fallido

Para reintentar un email que falló, resetea su estado:

```python
email = EmailPendiente.get_by_id(123)
email.estado = 'pendiente'
email.intentos = 0
email.procesando_desde = None
email.ultimo_error = None
email.save()
```

---

## Ejemplos de Uso en el Sistema

### 1. Envío de Facturas (Ya Implementado)

El sistema de facturación ahora usa automáticamente la cola. En `ImpresionComprobantes.py`:

```python
def envia_correo(self, cArchivoPDF, encabeza):
    from controladores.EnvioEmailsPendientes import encolar_email
    
    encolar_email(
        destinatario=cab.correos,
        asunto=f"Factura {cab.razon_social}",
        cuerpo_html=cab.mensaje_html,
        adjunto_ruta=cArchivoPDF,
        adjunto_nombre=os.path.basename(cArchivoPDF),
        cco="fe@ferreteriaavenida.com.ar"
    )
```

### 2. Notificación de Presupuestos Pendientes

Para enviar el presupuesto que estaba en el email original:

```python
from controladores.EnvioEmailsPendientes import encolar_email

# HTML del presupuesto (el que mostraste)
html_presupuesto = """<!doctype html>..."""

encolar_email(
    destinatario="oscar@ferreteriaavenida.com.ar, luis@ferreteriaavenida.com.ar, ventas_rolando@ferreteriaavenida.com.ar",
    asunto="Presupuesto #000000250905 | Cliente: [19820] JOHN JAVIER | Total: $5,633,303.55",
    cuerpo_html=html_presupuesto,
    cuerpo_texto="Se requiere autorización urgente para el presupuesto #000000250905"
)
```

### 3. Alertas Administrativas

```python
encolar_email(
    destinatario="admin@ferreteriaavenida.com.ar",
    asunto="⚠️ Error en Generación de CAE",
    cuerpo_html="<p>Se produjo un error al generar el CAE...</p>",
    cc="sistemas@ferreteriaavenida.com.ar"
)
```

---

## Monitoreo y Mantenimiento

### Ver Estado de la Cola

```python
from modelos.EmailsPendientes import EmailPendiente

# Contar por estado
pendientes = EmailPendiente.select().where(EmailPendiente.estado == 'pendiente').count()
enviados = EmailPendiente.select().where(EmailPendiente.estado == 'enviado').count()
fallidos = EmailPendiente.select().where(EmailPendiente.estado == 'fallido').count()

print(f"Pendientes: {pendientes}")
print(f"Enviados: {enviados}")
print(f"Fallidos: {fallidos}")
```

### Limpiar Emails Antiguos

```python
from datetime import datetime, timedelta
from modelos.EmailsPendientes import EmailPendiente

# Eliminar emails enviados de hace más de 30 días
hace_30_dias = datetime.now() - timedelta(days=30)
eliminados = EmailPendiente.delete().where(
    (EmailPendiente.estado == 'enviado') &
    (EmailPendiente.enviado_en < hace_30_dias)
).execute()

print(f"Eliminados {eliminados} emails antiguos")
```

---

## Troubleshooting

### Problema: Email queda en "procesando" indefinidamente

**Solución**: El sistema automáticamente libera emails que llevan más de 5 minutos procesando. Si necesitas liberarlo manualmente:

```python
from modelos.EmailsPendientes import EmailPendiente

EmailPendiente.update(procesando_desde=None).where(
    EmailPendiente.procesando_desde.is_null(False)
).execute()
```

### Problema: Email con múltiples destinatarios no se envía

**Solución**: Asegúrate de separar los emails con comas y que no haya espacios extras. La función `encolar_email()` maneja esto automáticamente.

### Problema: No llegan las notificaciones de fallos

**Solución**: Verifica que `EMAIL_ADMIN_NOTIFICACIONES` esté configurado:

```python
from modelos.ParametrosSistema import ParamSist
email = ParamSist.ObtenerParametro("EMAIL_ADMIN_NOTIFICACIONES")
print(f"Email configurado: {email}")
```

---

## Testing

Para probar las funcionalidades, ejecuta:

```bash
python test_nuevas_funcionalidades.py
```

Este script:
1. Crea un email de prueba con CC y BCC
2. Verifica campos de error
3. Muestra la configuración de parámetros
4. Lista emails pendientes

---

## Migración (Ya Ejecutada)

La migración de base de datos ya fue ejecutada exitosamente. Si necesitas ejecutarla nuevamente o en otro ambiente:

```bash
python migrations/add_cc_cco_error_fields.py
```

Para revertir la migración (eliminar los campos):

```bash
python migrations/add_cc_cco_error_fields.py --rollback
```

---

## Próximos Pasos Sugeridos

1. **Configurar parámetros**: Ejecutar los comandos de configuración mencionados arriba
2. **Migrar notificaciones de error**: Reemplazar los envíos directos de email en otros controladores (FE, FCE, InformaCAEA) por `encolar_email()`
3. **Implementar limpieza automática**: Agregar tarea programada para limpiar emails antiguos
4. **Dashboard de monitoreo**: Crear vista en la UI para ver estado de la cola
5. **Estadísticas**: Agregar métricas de éxito/fallo de envíos

---

## Contacto y Soporte

Para dudas o problemas con el sistema de envío de emails, contactar al equipo de desarrollo.
