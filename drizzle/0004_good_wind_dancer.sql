CREATE TABLE `textbook_pages` (
	`page` integer PRIMARY KEY NOT NULL,
	`status` text DEFAULT 'queued' NOT NULL,
	`file_key` text,
	`error` text,
	`lease` text,
	`created_at` integer NOT NULL,
	`updated_at` integer NOT NULL
);
--> statement-breakpoint
ALTER TABLE `textbook_bridge` ADD `sources_ready` integer DEFAULT 0 NOT NULL;--> statement-breakpoint
ALTER TABLE `textbook_jobs` ADD `references_json` text DEFAULT '[]' NOT NULL;