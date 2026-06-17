import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN_CONTROLLER = ROOT / "controladores" / "Main.py"
MAIN_VIEW = ROOT / "vistas" / "Main.py"


def _tree(path):
    return ast.parse(path.read_text(encoding="utf-8"))


def _function_def(path, name):
    for node in ast.walk(_tree(path)):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"No se encontro la funcion {name} en {path.relative_to(ROOT)}")


def _class_def(path, name):
    for node in ast.walk(_tree(path)):
        if isinstance(node, ast.ClassDef) and node.name == name:
            return node
    raise AssertionError(f"No se encontro la clase {name} en {path.relative_to(ROOT)}")


def _called_attributes(node):
    calls = []

    class CallVisitor(ast.NodeVisitor):
        def visit_Call(self, child):
            if isinstance(child.func, ast.Attribute):
                calls.append(child.func.attr)
            self.generic_visit(child)

    CallVisitor().visit(node)
    return calls


def _imported_from(path, module, name):
    for node in ast.walk(_tree(path)):
        if isinstance(node, ast.ImportFrom) and node.module == module:
            if any(alias.name == name for alias in node.names):
                return True
    return False


def test_main_controller_usa_qtimer_para_orquestar_el_ciclo():
    main_controller = MAIN_CONTROLLER.read_text(encoding="utf-8")

    assert _imported_from(MAIN_CONTROLLER, "PyQt5.QtCore", "QTimer")
    assert "self._procesamiento_timer = QTimer(self.view)" in main_controller
    assert "self._procesamiento_timer.timeout.connect(self._ejecutar_ciclo_procesamiento)" in main_controller


def test_generafe_no_tiene_loop_manual_ni_bombeo_de_eventos():
    generafe = _function_def(MAIN_CONTROLLER, "GeneraFE")
    calls = _called_attributes(generafe)

    assert not any(isinstance(node, (ast.While, ast.For)) for node in ast.walk(generafe))
    assert "processEvents" not in calls
    assert "sleep" not in calls


def test_ciclo_procesamiento_evita_reentradas_y_conserva_orden_operativo():
    ciclo = _function_def(MAIN_CONTROLLER, "_ejecutar_ciclo_procesamiento")
    source = ast.get_source_segment(MAIN_CONTROLLER.read_text(encoding="utf-8"), ciclo)
    calls = _called_attributes(ciclo)

    assert "self._procesando_ciclo" in source
    assert "self._procesando_ciclo = True" in source
    assert "self._procesando_ciclo = False" in source

    expected_order = [
        "VerificarEstadoAFIP",
        "GeneraCAE",
        "ImpresionFactura",
        "GeneraCAEA",
        "EnviaCorreos",
    ]
    positions = [calls.index(name) for name in expected_order]
    assert positions == sorted(positions)


def test_ciclo_no_bloquea_cae_por_dummy_afip_por_defecto(monkeypatch):
    from controladores.Main import MainController
    import controladores.Main as main_module

    controller = MainController.__new__(MainController)
    eventos = []

    monkeypatch.setattr(main_module, "LeerIni", lambda clave=None, key=None: "")
    controller.lProcesa = True
    controller._procesando_ciclo = False
    controller._procesamiento_timer = type(
        "FakeTimer",
        (),
        {"isActive": lambda self: False, "stop": lambda self: None},
    )()
    controller.view = type(
        "FakeView",
        (),
        {
            "btnIniciar": object(),
            "btnPausar": object(),
            "lblProcesamiento": type("FakeLabel", (), {"setText": lambda self, text: eventos.append(text)})(),
        },
    )()

    controller.VerificarEstadoAFIP = lambda: eventos.append("VerificarEstadoAFIP") or False
    controller.GeneraCAE = lambda: eventos.append("GeneraCAE")
    controller.ImpresionFactura = lambda: eventos.append("ImpresionFactura")
    controller.GeneraCAEA = lambda: eventos.append("GeneraCAEA")
    controller.EnviaCorreos = lambda: eventos.append("EnviaCorreos")
    controller._actualizar_estado_operativo_afip = lambda: None
    controller._actualizar_estado_operativo_emails = lambda: None

    controller._ejecutar_ciclo_procesamiento()

    assert eventos == [
        "VerificarEstadoAFIP",
        "GeneraCAE",
        "ImpresionFactura",
        "GeneraCAEA",
        "EnviaCorreos",
    ]


def test_ciclo_bloquea_cae_por_dummy_afip_solo_con_config_explicita(monkeypatch):
    from controladores.Main import MainController
    import controladores.Main as main_module

    controller = MainController.__new__(MainController)
    eventos = []

    def fake_leer_ini(clave=None, key=None):
        if clave == "bloquear_cae_si_afip_dummy_falla":
            return "S"
        return ""

    monkeypatch.setattr(main_module, "LeerIni", fake_leer_ini)
    controller.lProcesa = True
    controller._procesando_ciclo = False
    controller._procesamiento_timer = type(
        "FakeTimer",
        (),
        {"isActive": lambda self: False, "stop": lambda self: None},
    )()
    controller.view = type(
        "FakeView",
        (),
        {
            "btnIniciar": object(),
            "btnPausar": object(),
            "lblProcesamiento": type("FakeLabel", (), {"setText": lambda self, text: eventos.append(text)})(),
        },
    )()

    controller.VerificarEstadoAFIP = lambda: eventos.append("VerificarEstadoAFIP") or False
    controller.GeneraCAE = lambda: eventos.append("GeneraCAE")
    controller.ImpresionFactura = lambda: eventos.append("ImpresionFactura")
    controller.GeneraCAEA = lambda: eventos.append("GeneraCAEA")
    controller.EnviaCorreos = lambda: eventos.append("EnviaCorreos")
    controller._actualizar_estado_operativo_afip = lambda: None
    controller._actualizar_estado_operativo_emails = lambda: None

    controller._ejecutar_ciclo_procesamiento()

    assert "GeneraCAE" not in eventos
    assert eventos[0] == "VerificarEstadoAFIP"
    assert "ImpresionFactura" in eventos
    assert "GeneraCAEA" in eventos
    assert "EnviaCorreos" in eventos


def test_vista_expone_boton_pausar_para_detener_reanudar():
    view_source = MAIN_VIEW.read_text(encoding="utf-8")
    main_view = _class_def(MAIN_VIEW, "MainView")

    assert "btnPausar" in view_source
    assert "Pausar" in view_source
    assert "btnPausar" in ast.get_source_segment(view_source, main_view)
