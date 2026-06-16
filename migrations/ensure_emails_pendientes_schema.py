#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Migracion: asegurar columnas requeridas por el modelo EmailPendiente.

La migracion asume que la tabla emails_pendientes ya existe. No borra,
renombra ni modifica datos existentes; solo agrega columnas faltantes.
"""
import pathlib
import sys

# Añadir la raiz del proyecto al sys.path
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modelos.ModeloBase import ModeloBase


TABLE_NAME = "emails_pendientes"

REQUIRED_COLUMNS = {
    "destinatario": "VARCHAR(255) NULL",
    "quien_envia": "VARCHAR(255) NULL",
    "cc": "VARCHAR(500) NULL",
    "cco": "VARCHAR(500) NULL",
    "asunto": "VARCHAR(255) NULL",
    "cuerpo_html": "TEXT NULL",
    "cuerpo_texto": "TEXT NULL",
    "adjunto_ruta": "VARCHAR(512) NULL",
    "adjunto_nombre": "VARCHAR(255) NULL",
    "intentos": "INT NOT NULL DEFAULT 0",
    "estado": "VARCHAR(20) NOT NULL DEFAULT 'pendiente'",
    "procesando_desde": "DATETIME NULL",
    "ultimo_error": "TEXT NULL",
    "creado_en": "DATETIME NULL",
    "enviado_en": "DATETIME NULL",
    "empresa_id": "INT NOT NULL DEFAULT 1",
}


def is_sqlite(db):
    return db.__class__.__name__.lower().startswith("sqlite")


def check_table_exists(db):
    """Verifica si existe la tabla emails_pendientes."""
    if is_sqlite(db):
        cursor = db.execute_sql(
            "SELECT COUNT(*) FROM sqlite_master "
            "WHERE type = 'table' AND name = ?",
            (TABLE_NAME,),
        )
    else:
        cursor = db.execute_sql(
            "SELECT COUNT(*) FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA = DATABASE() "
            "AND TABLE_NAME = %s",
            (TABLE_NAME,),
        )
    return cursor.fetchone()[0] > 0


def check_column_exists(db, column_name):
    """Verifica si una columna existe en la tabla emails_pendientes."""
    if is_sqlite(db):
        cursor = db.execute_sql(f"PRAGMA table_info({TABLE_NAME})")
        return any(row[1] == column_name for row in cursor.fetchall())

    cursor = db.execute_sql(
        "SELECT COUNT(*) FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() "
        "AND TABLE_NAME = %s "
        "AND COLUMN_NAME = %s",
        (TABLE_NAME, column_name),
    )
    return cursor.fetchone()[0] > 0


def add_column_if_missing(db, column_name, ddl):
    if check_column_exists(db, column_name):
        print(f"El campo '{column_name}' ya existe")
        return False

    print(f"Agregando campo '{column_name}' a la tabla '{TABLE_NAME}'...")
    db.execute_sql(f"ALTER TABLE {TABLE_NAME} ADD COLUMN {column_name} {ddl}")
    print(f"Campo '{column_name}' agregado")
    return True


def rollback():
    raise RuntimeError(
        "Rollback no implementado: esta migracion no elimina columnas para "
        "evitar cambios destructivos accidentales."
    )


def migrate():
    db = ModeloBase().getDb()

    if db.is_closed():
        db.connect()

    try:
        if not check_table_exists(db):
            raise RuntimeError(
                "La tabla 'emails_pendientes' no existe. "
                "Esta migracion asume que la tabla base ya fue creada."
            )

        added_columns = []
        for column_name, ddl in REQUIRED_COLUMNS.items():
            if add_column_if_missing(db, column_name, ddl):
                added_columns.append(column_name)

        if added_columns:
            print(
                "Migracion completada. Columnas agregadas: "
                + ", ".join(added_columns)
            )
        else:
            print("Migracion completada. No habia columnas faltantes.")

    except Exception as exc:
        print(f"Error durante la migracion: {exc}")
        raise
    finally:
        if not db.is_closed():
            db.close()


if __name__ == "__main__":
    migrate()
