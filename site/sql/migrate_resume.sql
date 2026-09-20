-- Resume cookie tracking (run once on existing DBs)
ALTER TABLE participants
  ADD COLUMN resume_token CHAR(64) NULL DEFAULT NULL AFTER id,
  ADD COLUMN item_index INT UNSIGNED NOT NULL DEFAULT 0 AFTER item_order_json,
  ADD COLUMN phase VARCHAR(16) NOT NULL DEFAULT 'practice' AFTER item_index,
  ADD UNIQUE KEY uq_participants_resume_token (resume_token);
