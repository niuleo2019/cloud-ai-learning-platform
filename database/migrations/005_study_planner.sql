USE vocab_app;

-- Listening practice results (dictation / retell), used by the study-planning agent.
CREATE TABLE IF NOT EXISTS practice_attempts (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id BIGINT UNSIGNED NOT NULL,
  material_id BIGINT UNSIGNED NOT NULL,
  sentence_index INT UNSIGNED NOT NULL,
  mode VARCHAR(16) NOT NULL,
  score TINYINT UNSIGNED NOT NULL,
  expected_text VARCHAR(1000) NOT NULL,
  attempt_text VARCHAR(1000) NOT NULL,
  missed JSON NULL,
  wrong JSON NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_practice_attempts_user_time (user_id, created_at),
  CONSTRAINT fk_practice_attempts_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_practice_attempts_material_id FOREIGN KEY (material_id) REFERENCES listening_materials(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- One AI study plan per user per day.
CREATE TABLE IF NOT EXISTS study_plans (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id BIGINT UNSIGNED NOT NULL,
  plan_date DATE NOT NULL,
  summary TEXT NOT NULL,
  tasks JSON NOT NULL,
  done JSON NULL,
  model VARCHAR(80) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_study_plans_user_date (user_id, plan_date),
  CONSTRAINT fk_study_plans_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
