#!/usr/bin/env python
# coding=utf-8
"""
Script para limpiar emails atascados en estado de procesamiento.
Útil cuando emails quedan con procesando_desde establecido por errores inesperados.
"""

from datetime import datetime, timedelta
from modelos.EmailsPendientes import EmailPendiente
from modelos.ModeloBase import ModeloBase

def limpiar_emails_atascados():
    """Limpia emails que están en procesamiento hace más de 10 minutos"""
    db = ModeloBase().getDb()
    
    diez_minutos_atras = datetime.now() - timedelta(minutes=10)
    
    # Buscar emails pendientes con procesando_desde antiguo
    atascados = EmailPendiente.select().where(
        (EmailPendiente.estado == 'pendiente') &
        (EmailPendiente.procesando_desde.is_null(False)) &
        (EmailPendiente.procesando_desde < diez_minutos_atras)
    )
    
    count = atascados.count()
    
    if count == 0:
        print("✅ No hay emails atascados")
        return
    
    print(f"⚠️ Encontrados {count} emails atascados:")
    for email in atascados:
        print(f"  - ID {email.id}: {email.destinatario} (procesando desde {email.procesando_desde})")
    
    # Confirmar limpieza
    respuesta = input("\n¿Desea limpiar estos emails? (s/n): ")
    if respuesta.lower() != 's':
        print("❌ Operación cancelada")
        return
    
    # Limpiar procesando_desde
    EmailPendiente.update(
        procesando_desde=None
    ).where(
        (EmailPendiente.estado == 'pendiente') &
        (EmailPendiente.procesando_desde.is_null(False)) &
        (EmailPendiente.procesando_desde < diez_minutos_atras)
    ).execute()
    
    print(f"✅ {count} emails limpiados y listos para reintento")

if __name__ == "__main__":
    limpiar_emails_atascados()
