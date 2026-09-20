SET NAMES utf8mb4;
SET time_zone = '+00:00';

CREATE TABLE IF NOT EXISTS items (
  item_id VARCHAR(64) NOT NULL PRIMARY KEY,
  stimulus_id VARCHAR(16) NOT NULL,
  user_message_en TEXT NOT NULL,
  assistant_response_en TEXT NOT NULL,
  user_message_pt TEXT NOT NULL,
  assistant_response_pt TEXT NOT NULL,
  epoch_id VARCHAR(8) NOT NULL,
  model_id VARCHAR(128) NOT NULL,
  condition_name VARCHAR(32) NOT NULL,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_items_stim (stimulus_id),
  KEY idx_items_epoch (epoch_id, condition_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS participants (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  resume_token CHAR(64) NULL DEFAULT NULL,
  lang CHAR(2) NOT NULL,
  consent TINYINT(1) NULL,
  block_a TINYINT UNSIGNED NULL,
  block_b TINYINT UNSIGNED NULL,
  item_order_json LONGTEXT NULL,
  item_index INT UNSIGNED NOT NULL DEFAULT 0,
  phase VARCHAR(16) NOT NULL DEFAULT 'practice',
  status ENUM('in_progress','completed','abandoned') NOT NULL DEFAULT 'in_progress',
  last_step VARCHAR(32) NOT NULL DEFAULT 'lang',
  attention_ok TINYINT(1) NULL,
  excluded_reason VARCHAR(64) NULL,
  started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  finished_at TIMESTAMP NULL DEFAULT NULL,
  UNIQUE KEY uq_participants_resume_token (resume_token),
  KEY idx_part_status (status),
  KEY idx_part_lang (lang)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ratings (
  participant_id INT UNSIGNED NOT NULL,
  item_id VARCHAR(64) NOT NULL,
  score TINYINT UNSIGNED NOT NULL,
  position SMALLINT UNSIGNED NOT NULL,
  answered_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (participant_id, item_id),
  CONSTRAINT fk_ratings_participant FOREIGN KEY (participant_id)
    REFERENCES participants(id) ON DELETE CASCADE,
  CONSTRAINT fk_ratings_item FOREIGN KEY (item_id)
    REFERENCES items(item_id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
