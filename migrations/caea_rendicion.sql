-- Migracion MySQL: bitacora de rendido de CAEA
-- Equivale a migrations/ensure_caea_rendicion_schema.py (CREATE_TABLE_SQL).
-- Idempotente: se puede ejecutar mas de una vez. No toma datos existentes.
-- Ejecutar contra la base configurada en el sistema.ini de produccion.
-- Si el cliente MySQL no ya esta posicionado en la base, descomentar:
-- USE fe;

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
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

-- Verificacion: debe devolver la tabla con 14 columnas y el indice unico.
SHOW COLUMNS FROM caea_rendicion;
SHOW INDEX FROM caea_rendicion;
