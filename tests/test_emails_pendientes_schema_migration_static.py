from pathlib import Path


MIGRATION_PATH = Path("migrations/ensure_emails_pendientes_schema.py")

EXPECTED_COLUMNS = [
    "destinatario",
    "quien_envia",
    "cc",
    "cco",
    "asunto",
    "cuerpo_html",
    "cuerpo_texto",
    "adjunto_ruta",
    "adjunto_nombre",
    "intentos",
    "estado",
    "procesando_desde",
    "ultimo_error",
    "creado_en",
    "enviado_en",
    "empresa_id",
]


def test_emails_pendientes_schema_migration_contains_expected_safeguards():
    assert MIGRATION_PATH.exists()

    source = MIGRATION_PATH.read_text(encoding="utf-8")
    upper_source = source.upper()
    migrate_source = source.split("def migrate", 1)[1]

    for column in EXPECTED_COLUMNS:
        assert column in source

    assert "def migrate" in source
    assert "def check_column_exists" in source
    assert "DROP COLUMN" not in migrate_source.upper()
    assert "DELETE FROM" not in upper_source
    assert "TRUNCATE" not in upper_source
