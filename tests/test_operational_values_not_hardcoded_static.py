from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CODE_FILES = [
    ROOT / "controladores" / "Main.py",
    ROOT / "controladores" / "InformaCAEA.py",
    ROOT / "main.py",
]

FORBIDDEN_VALUES = [
    "20233472035",
    "oscar" + "@ferreteriaavenida.com.ar",
    "sistemas" + "@ferreteriaavenida.com.ar",
    "info" + "@ferreteriaavenida.com.ar",
    "vogel" + "_wsass",
    "clave_privada" + "_20233472035",
]


def test_operational_values_are_not_hardcoded_in_main_flows():
    offenders = []

    for path in CODE_FILES:
        source = path.read_text(encoding="utf-8")
        for value in FORBIDDEN_VALUES:
            if value in source:
                offenders.append(f"{path.relative_to(ROOT)} contains {value}")

    assert offenders == []
