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
