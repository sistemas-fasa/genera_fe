#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Migracion: crear tabla de respaldo para contingencia CAEA de imprefiscal.

La migracion es no destructiva. Crea la tabla si no existe y no modifica datos
existentes de imprefiscal ni de comprobantes.
"""
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modelos.ModeloBase import ModeloBaseFASA


TABLE_NAME = "imprefiscal_contingencia"

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS imprefiscal_contingencia (
  id int NOT NULL AUTO_INCREMENT,
  maquina varchar(30) NOT NULL,
  empresa_id int NOT NULL,
  ptovtafac_original char(4) NOT NULL,
  ptovtaticket_original char(4) NOT NULL,
  ptovtafac_caea char(4) NOT NULL,
  ptovtaticket_caea char(4) NOT NULL,
  activa bit(1) NOT NULL DEFAULT b'1',
  fecha_activacion datetime NOT NULL,
  fecha_restauracion datetime DEFAULT NULL,
  motivo varchar(250) NOT NULL DEFAULT '',
  PRIMARY KEY (id),
  KEY idx_maquina_empresa_activa (maquina, empresa_id, activa)
) ENGINE=InnoDB DEFAULT CHARSET=latin1
"""


def is_sqlite(db):
    return db.__class__.__name__.lower().startswith("sqlite")


def check_table_exists(db):
    if is_sqlite(db):
        cursor = db.execute_sql(
            "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name = ?",
            (TABLE_NAME,),
        )
    else:
        cursor = db.execute_sql(
            "SELECT COUNT(*) FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s",
            (TABLE_NAME,),
        )
    return cursor.fetchone()[0] > 0


def _create_sqlite_table(db):
    db.execute_sql(
        """
        CREATE TABLE IF NOT EXISTS imprefiscal_contingencia (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          maquina varchar(30) NOT NULL,
          empresa_id int NOT NULL,
          ptovtafac_original char(4) NOT NULL,
          ptovtaticket_original char(4) NOT NULL,
          ptovtafac_caea char(4) NOT NULL,
          ptovtaticket_caea char(4) NOT NULL,
          activa int NOT NULL DEFAULT 1,
          fecha_activacion datetime NOT NULL,
          fecha_restauracion datetime DEFAULT NULL,
          motivo varchar(250) NOT NULL DEFAULT ''
        )
        """
    )
    db.execute_sql(
        "CREATE INDEX IF NOT EXISTS idx_maquina_empresa_activa "
        "ON imprefiscal_contingencia (maquina, empresa_id, activa)"
    )


def rollback():
    raise RuntimeError(
        "Rollback no implementado: esta migracion no elimina la tabla "
        "para evitar cambios destructivos accidentales."
    )


def migrate():
    db = ModeloBaseFASA().getDb()

    if db.is_closed():
        db.connect()

    try:
        if check_table_exists(db):
            print("La tabla '{}' ya existe".format(TABLE_NAME))
            return

        if is_sqlite(db):
            _create_sqlite_table(db)
        else:
            db.execute_sql(CREATE_TABLE_SQL)

        print("Tabla '{}' creada correctamente".format(TABLE_NAME))
    except Exception as exc:
        print("Error durante la migracion: {}".format(exc))
        raise
    finally:
        if not db.is_closed():
            db.close()


if __name__ == "__main__":
    migrate()
