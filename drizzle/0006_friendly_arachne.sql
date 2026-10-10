CREATE TABLE `textbook_critiques` (
	`id` text PRIMARY KEY NOT NULL,
	`owner_id` text NOT NULL,
	`card_id` text NOT NULL,
	`card_version` integer NOT NULL,
	`job_id` text NOT NULL,
	`front` text NOT NULL,
	`back` text NOT NULL,
	`response` text NOT NULL,
	`references_json` text NOT NULL,
	`status` text DEFAULT 'queued' NOT NULL,
	`result_json` text,
	`error` text,
	`lease` text,
	`leased_at` integer,
	`created_at` integer NOT NULL,
	`completed_at` integer
);
--> statement-breakpoint
CREATE INDEX `critiques_owner_card` ON `textbook_critiques` (`owner_id`,`card_id`);--> statement-breakpoint
CREATE INDEX `critiques_status` ON `textbook_critiques` (`status`,`created_at`);--> statement-breakpoint
ALTER TABLE `textbook_bridge` ADD `critique_ready` integer DEFAULT 0 NOT NULL;--> statement-breakpoint
ALTER TABLE `textbook_reviews` ADD `critique_id` text;