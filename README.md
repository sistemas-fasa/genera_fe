# Genera FE 2025

Sistema de escritorio para generar, informar e imprimir comprobantes electronicos de FASA mediante servicios web de AFIP.

La aplicacion procesa comprobantes pendientes desde la base de datos, solicita CAE o informa CAEA, genera archivos de salida y administra el envio de correos pendientes.

## Funcionalidades principales

- Generacion de facturas electronicas por WSFEv1.
- Soporte para comprobantes de credito electronicos mediante FCE.
- Informes CAEA y flujo CAEA para contingencia.
- Constatacion de comprobantes con WSCDC.
- Generacion de PDF e impresion de comprobantes.
- Cola de emails pendientes con reintentos, CC/CCO y control de registros en proceso.
- Logging rotativo para operacion y diagnostico.

## Estructura del proyecto

```text
controladores/   Logica de negocio, AFIP, impresion y envio de emails
modelos/         Modelos Peewee y conexion a base de datos
vistas/          Pantallas PyQt
libs/            Utilidades de UI, configuracion, logging y helpers
migrations/      Scripts manuales de migracion de base de datos
plantillas/      Plantillas CSV y recursos usados para comprobantes
imagenes/        Iconos, logos y recursos graficos
documentacion/   Documentacion tecnica adicional
tests/           Scripts de prueba manual
```

## Requisitos

- Windows.
- Python compatible con las dependencias historicas del proyecto.
- PyQt5 para el flujo principal.
- Peewee.
- Dependencias de email, PDF, QR y servicios AFIP usadas por los modulos del proyecto.
- Carpeta local `pyafipws/` disponible junto al codigo.
- Certificados AFIP y claves privadas en `certificados/`.
- Acceso a la base de datos configurada en `sistema.ini`.

> `pyafipws/`, certificados, tokens WSAA, logs, facturas generadas y configuraciones reales no se versionan por seguridad.

## Configuracion local

Crear los archivos de configuracion locales a partir de los ejemplos:

```powershell
Copy-Item .env.example .env
Copy-Item sistema.ini.example sistema.ini
```

Completar `.env` con la configuracion SMTP real:

```dotenv
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USE_TLS=1
SMTP_USER=usuario@example.com
SMTP_PASSWORD=change-me
SMTP_FROM=usuario@example.com
FASA_ERROR_EMAIL_PASSWORD=change-me
```

Completar `sistema.ini` con:

- Ruta `iniciosistema`.
- Datos de base de datos.
- CUIT, punto de venta y condicion de IVA.
- Rutas de certificados y claves AFIP.
- Endpoint de homologacion o produccion.
- Parametro `homo = S` para homologacion o `homo = N` para produccion.

## Ejecucion

Ejecutar la aplicacion principal:

```powershell
python main.py
```

Ejecutar flujo CAEA desde linea de comandos:

```powershell
python main.py --caea
```

Ejecutar pantalla de informe CAEA:

```powershell
python informacaea.py
```

## Build

El proyecto incluye un script historico de compilacion:

```powershell
.\compila.bat
```

El build usa la configuracion de PyInstaller y `version.txt`. Los artefactos de build quedan fuera de Git.

## Pruebas y validaciones

Compilacion sintactica de los modulos versionados:

```powershell
$files = git ls-files '*.py'
python -m compileall -q $files
```

Prueba manual de funcionalidades nuevas:

```powershell
python test_nuevas_funcionalidades.py
```

Prueba manual de envio de email:

```powershell
python tests\send_email_test.py
```

Para la prueba de email, configurar antes `.env` y opcionalmente `TEST_TO`.

## Logging

El logging se inicializa desde `main.py` usando `initialize_logger(LeerIni("iniciosistema"))`.

Ver detalles en:

- `documentacion/README_LOGGING.md`
- `libs/Utiles.py`

## Seguridad

No subir al repositorio:

- `.env`
- `sistema.ini`
- `certificados/`
- claves privadas, `.key`, `.pem`, `.p12`, `.pfx`
- tokens WSAA `*-ta.xml`
- logs
- facturas y PDFs generados
- dumps SQL
- builds y ejecutables
- `pyafipws/`

Si una credencial real estuvo en un archivo local, rotarla aunque el archivo este ignorado.

## Notas para desarrollo

- Mantener la logica de AFIP en `controladores/FE.py`, `controladores/FCE.py` y `controladores/Main.py`.
- Usar los modelos Peewee existentes en `modelos/`.
- Para cambios de esquema, agregar scripts en `migrations/`.
- Para nuevos envios de correo operativos, preferir la cola de `controladores/EnvioEmailsPendientes.py`.
- Probar cambios de AFIP primero con `homo = S`.
