ALTER TABLE `textbook_bridge` ADD `modes` text DEFAULT '["default"]' NOT NULL;--> statement-breakpoint
ALTER TABLE `textbook_jobs` ADD `retrieval_mode` text DEFAULT 'default' NOT NULL;