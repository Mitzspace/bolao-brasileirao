-- Amplia codigo_api para slugs ESPN (ex.: conmebol.libertadores). Aplicar após backup.
ALTER TABLE campeonato ALTER COLUMN codigo_api TYPE VARCHAR(40);
