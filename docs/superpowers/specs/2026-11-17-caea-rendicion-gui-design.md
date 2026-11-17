# Diseño: rendición de CAEA integrada al GUI de `main.exe`

Fecha: 2026-11-17

## Contexto

Producción corre solo `main.exe` (onefile de PyInstaller; `main.spec` declara
`datas=[]` y `hiddenimports=[]`). Hoy la rendición/presentación de CAEA se
dispara con dos scripts sueltos que **no** van dentro del ejecutable:

- `informacaea.py` → diálogo PyQt (`vistas/InformaCAEA.py`, `controladores/InformaCAEA.py`)
- `rendir_caea.py` → CLI

Ya están empaquetados y confirmados en el xref del último build:
`controladores/RendirCAEA.py`, `controladores/CAEAProgramado.py` y
`controladores/EnvioEmailsPendientes.py`. No están empaquetados
`controladores/InformaCAEA.py` ni `vistas/InformaCAEA.py`.

## Objetivo

Que el operador pueda rendir/presentar CAEA desde un botón en la ventana
principal de `main.exe`, sin scripts Python separados, **sin detener la
generación de CAE**.

## Fuera de alcance

- No cambiar el servicio `rendir()`, la bitácora `caea_rendicion` ni el correo
  de resumen a `sistemas@ferreteriaavenida.com.ar`.
- No eliminar `informacaea.py` ni `rendir_caea.py`: quedan como utilidades de
  desarrollo y no se copian a producción.
- No modificar el SQL de migración ya entregado.

## Hechos verificados que sustentan el diseño

- `GeneraCAEA` (`Main.py:1113-1152`) solo usa el CAEA de la quincena **actual**
  (calculada con la fecha de hoy).
- `rendir_ptovta` (`RendirCAEA.py:196-201`) filtra encabezados por
  `cae == caea` de la quincena solicitada.
- La quincena a rendir está en la ventana de 8 días posteriores al cierre,
  por lo que es siempre la **cerrada/anterior**, distinta de la actual. Los dos
  flujos tocan filas distintas: no hace falta pausar nada.
- `CreaFE` (`Main.py:764-1014`) solo usa `self.view.gridFacturas`
  (`rowCount`, `removeRow`, `AgregaItem`); puede correr con una vista stub.
- `MainController.__init__` arranca timers y envía mail de arranque; el worker
  no debe hacerlo.

## Diseño

### 1. Botón en la ventana principal

- `vistas/Main.py`: agregar `btnRendirCAEA` al `layoutBotones`, antes de
  `btnCerrar`.
- `controladores/Main.py::conectarWidgets`: conectar el botón a
  `MainController.AbrirRendirCAEA`.

### 2. Apertura del diálogo (sin pausa)

- `MainController.AbrirRendirCAEA()` importa `InformaCAEAController` de forma
  perezosa (el módulo `InformaCAEA` importa `Main`, así que un import de
  módulo generaría ciclo), construye el controlador con `parent=self.view` y
  llama `exec_()`.
- **No** se llama a `PausarProcesamiento()` ni se detiene
  `_procesamiento_timer`.

### 3. Diálogo

- `vistas/InformaCAEA.py` (`InfromaCAEAView`): mantiene Periodo, Orden y
  Pto Vta; agrega `lblResultado` para mostrar el resumen. Pto Vta vacío
  significa "todos los puntos habilitados".
- `controladores/InformaCAEA.py`:
  - `__init__(self, parent=None, controlador=None)`: usa `parent`, guarda
    `controlador`. No crea un `MainController` propio.
  - Prellena periodo/orden con la quincena **cerrada**: si el día es <= 15,
    orden 2 del mes anterior; si es > 15, orden 1 del mes actual.
  - `Informa()`: valida que no se haya elegido la quincena actual (muestra
    aviso y aborta); deshabilita el botón y muestra "Rendiendo CAEA…";
    ejecuta `rendir()` en un worker; al terminar muestra el resumen y
    rehabilita el botón.
  - `Cerrar()`: marca `_want_to_close = True` y cierra solo el diálogo.
    **No** llama a `QApplication.exit(1)`.

### 4. Worker headless

- Agregar a `MainController.__init__` los parámetros opcionales
  `view=None` y `modo_servicio=False`:
  - usa `view or MainView()`;
  - si `modo_servicio`: no llama `initUi()`, no crea ni arranca timers
    (`_procesamiento_timer`, `_caea_timer`, `QTimer.singleShot`), no consulta
    estados operativos ni envía mail de arranque; sí inicializa la DB y
    `grabaxml = True`.
- Vista stub con `gridFacturas.rowCount()`, `removeRow()` y `AgregaItem()`
  no-op, para que `CreaFE` pueda correr sin widgets.
- El worker usa un `ThreadPoolExecutor(max_workers=1)` y devuelve el resumen.
  El diálogo recibe el resultado en el hilo GUI mediante
  `QTimer.singleShot(0, ...)`.

### 5. Empaquetado

- `main.py`: agregar un import de módulo
  `from controladores.InformaCAEA import InformaCAEAController  # noqa: F401`
  para que PyInstaller incluya el controlador y su vista. (Si aparece un ciclo
  de imports, alternativa: `hiddenimports` en `main.spec`.)

### 6. Email y bitácora

Sin cambios. `rendir()` ya envía el resumen por la cola de emails y escribe
`caea_rendicion`; el ciclo principal sigue enviando correos pendientes.

## Manejo de errores

- Tabla `caea_rendicion` faltante: mostrar mensaje entendible en el diálogo,
  no un traceback.
- Fallo de un punto de venta: el resumen igual se envía y se muestra.
- Excepción en el worker: se captura y se muestra en `lblResultado`.

## Tests y verificación

- Estáticos: botón presente y cableado; import de `InformaCAEA` en `main.py`;
  ausencia de `QApplication.exit`; ausencia de `PausarProcesamiento` en el
  flujo del diálogo; ausencia de timers en modo servicio.
- Unitarios: prefill de quincena cerrada; rechazo de la quincena actual;
  ptovta vacío → todos; vista stub sin widgets; resultado del worker.
- Build: correr `.\compilar.ps1` y confirmar en `build/main/xref-main.html`
  que `controladores.InformaCAEA` y `vistas.InformaCAEA` están incluidos.
