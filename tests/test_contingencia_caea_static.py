import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PTO_VTA = ROOT / "modelos" / "PtoVtaFasa.py"
MIGRATION = ROOT / "migrations" / "ensure_imprefiscal_contingencia_schema.py"


def test_ptovta_fasa_no_inventa_primary_key_para_tabla_real_sin_pk():
    source = PTO_VTA.read_text(encoding="utf-8")

    assert "primary_key = False" in source
    assert "CompositeKey" not in source
    assert "(('ptovta', 'empresa_id'), True)" in source


def test_existe_migracion_manual_para_imprefiscal_contingencia():
    source = MIGRATION.read_text(encoding="utf-8")
    tree = ast.parse(source)
    functions = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}

    assert MIGRATION.exists()
    assert {"migrate", "rollback", "check_table_exists"} <= functions
    assert "CREATE TABLE IF NOT EXISTS imprefiscal_contingencia" in source
    assert "idx_maquina_empresa_activa" in source
    assert "Rollback no implementado" in source
