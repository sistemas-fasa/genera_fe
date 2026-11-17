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


def test_main_view_tiene_boton_rendir_caea_y_esta_cableado():
    vista = VISTA_MAIN.read_text(encoding="utf-8")
    controlador = MAIN.read_text(encoding="utf-8")

    assert "self.btnRendirCAEA = Boton(" in vista
    assert "layoutBotones.addWidget(self.btnRendirCAEA)" in vista
    assert "self.view.btnRendirCAEA.clicked.connect(self.AbrirRendirCAEA)" in controlador
    assert "def AbrirRendirCAEA(self):" in controlador


def test_abrir_rendir_no_pausa_el_ciclo():
    import ast

    fuente = MAIN.read_text(encoding="utf-8")
    arbol = ast.parse(fuente)
    metodo = next(
        n for n in ast.walk(arbol)
        if isinstance(n, ast.FunctionDef) and n.name == "AbrirRendirCAEA"
    )
    cuerpo = ast.get_source_segment(fuente, metodo)
    assert "PausarProcesamiento" not in cuerpo
    assert "from controladores.InformaCAEA import InformaCAEAController" in cuerpo
