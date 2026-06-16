import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODELOBASE = ROOT / "modelos" / "ModeloBase.py"


def _source():
    return MODELOBASE.read_text(encoding="utf-8")


def _tree():
    return ast.parse(_source())


def test_modelobase_define_helpers_y_simbolos_publicos():
    tree = _tree()
    function_names = {
        node.name for node in tree.body if isinstance(node, ast.FunctionDef)
    }
    class_names = {
        node.name for node in tree.body if isinstance(node, ast.ClassDef)
    }
    assigned_names = {
        target.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    }

    assert "_leer_base_config" in function_names
    assert "_crear_mysql_database" in function_names
    assert {"ModeloBase", "ModeloBaseFASA", "BitBooleanField"} <= class_names
    assert {"db", "dbfasa"} <= assigned_names


def test_sqlite_reutiliza_dbfasa_sin_password_compartido_fuera_de_mysql():
    source = _source()
    tree = _tree()
    module_password_assignments = [
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name) and target.id == "password"
    ]
    dbfasa_mysql_assignments = [
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "dbfasa" for target in node.targets)
        and isinstance(node.value, ast.Call)
        and getattr(node.value.func, "id", "") == "MySQLDatabase"
    ]

    assert "dbfasa = db" in source
    assert module_password_assignments == []
    assert dbfasa_mysql_assignments == []


def test_creacion_mysql_valida_config_y_no_loguea_secretos():
    source = _source()

    assert "raise RuntimeError" in source
    assert "Faltan key/password" in source
    assert "desencriptar(str.encode(password_encrypted), str.encode(key))" in source

    forbidden_patterns = [
        "print(password",
        "print(key",
        "logging.info(password",
        "logging.info(key",
        "logging.error(password",
        "logging.error(key",
        "logging.warning(password",
        "logging.warning(key",
    ]

    for pattern in forbidden_patterns:
        assert pattern not in source
