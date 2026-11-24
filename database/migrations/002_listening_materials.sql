USE vocab_app;

CREATE TABLE IF NOT EXISTS listening_materials (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id BIGINT UNSIGNED NOT NULL,
  title VARCHAR(200) NOT NULL,
  audio_file VARCHAR(255) NOT NULL,
  original_filename VARCHAR(255) NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'processing',
  error_message VARCHAR(500) NULL,
  duration_seconds DECIMAL(8, 2) NULL,
  sentences JSON NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_listening_materials_user (user_id, created_at),
  CONSTRAINT fk_listening_materials_user_id
    FOREIGN KEY (user_id) REFERENCES users(id)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
