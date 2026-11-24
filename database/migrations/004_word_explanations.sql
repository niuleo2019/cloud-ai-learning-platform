USE vocab_app;

-- AI word explanations (deep etymology + letter-shape memory method), cached per word.
CREATE TABLE IF NOT EXISTS word_explanations (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  word VARCHAR(120) NOT NULL,
  content MEDIUMTEXT NOT NULL,
  model VARCHAR(80) NULL,
  truncated TINYINT(1) NOT NULL DEFAULT 0,
  input_tokens INT UNSIGNED NULL,
  output_tokens INT UNSIGNED NULL,
  created_by BIGINT UNSIGNED NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_word_explanations_word (word)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
