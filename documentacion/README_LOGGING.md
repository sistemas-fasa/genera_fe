# Logging — Genera-FE

Resumen corto
- El sistema usa un logger central inicializado por la función `initialize_logger` en `libs/Utiles.py`.
- Los logs se escriben en la carpeta configurada por la clave `iniciosistema` del `sistema.ini`.

Archivos de log
- `genera-fe.log`: registro principal con nivel DEBUG; manejador rotativo con límite de 100 MB y `backupCount=5`.
- `error.log`: registro de errores con nivel ERROR; manejador rotativo (10 MB, `backupCount=5`).

Dónde se inicializa
- La inicialización se hace en el arranque de la aplicación. Ver [main.py](main.py) que llama a `initialize_logger(LeerIni("iniciosistema"))`.
- Implementación y configuración: [libs/Utiles.py](libs/Utiles.py)

Cómo usar el logger en el código
1. Importar logging y obtener un logger por módulo:

```
import logging
logger = logging.getLogger(__name__)
logger.debug("valor calculado: %s", valor)
logger.info("Operación completada para %s", cliente)
logger.error("Error procesando pedido %s: %s", pedido_id, exc)
```

Buenas prácticas
- Usa `logger.debug` para trazas detalladas (valores, estructuras). Evita imprimir datos sensibles.
- Usa `logger.info` para eventos operativos importantes (inicio/parada, acciones del usuario).
- Usa `logger.error`/`logger.exception` dentro de bloques except para capturar stack traces.

Ubicación física de logs
- La carpeta objetivo proviene de la clave `iniciosistema` en `sistema.ini`. Si la ruta no existe, el logger intentará crearla.

Rotación y retención
- `genera-fe.log` rota cuando alcanza ~100 MB; se conservan hasta 5 archivos históricos (`genera-fe.log.1`, etc.).
- `error.log` rota a ~10 MB con el mismo `backupCount=5`.

Prueba rápida
- Para forzar generación de logs y comprobar rotación, ejecuta un script que emita muchas entradas DEBUG hacia el logger global.

Contacto
- Si quieres otros ajustes (nivel por defecto distinto, archivo con nombre diferente, o rotación por tiempo), dime cómo prefieres y lo ajusto.
