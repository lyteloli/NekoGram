CREATE TABLE IF NOT EXISTS "nekogram_users" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT,
    "lang" VARCHAR(2) NOT NULL DEFAULT 'en',
    "data" VARCHAR NOT NULL DEFAULT '{}',
    "last_message_id" INT DEFAULT NULL,
    "full_name" VARCHAR(100) NOT NULL,
    "username" VARCHAR(100) DEFAULT NULL
);