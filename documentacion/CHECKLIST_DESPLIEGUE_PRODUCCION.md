# Checklist de despliegue a produccion - Genera FE

Este checklist prepara un despliegue manual controlado de Genera FE en Windows. No reemplaza la prueba funcional en homologacion ni la validacion fiscal posterior al primer comprobante real.

## 1. Precondiciones

- [ ] Confirmar que la rama a publicar es la rama aprobada para produccion.
- [ ] Confirmar que el working tree esta limpio antes de compilar: `git status --short`.
- [ ] Confirmar el commit exacto a publicar: `git rev-parse --short HEAD`.
- [ ] Ejecutar validaciones locales desde el entorno de proyecto:

```powershell
H:\venv\PyFE\Scripts\python.exe -m compileall -q .
H:\venv\PyFE\Scripts\python.exe check_project.py
H:\venv\PyFE\Scripts\python.exe -m pytest tests -q
```

- [ ] Ejecutar validacion estricta de produccion antes de liberar:

```powershell
H:\venv\PyFE\Scripts\python.exe check_project.py --production
```

## 2. Backups obligatorios

- [ ] Crear backup del ejecutable actual antes de reemplazarlo.
- [ ] Crear backup de `sistema.ini` antes de editar o reemplazar configuracion.
- [ ] Guardar los backups con fecha y hora en una carpeta fuera de `dist/`, por ejemplo:

```powershell
$fecha = Get-Date -Format "yyyyMMdd_HHmmss"
New-Item -ItemType Directory -Force -Path ".\backups_release\$fecha"
Copy-Item ".\dist\main.exe" ".\backups_release\$fecha\main.exe" -ErrorAction Stop
Copy-Item ".\sistema.ini" ".\backups_release\$fecha\sistema.ini" -ErrorAction Stop
```

## 3. Configuracion productiva

Validar `sistema.ini` sin exponer credenciales.

- [ ] Confirmar `[param] homo = N`.
- [ ] Confirmar `[param] base = mysql`.
- [ ] Confirmar `[param] bloquear_cae_si_afip_dummy_falla = N`, salvo decision operativa explicita de bloquear CAE cuando falle FEDummy.
- [ ] Confirmar `afip_timeout_segundos` con valor entero mayor o igual a 1.
- [ ] Confirmar CUIT y punto de venta productivos en `[WSFEv1]`.
- [ ] Confirmar certificados productivos en `[WSAA]`:
  - [ ] `cert_prod` apunta al certificado productivo correcto.
  - [ ] `privatekey_prod` apunta a la clave productiva correcta.
  - [ ] Los archivos existen y son accesibles por el usuario que ejecuta la app.
- [ ] Confirmar URLs productivas AFIP/ARCA:
  - [ ] `[WSFEv1] url_prod` apunta al endpoint productivo de WSFEv1.
  - [ ] `[WSAA] url_prod` apunta al endpoint productivo de LoginCms.
  - [ ] `[WSCDC] url_prod` apunta al endpoint productivo de constatacion, si se usa.
- [ ] Confirmar SMTP:
  - [ ] Host/puerto/usuario configurados para la empresa o variables de entorno.
  - [ ] Remitente esperado.
  - [ ] Destinatarios de alertas operativas.
  - [ ] No registrar ni compartir passwords.

## 4. Build

El script historico de build es:

```bat
compila.bat
```

Contenido esperado del script:

```bat
rd /S /Q dist\main
pyinstaller --clean --version-file=version.txt -F --icon=imagenes\logo.ico main.py
```

Comando recomendado desde la raiz del repo, usando el entorno validado:

```cmd
H:\venv\PyFE\Scripts\activate.bat
compila.bat
```

Resultado esperado:

- [ ] PyInstaller termina sin errores.
- [ ] Se genera `dist\main.exe`.
- [ ] El ejecutable tiene fecha/hora del build actual.
- [ ] No se reemplaza el ejecutable productivo hasta completar las pruebas locales.

## 5. Prueba del ejecutable compilado

- [ ] Ejecutar `dist\main.exe` en una estacion controlada.
- [ ] Confirmar que la app abre correctamente.
- [ ] Confirmar visualmente modo Produccion.
- [ ] Confirmar que el monitor AFIP muestra estado sin bloquear CAE por defecto.
- [ ] Confirmar estado de emails.
- [ ] Confirmar que el boton pausar/reanudar funciona.
- [ ] Confirmar que la grilla muestra columnas sin cortar datos clave.
- [ ] Revisar `info.log` y `error.log` despues de abrir y cerrar la app.

## 6. Prueba fiscal controlada

Realizar con supervision y comprobante real controlado.

- [ ] Procesar 1 comprobante real controlado.
- [ ] Validar que se solicito CAE.
- [ ] Validar CAE y vencimiento contra el registro del comprobante.
- [ ] Validar PDF generado.
- [ ] Validar impresion o salida prevista.
- [ ] Validar email enviado o cola de email pendiente/enviado.
- [ ] Validar que no haya errores criticos en `error.log`.
- [ ] Validar que `info.log` refleje el ciclo esperado.
- [ ] Confirmar que no se usó CAEA salvo que correspondiera por regla operativa.

## 7. Publicacion

- [ ] Detener o cerrar la instancia productiva anterior.
- [ ] Copiar el ejecutable nuevo al destino productivo.
- [ ] Mantener disponible el backup del ejecutable anterior.
- [ ] Mantener disponible el backup de `sistema.ini`.
- [ ] Abrir la app productiva y repetir validaciones basicas de inicio.
- [ ] Registrar commit/tag publicado, fecha, responsable y estacion usada.

## 8. Rollback

Ejecutar rollback si falla apertura, CAE, impresion, PDF, email o logs muestran error critico.

- [ ] Cerrar la app.
- [ ] Restaurar `main.exe` desde el backup.
- [ ] Restaurar `sistema.ini` desde el backup si fue modificado.
- [ ] Abrir la version anterior.
- [ ] Confirmar que vuelve a procesar normalmente.
- [ ] Registrar motivo del rollback y adjuntar extractos relevantes de logs.

## 9. Cierre

- [ ] Confirmar que el release quedo documentado.
- [ ] Confirmar que el tag/release coincide con el ejecutable publicado.
- [ ] Confirmar que no quedaron cambios locales sin commit despues del release.
- [ ] Confirmar que el primer comprobante real controlado quedo validado.
