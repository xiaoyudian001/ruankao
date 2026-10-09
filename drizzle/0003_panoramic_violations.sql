ALTER TABLE `textbook_bridge` ADD `conversation_ready` integer DEFAULT 0 NOT NULL;--> statement-breakpoint
ALTER TABLE `textbook_jobs` ADD `history_json` text DEFAULT '[]' NOT NULL;--> statement-breakpoint
ALTER TABLE `textbook_jobs` ADD `retrieval_query` text;--> statement-breakpoint
ALTER TABLE `textbook_jobs` ADD `rewrite_route` text;