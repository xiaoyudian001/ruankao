ALTER TABLE `textbook_jobs` ADD `partial_answer` text DEFAULT '' NOT NULL;--> statement-breakpoint
ALTER TABLE `textbook_jobs` ADD `partial_seq` integer DEFAULT 0 NOT NULL;--> statement-breakpoint
ALTER TABLE `textbook_jobs` ADD `cancel_requested` integer DEFAULT 0 NOT NULL;