CREATE TABLE `checkins` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`study_date` text NOT NULL,
	`content` text NOT NULL,
	`duration` integer DEFAULT 0 NOT NULL,
	`questions` integer DEFAULT 0 NOT NULL,
	`confidence` integer DEFAULT 3 NOT NULL,
	`created_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
	`updated_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL
);
--> statement-breakpoint
CREATE UNIQUE INDEX `checkins_study_date_unique` ON `checkins` (`study_date`);--> statement-breakpoint
CREATE TABLE `materials` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`file_key` text NOT NULL,
	`name` text NOT NULL,
	`kind` text DEFAULT '资料' NOT NULL,
	`content_type` text NOT NULL,
	`size` integer NOT NULL,
	`created_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL
);
--> statement-breakpoint
CREATE UNIQUE INDEX `materials_file_key_unique` ON `materials` (`file_key`);
--> statement-breakpoint
PRAGMA optimize;
