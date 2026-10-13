#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Migracion: crear la bitacora de rendido de CAEA.

La migracion es no destructiva. Crea la tabla si no existe y no modifica datos
existentes de CAEA ni de comprobantes. Es idempotente: se puede correr mas de
una vez.
"""
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modelos.ModeloBase import ModeloBase


TABLE_NAME = "caea_rendicion"


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS caea_rendicion (
  id int NOT NULL AUTO_INCREMENT,
  empresa_id int NOT NULL DEFAULT 1,
  periodo char(6) NOT NULL DEFAULT '',
  orden char(1) NOT NULL DEFAULT '',
  ptovta char(4) NOT NULL DEFAULT '',
  caea char(14) NOT NULL DEFAULT '',
  estado char(1) NOT NULL DEFAULT '',
  sin_movimiento bit(1) NOT NULL DEFAULT b'0',
  comprobantes_total int NOT NULL DEFAULT 0,
  comprobantes_ok int NOT NULL DEFAULT 0,
  comprobantes_error int NOT NULL DEFAULT 0,
  fecha_inicio datetime DEFAULT NULL,
  fecha_fin datetime DEFAULT NULL,
  ultimo_error text,
  PRIMARY KEY (id),
  UNIQUE KEY idx_empresa_periodo_orden_ptovta (empresa_id, periodo, orden, ptovta)
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
        CREATE TABLE IF NOT EXISTS caea_rendicion (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          empresa_id int NOT NULL DEFAULT 1,
          periodo char(6) NOT NULL DEFAULT '',
          orden char(1) NOT NULL DEFAULT '',
          ptovta char(4) NOT NULL DEFAULT '',
          caea char(14) NOT NULL DEFAULT '',
          estado char(1) NOT NULL DEFAULT '',
          sin_movimiento int NOT NULL DEFAULT 0,
          comprobantes_total int NOT NULL DEFAULT 0,
          comprobantes_ok int NOT NULL DEFAULT 0,
          comprobantes_error int NOT NULL DEFAULT 0,
          fecha_inicio datetime DEFAULT NULL,
          fecha_fin datetime DEFAULT NULL,
          ultimo_error text
        )
        """
    )
    db.execute_sql(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_empresa_periodo_orden_ptovta "
        "ON caea_rendicion (empresa_id, periodo, orden, ptovta)"
    )


def rollback():
    raise RuntimeError(
        "Rollback no implementado: esta migracion no elimina la tabla "
        "para evitar cambios destructivos accidentales."
    )


def migrate():
    db = ModeloBase().getDb()

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