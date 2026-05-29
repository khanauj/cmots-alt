-- 002_sector_confidence.sql — persist the derived SectorConfidence label
-- (HIGH / MEDIUM / LOW / UNKNOWN) on the canonical company row.
ALTER TABLE company ADD COLUMN sector_confidence TEXT;
