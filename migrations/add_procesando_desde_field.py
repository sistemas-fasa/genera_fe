#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Migración: Agregar campo procesando_desde a emails_pendientes
Para prevenir envíos duplicados por condición de carrera
"""
import sys
import pathlib

# Añadir la raíz del proyecto al sys.path
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modelos.ModeloBase import ModeloBase
from peewee import DateTimeField

def migrate():
    db = ModeloBase().getDb()
    
    if db.is_closed():
        db.connect()
    
    try:
        # Verificar si la columna ya existe
        cursor = db.execute_sql(
            "SELECT COUNT(*) FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() "
            "AND TABLE_NAME = 'emails_pendientes' "
            "AND COLUMN_NAME = 'procesando_desde'"
        )
        exists = cursor.fetchone()[0] > 0
        
        if exists:
            print("✓ El campo 'procesando_desde' ya existe en la tabla 'emails_pendientes'")
            return
        
        # Agregar la columna
        print("Agregando campo 'procesando_desde' a la tabla 'emails_pendientes'...")
        db.execute_sql(
            "ALTER TABLE emails_pendientes "
            "ADD COLUMN procesando_desde DATETIME NULL"
        )
        print("✓ Campo agregado exitosamente")
        
        # Opcional: crear índice para mejorar rendimiento
        print("Creando índice para procesando_desde...")
        db.execute_sql(
            "CREATE INDEX idx_emails_procesando ON emails_pendientes(procesando_desde)"
        )
        print("✓ Índice creado exitosamente")
        
    except Exception as e:
        print(f"✗ Error durante la migración: {e}")
        raise
    finally:
        if not db.is_closed():
            db.close()

if __name__ == '__main__':
    migrate()
