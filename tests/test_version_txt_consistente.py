import sys


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
    return eval(compile(src, ruta, "eval"), g)


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


v = cargar(sys.argv[1])
ffi = v.k["ffi"]
sts = recorrer(v.k["kids"])

fv_file = ffi.k["filevers"]
fv_prod = ffi.k["prodvers"]
pv = sts["ProductVersion"]
fv = sts["FileVersion"]

print("filevers       =", fv_file)
print("prodvers       =", fv_prod)
print("ProductVersion =", pv)
print("FileVersion    =", fv)
print("InternalName   =", sts["InternalName"])
print("OriginalFilename =", sts["OriginalFilename"])

pv_t = tuple(int(x) for x in pv.split("."))
fv_t = tuple(int(x) for x in fv.split("."))

assert fv_file == fv_prod, "filevers != prodvers"
assert pv_t == fv_file, (pv_t, fv_file)
assert fv_t == fv_file, (fv_t, fv_file)
assert sts["OriginalFilename"] == "main.exe", sts["OriginalFilename"]
print("\nOK: filevers == prodvers == ProductVersion == FileVersion == 0.2.0.0")
