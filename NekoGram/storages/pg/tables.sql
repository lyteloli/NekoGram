CREATE TABLE IF NOT EXISTS "nekogram_users" (
    "id" BIGINT PRIMARY KEY,
    "username" VARCHAR(100) DEFAULT NULL,
    "full_name" VARCHAR(100) NOT NULL,
    "last_message_id" INT DEFAULT NULL,
    "data" JSONB NOT NULL DEFAULT '{}'::JSONB,
    "lang" VARCHAR(2) NOT NULL DEFAULT 'en'
);