#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Migración: Agregar campos cc, cco y ultimo_error a emails_pendientes
Para soporte de CC/BCC y persistencia de errores
"""
import sys
import pathlib

# Añadir la raíz del proyecto al sys.path
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modelos.ModeloBase import ModeloBase


def check_column_exists(db, column_name):
    """Verifica si una columna existe en la tabla emails_pendientes"""
    cursor = db.execute_sql(
        "SELECT COUNT(*) FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() "
        "AND TABLE_NAME = 'emails_pendientes' "
        f"AND COLUMN_NAME = '{column_name}'"
    )
    return cursor.fetchone()[0] > 0


def migrate():
    db = ModeloBase().getDb()
    
    if db.is_closed():
        db.connect()
    
    try:
        # Agregar campo 'cc' si no existe
        if not check_column_exists(db, 'cc'):
            print("Agregando campo 'cc' a la tabla 'emails_pendientes'...")
            db.execute_sql(
                "ALTER TABLE emails_pendientes "
                "ADD COLUMN cc VARCHAR(500) NULL"
            )
            print("✓ Campo 'cc' agregado exitosamente")
        else:
            print("✓ El campo 'cc' ya existe")
        
        # Agregar campo 'cco' si no existe
        if not check_column_exists(db, 'cco'):
            print("Agregando campo 'cco' a la tabla 'emails_pendientes'...")
            db.execute_sql(
                "ALTER TABLE emails_pendientes "
                "ADD COLUMN cco VARCHAR(500) NULL"
            )
            print("✓ Campo 'cco' agregado exitosamente")
        else:
            print("✓ El campo 'cco' ya existe")
        
        # Agregar campo 'ultimo_error' si no existe
        if not check_column_exists(db, 'ultimo_error'):
            print("Agregando campo 'ultimo_error' a la tabla 'emails_pendientes'...")
            db.execute_sql(
                "ALTER TABLE emails_pendientes "
                "ADD COLUMN ultimo_error TEXT NULL"
            )
            print("✓ Campo 'ultimo_error' agregado exitosamente")
        else:
            print("✓ El campo 'ultimo_error' ya existe")
        
        print("\n✅ Migración completada exitosamente")
        
    except Exception as e:
        print(f"❌ Error durante la migración: {e}")
        raise
    finally:
        if not db.is_closed():
            db.close()


def rollback():
    """Revertir la migración (eliminar los campos agregados)"""
    db = ModeloBase().getDb()
    
    if db.is_closed():
        db.connect()
    
    try:
        for column in ['cc', 'cco', 'ultimo_error']:
            if check_column_exists(db, column):
                print(f"Eliminando campo '{column}'...")
                db.execute_sql(f"ALTER TABLE emails_pendientes DROP COLUMN {column}")
                print(f"✓ Campo '{column}' eliminado")
        
        print("\n✅ Rollback completado")
        
    except Exception as e:
        print(f"❌ Error durante el rollback: {e}")
        raise
    finally:
        if not db.is_closed():
            db.close()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Migración de campos cc, cco y ultimo_error')
    parser.add_argument('--rollback', action='store_true', help='Revertir la migración')
    args = parser.parse_args()
    
    if args.rollback:
        rollback()
    else:
        migrate()
