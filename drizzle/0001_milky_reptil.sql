CREATE TABLE `textbook_bridge` (
	`id` text PRIMARY KEY NOT NULL,
	`last_seen` integer NOT NULL,
	`ready` integer DEFAULT 0 NOT NULL
);
--> statement-breakpoint
CREATE TABLE `textbook_jobs` (
	`id` text PRIMARY KEY NOT NULL,
	`session_id` text NOT NULL,
	`owner_id` text NOT NULL,
	`question` text NOT NULL,
	`status` text DEFAULT 'queued' NOT NULL,
	`answer` text,
	`error` text,
	`created_at` integer NOT NULL,
	`completed_at` integer,
	`lease` text,
	`leased_at` integer,
	`elapsed_ms` integer,
	FOREIGN KEY (`session_id`) REFERENCES `textbook_sessions`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `textbook_sessions` (
	`id` text PRIMARY KEY NOT NULL,
	`owner_id` text NOT NULL,
	`title` text NOT NULL,
	`created_at` integer NOT NULL,
	`updated_at` integer NOT NULL
);
