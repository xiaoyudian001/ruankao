CREATE TABLE `textbook_session_deletions` (
	`session_id` text PRIMARY KEY NOT NULL,
	`owner_id` text NOT NULL,
	`deleted_at` integer NOT NULL,
	FOREIGN KEY (`session_id`) REFERENCES `textbook_sessions`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE INDEX `session_deletions_owner` ON `textbook_session_deletions` (`owner_id`);