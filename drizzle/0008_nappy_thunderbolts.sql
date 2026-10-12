ALTER TABLE `textbook_bridge` ADD `screenshot_ready` integer DEFAULT 0 NOT NULL;--> statement-breakpoint
ALTER TABLE `textbook_jobs` ADD `screenshot_json` text;--> statement-breakpoint
ALTER TABLE `textbook_jobs` ADD `recognition_json` text;