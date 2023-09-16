CREATE TABLE `nekogram_admins` (
  `id` bigint(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

ALTER TABLE `nekogram_admins`
  ADD PRIMARY KEY (`id`),
  ADD CONSTRAINT `nekogram_stats_ibfk_1` FOREIGN KEY (`id`) REFERENCES `nekogram_users` (`id`) ON DELETE CASCADE ON UPDATE CASCADE;
