CREATE TABLE `nekogram_stats` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` bigint(20) NOT NULL,
  `interaction_date` timestamp NULL DEFAULT NULL,
  `interaction`  longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL DEFAULT '{}'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

ALTER TABLE `nekogram_stats`
  ADD PRIMARY KEY (`id`),
  ADD KEY `user_id` (`user_id`);

ALTER TABLE `nekogram_stats`
  ADD CONSTRAINT `nekogram_stats_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `nekogram_users` (`id`) ON DELETE CASCADE ON UPDATE CASCADE;
