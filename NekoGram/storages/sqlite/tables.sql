CREATE TABLE IF NOT EXISTS "nekogram_users" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT,
    "username" VARCHAR(100) DEFAULT NULL,
    "full_name" VARCHAR(100) NOT NULL,
    "last_message_id" INT DEFAULT NULL,
    "data" VARCHAR NOT NULL DEFAULT '{}',
    "lang" VARCHAR(2) NOT NULL DEFAULT 'en'
);