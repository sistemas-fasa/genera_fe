# Rendición de CAEA integrada al GUI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que `main.exe` permita rendir/presentar CAEA desde un botón de su GUI, en segundo plano, sin detener la generación de CAE ni requerir scripts Python separados.

**Architecture:** Un botón nuevo en `MainView` abre el diálogo `InfromaCAEAView` como modal. El diálogo prellena la quincena cerrada y envía `rendir()` a un `ThreadPoolExecutor`; el worker usa un `MainController` modo servicio con vista stub (sin timers, sin widgets, sin mail de arranque), y una `pyqtSignal` devuelve el resumen al hilo GUI. El ciclo principal no se pausa.

**Tech Stack:** Python 3.13, PyQt5, Peewee/MySQL, PyInstaller 6.21, pytest.

---

### Task 1: Vista stub y `MainController` modo servicio

**Files:**
- Create: `libs/VistaStub.py`
- Modify: `controladores/Main.py:259-298` (`__init__`)
- Test: `tests/test_informa_caea_gui.py`

- [ ] **Step 1: Write the failing test**

En `tests/test_informa_caea_gui.py` (archivo nuevo):

```python
"""Tests del rendido de CAEA desde el GUI, sin AFIP y sin base."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "controladores" / "Main.py"
VISTA_MAIN = ROOT / "vistas" / "Main.py"
INFORMA = ROOT / "controladores" / "InformaCAEA.py"
ENTRY = ROOT / "main.py"


def test_vista_stub_satisface_creafe():
    from libs.VistaStub import VistaStub

    vista = VistaStub()
    assert vista.gridFacturas.rowCount() == 0
    vista.gridFacturas.removeRow(0)
    vista.gridFacturas.AgregaItem(items=["x"], backgroundColor="white")


def test_main_controller_acepta_modo_servicio():
    fuente = MAIN.read_text(encoding="utf-8")
    assert "def __init__(self, view=None, modo_servicio=False):" in fuente
    assert "if modo_servicio:" in fuente
    assert "self.view = view or MainView()" in fuente
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_informa_caea_gui.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'libs.VistaStub'` y el assert del `__init__`.

- [ ] **Step 3: Write minimal implementation**

Crear `libs/VistaStub.py`:

```python
# coding=utf-8
"""Vista sin widgets para ejecutar CreaFE fuera del hilo GUI.

MainController.CreaFE solo usa self.view.gridFacturas (rowCount, removeRow y
AgregaItem). Este stub evita construir widgets Qt en un hilo worker y evita
mostrar una segunda ventana.
"""


class GrillaStub:

    def rowCount(self):
        return 0

    def removeRow(self, fila):
        pass

    def AgregaItem(self, **kwargs):
        pass


class VistaStub:

    def __init__(self):
        self.gridFacturas = GrillaStub()
```

Reemplazar el `__init__` de `controladores/Main.py` (líneas 259-298) por:

```python
    def __init__(self, view=None, modo_servicio=False):
        super(MainController, self).__init__()
        self.modo_servicio = modo_servicio
        self.view = view or MainView()
        self.lProcesa = False
        self._procesando_ciclo = False
        self._caea_ausente_alertado_en = None
        self.model = ModeloBase()
        self.model.getDb()
        # Graba xmlrequest.xml y xmlresponse.xml del ultimo comprobante para
        # poder depurar contra AFIP. Queda en disco, no se guarda en la base.
        self.grabaxml = True
        if modo_servicio:
            # Worker del rendido: reutiliza CreaFE sin timers, sin segunda
            # MainView y sin mail de arranque. El ciclo principal sigue vivo.
            return
        self.view.initUi()
        self._procesamiento_timer = QTimer(self.view)
        self._procesamiento_timer.setInterval(500)
        self._procesamiento_timer.timeout.connect(self._ejecutar_ciclo_procesamiento)
        self.conectarWidgets()
        QTimer.singleShot(1000, self._verificar_caea_programado)
        self._caea_timer = QTimer(self.view)
        self._caea_timer.setInterval(self._intervalo_verificacion_caea_ms())
        self._caea_timer.timeout.connect(self._verificar_caea_programado)
        self._caea_timer.start()
        self._actualizar_estado_operativo_afip()
        self._actualizar_estado_operativo_emails()
        self.afip_intervalo_verificacion = self._leer_intervalo_verificacion_afip()
        self._email_executor = ThreadPoolExecutor(max_workers=5)
        self._email_futures = {}
        destinatario, cc = self._destinatarios_alerta_afip()
        logging.info(
            "Monitor AFIP inicializado - intervalo de verificacion: %s minuto(s)",
            int(self.afip_intervalo_verificacion.total_seconds() // 60),
        )
        logging.info(
            "Monitor AFIP destinatarios - to: %s | cc: %s",
            destinatario, cc or "sin cc",
        )
        if self._debe_notificar_arranque_afip():
            self._notificar_arranque_monitor_afip(destinatario, cc)
        else:
            logging.info(
                "Monitor AFIP arranque - notificacion por email deshabilitada por configuracion"
            )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/test_informa_caea_gui.py -q`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```powershell
git add libs/VistaStub.py controladores/Main.py tests/test_informa_caea_gui.py
git commit -m "feat: vista stub y modo servicio para rendir CAEA en worker"
```

---

### Task 2: Botón "Rendir CAEA" en la ventana principal

**Files:**
- Modify: `vistas/Main.py:73-86`
- Modify: `controladores/Main.py:407-413`
- Test: `tests/test_informa_caea_gui.py`

- [ ] **Step 1: Write the failing test**

Agregar a `tests/test_informa_caea_gui.py`:

```python
def test_main_view_tiene_boton_rendir_caea_y_esta_cableado():
    vista = VISTA_MAIN.read_text(encoding="utf-8")
    controlador = MAIN.read_text(encoding="utf-8")

    assert "self.btnRendirCAEA = Boton(" in vista
    assert "layoutBotones.addWidget(self.btnRendirCAEA)" in vista
    assert "self.view.btnRendirCAEA.clicked.connect(self.AbrirRendirCAEA)" in controlador
    assert "def AbrirRendirCAEA(self):" in controlador


def test_abrir_rendir_no_pausa_el_ciclo():
    import ast

    arbol = ast.parse(MAIN.read_text(encoding="utf-8"))
    metodo = next(
        n for n in ast.walk(arbol)
        if isinstance(n, ast.FunctionDef) and n.name == "AbrirRendirCAEA"
    )
    cuerpo = ast.get_source_segment(MAIN.read_text(encoding="utf-8"), metodo)
    assert "PausarProcesamiento" not in cuerpo
    assert "from controladores.InformaCAEA import InformaCAEAController" in cuerpo
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_informa_caea_gui.py -q`
Expected: FAIL con los 2 asserts del botón.

- [ ] **Step 3: Write minimal implementation**

En `vistas/Main.py`, luego de `self.btnDiagnostico = ...` (línea 78):

```python
        self.btnRendirCAEA = Boton(texto='Rendir CAEA', imagen='imagenes/buscar.png')
```

En `layoutBotones`, antes de `addWidget(self.btnCerrar)`:

```python
        layoutBotones.addWidget(self.btnRendirCAEA)
```

En `controladores/Main.py::conectarWidgets`, después de la línea de `btnDiagnostico`:

```python
        self.view.btnRendirCAEA.clicked.connect(self.AbrirRendirCAEA)
```

Agregar método nuevo después de `AbrirDiagnostico` (línea 417):

```python
    def AbrirRendirCAEA(self):
        # Import perezoso: InformaCAEA importa Main, asi que hacerlo arriba
        # daria un ciclo de imports.
        from controladores.InformaCAEA import InformaCAEAController

        dialogo = InformaCAEAController(controlador=self)
        dialogo.exec_()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/test_informa_caea_gui.py -q`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```powershell
git add vistas/Main.py controladores/Main.py tests/test_informa_caea_gui.py
git commit -m "feat: boton Rendir CAEA en el GUI principal"
```

---

### Task 3: `quincena_anterior` en `CAEAProgramado`

**Files:**
- Modify: `controladores/CAEAProgramado.py:36-43`
- Test: `tests/test_informa_caea_gui.py`

- [ ] **Step 1: Write the failing test**

Agregar a `tests/test_informa_caea_gui.py`:

```python
def test_quincena_anterior_calcula_la_cerrada():
    from controladores.CAEAProgramado import quincena_anterior

    assert quincena_anterior("202611", "1") == ("202610", "2")
    assert quincena_anterior("202611", "2") == ("202611", "1")
    assert quincena_anterior("202601", "1") == ("202512", "2")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_informa_caea_gui.py -q`
Expected: FAIL con `ImportError: cannot import name 'quincena_anterior'`.

- [ ] **Step 3: Write minimal implementation**

Agregar después de `_quincena_siguiente` en `controladores/CAEAProgramado.py`:

```python
def quincena_anterior(periodo, orden):
    """Devuelve (periodo, orden) de la quincena inmediatamente anterior.

    Es la que debe rendirse: siempre es distinta de la actual, que es la
    unica que usa GeneraCAEA en el ciclo principal.
    """
    anio = int(periodo[:4])
    mes = int(periodo[4:6])
    if orden == "1":
        if mes == 1:
            return "{:04d}{:02d}".format(anio - 1, 12), "2"
        return "{:04d}{:02d}".format(anio, mes - 1), "2"
    return "{:04d}{:02d}".format(anio, mes), "1"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/test_informa_caea_gui.py -q`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```powershell
git add controladores/CAEAProgramado.py tests/test_informa_caea_gui.py
git commit -m "feat: helper de quincena anterior para el rendido"
```

---

### Task 4: Diálogo con ejecución en segundo plano

**Files:**
- Modify: `vistas/InformaCAEA.py:19-42`
- Rewrite: `controladores/InformaCAEA.py`
- Test: `tests/test_informa_caea_gui.py`

- [ ] **Step 1: Write the failing test**

Agregar a `tests/test_informa_caea_gui.py`:

```python
def test_dialogo_muestra_resultado_y_no_mata_la_app():
    vista = (ROOT / "vistas" / "InformaCAEA.py").read_text(encoding="utf-8")
    fuente = INFORMA.read_text(encoding="utf-8")

    assert "self.lblResultado = Etiqueta" in vista
    assert "QApplication.exit" not in fuente
    assert "PausarProcesamiento" not in fuente
    assert "ThreadPoolExecutor" in fuente
    assert "pyqtSignal" in fuente
    assert "modo_servicio=True" in fuente


def test_rendir_del_worker_pasa_todos_los_ptovtas_cuando_esta_vacio(monkeypatch):
    import controladores.InformaCAEA as modulo

    capturado = {}

    def rendir_falso(periodo, orden, **kwargs):
        capturado.update(periodo=periodo, orden=orden, kwargs=kwargs)
        return {"ok": True, "mensaje": "listo", "detalle": []}

    monkeypatch.setattr(modulo, "rendir", rendir_falso)
    controlador = object()
    dialogo = modulo.InformaCAEAController.__new__(modulo.InformaCAEAController)
    dialogo.controlador = controlador

    resumen = dialogo._rendir("202610", "2", "")

    assert resumen["ok"] is True
    assert capturado["periodo"] == "202610"
    assert capturado["kwargs"]["ptovta"] is None
    assert capturado["kwargs"]["controlador"] is controlador
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_informa_caea_gui.py -q`
Expected: FAIL (no existe `lblResultado`, `InformaCAEA.py` aún tiene `QApplication.exit`, y no hay `_rendir`).

- [ ] **Step 3: Write minimal implementation**

En `vistas/InformaCAEA.py`, después de `self.layoutPpal.addLayout(self.layoutParametros)`:

```python
        self.lblResultado = Etiqueta(texto='')
        self.layoutPpal.addWidget(self.lblResultado)
```

Reemplazar todo `controladores/InformaCAEA.py` por:

```python
# coding=utf-8
"""Rendido de CAEA desde el GUI principal de main.exe.

Antes este modulo era el entrypoint de informacaea.py y cerraba toda la
aplicacion al terminar. Ahora es un dialogo modal del proceso principal: el
rendido corre en un worker con un MainController sin timers ni widgets, asi
que la generacion de CAE del ciclo principal NO se detiene.
"""
import logging
from concurrent.futures import ThreadPoolExecutor

from PyQt5.QtCore import QObject, pyqtSignal

from controladores.CAEAProgramado import (
    calcular_periodo_orden_actual,
    quincena_anterior,
)
from controladores.ControladorBase import ControladorBase
from controladores.Main import MainController
from controladores.RendirCAEA import rendir
from libs.Avisos import mostrar_advertencia, mostrar_error
from libs.VistaStub import VistaStub
from modelos.ModeloBase import ModeloBase
from vistas.InformaCAEA import InfromaCAEAView


class _Senales(QObject):

    terminado = pyqtSignal(object)


class InformaCAEAController(ControladorBase):

    def __init__(self, controlador=None, executor=None):
        super(InformaCAEAController, self).__init__()
        self.view = InfromaCAEAView()
        self.view.initUi()
        self.conectarWidgets()
        self.model = ModeloBase()
        self.model.getDb()
        self.controlador = controlador
        self._executor = executor or ThreadPoolExecutor(max_workers=1)
        self._future = None
        self._senales = _Senales()
        self._senales.terminado.connect(self._al_terminar)

        periodo, orden = calcular_periodo_orden_actual()
        periodo, orden = quincena_anterior(periodo, orden)
        self.view.layoutParametros.lineEditAnio.setValue(int(periodo[:4]))
        self.view.layoutParametros.lineEditMes.setValue(int(periodo[4:]))
        self.view.txtOrden.setText(orden)
        self.view.lblResultado.setText("")

    def conectarWidgets(self):
        self.view.btnCerrar.clicked.connect(self.Cerrar)
        self.view.btnIniciar.clicked.connect(self.Informa)

    def Cerrar(self):
        # Antes: QApplication.exit(1) cerraba todo el sistema, no este dialogo.
        self.view._want_to_close = True
        self.view.close()

    def Informa(self):
        periodo = self.view.layoutParametros.cPeriodo
        orden = str(self.view.txtOrden.text()).strip()
        ptovta = str(self.view.txtPtoVta.text()).strip()
        if (periodo, orden) == calcular_periodo_orden_actual():
            mostrar_advertencia(
                "Rendir CAEA",
                "Esa es la quincena actual: todavia no cerro. "
                "Rinda la quincena anterior.",
            )
            return
        if self._future is not None and not self._future.done():
            return
        self.view.btnIniciar.setEnabled(False)
        self.view.lblResultado.setText("Rendiendo CAEA...")
        self._future = self._executor.submit(
            self._rendir_y_avisar, periodo, orden, ptovta
        )

    def _rendir(self, periodo, orden, ptovta):
        """Corre en el worker: no toca ningun widget de Qt."""
        try:
            controlador = self.controlador
            if controlador is None:
                controlador = MainController(view=VistaStub(), modo_servicio=True)
            return rendir(
                periodo,
                orden,
                empresa_id=1,
                ptovta=ptovta or None,
                controlador=controlador,
            )
        except Exception as exc:
            logging.exception("No se pudo rendir el CAEA desde el GUI")
            return {
                "periodo": periodo,
                "orden": str(orden),
                "ok": False,
                "mensaje": str(exc),
                "detalle": [],
            }

    def _rendir_y_avisar(self, periodo, orden, ptovta):
        resumen = self._rendir(periodo, orden, ptovta)
        # La conexion automatica de pyqtSignal hace que _al_terminar corra en
        # el hilo GUI aunque el emit venga del worker.
        self._senales.terminado.emit(resumen)

    def _al_terminar(self, resumen):
        self.view.btnIniciar.setEnabled(True)
        self.view.lblResultado.setText(resumen["mensaje"])
        if not resumen["ok"]:
            mostrar_error("Rendido de CAEA", resumen["mensaje"])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/test_informa_caea_gui.py -q`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```powershell
git add vistas/InformaCAEA.py controladores/InformaCAEA.py tests/test_informa_caea_gui.py
git commit -m "feat: rendido de CAEA en segundo plano desde el dialogo del GUI"
```

---

### Task 5: Empaquetado en PyInstaller

**Files:**
- Modify: `main.py:29-35`
- Test: `tests/test_informa_caea_gui.py`

- [ ] **Step 1: Write the failing test**

Agregar a `tests/test_informa_caea_gui.py`:

```python
def test_main_importa_informa_caea_para_pyinstaller():
    fuente = ENTRY.read_text(encoding="utf-8")
    assert (
        "from controladores.InformaCAEA import InformaCAEAController"
        in fuente
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_informa_caea_gui.py -q`
Expected: FAIL con el assert del import.

- [ ] **Step 3: Write minimal implementation**

En `main.py`, después de `from controladores.FE import FEv1`:

```python
# Import de modulo para que PyInstaller incluya el dialogo de rendido: sin
# esta referencia main.spec (datas=[], hiddenimports=[]) no lo empaqueta.
from controladores.InformaCAEA import InformaCAEAController  # noqa: F401
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests -q`
Expected: PASS (159 tests; 145 anteriores + 14 nuevos).

- [ ] **Step 5: Commit**

```powershell
git add main.py tests/test_informa_caea_gui.py
git commit -m "build: empaquetar el dialogo de rendido CAEA en main.exe"
```

---

### Task 6: Build y verificación final

**Files:**
- Modify: `version.txt` (lo reescribe `compilar.ps1`)
- Verify: `dist/main.exe`, `build/main/xref-main.html`

- [ ] **Step 1: Verificar compilación Python y suite completa**

Run:
```powershell
.venv\Scripts\python.exe -m py_compile controladores/Main.py controladores/InformaCAEA.py controladores/CAEAProgramado.py vistas/Main.py vistas/InformaCAEA.py libs/VistaStub.py main.py
.venv\Scripts\python.exe -m pytest tests -q
```
Expected: `compilacion` sin errores; `159 passed`.

- [ ] **Step 2: Recompilar el ejecutable**

Run: `.\compilar.ps1`
Expected: salida con `Version embebida en main.exe: 2026.11.17.02` (o el build que corresponda), `main.exe generado` y exit 0.

- [ ] **Step 3: Verificar que el diálogo quedó empaquetado**

Run:
```powershell
Select-String -Path build\main\xref-main.html -Pattern "controladores.InformaCAEA","vistas.InformaCAEA" | Select-Object -First 4
```
Expected: al menos una coincidencia para cada módulo.

- [ ] **Step 4: Commit del bump de versión**

```powershell
git add version.txt
git commit -m "build: version del ejecutable con rendido CAEA en el GUI"
```
