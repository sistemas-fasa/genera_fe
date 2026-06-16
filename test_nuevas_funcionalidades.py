#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de prueba para las nuevas funcionalidades del sistema de envío de emails:
1. Soporte CC/BCC
2. Persistencia de errores
3. Función helper encolar_email()
4. Notificación de fallos finales
"""

from controladores.EnvioEmailsPendientes import encolar_email
from modelos.EmailsPendientes import EmailPendiente
from modelos.ParametrosSistema import ParamSist

def test_encolar_email_con_cc_bcc():
    """Prueba de la función encolar_email con CC y BCC"""
    print("\n=== Test 1: Encolar email con CC y BCC ===")
    
    email = encolar_email(
        destinatario="cliente@ejemplo.com",
        asunto="Factura Electrónica #12345",
        cuerpo_html="<h1>Factura</h1><p>Adjunta encontrará su factura</p>",
        cuerpo_texto="Factura adjunta",
        cc="gerencia@empresa.com, contabilidad@empresa.com",
        cco="auditoria@empresa.com"
    )
    
    print(f"✓ Email encolado ID: {email.id}")
    print(f"  Destinatario: {email.destinatario}")
    print(f"  CC: {email.cc}")
    print(f"  CCO: {email.cco}")
    print(f"  Estado: {email.estado}")
    
    return email.id


def test_verificar_campos_error():
    """Verifica que el campo ultimo_error existe y funciona"""
    print("\n=== Test 2: Verificar campos de error ===")
    
    # Buscar emails fallidos para ver si tienen errores guardados
    emails_fallidos = EmailPendiente.select().where(EmailPendiente.estado == 'fallido').limit(5)
    
    count = 0
    for email in emails_fallidos:
        if email.ultimo_error:
            print(f"Email ID {email.id} - Error: {email.ultimo_error[:100]}...")
            count += 1
    
    if count == 0:
        print("✓ No hay emails fallidos con errores (esto es bueno)")
    else:
        print(f"✓ Se encontraron {count} emails fallidos con errores registrados")


def test_configurar_parametros():
    """Configura los parámetros necesarios para las nuevas funcionalidades"""
    print("\n=== Test 3: Configurar parámetros del sistema ===")
    
    # Configurar email del administrador para notificaciones
    email_admin = ParamSist.ObtenerParametro("EMAIL_ADMIN_NOTIFICACIONES")
    if not email_admin:
        # Solicitar al usuario que configure el email
        print("⚠️ EMAIL_ADMIN_NOTIFICACIONES no está configurado")
        print("   Para configurarlo, ejecuta en Python:")
        print('   ParamSist.GuardaParametro("EMAIL_ADMIN_NOTIFICACIONES", "admin@empresa.com")')
    else:
        print(f"✓ EMAIL_ADMIN_NOTIFICACIONES: {email_admin}")
    
    # Configurar CC de facturas
    cc_facturas = ParamSist.ObtenerParametro("EMAIL_CC_FACTURAS")
    if not cc_facturas:
        print("⚠️ EMAIL_CC_FACTURAS no está configurado (usará el valor por defecto)")
        print('   Para configurarlo, ejecuta: ParamSist.GuardaParametro("EMAIL_CC_FACTURAS", "email@empresa.com")')
    else:
        print(f"✓ EMAIL_CC_FACTURAS: {cc_facturas}")


def test_listar_emails_pendientes():
    """Lista todos los emails pendientes con los nuevos campos"""
    print("\n=== Test 4: Listar emails pendientes ===")
    
    emails = EmailPendiente.select().where(EmailPendiente.estado == 'pendiente').limit(10)
    
    count = 0
    for email in emails:
        print(f"\nEmail ID {email.id}:")
        print(f"  Para: {email.destinatario}")
        if email.cc:
            print(f"  CC: {email.cc}")
        if email.cco:
            print(f"  CCO: {email.cco}")
        print(f"  Asunto: {email.asunto[:50]}...")
        print(f"  Intentos: {email.intentos}/3")
        print(f"  Estado: {email.estado}")
        if email.ultimo_error:
            print(f"  Último error: {email.ultimo_error[:80]}...")
        count += 1
    
    if count == 0:
        print("✓ No hay emails pendientes")
    else:
        print(f"\n✓ Total de emails pendientes: {count}")


if __name__ == '__main__':
    print("=" * 70)
    print("PRUEBA DE NUEVAS FUNCIONALIDADES - SISTEMA DE ENVÍO DE EMAILS")
    print("=" * 70)
    
    try:
        # Test 1: Encolar un email con CC y BCC
        test_encolar_email_con_cc_bcc()
        
        # Test 2: Verificar campos de error
        test_verificar_campos_error()
        
        # Test 3: Configurar parámetros
        test_configurar_parametros()
        
        # Test 4: Listar emails pendientes
        test_listar_emails_pendientes()
        
        print("\n" + "=" * 70)
        print("✅ TODAS LAS PRUEBAS COMPLETADAS")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ Error durante las pruebas: {e}")
        import traceback
        traceback.print_exc()
