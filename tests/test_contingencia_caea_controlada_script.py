import subprocess
import sys
from pathlib import Path


def test_script_controlado_simula_caida_y_recuperacion_sin_efectos_reales():
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "probar_contingencia_caea_controlada.py"
    source = script.read_text(encoding="utf-8")

    assert "side-effect free" in source
    assert "no abre conexiones" in source
    assert "no llama AFIP" in source
    resultado = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(root),
        text=True,
        capture_output=True,
        check=False,
    )

    assert resultado.returncode == 0, resultado.stderr
    assert resultado.stderr == ""
    assert "Prueba controlada de contingencia CAEA" in resultado.stdout
    assert "Sin DB real, sin AFIP real, sin email real." in resultado.stdout
    assert "CAEA vigente simulado: si" in resultado.stdout
    assert "AFIP disponible=False -> activar contingencia" in resultado.stdout
    assert "CAJA-CONTROLADA: ptovtafac=0021 ptovtaticket=0022" in resultado.stdout
    assert "AFIP disponible=True -> restaurar WS" in resultado.stdout
    assert "CAJA-CONTROLADA: ptovtafac=0019 ptovtaticket=0018" in resultado.stdout
    assert "Resultado: OK" in resultado.stdout
    assert "SolicitarCAEA" not in resultado.stdout
