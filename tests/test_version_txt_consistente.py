"""Consistencia interna de version.txt.

Ademas de correr como pytest, se puede ejecutar a mano para inspeccionar los
valores:

    python tests\test_version_txt_consistente.py [ruta]
"""

import sys
from pathlib import Path


VERSION_TXT = Path(__file__).resolve().parents[1] / "version.txt"


class N:
    def __init__(self, *a, **k):
        self.a = a
        self.k = k


NAMES = [
    "FixedFileInfo",
    "StringStruct",
    "StringFileInfo",
    "StringTable",
    "VarStruct",
    "VarFileInfo",
    "VSVersionInfo",
]


def cargar(ruta):
    g = {n: type(n, (N,), {}) for n in NAMES}
    src = open(ruta, encoding="utf-8").read()
    return eval(compile(src, str(ruta), "eval"), g)


def recorrer(nodo):
    """Devuelve dicts de todos los StringStruct del arbol."""
    out = {}
    if isinstance(nodo, N):
        if type(nodo).__name__ == "StringStruct":
            out[nodo.a[0]] = nodo.a[1]
        for hijo in list(nodo.a) + list(nodo.k.values()):
            out.update(recorrer(hijo))
    elif isinstance(nodo, (list, tuple)):
        for hijo in nodo:
            out.update(recorrer(hijo))
    return out


def leer(ruta):
    """Devuelve (filevers, prodvers, ProductVersion, FileVersion, InternalName, OriginalFilename)."""
    v = cargar(ruta)
    ffi = v.k["ffi"]
    sts = recorrer(v.k["kids"])
    return (
        ffi.k["filevers"],
        ffi.k["prodvers"],
        sts["ProductVersion"],
        sts["FileVersion"],
        sts["InternalName"],
        sts["OriginalFilename"],
    )


def test_version_txt_es_consistente():
    fv_file, fv_prod, pv, fv, _internal, original = leer(VERSION_TXT)

    pv_t = tuple(int(x) for x in pv.split("."))
    fv_t = tuple(int(x) for x in fv.split("."))

    assert fv_file == fv_prod, "filevers != prodvers"
    assert pv_t == fv_file, (pv_t, fv_file)
    assert fv_t == fv_file, (fv_t, fv_file)
    assert original == "main.exe", original


if __name__ == "__main__":
    ruta = sys.argv[1] if len(sys.argv) > 1 else VERSION_TXT
    fv_file, fv_prod, pv, fv, internal, original = leer(ruta)

    print("filevers         =", fv_file)
    print("prodvers         =", fv_prod)
    print("ProductVersion   =", pv)
    print("FileVersion      =", fv)
    print("InternalName     =", internal)
    print("OriginalFilename =", original)

    test_version_txt_es_consistente()
    print("\nOK: filevers == prodvers == ProductVersion == FileVersion ==" " {}".format(pv))