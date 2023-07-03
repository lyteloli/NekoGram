CREATE TABLE IF NOT EXISTS "nekogram_users" (
    "id" BIGINT PRIMARY KEY,
    "lang" VARCHAR(2) NOT NULL DEFAULT 'en',
    "data" JSONB NOT NULL DEFAULT '{}'::JSONB,
    "last_message_id" INT DEFAULT NULL,
    "full_name" VARCHAR(100) NOT NULL,
    "username" VARCHAR(100) DEFAULT NULL
);